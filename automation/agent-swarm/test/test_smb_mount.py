import importlib.machinery
import importlib.util
import json
import os
import plistlib
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "swarm-smb-mount"

loader = importlib.machinery.SourceFileLoader("swarm_smb_mount", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
mount_tool = importlib.util.module_from_spec(spec)
loader.exec_module(mount_tool)

MOUNTED = "//leo@MacBookLeo.local/agent-projects on /Volumes/agent-projects (smbfs, nodev, nosuid, mounted by leo)\n"


class Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class Runner:
    def __init__(self, results=()):
        self.results = list(results)
        self.calls = []

    def __call__(self, argv, timeout):
        self.calls.append((argv, timeout))
        if self.results:
            result = self.results.pop(0)
            if callable(result):
                return result(argv, timeout)
            return result
        return Result()


class SMBMountTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.home = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def tool(self, results=(), sleep=None, env=None):
        self.runner = Runner(results)
        return mount_tool.SMBMount(self.runner, self.home, 501, sleep or (lambda _: None), env=env)

    def test_status_parses_realistic_matching_mount(self):
        result = self.tool([Result(stdout=MOUNTED)]).status("MacBookLeo.local", "agent-projects", "leo")
        self.assertEqual({"ok": True, "mounted": True, "mount_point": "/Volumes/agent-projects"}, result)

    def test_status_requires_exact_host_and_source(self):
        output = MOUNTED.replace("MacBookLeo.local", "MacBookLeo")
        result = self.tool([Result(stdout=output)]).status("MacBookLeo.local", "agent-projects", "leo")
        self.assertEqual({"ok": True, "mounted": False}, result)

    def test_mount_is_idempotent(self):
        result = self.tool([Result(stdout=MOUNTED)]).mount("MacBookLeo.local", "agent-projects", "leo", False, 3)
        self.assertEqual("already_mounted", result["via"])
        self.assertEqual([], self.runner.calls[1:])

    def test_mount_uses_exact_osascript_argv(self):
        tool = self.tool([Result(stdout=""), Result(), Result(stdout=MOUNTED)])
        result = tool.mount("MacBookLeo.local", "agent-projects", "leo", False, 3)
        self.assertEqual("osascript", result["via"])
        self.assertEqual(
            ["/usr/bin/osascript", "-e", 'mount volume "smb://leo@MacBookLeo.local/agent-projects"'],
            self.runner.calls[1][0],
        )

    def test_mount_warns_for_disambiguated_volume_path(self):
        output = MOUNTED.replace("/Volumes/agent-projects", "/Volumes/agent-projects-1")
        result = self.tool([Result(stdout=""), Result(), Result(stdout=output)]).mount("MacBookLeo.local", "agent-projects", "leo", False, 3)
        self.assertEqual("/Volumes/agent-projects-1", result["mount_point"])
        self.assertEqual("/Volumes/agent-projects-1", result["unexpected_mount_point"])

    def test_persistent_no_gui_installs_then_kickstarts_and_polls(self):
        tool = self.tool([Result(1), Result(), Result(stdout=""), Result(1, stderr="no GUI session"), Result(), Result(), Result(stdout=MOUNTED)])
        result = tool.mount("MacBookLeo.local", "agent-projects", "leo", True, 3)
        local = self.home / ".local/agent-swarm/bin/swarm-smb-mount"
        plist_path = Path(result["plist"])
        self.assertEqual("launchagent", result["via"])
        self.assertTrue(local.exists())
        self.assertEqual(0o755, local.stat().st_mode & 0o777)
        self.assertTrue(plist_path.exists())
        plist = plistlib.loads(plist_path.read_bytes())
        self.assertEqual(
            ["/usr/bin/python3", str(local), "mount", "--host", "MacBookLeo.local", "--share", "agent-projects", "--user", "leo"],
            plist["ProgramArguments"],
        )
        self.assertTrue(plist["RunAtLoad"])
        self.assertEqual(300, plist["StartInterval"])
        self.assertEqual(["/bin/launchctl", "bootout", "gui/501/" + result["label"]], self.runner.calls[0][0])
        self.assertEqual(["/bin/launchctl", "bootstrap", "gui/501", str(plist_path)], self.runner.calls[1][0])
        self.assertEqual(["/bin/launchctl", "kickstart", "-k", "gui/501/" + result["label"]], self.runner.calls[5][0])

    def test_persistent_osascript_success_installs_agent_first(self):
        tool = self.tool([Result(1), Result(), Result(stdout=""), Result(), Result(stdout=MOUNTED)])
        result = tool.mount("MacBookLeo.local", "agent-projects", "leo", True, 3)
        self.assertEqual("osascript", result["via"])
        self.assertEqual("/bin/launchctl", self.runner.calls[0][0][0])
        self.assertEqual("/bin/launchctl", self.runner.calls[1][0][0])
        self.assertEqual("/usr/bin/osascript", self.runner.calls[3][0][0])

    def test_persistent_already_mounted_installs_agent_without_osascript(self):
        tool = self.tool([Result(1), Result(), Result(stdout=MOUNTED)])
        result = tool.mount("MacBookLeo.local", "agent-projects", "leo", True, 3)
        self.assertEqual("already_mounted", result["via"])
        self.assertFalse(any(call[0][0] == "/usr/bin/osascript" for call in self.runner.calls))

    def test_ssh_non_gui_exit_uses_persistent_agent_even_without_known_text(self):
        tool = self.tool([Result(1), Result(), Result(stdout=""), Result(1, stderr="unexpected failure"), Result(), Result(), Result(stdout=MOUNTED)], env={"SSH_CONNECTION": "10.0.0.2 22 10.0.0.1 22"})
        result = tool.mount("MacBookLeo.local", "agent-projects", "leo", True, 3)
        self.assertEqual("launchagent", result["via"])
        self.assertEqual("kickstart", self.runner.calls[5][0][1])

    def test_no_persistent_agent_and_no_gui_requires_gui_session(self):
        tool = self.tool([Result(stdout=""), Result(1, stderr="no GUI session"), Result(1)])
        with self.assertRaises(mount_tool.ToolError) as caught:
            tool.mount("MacBookLeo.local", "agent-projects", "leo", False, 2)
        self.assertEqual("gui_session_required", caught.exception.code)

    def test_gui_failure_uses_loaded_agent_and_polls(self):
        tool = self.tool([
            Result(stdout=""),
            Result(1, stderr="no GUI session"),
            Result(),
            Result(),
            Result(stdout=""),
            Result(stdout=MOUNTED),
        ])
        result = tool.mount("MacBookLeo.local", "agent-projects", "leo", False, 2)
        self.assertEqual("launchagent", result["via"])
        self.assertEqual(["/bin/launchctl", "kickstart", "-k", "gui/501/" + mount_tool.agent_label("MacBookLeo.local", "agent-projects")], self.runner.calls[3][0])

    def test_gui_fallback_timeout_is_typed_failure(self):
        tool = self.tool([Result(stdout=""), Result(1, stderr="no GUI session"), Result(), Result(), Result(stdout=""), Result(stdout="")])
        with self.assertRaises(mount_tool.ToolError) as caught:
            tool.mount("MacBookLeo.local", "agent-projects", "leo", False, 1)
        self.assertEqual("mount_timeout", caught.exception.code)

    def test_unmount_only_matching_source(self):
        other = "//leo@MacMiniLeo.local/agent-projects on /Volumes/other (smbfs, nodev)\n"
        result = self.tool([Result(stdout=other + MOUNTED), Result()]).unmount("MacBookLeo.local", "agent-projects", "leo", False)
        self.assertTrue(result["unmounted"])
        self.assertEqual(["/usr/sbin/diskutil", "unmount", "/Volumes/agent-projects"], self.runner.calls[1][0])

    def test_remove_persistent_boots_out_and_removes_only_plist(self):
        tool = self.tool([Result(stdout=""), Result(1)])
        plist_path = tool.plist_path("MacBookLeo.local", "agent-projects")
        plist_path.parent.mkdir(parents=True)
        plist_path.write_text("test")
        result = tool.unmount("MacBookLeo.local", "agent-projects", "leo", True)
        self.assertFalse(result["mounted"])
        self.assertTrue(result["persistent_removed"])
        self.assertFalse(plist_path.exists())
        self.assertEqual(["/bin/launchctl", "bootout", "gui/501/" + mount_tool.agent_label("MacBookLeo.local", "agent-projects")], self.runner.calls[1][0])

    def test_invalid_values_are_rejected(self):
        for argv in (["status", "--host", "bad host", "--share", "x"], ["status", "--host", "host", "--share", "bad/share"], ["status", "--host", "host", "--share", "x", "--user", "bad@user"], ["mount", "--host", "host", "--share", "x", "--wait", "0"]):
            code, output = mount_tool.run(argv, runner=Runner(), home=self.home, uid=501)
            self.assertEqual(2, code)
            self.assertFalse(output["ok"])
            self.assertEqual("invalid_arguments", output["error"])

    def test_no_password_option_and_no_traceback_on_unexpected_error(self):
        code, output = mount_tool.run(["status", "--host", "host", "--share", "x", "--password", "secret"], runner=Runner(), home=self.home, uid=501)
        self.assertEqual(2, code)
        self.assertEqual("invalid_arguments", output["error"])
        code, output = mount_tool.run(["status", "--host", "host", "--share", "x"], runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")), home=self.home, uid=501)
        self.assertEqual(2, code)
        self.assertEqual("unexpected_error", output["error"])
        self.assertNotIn("Traceback", json.dumps(output))


if __name__ == "__main__":
    unittest.main()
