import importlib.machinery
import importlib.util
import json
import os
import plistlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    @patch.object(mount_tool.sys, "platform", "darwin")
    def test_invalid_values_are_rejected(self):
        for argv in (["status", "--host", "bad host", "--share", "x"], ["status", "--host", "host", "--share", "bad/share"], ["status", "--host", "host", "--share", "x", "--user", "bad@user"], ["mount", "--host", "host", "--share", "x", "--wait", "0"]):
            with self.subTest(argv=argv):
                runner = Runner()
                code, output = mount_tool.run(argv, runner=runner, home=self.home, uid=501)
                self.assertEqual(2, code)
                self.assertFalse(output["ok"])
                self.assertEqual("invalid_arguments", output["error"])
                self.assertEqual([], runner.calls)
                self.assertEqual([], list(self.home.iterdir()))

    @patch.object(mount_tool.sys, "platform", "darwin")
    def test_no_password_option_and_no_traceback_on_unexpected_error(self):
        code, output = mount_tool.run(["status", "--host", "host", "--share", "x", "--password", "secret"], runner=Runner(), home=self.home, uid=501)
        self.assertEqual(2, code)
        self.assertEqual("invalid_arguments", output["error"])
        code, output = mount_tool.run(["status", "--host", "host", "--share", "x"], runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")), home=self.home, uid=501)
        self.assertEqual(2, code)
        self.assertEqual("unexpected_error", output["error"])
        self.assertNotIn("Traceback", json.dumps(output))

    @patch.object(mount_tool.sys, "platform", "freebsd")
    def test_other_platform_returns_unsupported_platform_without_side_effects(self):
        for command in ("status", "mount", "unmount"):
            with self.subTest(command=command):
                runner = Runner()
                code, output = mount_tool.run([command, "--host", "host", "--share", "x"], runner=runner, home=self.home, uid=501)
                self.assertEqual(2, code)
                self.assertEqual({"ok": False, "error": "unsupported_platform", "message": "swarm-smb-mount only supports macOS or Linux"}, output)
                self.assertEqual([], runner.calls)
                self.assertEqual([], list(self.home.iterdir()))


@patch.object(mount_tool.sys, "platform", "linux")
class LinuxMountTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        self.mounted = "//HOST/projects /mnt/projects\n"
        self.fstab = "//host/projects /mnt/projects user,noauto,credentials=/home/leo/.config/agent-swarm/smb-credentials\n"

    def run_tool(self, command, results=(), *options):
        self.runner = Runner(results)
        return mount_tool.run([command, "--host", "host", "--share", "projects", "--user", "leo", *options], runner=self.runner, home=self.home, uid=501)

    def test_status_matches_host_case_insensitively_but_exact_share(self):
        for source, mounted in ((self.mounted, True), ("//host/projects-other /mnt/other\n", False), ("//other/projects /mnt/projects\n", False)):
            with self.subTest(source=source):
                code, response = self.run_tool("status", [Result(stdout=source)])
                self.assertEqual(code, 0)
                self.assertEqual(response, {"ok": True, "mounted": mounted, **({"mount_point": "/mnt/projects"} if mounted else {})})
                self.assertEqual(self.runner.calls, [(["findmnt", "-rn", "-t", "cifs", "-o", "SOURCE,TARGET"], 30)])

    def test_mount_requires_user_fstab_entry_without_writes(self):
        for entry in ("", self.fstab.replace("user,noauto", "defaults"), self.fstab.replace("/mnt/projects", "/elsewhere"), self.fstab.replace("//host/", "//other/")):
            with self.subTest(entry=entry):
                code, response = self.run_tool("mount", [Result(), Result(stdout=entry)], "--persistent")
                self.assertEqual(code, 2)
                self.assertEqual(response["error"], "fstab_entry_required")
                self.assertIn("fstab-line", response["message"])
                self.assertEqual(list(self.home.iterdir()), [])
                self.assertEqual(len(self.runner.calls), 2)

    def test_mount_and_unmount_use_plain_commands(self):
        code, response = self.run_tool("mount", [Result(), Result(stdout=self.fstab), Result(), Result(stdout=self.mounted)])
        self.assertEqual((code, response), (0, {"ok": True, "mounted": True, "mount_point": "/mnt/projects", "via": "mount"}))
        self.assertEqual(self.runner.calls[2][0], ["mount", "/mnt/projects"])
        code, response = self.run_tool("unmount", [Result(stdout=self.mounted), Result()])
        self.assertEqual((code, response), (0, {"ok": True, "mounted": True, "unmounted": True}))
        self.assertEqual(self.runner.calls[1][0], ["umount", "/mnt/projects"])

    def test_already_mounted_is_idempotent(self):
        code, response = self.run_tool("mount", [Result(stdout=self.mounted)])
        self.assertEqual((code, response["via"]), (0, "already_mounted"))
        self.assertEqual(len(self.runner.calls), 1)

    def test_fstab_line_has_caller_ids_and_human_credentials_template(self):
        with patch.object(mount_tool.os, "getgid", return_value=502):
            code, response = self.run_tool("fstab-line")
        self.assertEqual(code, 0)
        self.assertEqual(response["fstab_line"], "//host/projects /mnt/projects cifs credentials=%s/.config/agent-swarm/smb-credentials,uid=501,gid=502,vers=3.0,noauto,user,_netdev 0 0" % self.home.resolve())
        self.assertEqual(response["credentials_template"], "username=leo\npassword=<your SMB password>\n")
        self.assertEqual(response["credentials_mode"], "0600")
        self.assertEqual(self.runner.calls, [])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_persistence_installs_timer_and_removal_disables_it(self):
        code, response = self.run_tool("mount", [Result(stdout=self.mounted), Result(), Result(), Result()], "--persistent")
        self.assertEqual(code, 0)
        self.assertTrue(response["persistent"])
        timer = Path(response["timer"])
        service = timer.with_suffix(".service")
        self.assertIn("OnBootSec=1s", timer.read_text())
        self.assertIn("OnUnitActiveSec=300s", timer.read_text())
        self.assertIn("mount --host host --share projects --user leo", service.read_text())
        self.assertTrue((self.home / ".local/state/agent-swarm/logs").is_dir())
        self.assertEqual(self.runner.calls[-1][0], ["systemctl", "--user", "enable", "--now", timer.name])
        code, response = self.run_tool("unmount", [Result(), Result(), Result()], "--remove-persistent")
        self.assertEqual((code, response["persistent_removed"]), (0, True))
        self.assertFalse(timer.exists())
        self.assertFalse(service.exists())
        self.assertIn((["systemctl", "--user", "disable", "--now", timer.name], 30), self.runner.calls)

    def test_generated_units_have_separate_executable_argument_and_log_escaping(self):
        for suffix in ("normal", "space % $ home"):
            with self.subTest(home=suffix):
                self.home = Path(self.directory.name) / suffix
                code, response = self.run_tool("mount", [Result(stdout=self.mounted)], "--persistent")
                self.assertEqual(code, 0)
                service = Path(response["service"])
                text = service.read_text()
                executable = str(self.home / ".local/agent-swarm/bin/swarm-smb-mount").replace("%", "%%")
                self.assertIn('ExecStart="%s" mount --host host --share projects --user leo\n' % executable, text)
                for stream, extension in (("Output", "out"), ("Error", "err")):
                    expected = "journal" if suffix != "normal" else "append:" + str(self.home / ".local/state/agent-swarm/logs" / (service.stem + "." + extension + ".log"))
                    self.assertIn("Standard%s=%s\n" % (stream, expected), text)

    @unittest.skipUnless(shutil.which("systemd-analyze"), "requires systemd-analyze")
    def test_generated_units_verify_offline_for_normal_and_special_home(self):
        for suffix in ("normal", "space % $ home"):
            with self.subTest(home=suffix):
                self.home = Path(self.directory.name) / suffix
                code, response = self.run_tool("mount", [Result(stdout=self.mounted)], "--persistent")
                self.assertEqual(code, 0)
                result = subprocess.run(["systemd-analyze", "--user", "verify", response["service"], response["timer"]],
                                        text=True, capture_output=True,
                                        env=dict(os.environ, HOME=str(self.home), TMPDIR=self.directory.name,
                                                 XDG_CONFIG_HOME=str(self.home / ".config"),
                                                 XDG_RUNTIME_DIR=self.directory.name))
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_disable_failure_retains_existing_units_but_absence_is_removed(self):
        for existing in (True, False):
            for raises in (True, False):
                with self.subTest(existing=existing, raises=raises):
                    self.home = Path(self.directory.name) / (str(existing) + str(raises))
                    paths = [self.home / ".config/systemd/user" / (mount_tool.agent_label("host", "projects") + ext) for ext in (".service", ".timer")]
                    if existing:
                        paths[0].parent.mkdir(parents=True)
                        for path in paths: path.write_text("unchanged")
                    def fail(argv, timeout):
                        raise FileNotFoundError("systemctl unavailable")
                    code, response = self.run_tool("unmount", [Result(), fail if raises else Result(1)], "--remove-persistent")
                    self.assertEqual(code, 0)
                    self.assertEqual(response["persistent_removed"], not existing)
                    self.assertIn("warning", response)
                    for path in paths:
                        self.assertEqual(path.exists(), existing)
                        if existing: self.assertEqual(path.read_text(), "unchanged")
                    self.assertEqual(len(self.runner.calls), 2)

    def test_unavailable_user_systemd_degrades_without_credentials_or_sudo(self):
        code, response = self.run_tool("mount", [Result(stdout=self.mounted), Result(1, stderr="no bus")], "--persistent")
        self.assertEqual(code, 0)
        self.assertFalse(response["persistent"])
        self.assertIn("systemctl --user", response["warning"])
        self.assertFalse((self.home / ".config/agent-swarm/smb-credentials").exists())
        self.assertFalse(any("sudo" in argv for argv, _ in self.runner.calls))


if __name__ == "__main__":
    unittest.main()
