import contextlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import plistlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1] / "bin" / "fabric-update"


def load_module():
    spec = importlib.util.spec_from_loader("fabric_update", SourceFileLoader("fabric_update", str(SCRIPT)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Runner:
    def __init__(self, replies=None):
        self.replies = replies or {}
        self.calls = []
        self.environments = []

    def __call__(self, argv, timeout=30, env=None):
        self.calls.append(argv)
        self.environments.append(dict(env) if env is not None else None)
        reply = self.replies.get(tuple(argv), self.replies.get(argv[0], (0, "", "")))
        if callable(reply):
            reply = reply(argv)
        return SimpleNamespace(returncode=reply[0], stdout=reply[1], stderr=reply[2])


class FabricUpdateTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def tool(self, replies=None, clock=lambda: 1000000):
        return self.mod.FabricUpdate(Runner(replies), self.home, 501, clock=clock, environ={"PATH": "/test/bin"})

    def test_check_discovers_nvm_path_without_config_and_verbose_prints_it(self):
        nvm_bin = self.home / ".nvm/versions/node/v20.1.0/bin"
        nvm_bin.mkdir(parents=True)
        (self.home / ".nvm/alias").mkdir()
        (self.home / ".nvm/alias/default").write_text("v20.1.0\n")
        runner = Runner({("pi", "--version"): (0, "1.2.3\n", "")})
        output = io.StringIO()
        with patch.object(self.mod.Path, "home", return_value=self.home), \
             patch.object(self.mod.FabricUpdate, "_subprocess_runner", staticmethod(runner)), \
             patch.object(sys, "argv", [str(SCRIPT), "--verbose", "check"]), \
             contextlib.redirect_stdout(output):
            self.assertEqual(self.mod.main(), 0)
        self.assertIn(str(nvm_bin), runner.environments[-1]["PATH"])
        self.assertIn("PATH=", output.getvalue())
        self.assertIn(str(nvm_bin), output.getvalue())

    def test_default_runner_runs_real_subprocess_once(self):
        result = self.mod.FabricUpdate._subprocess_runner(["/usr/bin/true"])
        self.assertEqual(result.returncode, 0)

    def test_update_help_uses_real_subprocess(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)

    def test_component_detection_and_skip(self):
        tool = self.tool({"brew": (1, "", "missing"), "moshi-hook": (1, "", ""), "pi": (1, "", "")})
        results = tool.check(["herdr", "mosh", "moshi-hook", "pi", "pi-extensions"])
        self.assertTrue(all(item["status"] == "skipped" for item in results))
        self.assertIn("not installed", results[0]["reason"])

    def test_brew_outdated_json(self):
        payload = json.dumps({"formulae": [{"name": "herdr", "installed_versions": ["0.9.3"], "current_version": "0.9.4"}]})
        tool = self.tool({("brew", "list", "--versions", "herdr"): (0, "herdr 0.9.3\n", ""),
                          ("brew", "outdated", "--json=v2", "herdr"): (0, payload, "")})
        item = tool.component("herdr").check()
        self.assertTrue(item["outdated"])
        self.assertEqual(item["current"], "0.9.3")
        self.assertEqual(item["available"], "0.9.4")

    def test_moshi_brew_precedes_standalone(self):
        tool = self.tool({("brew", "list", "--versions", "moshi-hook"): (0, "moshi-hook 1.0\n", "")})
        self.assertEqual(tool.component("moshi-hook").source(), "brew")

    def test_pi_update_commands(self):
        tool = self.tool({("pi", "--version"): (0, "1.0\n", ""), ("pi", "update", "--self"): (0, "", ""), ("pi", "update", "--extensions"): (0, "", "")})
        tool.component("pi").update()
        tool.component("pi-extensions").update()
        self.assertIn(["pi", "update", "--self"], tool.runner.calls)
        self.assertIn(["pi", "update", "--extensions"], tool.runner.calls)

    def test_herdr_update_never_restarts_server(self):
        tool = self.tool({("brew", "upgrade", "herdr"): (0, "", ""), ("herdr", "--version"): (0, "0.9.4\n", "")})
        item = tool.component("herdr").update()
        self.assertTrue(item["server_restart_pending"])
        self.assertNotIn(["herdr", "server", "restart"], tool.runner.calls)

    def test_throttle_force_and_failures_continue(self):
        config = self.mod.DEFAULT_CONFIG.copy()
        config["path"] = "/test/bin"
        tool = self.tool({("pi", "--version"): (0, "1\n", ""), ("pi", "update", "--self"): (1, "", "bad"),
                          ("pi", "update", "--extensions"): (0, "", "")})
        tool.write_config(config)
        tool.write_stamp({"finished_at": 999999})
        response = tool.run_update(force=False)
        self.assertTrue(response["throttled"])
        response = tool.run_update(force=True)
        self.assertEqual(response["exit_code"], 1)
        self.assertIn(["pi", "update", "--extensions"], tool.runner.calls)

    def test_install_uninstall_and_exact_plist(self):
        runner = Runner({"/bin/launchctl": (0, "", "")})
        tool = self.mod.FabricUpdate(runner, self.home, 501, environ={"PATH": "/test/bin"})
        tool.install(4, 30, ["pi"], "/test/bin")
        data = plistlib.loads(tool.plist_path().read_bytes())
        self.assertEqual(data["StartCalendarInterval"], {"Hour": 4, "Minute": 30})
        self.assertEqual(data["ProgramArguments"], ["/usr/bin/python3", str(tool.local_script_path()), "run"])
        self.assertIn(["/bin/launchctl", "bootstrap", "gui/501", str(tool.plist_path())], runner.calls)
        tool.uninstall()
        self.assertFalse(tool.plist_path().exists())

    def test_invalid_config_root_verbose_and_json(self):
        tool = self.tool()
        tool.config_path().parent.mkdir(parents=True)
        tool.config_path().write_text('{"enabled": "yes"}')
        with self.assertRaises(self.mod.ToolError):
            tool.read_config()
        self.assertEqual(self.mod.run(["check"], runner=Runner(), home=self.home, uid=0)[0], 2)
        code, response = self.mod.run(["check", "--json"], runner=Runner(), home=self.home, uid=501)
        self.assertEqual(code, 0)
        self.assertIn("components", response)


if __name__ == "__main__":
    unittest.main()
