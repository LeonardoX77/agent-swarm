import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "lib"))
from fabric_setup import Setup
from host_registry import HostRegistry


class Result:
    def __init__(self, code=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


class FakeMacs:
    """Focused two-Mac command model; unknown commands are test failures."""
    def __init__(self):
        self.origin = tempfile.TemporaryDirectory()
        self.remote = tempfile.TemporaryDirectory()
        self.origin_home = Path(self.origin.name)
        self.remote_home = Path(self.remote.name)
        self.port_open_after, self.authorized_after, self.keychain_after = 2, 2, 1
        self.port_polls = self.authorization_polls = self.keychain_polls = 0
        self.tools = {"brew", "herdr", "node", "pi", "gentle-pi", "python3"}
        self.mounted = self.reverse_alias = self.update_installed = False
        self.update_calls, self.nonces = [], []
        self.nonce_mismatch = False

    def close(self):
        self.origin.cleanup()
        self.remote.cleanup()

    @staticmethod
    def _keypair(path, key="KEY"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(key + "\n")
        path.with_suffix(".pub").write_text("ssh-ed25519 %s public\n" % key)

    def socket_check(self):
        self.port_polls += 1
        return self.port_polls >= self.port_open_after

    def _remote_python(self, command, program):
        args = shlex.split(command)[2:]
        environment = dict(os.environ, HOME=str(self.remote_home))
        result = subprocess.run([sys.executable, "-", *args], input=program, text=True,
                                capture_output=True, cwd=str(self.remote_home), env=environment)
        return Result(result.returncode, result.stdout, result.stderr)

    def _remote(self, command, program):
        if command == 'printf %s "$HOME"': return Result(out=str(self.remote_home))
        if command == "true": return Result(0 if self.authorization_polls >= self.authorized_after else 1)
        if command.startswith("command -v "):
            name = command.split()[-1]
            return Result(out="/opt/fake/bin/%s\n" % name) if name in self.tools else Result(1)
        if command == "pi list 2>/dev/null | grep -F gentle-pi": return Result(0 if "gentle-pi" in self.tools else 1, "gentle-pi\n")
        if command == "herdr tab list": return Result()
        if command == "scutil --get LocalHostName": return Result(out="Bea\n")
        if command.startswith("ssh -o BatchMode=yes fabric-origin true"):
            return Result(0 if self.reverse_alias else 1)
        if command.startswith("ssh-keyscan -t ed25519 "):
            return Result(out="Origin.local ssh-ed25519 ORIGINKEY\n")
        if command.endswith(" | ssh-keygen -lf -"):
            return Result(out="256 SHA256:ORIGINFP origin\n")
        if command.startswith("test -f ") and "ssh-keygen -t ed25519" in command:
            key = Path(shlex.split(command)[shlex.split(command).index("-f") + 1])
            if not key.exists(): self._keypair(key, "REMOTEKEY")
            return Result()
        if command.startswith("cat "):
            return Result(out=Path(shlex.split(command)[1]).read_text())
        if command.startswith("python3 - "):
            result = self._remote_python(command, program)
            if "Host fabric-origin" in command: self.reverse_alias = True
            return result
        if "fabric-smb-mount status" in command:
            return Result(out=json.dumps({"mounted": self.mounted}))
        if "fabric-smb-mount mount" in command:
            self.keychain_polls += 1
            self.mounted = self.keychain_polls >= self.keychain_after
            return Result(0 if self.mounted else 1)
        if command.startswith("test -d /Volumes/"): return Result(0 if self.mounted else 1)
        if "fabric-update" in command and command.endswith(" status"):
            return Result(0 if self.update_installed else 1, json.dumps({"hour": 4, "minute": 30, "loaded": self.update_installed}))
        if "fabric-update" in command and " install --hour " in command:
            self.update_calls.append(command); self.update_installed = True; return Result()
        if "fabric-delegate" in command:
            if " submit " in command:
                self.nonces.append(json.loads(program)["goal"].split()[3]); return Result(out="submitted")
            if " recover " in command: return Result(out="ACCEPT_wrong" if self.nonce_mismatch else self.nonces[-1])
            return Result(out="closed")
        if command.startswith("mkdir -p ") and " && mv " in command:
            words = shlex.split(command); source, destination = Path(words[-2]), Path(words[-1])
            destination.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(source), str(destination)); return Result()
        if command.startswith("test ! -e "):
            words = shlex.split(command); source = Path(words[words.index("-e") + 1])
            if source.exists():
                destination = Path(words[words.index("mv") + 2]); destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(destination))
            return Result()
        if " tar -xf " in " " + command:
            words = shlex.split(command); archive = Path(words[words.index("-xf") + 1]); target = Path(words[words.index("-C") + 1])
            target.mkdir(parents=True, exist_ok=True)
            with tarfile.open(archive) as bundle: bundle.extractall(target)
            return Result()
        if command.startswith("mkdir -p "): return Result()
        raise AssertionError("unrecognized remote command: %r" % command)

    def __call__(self, argv, **kwargs):
        program = kwargs.get("input") or ""
        if argv[:2] == ["ssh", "fabric-bea"]: return self._remote(argv[2], program)
        text = " ".join(str(item) for item in argv)
        if argv[:1] == ["ssh"] and "fabric-bea" in argv:
            return Result(0 if self.authorization_polls >= self.authorized_after else 1)
        if argv[:1] == ["ssh"] and "bea@Bea.local" in text:
            self.authorization_polls += 1
            return Result(0 if self.authorization_polls >= self.authorized_after else 1)
        if argv[:1] == ["ssh-keygen"] and "-lf" in argv:
            return Result(out="256 SHA256:NEWFP new\n" if "-" in argv else "256 SHA256:ORIGINFP origin\n")
        if argv[:1] == ["ssh-keygen"]:
            self._keypair(Path(argv[argv.index("-f") + 1]), "ORIGINKEY"); return Result()
        if argv[:1] == ["ssh-keyscan"]: return Result(out="Bea.local ssh-ed25519 NEWKEY\n")
        if argv[:1] == ["scp"]:
            source, remote = Path(argv[1]), argv[2].split(":", 1)[1]
            destination = Path(remote); destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(source), str(destination)); return Result()
        if argv[:1] == ["tar"]:
            source = Path(argv[argv.index("-C") + 1]) / argv[-1]
            with tarfile.open(argv[2], "w") as bundle: bundle.add(source, arcname=argv[-1])
            return Result()
        if "fabric-delegate" in text:
            if " submit " in text:
                self.nonces.append(json.loads(program)["goal"].split()[3]); return Result(out="submitted")
            if " recover " in text: return Result(out="ACCEPT_wrong" if self.nonce_mismatch else self.nonces[-1])
            return Result(out="closed")
        raise AssertionError("unrecognized local command: %r" % argv)


class SetupScenarioTests(unittest.TestCase):
    def make_setup(self, machines, registry_path=None, **options):
        registry_path = registry_path or machines.origin_home / "hosts.json"
        if not registry_path.exists():
            registry_path.write_text(json.dumps({"version": 1, "hub": "origin", "share": {"host": "Origin.local", "name": "projects", "user": "leo"}, "hosts": {"origin": {"hostname_prefix": "Origin", "role": "hub", "ssh_alias": "fabric-origin", "address": "Origin.local", "catalog_root": "/catalog", "repo": "/catalog/leo/mac-agent-fabric", "path": "/usr/bin:/bin", "gui_cwd": "/Users/leo/tmp", "runtimes": ["pi"]}}}))
        now = options.pop("now", [0])
        output = options.pop("output", io.StringIO())
        setup = Setup("bea", "Bea.local", "bea", registry=HostRegistry(registry_path), runner=machines,
                      home=machines.origin_home, nodename="Origin.local", tty=False, uid=501,
                      host_fingerprint="SHA256:NEWFP", output=output,
                      sleep=lambda seconds: now.__setitem__(0, now[0] + seconds),
                      clock=lambda: now[0], wait_timeout=1, update_time="04:30", **options)
        setup.socket_check = lambda address: machines.socket_check()
        return setup, registry_path

    def run_zero_to_done(self, **options):
        machines = FakeMacs(); self.addCleanup(machines.close)
        setup, registry_path = self.make_setup(machines, **options)
        code = setup.run()
        self.assertEqual(code, 0, setup.output.getvalue() + "\n" + setup.log_path.read_text())
        return machines, setup, registry_path

    @staticmethod
    def snapshot(root):
        return {path.relative_to(root): (path.read_bytes(), path.stat().st_mode & 0o777)
                for path in root.rglob("*") if path.is_file()}

    def test_zero_to_done_without_tty(self):
        machines, setup, registry_path = self.run_zero_to_done()
        summary = setup.output.getvalue()
        positions = [summary.index("[%2d/10]" % index) for index in range(1, 11)]
        self.assertEqual(positions, sorted(positions))
        origin_config = (machines.origin_home / ".ssh/config").read_text()
        remote_config = (machines.remote_home / ".ssh/config").read_text()
        self.assertEqual(origin_config.count("Host fabric-bea\n"), 1)
        self.assertEqual(remote_config.count("Host fabric-origin\n"), 1)
        remote_pub = (machines.remote_home / ".ssh/agent_fabric_origin.pub").read_text().strip()
        authorized = (machines.origin_home / ".ssh/authorized_keys").read_text()
        self.assertEqual(authorized.count("no-agent-forwarding,no-port-forwarding,no-X11-forwarding " + remote_pub), 1)
        known = (machines.remote_home / ".ssh/known_hosts").read_bytes()
        self.assertEqual(known, b"Origin.local ssh-ed25519 ORIGINKEY\n")
        repository = Path(__file__).resolve().parents[3]
        self.assertEqual(Setup.canonical_digest(repository / "skills/agent-fabric-remote"), Setup.canonical_digest(machines.remote_home / ".pi/agent/skills/agent-fabric-remote"))
        agents = (machines.remote_home / ".pi/agent/AGENTS.md").read_text()
        self.assertEqual(agents.count("<!-- BEGIN AGENT-FABRIC-REMOTE-BOOTSTRAP -->"), 1)
        self.assertIn("Agent Fabric repository on this host: /Volumes/projects/leo/mac-agent-fabric", agents)
        registry = HostRegistry(registry_path)
        self.assertEqual(registry.get("bea")["address"], "Bea.local")
        self.assertEqual(len(machines.update_calls), 1)
        self.assertIn("install --hour 04 --minute 30", machines.update_calls[0])
        self.assertTrue(setup.log_path.exists())

    def test_rerun_on_configured_host_writes_nothing(self):
        machines, first, registry_path = self.run_zero_to_done()
        origin_before = self.snapshot(machines.origin_home)
        remote_before = self.snapshot(machines.remote_home)
        registry_before = registry_path.read_bytes()
        submits_before = len(machines.nonces)
        rerun, _ = self.make_setup(machines, registry_path)

        self.assertEqual(rerun.run(), 0, rerun.output.getvalue())
        phases = [line for line in rerun.output.getvalue().splitlines() if line.startswith("[")]
        self.assertEqual(len(phases), 10)
        self.assertTrue(all(" CHANGED " not in line and " WAITING " not in line and " FAILED " not in line for line in phases))
        self.assertTrue(all(" OK " in line or " SKIPPED " in line for line in phases))
        ignored = {rerun.state_path.relative_to(machines.origin_home), rerun.log_path.relative_to(machines.origin_home)}
        origin_after = self.snapshot(machines.origin_home)
        self.assertEqual({path: item for path, item in origin_before.items() if path not in ignored},
                         {path: item for path, item in origin_after.items() if path not in ignored})
        self.assertEqual(remote_before, self.snapshot(machines.remote_home))
        self.assertEqual(registry_before, registry_path.read_bytes())
        self.assertEqual(len(machines.nonces), submits_before)

    def test_dry_run_on_zero_state_reports_changes_and_writes_nothing(self):
        machines = FakeMacs(); self.addCleanup(machines.close)
        setup, registry_path = self.make_setup(machines, dry_run=True)
        origin_before, remote_before, registry_before = self.snapshot(machines.origin_home), self.snapshot(machines.remote_home), registry_path.read_bytes()

        self.assertEqual(setup.run(), 4, setup.output.getvalue())
        self.assertIn(" CHANGED ", setup.output.getvalue())
        ignored = {setup.log_path.relative_to(machines.origin_home), setup.state_path.relative_to(machines.origin_home)}
        origin_after = self.snapshot(machines.origin_home)
        self.assertEqual({path: item for path, item in origin_before.items() if path not in ignored},
                         {path: item for path, item in origin_after.items() if path not in ignored})
        self.assertEqual(remote_before, self.snapshot(machines.remote_home))
        self.assertEqual(registry_before, registry_path.read_bytes())
        self.assertFalse(setup.state_path.exists())

    def test_dry_run_on_configured_state_exits_zero(self):
        machines, first, registry_path = self.run_zero_to_done()
        dry_run, _ = self.make_setup(machines, registry_path, dry_run=True)
        self.assertEqual(dry_run.run(), 0, dry_run.output.getvalue())
        self.assertNotIn(" CHANGED ", dry_run.output.getvalue())

    def test_no_wait_exits_10_at_first_person_step_and_resume_continues(self):
        machines = FakeMacs(); self.addCleanup(machines.close)
        machines.port_open_after = 2
        waiting, registry_path = self.make_setup(machines, no_wait=True)
        self.assertEqual(waiting.run(), 10)
        self.assertIn("[ 2/10] remote-login    WAITING", waiting.output.getvalue())
        self.assertIn("Re-run the same command to resume.", waiting.output.getvalue())

        machines.port_open_after = 1
        machines.authorized_after = 1
        resumed, _ = self.make_setup(machines, registry_path)
        self.assertEqual(resumed.run(), 0, resumed.output.getvalue())

    def test_registry_drift_rewrites_only_registry(self):
        machines, first, registry_path = self.run_zero_to_done()
        machines.tools.add("claude")
        rerun, _ = self.make_setup(machines, registry_path)

        self.assertEqual(rerun.run(), 0, rerun.output.getvalue())
        phases = [line for line in rerun.output.getvalue().splitlines() if line.startswith("[")]
        changed = [line.split("] ", 1)[1].split()[0] for line in phases if " CHANGED " in line]
        self.assertEqual(changed, ["registry", "skill"])
        self.assertTrue(all(" OK " in line or " CHANGED " in line for line in phases))
        self.assertIn("claude", HostRegistry(registry_path).get("bea")["runtimes"])
        self.assertEqual(Setup.canonical_digest(Path(__file__).resolve().parents[3] / "skills/agent-fabric-remote"),
                         Setup.canonical_digest(machines.remote_home / ".claude/skills/agent-fabric-remote"))

    def test_alias_conflict_fails_before_writing_more(self):
        machines = FakeMacs(); self.addCleanup(machines.close)
        ssh = machines.origin_home / ".ssh"; ssh.mkdir()
        config = ssh / "config"; config.write_text("Host fabric-bea\n  HostName elsewhere\n")
        before, remote_before = config.read_bytes(), self.snapshot(machines.remote_home)
        setup, _ = self.make_setup(machines)

        self.assertEqual(setup.run(), 1)
        self.assertIn("[ 3/10] ssh-to-new      FAILED   SSH alias conflict", setup.output.getvalue())
        self.assertEqual(config.read_bytes(), before)
        self.assertEqual(self.snapshot(machines.remote_home), remote_before)

    def test_existing_different_skill_is_backed_up_outside_skills_dirs(self):
        machines, first, registry_path = self.run_zero_to_done()
        old_skill = machines.remote_home / ".pi/agent/skills/agent-fabric-remote"
        (old_skill / "legacy.txt").write_text("old")
        agents = machines.remote_home / ".pi/agent/AGENTS.md"
        agents.write_text(agents.read_text().replace("/Volumes/projects/leo/mac-agent-fabric", "/other/repo"))
        rerun, _ = self.make_setup(machines, registry_path)

        self.assertEqual(rerun.run(), 0, rerun.output.getvalue())
        backups = list((machines.remote_home / ".local/state/agent-fabric/skill-backups").glob("pi-agent-fabric-remote-*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / "legacy.txt").exists())
        self.assertEqual(Setup.canonical_digest(Path(__file__).resolve().parents[3] / "skills/agent-fabric-remote"), Setup.canonical_digest(old_skill))
        self.assertEqual(agents.read_text().count("<!-- BEGIN AGENT-FABRIC-REMOTE-BOOTSTRAP -->"), 1)
        self.assertIn("Agent Fabric repository on this host: /Volumes/projects/leo/mac-agent-fabric", agents.read_text())
        self.assertEqual(len(list(agents.parent.glob("AGENTS.md.fabric-setup-*.bak"))), 1)

    def test_no_auto_update_skips_phase_9(self):
        machines, setup, registry_path = self.run_zero_to_done(auto_update=False)
        self.assertIn("[ 9/10] auto-update     SKIPPED", setup.output.getvalue())

    def test_acceptance_nonce_mismatch_fails(self):
        machines = FakeMacs(); self.addCleanup(machines.close)
        machines.nonce_mismatch = True
        setup, _ = self.make_setup(machines)
        self.assertEqual(setup.run(), 1)
        self.assertIn("[10/10] acceptance      FAILED   Acceptance nonce mismatch", setup.output.getvalue())

    def test_verbose_prints_commands_default_does_not(self):
        default_machines, default, default_registry = self.run_zero_to_done()
        self.assertNotIn("$ ", default.output.getvalue())
        self.assertIn("$ ", default.log_path.read_text())
        verbose_machines, verbose, verbose_registry = self.run_zero_to_done(verbose=True)
        self.assertIn("$ ", verbose.output.getvalue())
        self.assertIn("$ ", verbose.log_path.read_text())


if __name__ == "__main__":
    unittest.main()
