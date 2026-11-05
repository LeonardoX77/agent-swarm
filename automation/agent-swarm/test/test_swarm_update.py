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

SCRIPT = Path(__file__).parents[1] / "bin" / "swarm-update"


def load_module():
    spec = importlib.util.spec_from_loader("swarm_update", SourceFileLoader("swarm_update", str(SCRIPT)))
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


class SwarmUpdateTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        platform = patch.object(self.mod.sys, "platform", "darwin")
        platform.start()
        self.addCleanup(platform.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def tool(self, replies=None, clock=lambda: 1000000):
        return self.mod.SwarmUpdate(Runner(replies), self.home, 501, clock=clock, environ={"PATH": "/test/bin"})

    def test_check_discovers_nvm_path_without_config_and_verbose_prints_it(self):
        nvm_bin = self.home / ".nvm/versions/node/v20.1.0/bin"
        nvm_bin.mkdir(parents=True)
        (self.home / ".nvm/alias").mkdir()
        (self.home / ".nvm/alias/default").write_text("v20.1.0\n")
        runner = Runner({("pi", "--version"): (0, "1.2.3\n", "")})
        output = io.StringIO()
        with patch.object(self.mod.Path, "home", return_value=self.home), \
             patch.object(self.mod.SwarmUpdate, "_subprocess_runner", staticmethod(runner)), \
             patch.object(sys, "argv", [str(SCRIPT), "--verbose", "check"]), \
             contextlib.redirect_stdout(output):
            self.assertEqual(self.mod.main(), 0)
        self.assertIn(str(nvm_bin), runner.environments[-1]["PATH"])
        self.assertIn("PATH=", output.getvalue())
        self.assertIn(str(nvm_bin), output.getvalue())

    def test_pi_installer_path_discovered_by_check_and_install(self):
        for platform in ("darwin", "linux"):
            with self.subTest(platform=platform), patch.object(self.mod.sys, "platform", platform):
                self.home = Path(self.temp.name) / platform
                self.home.mkdir()
                for suffix in (".local/bin", ".pi/agent/bin"):
                    (self.home / suffix).mkdir(parents=True, exist_ok=True)
                runner = Runner()
                code, response = self.mod.run(["check"], runner=runner, home=self.home, uid=501)
                self.assertEqual(code, 0, response)
                expected = str(self.home / ".local/bin") + ":" + str(self.home / ".pi/agent/bin")
                self.assertIn(expected, response["path_used"])
                self.assertTrue(all(expected in env["PATH"] for env in runner.environments))
                tool = self.mod.SwarmUpdate(runner, self.home, 501)
                tool.install(components=["pi"])
                self.assertEqual(tool.read_config()["path"], response["path_used"])
                # Explicit configured PATH remains authoritative on both platforms.
                tool.install(components=["pi"], path="/custom/bin:/usr/bin")
                self.assertEqual(tool.status()["config"]["path"], "/custom/bin:/usr/bin")

    def test_default_runner_runs_real_subprocess_once(self):
        result = self.mod.SwarmUpdate._subprocess_runner(["/usr/bin/true"])
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

    def test_gentle_ai_is_a_brew_component(self):
        payload = json.dumps({"formulae": [{"name": "gentle-ai", "installed_versions": ["4.0.0"], "current_version": "4.3.1"}]})
        tool = self.tool({("brew", "list", "--versions", "gentle-ai"): (0, "gentle-ai 4.0.0\n", ""),
                          ("brew", "outdated", "--json=v2", "gentle-ai"): (0, payload, "")})
        self.assertIn("gentle-ai", self.mod.COMPONENTS)
        item = tool.component("gentle-ai").check()
        self.assertEqual((item["current"], item["available"], item["outdated"]), ("4.0.0", "4.3.1", True))
        self.assertEqual(tool.component("gentle-ai").update()["status"], "updated")
        self.assertIn(["brew", "upgrade", "gentle-ai"], tool.runner.calls)

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
        tool = self.mod.SwarmUpdate(runner, self.home, 501, environ={"PATH": "/test/bin"})
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


class LinuxSwarmUpdateTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        platform = patch.object(self.mod.sys, "platform", "linux")
        platform.start()
        self.addCleanup(platform.stop)
        temp = tempfile.TemporaryDirectory(prefix="swarm-update-test-")
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name) / "home with spaces"
        self.home.mkdir()
        self.runner = Runner()

    def run_cli(self, *args):
        return self.mod.run(list(args), runner=self.runner, home=self.home, uid=1000,
                            environ={"PATH": "/test/bin"}, clock=lambda: 1000000)

    def test_install_units_status_and_uninstall(self):
        node = self.home / ".nvm/versions/node/v22.0.0/bin"
        node.mkdir(parents=True)
        code, installed = self.run_cli("install", "--hour", "6", "--minute", "7",
                                        "--components", "pi,pi-extensions")
        self.assertEqual(code, 0, installed)
        self.assertTrue(installed["installed"])
        units = self.home / ".config/systemd/user"
        service = units / "agent-swarm-update.service"
        timer = units / "agent-swarm-update.timer"
        tool = self.mod.SwarmUpdate(self.runner, self.home, 1000)
        path = tool.read_config()["path"]
        self.assertIn(str(node), path)
        self.assertEqual(service.read_text(),
            '[Unit]\nDescription=Agent Swarm updates\n\n[Service]\nType=oneshot\n'
            'ExecStart=/usr/bin/env python3 "' + str(tool.local_script_path()) + '" run\n'
            'Environment="PATH=' + path + '"\n')
        self.assertEqual(timer.read_text(),
            '[Unit]\nDescription=Schedule Agent Swarm updates\n\n[Timer]\n'
            'OnCalendar=*-*-* 06:07:00\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n')
        self.assertEqual(tool.local_script_path().read_bytes(), SCRIPT.read_bytes())
        self.assertIn(["systemctl", "--user", "daemon-reload"], self.runner.calls)
        self.assertIn(["systemctl", "--user", "enable", "--now", timer.name], self.runner.calls)
        self.runner.replies[("systemctl", "--user", "is-enabled", timer.name)] = (1, "disabled\n", "")
        code, status = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertTrue(status["loaded"], "An active timer is loaded even if not enabled")
        self.assertEqual(status["config"], tool.read_config())
        self.assertIsNone(status["last_run"])
        self.runner.replies[("systemctl", "--user", "is-active", timer.name)] = (3, "inactive\n", "")
        self.assertFalse(self.run_cli("status")[1]["loaded"])
        code, result = self.run_cli("uninstall")
        self.assertEqual(code, 0)
        self.assertTrue(result["uninstalled"])
        self.assertFalse(service.exists())
        self.assertFalse(timer.exists())
        self.assertIn(["systemctl", "--user", "disable", "--now", timer.name], self.runner.calls)
        self.assertEqual(self.runner.calls[-1], ["systemctl", "--user", "daemon-reload"])

    def test_systemd_unavailable_does_not_install(self):
        self.runner.replies["systemctl"] = (1, "", "Failed to connect to bus")
        code, response = self.run_cli("install")
        self.assertEqual((code, response), (2, {"error": "systemctl --user is unavailable: Failed to connect to bus"}))
        self.assertEqual(list(self.home.iterdir()), [])

    def test_enable_failure_is_not_success(self):
        self.runner.replies[("systemctl", "--user", "enable", "--now", "agent-swarm-update.timer")] = (1, "", "denied")
        code, response = self.run_cli("install", "--path", "/custom/bin")
        self.assertEqual((code, response), (2, {"error": "Could not enable systemd update timer: denied"}))

    def test_linux_component_matrix_and_run_log(self):
        self.runner.replies[("herdr", "--version")] = (0, "0.9.4\n", "")
        code, checked = self.run_cli("check", "--refresh")
        self.assertEqual(code, 0)
        items = {item["name"]: item for item in checked["components"]}
        self.assertEqual(items["herdr"], {"name": "herdr", "status": "installed", "current": "0.9.4", "outdated": True, "source": "standalone"})
        self.assertEqual(items["mosh"], {"name": "mosh", "status": "skipped", "reason": "managed by the system package manager"})
        self.assertEqual(items["moshi-hook"]["source"], "standalone")
        self.assertEqual(self.run_cli("install", "--path", "/custom/bin")[0], 0)
        code, result = self.run_cli("run")
        self.assertEqual(code, 0, result)
        for command in (["herdr", "update"], ["moshi-hook", "update"],
                        ["pi", "update", "--self"], ["pi", "update", "--extensions"]):
            self.assertIn(command, self.runner.calls)
        self.assertFalse(any(call[0] in ("brew", "sudo", "/bin/launchctl") for call in self.runner.calls))
        self.assertNotIn(["herdr", "server", "restart"], self.runner.calls)
        log = self.home / ".local/state/agent-swarm/logs/swarm-update.log"
        self.assertIn('"commands"', log.read_text())
        code, status = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertEqual(status["last_run"], {"finished_at": 1000000, "result": "ok"})

    def test_missing_herdr_is_skipped_and_pi_failure_preserves_stamp(self):
        self.runner.replies["herdr"] = (127, "", "not found")
        self.runner.replies[("pi", "update", "--self")] = (1, "", "failed")
        self.assertEqual(self.run_cli("install")[0], 0)
        code, result = self.run_cli("run")
        self.assertEqual(code, 1)
        self.assertEqual(result["components"][0], {"name": "herdr", "status": "skipped", "reason": "not installed"})
        self.assertNotIn(["herdr", "update"], self.runner.calls)
        self.assertIn(["pi", "update", "--extensions"], self.runner.calls)
        self.assertIsNone(self.run_cli("status")[1]["last_run"])


if __name__ == "__main__":
    unittest.main()
