import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "lib"))
from swarm_setup import PHASES, Setup, SetupError, Waiting


class Registry:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.share = {"host": "Origin.local", "name": "projects", "user": "leo"}
        self._hosts = {"origin": {"name": "origin", "hostname_prefix": "Origin", "role": "hub", "address": "Origin.local", "ssh_alias": "swarm-origin", "catalog_root": "/catalog", "repo": "/catalog/org/repo", "path": "/usr/bin:/bin", "gui_cwd": "/Users/leo/tmp", "runtimes": ["pi"]}}
    @property
    def hosts(self): return dict(self._hosts)
    def get(self, name): return self._hosts[name]
    def self_host(self, node): return self._hosts["origin"] if node.startswith("Origin") else None


class Result:
    def __init__(self, code=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


class TwoMachineRunner:
    """Command model with independent origin/remote state, not a shell emulator."""
    def __init__(self):
        self.calls = []; self.remote_home = "/Users/leo"; self.authorized = False
        self.mounted = False; self.alias = False; self.fingerprint = "SHA256:ok"
    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), kwargs.get("input")))
        text = " ".join(argv)
        if "ssh-keyscan" in text: return Result(out="New.local ssh-ed25519 key")
        if "ssh-keygen" in text and "-lf" in text: return Result(out="256 %s host" % self.fingerprint)
        if argv[:2] == ["ssh", "swarm-new-mac"]:
            command = argv[2]
            if command == 'printf %s "$HOME"': return Result(out=self.remote_home)
            if "BatchMode=yes swarm-origin true" in command: return Result(0 if self.alias else 1)
            if "swarm-smb-mount status" in command: return Result(out=json.dumps({"mounted": self.mounted}))
            if "swarm-smb-mount mount" in command: self.mounted = True; return Result()
            if command.startswith("test -d /Volumes/projects"): return Result(0 if self.mounted else 1)
            if command.startswith("python3 - "): return Result(out="")
            return Result()
        if argv[:1] == ["ssh"] and "@New.local" in text: return Result(0 if self.authorized else 1)
        return Result()


class SetupTests(unittest.TestCase):
    def make(self, **kwargs):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        home = Path(directory.name) / "home"; home.mkdir()
        runner = kwargs.pop("runner", TwoMachineRunner())
        now = [0]
        def sleep(seconds): now[0] += seconds
        uid = kwargs.pop("uid", 501)
        output = kwargs.pop("output", io.StringIO())
        return Setup("new-mac", "New.local", "leo", registry=Registry(), runner=runner, home=home,
                     nodename="Origin.local", tty=False, uid=uid, output=output,
                     sleep=sleep, clock=lambda: now[0], **kwargs)

    def test_default_runner_runs_commands_once(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        home = Path(directory.name) / "home"; home.mkdir()
        setup = Setup("new-mac", "New.local", "leo", registry=Registry(), home=home,
                      nodename="Origin.local", uid=501, output=io.StringIO())
        self.assertEqual(setup.command(["/usr/bin/true"]).returncode, 0)
        result = setup.command(["/bin/echo", "x"])
        self.assertEqual((result.returncode, result.stdout), (0, "x\n"))

    def test_setup_help_subcommands_use_real_subprocess(self):
        script = Path(__file__).parents[1] / "bin" / "swarm-setup"
        for command in ("add-host", "status"):
            result = subprocess.run([sys.executable, str(script), command, "--help"], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("usage:", result.stdout)

    def test_person_wait_polls_without_tty_until_condition(self):
        setup = self.make(wait_timeout=1)
        polls = [0]
        def condition(): polls[0] += 1; return polls[0] == 3
        setup.wait_for("enable Remote Login", condition)
        self.assertEqual(polls[0], 3)

    def test_no_wait_exits_at_first_person_step(self):
        setup = self.make(no_wait=True)
        with self.assertRaises(Waiting): setup.wait_for("person", lambda: False)

    def test_wait_timeout_exits_after_polling(self):
        setup = self.make(wait_timeout=0)
        with self.assertRaises(Waiting): setup.wait_for("person", lambda: False)

    def test_non_tty_fingerprint_requires_option_and_prints_hint(self):
        setup = self.make()
        setup.command = lambda argv, **kw: Result(1 if argv[:1] == ["ssh"] else 0, "256 SHA256:ok host")
        with self.assertRaisesRegex(Waiting, "--host-fingerprint SHA256:ok"): setup.ssh_to_new()

    def test_fingerprint_mismatch_stops_hard(self):
        setup = self.make(host_fingerprint="SHA256:not-it")
        setup.command = lambda argv, **kw: Result(1 if argv[:1] == ["ssh"] else 0, "256 SHA256:ok host")
        with self.assertRaisesRegex(SetupError, "mismatch"): setup.ssh_to_new()

    def test_fingerprint_option_continues_to_authorization_wait(self):
        setup = self.make(host_fingerprint="SHA256:ok")
        key = setup.home / ".ssh/agent_swarm_new_mac"; key.parent.mkdir(); key.write_text("key"); key.with_suffix(".pub").write_text("ssh-ed25519 public")
        setup.command = lambda argv, **kw: Result(1 if argv[:1] == ["ssh"] else 0, "256 SHA256:ok host")
        with self.assertRaises(Waiting): setup.ssh_to_new()

    def test_known_hosts_uses_real_newline_once(self):
        setup = self.make(host_fingerprint="SHA256:ok", no_wait=True)
        key = setup.home / ".ssh/agent_swarm_new_mac"; key.parent.mkdir(); key.write_text("key"); key.with_suffix(".pub").write_text("pub")
        setup.command = lambda argv, **kw: Result(1 if argv[:1] == ["ssh"] or "@New.local" in " ".join(argv) else 0, "256 SHA256:ok host" if "ssh-keygen" in argv else "keyline")
        with self.assertRaises(Waiting): setup.ssh_to_new()
        self.assertEqual((setup.home / ".ssh/known_hosts").read_bytes(), b"keyline\n")

    def test_remote_copy_expands_home_before_scp(self):
        setup = self.make(); source = setup.home / "source"; source.write_text("x")
        setup._remote_copy(source, "~/.local/agent-swarm/bin/tool")
        scp = next(call[0] for call in setup.runner.calls if call[0][0] == "scp")
        self.assertIn("/Users/leo/.local", scp[-1]); self.assertNotIn("~", scp[-1])

    def test_alias_conflict_is_rejected(self):
        setup = self.make(); ssh = setup.home / ".ssh"; ssh.mkdir(); (ssh / "config").write_text("Host swarm-new-mac\n  HostName other\n")
        with self.assertRaises(SetupError): setup.write_alias(ssh / "config", "swarm-new-mac", "New.local", "leo", "/tmp/key")

    def test_explicit_phase_status_drives_changed_summary(self):
        setup = self.make(dry_run=True)
        setup.local_preflight = lambda: ("ok", "done")
        setup.remote_login = lambda: ("changed", "installed daily update")
        for name in PHASES[2:]: setattr(setup, name.replace("-", "_") + ("_phase" if name in ("registry", "auto-update") else ""), lambda: ("ok", "done"))
        # Directly exercise bookkeeping: arbitrary detail text must not classify status.
        setup.mark("remote-login", "changed", "installed daily update")
        self.assertEqual(setup.changed, ["remote-login"])

    def test_registry_identical_is_ok_and_different_is_changed(self):
        setup = self.make(); setup.origin = setup.registry.get("origin")
        entry = {"hostname_prefix": "New", "role": "spoke", "ssh_alias": "swarm-new-mac", "address": "New.local", "catalog_root": "/Volumes/projects", "repo": "/Volumes/projects/org/repo", "path": "/usr/bin:/bin", "gui_cwd": "/Users/leo/tmp", "runtimes": ["pi"]}
        setup.registry._hosts["new-mac"] = dict(entry, name="new-mac")
        setup.build_registry_entry = lambda: entry
        self.assertEqual(setup.registry_phase()[0], "ok")

    def test_canonical_digest_includes_relative_names(self):
        setup = self.make(); root = setup.home / "skill"; root.mkdir(); (root / "a").write_text("same"); (root / "b").write_text("same")
        first = setup.canonical_digest(root); (root / "b").unlink(); (root / "c").write_text("same")
        self.assertNotEqual(first, setup.canonical_digest(root))

    def test_no_auto_update_skips_phase_nine(self):
        self.assertEqual(self.make(auto_update=False).auto_update_phase()[0], "skipped")

    def test_root_is_refused_and_log_is_written(self):
        setup = self.make(uid=0); self.assertEqual(setup.run(), 2); self.assertTrue(setup.log_path.exists())

    def test_unexpected_exception_has_traceback_only_in_log(self):
        setup = self.make()
        setup.local_preflight = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        self.assertEqual(setup.run(), 1)
        self.assertIn("Unexpected RuntimeError (see log)", setup.output.getvalue())
        self.assertNotIn("Traceback", setup.output.getvalue())
        self.assertIn("Traceback", setup.log_path.read_text())

    def test_command_audit_is_logged_without_verbose_console_output(self):
        setup = self.make()
        setup.command(["example-command", "argument"])
        self.assertNotIn("$ example-command", setup.output.getvalue())
        self.assertIn("$ example-command argument", setup.log_path.read_text())

    def test_acceptance_is_bidirectional(self):
        """RED for D5/S5: both directions must submit an acceptance task."""
        setup = self.make(); setup.origin = setup.registry.get("origin")
        setup.registry._hosts["new-mac"] = dict(setup.origin, name="new-mac", catalog_root="/Volumes/projects", repo="/Volumes/projects/org/repo")
        calls = []; nonces = []; envelopes = []
        def command(argv, timeout=45, input=None):
            calls.append(argv)
            if input:
                envelope = json.loads(input); envelopes.append(envelope)
                nonces.append(envelope["goal"].split()[3])
            if "recover" in " ".join(argv): return Result(out=nonces[-1])
            return Result()
        setup.command = command; setup.remote = lambda command, timeout=60, input=None: Result()
        self.assertEqual(setup.acceptance()[0], "ok")
        self.assertTrue(any(argv[:2] == ["ssh", "swarm-new-mac"] for argv in calls), "remote direction was not submitted")
        self.assertEqual([set(value) for value in envelopes], [{"task_id", "origin_host", "project", "goal", "acceptance", "mode"}] * 2)
        self.assertEqual([value["origin_host"] for value in envelopes], ["origin", "new-mac"])
        self.assertEqual([value["project"] for value in envelopes], ["org/repo", "org/repo"])
        self.assertTrue(all(value["acceptance"] == "Return the exact nonce." and value["mode"] == "executor" for value in envelopes))

    def test_acceptance_login_hint_exits_without_polling_submit(self):
        setup = self.make(); setup.origin = setup.registry.get("origin")
        setup.registry._hosts["new-mac"] = dict(setup.origin, name="new-mac", catalog_root="/Volumes/projects", repo="/Volumes/projects/org/repo")
        setup.command = lambda argv, timeout=45, input=None: Result(1, "Not logged in") if input else Result()
        setup.wait_for = lambda *args: self.fail("login cannot safely be polled")
        with self.assertRaisesRegex(Waiting, "Log Pi in from the GUI on new-mac"):
            setup.acceptance()

    def test_acceptance_nonlogin_failure_reports_remote_diagnostic(self):
        setup = self.make(); setup.origin = setup.registry.get("origin")
        setup.registry._hosts["new-mac"] = dict(setup.origin, name="new-mac", catalog_root="/Volumes/projects", repo="/Volumes/projects/org/repo")
        setup.command = lambda argv, timeout=45, input=None: Result(1, '{"status":"failed","diagnostic_code":"INVALID_ENVELOPE"}') if input else Result()
        with self.assertRaisesRegex(SetupError, "INVALID_ENVELOPE") as raised:
            setup.acceptance()
        self.assertIn("remote output", str(raised.exception))

    def test_emit_flushes_console_and_log(self):
        class Stream(io.StringIO):
            def __init__(self): super().__init__(); self.flushes = 0
            def flush(self): self.flushes += 1; super().flush()
        output = Stream(); setup = self.make(output=output)
        setup.emit("progress")
        self.assertGreaterEqual(output.flushes, 1)
        self.assertIn("progress\n", setup.log_path.read_text())

    def test_setup_cli_configures_line_buffered_stdout(self):
        script = Path(__file__).parents[1] / "bin" / "swarm-setup"
        self.assertIn("reconfigure(line_buffering=True)", script.read_text())


if __name__ == "__main__": unittest.main()
