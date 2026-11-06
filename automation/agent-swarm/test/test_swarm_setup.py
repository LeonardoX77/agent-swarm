import io
import os
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import contextlib
import runpy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "lib"))
from swarm_setup import PHASES, Setup, SetupError, Waiting
from host_registry import HostRegistry


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

    def test_target_ports_preserve_default_commands_and_alias_bytes(self):
        for system in ("Darwin", "Linux"):
            for port in (22, 2222, 1, 65535):
                with self.subTest(system=system, port=port):
                    setup = self.make(local_system=system, ssh_port=port, host_fingerprint="SHA256:ok")
                    key = setup.home / ".ssh/agent_swarm_new_mac"
                    key.parent.mkdir(); key.write_text("key"); key.with_suffix(".pub").write_text("pub")
                    calls = []; polls = []
                    scan = ("New.local" if port == 22 else "[New.local]:%s" % port) + " ssh-ed25519 KEY\n"
                    def runner(argv, **kwargs):
                        calls.append(argv)
                        if argv[0] == "ssh-keyscan": return Result(out=scan)
                        if argv[0] == "ssh-keygen": return Result(out="256 SHA256:ok host")
                        return Result(1 if "swarm-new-mac" in argv else 0)
                    setup.runner = runner
                    setup.socket_check = lambda address, port: polls.append((address, port)) or len(polls) > 1
                    self.assertEqual(setup.remote_login(), ("ok", "Remote Login reachable"))
                    self.assertEqual(polls, [("New.local", port)] * 2)
                    self.assertEqual(setup.ssh_to_new(), ("changed", "configured SSH channel"))
                    flags = [] if port == 22 else ["-p", str(port)]
                    self.assertEqual([c for c in calls if c[0] == "ssh-keyscan"], [["ssh-keyscan", *flags, "-t", "ed25519", "New.local"]] * 2)
                    self.assertIn(["ssh", *flags, "-i", str(key), "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "leo@New.local", "true"], calls)
                    expected = "Host swarm-new-mac\n  HostName New.local\n" + ("  Port %s\n" % port if port != 22 else "") + "  User leo\n  IdentityFile %s\n  IdentitiesOnly yes\n  BatchMode yes\n  StrictHostKeyChecking yes\n  ConnectTimeout 15\n  ServerAliveInterval 15\n  ServerAliveCountMax 4\n  ForwardAgent no\n" % key
                    self.assertEqual((key.parent / "config").read_text(), expected)
                    self.assertEqual((key.parent / "known_hosts").read_text(), scan)
                    setup.ssh_to_new()
                    self.assertEqual((key.parent / "known_hosts").read_text(), scan)
                    self.assertEqual((key.parent / "config").read_text(), expected)
                    before = (key.parent / "config").read_bytes()
                    setup.ssh_port = 2223
                    with self.assertRaisesRegex(SetupError, "SSH alias conflict for swarm-new-mac"):
                        setup.ssh_to_new()
                    self.assertEqual((key.parent / "config").read_bytes(), before)

    def test_single_candidate_alias_bytes_are_unchanged_in_both_directions(self):
        key = "/tmp/key"
        expected = ("Host swarm-peer\n  HostName peer.local\n  Port 2222\n  User leo\n  IdentityFile /tmp/key\n"
                    "  IdentitiesOnly yes\n  BatchMode yes\n  StrictHostKeyChecking yes\n  ConnectTimeout 15\n"
                    "  ServerAliveInterval 15\n  ServerAliveCountMax 4\n  ForwardAgent no\n")
        self.assertEqual(Setup.alias_block("swarm-peer", "peer.local", "leo", key, 2222, ["peer.local"]), expected)
        self.assertEqual(Setup.alias_block("swarm-peer", "peer.local", "leo", key, 2222, ["peer.local"]), expected)

    def test_multi_candidate_alias_uses_host_key_alias_and_proxy_command(self):
        block = Setup.alias_block("swarm-peer", "tailnet", "leo", "/tmp/key", 2222,
                                  ["tailnet", "192.168.1.2"], "/tmp/swarm ssh connect")
        self.assertIn("  HostKeyAlias swarm-peer\n", block)
        self.assertIn("ProxyCommand ", block)
        self.assertIn("--port 2222 -- tailnet 192.168.1.2", block)
        self.assertNotIn("HostName", block)

    def test_port_cli_validation_and_help(self):
        script = Path(__file__).parents[1] / "bin/swarm-setup"
        with tempfile.TemporaryDirectory() as home:
            for option in ("--ssh-port", "--origin-ssh-port"):
                for value in ("0", "65536", "-1", "abc", "22.5", ""):
                    with self.subTest(option=option, value=value):
                        result = subprocess.run([sys.executable, str(script), "add-host", "--name", "new", "--address", "New.local", "--user", "leo", option, value], env=dict(os.environ, HOME=home), capture_output=True, text=True)
                        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, "", "INVALID_INPUT\n"))
                        self.assertEqual(list(Path(home).iterdir()), [])
            result = subprocess.run([sys.executable, str(script), "add-host", "--help"], capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stderr), (0, ""))
            for option in ("--ssh-port PORT", "--origin-ssh-port PORT"):
                self.assertIn(option, result.stdout)

    def test_candidate_cli_rejects_invalid_values_without_writing_state(self):
        script = Path(__file__).parents[1] / "bin/swarm-setup"
        common = ["add-host", "--name", "new", "--address", "New.local", "--user", "leo"]
        cases = (
            ("address repeated as fallback", ["--fallback-address", "New.local"]),
            ("repeated fallback", ["--fallback-address", "one.local", "--fallback-address", "one.local"]),
            ("repeated share host", ["--share-host", "one.local", "--share-host", "one.local"]),
            ("repeated origin address", ["--origin-address", "one.local", "--origin-address", "one.local"]),
            ("hub share host", ["--role", "hub", "--share-host", "one.local"]),
        )
        for label, arguments in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as home:
                result = subprocess.run([sys.executable, str(script), *common, *arguments],
                                        env=dict(os.environ, HOME=home), capture_output=True, text=True)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (2, "", "INVALID_INPUT\n"))
                self.assertEqual(list(Path(home).iterdir()), [])
        for option in ("--address", "--fallback-address", "--origin-address", "--share-host"):
            for invalid in ("bad address", "-x", "--help", "-oProxyCommand"):
                with self.subTest(option=option, invalid=invalid), tempfile.TemporaryDirectory() as home:
                    arguments = ["--address", "New.local", "--user", "leo"]
                    if option == "--address":
                        arguments[:2] = ["--address=" + invalid] if invalid.startswith("-") else ["--address", invalid]
                    else:
                        arguments.extend([option + "=" + invalid] if invalid.startswith("-") else [option, invalid])
                    if invalid.startswith("-"):
                        main = runpy.run_path(str(script))["main"]
                        stdout, stderr = io.StringIO(), io.StringIO()
                        with patch.dict(main.__globals__, Setup=unittest.mock.Mock()) as namespace:
                            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                                code = main(["add-host", "--name", "new", *arguments])
                            self.assertEqual(code, 2)
                            namespace["Setup"].assert_not_called()
                        self.assertEqual((stdout.getvalue(), stderr.getvalue()), ("", "INVALID_INPUT\n"))
                    else:
                        result = subprocess.run([sys.executable, str(script), "add-host", "--name", "new", *arguments],
                                                env=dict(os.environ, HOME=home), capture_output=True, text=True)
                        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, "", "INVALID_INPUT\n"))
                    self.assertEqual(list(Path(home).iterdir()), [])

    def test_candidate_cli_help_lists_all_candidate_options(self):
        script = Path(__file__).parents[1] / "bin/swarm-setup"
        result = subprocess.run([sys.executable, str(script), "add-host", "--help"], capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        for option in ("--fallback-address ADDR", "--origin-address ADDR", "--share-host HOST"):
            self.assertIn(option, result.stdout)

    def test_build_registry_entry_keeps_optional_candidates_optional_and_valid(self):
        for options, expected in (({}, {}), ({"fallback_addresses": ["100.64.0.2"], "share_hosts": ["smb.tail", "192.168.1.2"]}, {"fallback_addresses": ["100.64.0.2"], "share_hosts": ["smb.tail", "192.168.1.2"]})):
            with self.subTest(options=options):
                setup = self.make(**options)
                setup.origin = setup.registry.get("origin")
                setup.remote_path = "/usr/bin:/bin"
                setup.remote_home = "/Users/remote"
                setup.remote_system = "Darwin"
                setup.remote_tool = lambda command: Result(out="Remote\n" if command == "scutil --get LocalHostName" else "/usr/bin/tool\n")
                entry = setup.build_registry_entry()
                self.assertEqual({key: entry[key] for key in expected}, expected)
                self.assertEqual(set(entry) & {"fallback_addresses", "share_hosts"}, set(expected))
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "hosts.json"
                    origin = {key: value for key, value in setup.registry.get("origin").items() if key != "name"}
                    path.write_text(json.dumps({"version": 1, "hub": "origin", "share": setup.registry.share,
                                                "hosts": {"origin": origin, "new-mac": entry}}))
                    self.assertEqual(HostRegistry(path).get("new-mac")["fallback_addresses"] if expected else None,
                                     expected.get("fallback_addresses"))

    def test_valid_port_options_reach_setup_and_status_stays_unchanged(self):
        script = Path(__file__).parents[1] / "bin/swarm-setup"
        main = runpy.run_path(str(script))["main"]
        for port in (1, 22, 65535):
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.dict(main.__globals__, Setup=unittest.mock.Mock()) as namespace:
                namespace["Setup"].return_value.run.return_value = 0
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = main(["add-host", "--name", "new", "--address", "New.local", "--user", "leo", "--ssh-port", str(port), "--origin-ssh-port", str(port)])
                self.assertEqual((code, stdout.getvalue(), stderr.getvalue()), (0, "", ""))
                options = namespace["Setup"].call_args.kwargs
                self.assertEqual((options["ssh_port"], options["origin_ssh_port"]), (port, port))
        for option in ("--ssh-port", "--origin-ssh-port"):
            result = subprocess.run([sys.executable, str(script), "status", "--name", "new", option, "2222"], text=True, capture_output=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (2, "", "usage: swarm-setup [-h] {add-host,status} ...\nswarm-setup: error: unrecognized arguments: %s 2222\n" % option))

    def test_runtime_integration_probe_install_and_dry_run(self):
        probe = "herdr integration status 2>/dev/null | grep -E '^pi: ' | grep -v 'not installed'"
        for system in ("Darwin", "Linux"):
            for present, install, dry in ((True, False, False), (False, True, False),
                                           (False, True, True), (False, False, False)):
                with self.subTest(system=system, present=present, install=install, dry=dry):
                    setup = self.make(no_wait=True, install_missing=install, dry_run=dry)
                    setup.discover_remote_path = lambda: None
                    setup.remote_system_name = lambda: system
                    calls = []; integrated = [present]
                    before = list(setup.home.iterdir())
                    def remote(command, *args):
                        calls.append(command)
                        if command == probe: return Result(0 if integrated[0] else 1)
                        if command == "herdr integration install pi":
                            integrated[0] = True; return Result()
                        return Result()
                    setup.remote_tool = remote
                    if not present and not install:
                        with self.assertRaises(Waiting) as raised: setup.runtimes()
                        expected = "On new-mac: install missing runtimes and log Pi in once from the GUI; missing probes: herdr-pi-integration"
                        if system == "Linux":
                            expected = "On new-mac: install missing runtimes and log Pi in once locally; missing probes: herdr-pi-integration"
                        self.assertEqual(str(raised.exception), expected)
                        self.assertEqual(setup.output.getvalue(), expected + "\n")
                        self.assertEqual(setup.log_path.read_text(), expected + "\n")
                    else:
                        expected = ("ok", "required runtimes available") if present else ("changed", ("would install" if dry else "installed") + " herdr pi integration")
                        self.assertEqual(setup.runtimes(), expected)
                        self.assertEqual(setup.output.getvalue(), "")
                        self.assertEqual(list(setup.home.iterdir()), before)
                    self.assertIn(probe, calls)
                    self.assertEqual(calls.count("herdr integration install pi"), int(not present and install and not dry))
                    self.assertEqual(integrated[0], present or (install and not dry))
                    self.assertFalse(setup.state_path.exists())

    def test_integration_follows_herdr_install_and_never_runs_without_herdr(self):
        for system in ("Darwin", "Linux"):
            for success, dry in ((True, False), (False, False), (True, True)):
                with self.subTest(system=system, success=success, dry=dry):
                    setup = self.make(no_wait=True, install_missing=True, dry_run=dry)
                    setup.discover_remote_path = lambda: None
                    setup.remote_system_name = lambda: system
                    installed = set(); calls = []
                    def remote(command, *args):
                        calls.append(command)
                        if command == "command -v herdr" or command == "herdr tab list":
                            return Result(0 if "herdr" in installed else 1)
                        if command.startswith("herdr integration status "):
                            return Result(0 if "integration" in installed else 1)
                        if command == "brew install herdr" or "install.sh" in command:
                            if success: installed.add("herdr")
                            return Result(0 if success else 1)
                        if command == "herdr integration install pi":
                            self.assertIn("herdr", installed)
                            installed.add("integration")
                        return Result()
                    setup.remote_tool = remote
                    if not success:
                        with self.assertRaises(Waiting): setup.runtimes()
                        self.assertNotIn("herdr integration install pi", calls)
                    else:
                        verb = "would install" if dry else "installed"
                        self.assertEqual(setup.runtimes(), ("changed", verb + " herdr, " + verb + " herdr pi integration"))
                        self.assertEqual(installed, set() if dry else {"herdr", "integration"})
                    self.assertFalse(setup.state_path.exists())

    def test_runtime_wait_lists_probes_and_linux_server_instructions(self):
        for system in ("Darwin", "Linux"):
            setup = self.make(no_wait=True)
            setup.discover_remote_path = lambda: None
            setup.remote_system_name = lambda: system
            setup.remote_tool = lambda *args: Result(1)
            with self.assertRaises(Waiting) as raised: setup.runtimes()
            # Preserve the macOS prefix byte-for-byte, even with every probe failing.
            prefix = "On new-mac: install missing runtimes and log Pi in once "
            expected = prefix + ("from the GUI" if system == "Darwin" else "locally")
            expected += "; missing probes: herdr, node, pi, python3, gentle-pi, herdr-server, herdr-pi-integration"
            if system == "Darwin": expected += ", brew"
            else:
                expected += "; start the herdr server by running herdr in a normal terminal, then detach, or use a pty with a non-zero grid (rows and columns); the server survives the client exiting"
            self.assertEqual(str(raised.exception), expected)
            self.assertEqual(setup.output.getvalue(), expected + "\n")
            self.assertNotIn("herdr server start", expected)
            self.assertFalse(setup.state_path.exists())

    def test_remote_path_includes_pi_installer_bin_next_to_local_bin(self):
        setup = self.make()
        for suffix in (".local/bin", ".pi/agent/bin", ".hermes/node/bin"):
            (setup.home / suffix).mkdir(parents=True)
        pi = setup.home / ".pi/agent/bin/pi"
        pi.write_text("#!/bin/sh\nprintf 'gentle-pi\\n'\n"); pi.chmod(0o755)
        def remote(command, *args, **kwargs):
            return subprocess.run(["/bin/sh", "-c", command], text=True, capture_output=True,
                                  env=dict(os.environ, HOME=str(setup.home)))
        setup.remote = remote
        path = setup.discover_remote_path()
        self.assertIn(str(setup.home / ".local/bin") + ":" + str(pi.parent), path)
        self.assertIn(str(setup.home / ".hermes/node/bin"), path)
        self.assertTrue(path.endswith("/usr/bin:/bin:/usr/sbin:/sbin"))
        # Restrict the lookup to the fake home directories so a host-installed pi (for example
        # Homebrew's) cannot shadow the one under test.
        home_path = ":".join(p for p in path.split(":") if p.startswith(str(setup.home)))
        self.assertEqual(setup.remote_tool("PATH='%s' command -v pi" % home_path).stdout, str(pi) + "\n")
        self.assertEqual(setup.remote_tool("PATH='%s' pi list" % home_path).stdout, "gentle-pi\n")

    def test_platform_specific_log_locations(self):
        for system, suffix in (("Linux", ".local/state/agent-swarm/logs"),
                               ("Darwin", "Library/Logs/mac-agent-swarm")):
            with self.subTest(system=system):
                setup = self.make(local_system=system)
                setup.emit("progress")
                self.assertEqual(setup.log_path, setup.home / suffix / "swarm-setup-new-mac.log")
                self.assertEqual(setup.log_path.read_text(), "progress\n")
                self.assertEqual(setup.output.getvalue(), "progress\n")

    def test_linux_herdr_installer_requires_curl_and_install_missing(self):
        for enabled, curl in ((True, True), (True, False), (False, True)):
            with self.subTest(enabled=enabled, curl=curl):
                setup = self.make(no_wait=True, install_missing=enabled)
                calls = []; installed = []
                def remote(command, timeout=60, input=None):
                    calls.append((command, timeout))
                    if command == "uname -s": return Result(out="Linux\n")
                    if command.startswith("# agent-swarm-path"): return Result(out="/usr/bin:/bin\n")
                    command = command.removeprefix("PATH=/usr/bin:/bin ")
                    if command == "command -v curl": return Result(0 if curl else 1)
                    if command in ("command -v herdr", "herdr tab list"): return Result(0 if installed else 1)
                    if 'curl -fsSL https://herdr.dev/install.sh -o "$tmp"' in command:
                        installed.append(True); return Result()
                    return Result()
                setup.remote = remote
                if enabled and curl:
                    self.assertEqual(setup.runtimes(), ("changed", "installed herdr"))
                    self.assertTrue(any('curl -fsSL https://herdr.dev/install.sh -o "$tmp"' in command and timeout == 1200 for command, timeout in calls))
                    self.assertEqual(setup.output.getvalue(), "")
                else:
                    with self.assertRaises(Waiting): setup.runtimes()
                    self.assertEqual(installed, [])
                self.assertFalse(setup.state_path.exists())

    def test_dry_run_never_installs_runtimes_on_either_platform(self):
        for system in ("Darwin", "Linux"):
            with self.subTest(system=system):
                setup = self.make(dry_run=True, install_missing=True, no_wait=True)
                setup.discover_remote_path = lambda: None
                setup.remote_system_name = lambda: system
                calls = []
                def remote(command, *args):
                    calls.append(command)
                    return Result(1 if command in ("command -v herdr", "herdr tab list", "pi list 2>/dev/null | grep -F gentle-pi") else 0)
                setup.remote_tool = remote
                self.assertEqual(setup.runtimes(), ("changed", "would install herdr, would install gentle-pi"))
                self.assertFalse(any(" install " in command or "install.sh" in command for command in calls))
                self.assertEqual(setup.output.getvalue(), "")
                self.assertEqual(list(setup.home.iterdir()), [])
                self.assertEqual(setup.changed, [])

    def test_linux_installer_propagates_download_and_script_failures_and_cleans_up(self):
        for curl_code, script_code in ((22, 0), (0, 7), (0, 0)):
            with self.subTest(curl_code=curl_code, script_code=script_code):
                setup = self.make(install_missing=True, no_wait=True)
                setup.discover_remote_path = lambda: None
                setup.remote_system_name = lambda: "Linux"
                commands = []
                def remote(command, *args):
                    commands.append(command)
                    if "install.sh" in command: return Result(1)
                    return Result(1 if command in ("command -v herdr", "herdr tab list") else 0)
                setup.remote_tool = remote
                with self.assertRaises(Waiting): setup.runtimes()
                command = next(c for c in commands if "install.sh" in c)
                with tempfile.TemporaryDirectory() as scratch:
                    root = Path(scratch); tools = root / "bin"; tools.mkdir()
                    marker = root / "ran"
                    curl = tools / "curl"
                    curl.write_text('#!/bin/sh\n[ "$1" = "-fsSL" ] || exit 99\n[ "$3" = "-o" ] || exit 99\nprintf \'echo ran > "%s"; exit %s\\n\' > "$4"\nexit %s\n' % (marker, script_code, curl_code))
                    curl.chmod(0o755)
                    result = subprocess.run(["/bin/sh", "-c", command], capture_output=True, text=True,
                                            env=dict(os.environ, PATH=str(tools) + ":/usr/bin:/bin", TMPDIR=scratch))
                    self.assertEqual((result.returncode, result.stdout, result.stderr), (curl_code or script_code, "", ""))
                    self.assertEqual(marker.exists(), curl_code == 0)
                    self.assertEqual({p.name for p in root.iterdir()}, {"bin", "ran"} if marker.exists() else {"bin"})

    def test_macos_runtimes_still_require_homebrew(self):
        setup = self.make(no_wait=True)
        def remote(command, timeout=60, input=None):
            if command == "uname -s": return Result(out="Darwin\n")
            if command.startswith("# agent-swarm-path"): return Result(out="/usr/bin:/bin\n")
            return Result(1 if command.endswith("command -v brew") else 0)
        setup.remote = remote
        with self.assertRaises(Waiting): setup.runtimes()
        self.assertFalse(setup.state_path.exists())

    def test_remote_platform_probe_failure_is_not_treated_as_linux(self):
        setup = self.make()
        setup.remote = lambda *args, **kwargs: Result(1, "Linux\n")
        with self.assertRaisesRegex(SetupError, "Could not determine remote platform"):
            setup.remote_system_name()

    def test_local_os_does_not_select_remote_runtime_or_hostname_behavior(self):
        for local in ("Darwin", "Linux"):
            for target in ("Darwin", "Linux"):
                with self.subTest(local=local, target=target):
                    setup = self.make(local_system=local, no_wait=True, role="hub")
                    setup.origin = setup.registry.get("origin")
                    calls = []
                    hostname_command = "scutil --get LocalHostName" if target == "Darwin" else "hostname -s"
                    remote_home = ("/Users/remote" if local == "Darwin" else "/custom/home/remote") if target == "Darwin" else "/home/remote"
                    def remote(command, timeout=60, input=None):
                        calls.append(command)
                        if command.startswith("# agent-swarm-path"): return Result(out="/usr/bin:/bin\n")
                        if command == "uname -s": return Result(out=target + "\n")
                        if command == 'printf %s "$HOME"': return Result(out=remote_home)
                        command = command.removeprefix("PATH=/usr/bin:/bin ")
                        if command == hostname_command: return Result(out="Target\n")
                        if command == "command -v brew":
                            self.assertEqual(target, "Darwin")
                            return Result(out="/opt/homebrew/bin/brew\n")
                        if command == "command -v claude": return Result(1)
                        if command.startswith("command -v "): return Result(out="/usr/bin/tool\n")
                        if command in ("pi list 2>/dev/null | grep -F gentle-pi", "herdr tab list") or command.startswith("herdr integration status "): return Result()
                        self.fail("unexpected remote command: " + command)
                    setup.remote = remote
                    self.assertEqual(setup.runtimes(), ("ok", "required runtimes available"))
                    entry = setup.build_registry_entry()
                    self.assertEqual(entry["hostname_prefix"], "Target")
                    self.assertEqual(entry["gui_cwd"], remote_home + "/tmp")
                    self.assertEqual(entry["catalog_root"], "/catalog")
                    self.assertEqual(entry["runtimes"], ["pi"])
                    log_directory = "Library/Logs/mac-agent-swarm" if local == "Darwin" else ".local/state/agent-swarm/logs"
                    self.assertEqual(setup.log_path.parent, setup.home / log_directory)
                    self.assertEqual(sum(command.endswith("command -v brew") for command in calls), 2 if target == "Darwin" else 0)
                    self.assertEqual(calls.count("uname -s"), 1)
                    self.assertEqual(setup.output.getvalue(), "")
                    self.assertFalse(setup.state_path.exists())

    def test_darwin_installs_missing_herdr_with_homebrew_from_either_origin(self):
        for local in ("Darwin", "Linux"):
            with self.subTest(local=local):
                setup = self.make(local_system=local, no_wait=True, install_missing=True)
                calls = []; installed = []
                def remote(command, timeout=60, input=None):
                    calls.append((command, timeout))
                    if command.startswith("# agent-swarm-path"): return Result(out="/usr/bin:/bin\n")
                    if command == "uname -s": return Result(out="Darwin\n")
                    command = command.removeprefix("PATH=/usr/bin:/bin ")
                    if command in ("command -v herdr", "herdr tab list"): return Result(0 if installed else 1)
                    if command == "brew install herdr": installed.append("herdr"); return Result()
                    if command.startswith("command -v ") or command == "pi list 2>/dev/null | grep -F gentle-pi" or command.startswith("herdr integration status "): return Result()
                    self.fail("unexpected remote command: " + command)
                setup.remote = remote
                self.assertEqual(setup.runtimes(), ("changed", "installed herdr"))
                self.assertEqual(installed, ["herdr"])
                self.assertEqual([call for call in calls if " install " in call[0]], [("PATH=/usr/bin:/bin brew install herdr", 1200)])
                self.assertEqual(setup.output.getvalue(), "")
                self.assertFalse(setup.state_path.exists())

    def test_invalid_remote_platform_output_fails_closed_before_runtime_probes(self):
        for output in ("", "FreeBSD\n", "linux\n", "Linux\nDarwin\n"):
            with self.subTest(output=output):
                setup = self.make(no_wait=True, install_missing=True)
                calls = []
                def remote(command, timeout=60, input=None):
                    calls.append(command)
                    if command.startswith("# agent-swarm-path"): return Result(out="/usr/bin:/bin\n")
                    if command == "uname -s": return Result(out=output)
                    self.fail("invalid platform must stop remote probes: " + command)
                setup.remote = remote
                with self.assertRaises(SetupError) as raised:
                    setup.runtimes()
                self.assertEqual(str(raised.exception), "Could not determine remote platform (expected Darwin or Linux)")
                self.assertEqual(len(calls), 2)
                self.assertEqual(calls[-1], "uname -s")
                self.assertEqual(setup.output.getvalue(), "")
                self.assertFalse(setup.state_path.exists())
                self.assertEqual(setup.changed, [])
                self.assertEqual(setup.results, [])

    def test_remote_hostname_failure_rejects_empty_registry_prefix(self):
        setup = self.make()
        setup.remote_path = "/usr/bin:/bin"
        setup.remote = lambda command, *args, **kw: Result(out="Linux\n") if command == "uname -s" else Result(1)
        with self.assertRaisesRegex(SetupError, "Could not determine remote hostname"):
            setup.remote_facts()

    def test_dry_run_missing_base_runtimes_only_reports_requirements(self):
        for system in ("Linux", "Darwin"):
            with self.subTest(system=system):
                setup = self.make(dry_run=True, install_missing=True, no_wait=True)
                setup.discover_remote_path = lambda: None
                setup.remote_system_name = lambda: system
                calls = []

                def remote(command, *args):
                    calls.append(command)
                    return Result(1 if command in ("command -v node", "command -v pi", "command -v python3") else 0)

                setup.remote_tool = remote
                self.assertEqual(setup.runtimes(), ("changed", "would require missing runtimes: node, pi, python3"))
                self.assertFalse(any(" install " in command or "install.sh" in command for command in calls))
                self.assertEqual(list(setup.home.iterdir()), [])
                self.assertEqual(setup.output.getvalue(), "")

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

    def test_install_missing_help_documents_linux_installer(self):
        script = Path(__file__).parents[1] / "bin" / "swarm-setup"
        result = subprocess.run([sys.executable, str(script), "add-host", "--help"], text=True, capture_output=True)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        help_text = " ".join(result.stdout.split())
        self.assertIn("download https://herdr.dev/install.sh with curl and run with sh on Linux", help_text)
        self.assertIn("dry-run only reports planned installs", help_text)
        self.assertIn("herdr Pi integration", help_text)

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

    def test_multi_candidate_stale_alias_known_host_fails_closed_without_writes(self):
        setup = self.make(host_fingerprint="SHA256:ok", fallback_addresses=["lan.local"], no_wait=True)
        ssh = setup.home / ".ssh"; ssh.mkdir()
        key = ssh / "agent_swarm_new_mac"; key.write_text("key"); key.with_suffix(".pub").write_text("pub")
        known = ssh / "known_hosts"; known.write_text("swarm-new-mac ssh-ed25519 STALEKEY\nuser-entry ssh-ed25519 KEEP\n")
        original_known = known.read_bytes()
        def runner(argv, **kwargs):
            if argv[:1] == ["ssh"]: return Result(1)
            if argv[:1] == ["ssh-keyscan"]: return Result(out="%s ssh-ed25519 NEWKEY\n" % argv[-1])
            if argv[:2] == ["ssh-keygen", "-lf"]: return Result(out="256 SHA256:ok host\n")
            return Result()
        setup.runner = runner
        with self.assertRaisesRegex(SetupError, "swarm-new-mac.*verify and remove.*stale"):
            setup.ssh_to_new()
        self.assertFalse((ssh / "config").exists())
        self.assertEqual(known.read_bytes(), original_known)
        self.assertFalse(setup.state_path.exists())

    @unittest.skipUnless(shutil.which("ssh"), "ssh unavailable")
    def test_multi_candidate_alias_quotes_identity_file_for_home_with_spaces(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home with spaces"; key = home / ".ssh/agent_swarm_peer"
            config = Path(directory) / "config"
            config.write_text(Setup.alias_block("swarm-peer", "tailnet", "leo", str(key), 2222,
                                                ["tailnet", "192.168.1.2"], "/tmp/swarm-ssh-connect"))
            result = subprocess.run(["ssh", "-G", "-F", str(config), "swarm-peer"], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            values = dict(line.split(" ", 1) for line in result.stdout.splitlines() if " " in line)
            self.assertEqual(values["identityfile"], str(key))
            self.assertIn("--port 2222 -- tailnet 192.168.1.2", values["proxycommand"])

    def test_multi_candidate_different_key_fails_closed_without_alias_known_hosts_or_state(self):
        setup = self.make(host_fingerprint="SHA256:ok", fallback_addresses=["lan.local"])
        key = setup.home / ".ssh/agent_swarm_new_mac"; key.parent.mkdir(); key.write_text("key"); key.with_suffix(".pub").write_text("pub")
        def runner(argv, **kwargs):
            if argv[:1] == ["ssh"]: return Result(1)
            if argv[:1] == ["ssh-keyscan"]:
                return Result(out="%s ssh-ed25519 KEY\n" % argv[-1])
            if argv[:2] == ["ssh-keygen", "-lf"]:
                return Result(out="256 %s host\n" % ("SHA256:ok" if kwargs.get("input", "").startswith("New.local") else "SHA256:other"))
            return Result()
        setup.runner = runner
        with self.assertRaisesRegex(SetupError, "SSH host fingerprint mismatch"):
            setup.ssh_to_new()
        self.assertFalse((setup.home / ".ssh/config").exists())
        self.assertFalse((setup.home / ".ssh/known_hosts").exists())
        self.assertFalse(setup.state_path.exists())

    def test_multi_candidate_all_unreachable_uses_remote_login_wait(self):
        setup = self.make(fallback_addresses=["lan.local"], no_wait=True)
        setup.socket_check = lambda address, port: False
        with self.assertRaisesRegex(Waiting, "On new-mac: enable macOS Remote Login or a running sshd on Linux for user leo"):
            setup.remote_login()
        self.assertFalse((setup.home / ".ssh/config").exists())
        self.assertFalse((setup.home / ".ssh/known_hosts").exists())
        self.assertFalse(setup.state_path.exists())

    def test_multi_candidate_skips_unreachable_candidate_but_writes_one_alias_key(self):
        setup = self.make(host_fingerprint="SHA256:ok", fallback_addresses=["lan.local"])
        key = setup.home / ".ssh/agent_swarm_new_mac"; key.parent.mkdir(); key.write_text("key"); key.with_suffix(".pub").write_text("pub")
        def runner(argv, **kwargs):
            if argv[:1] == ["ssh"]: return Result(0 if "leo@New.local" in " ".join(argv) else 1)
            if argv[:1] == ["ssh-keyscan"]:
                return Result(1) if argv[-1] == "lan.local" else Result(out="New.local ssh-ed25519 KEY\n")
            if argv[:2] == ["ssh-keygen", "-lf"]: return Result(out="256 SHA256:ok host\n")
            return Result()
        setup.runner = runner
        setup.socket_check = lambda address, port: address == "New.local"
        self.assertEqual(setup.ssh_to_new(), ("changed", "configured SSH channel"))
        self.assertIn("SSH candidate unreachable: lan.local\n", setup.output.getvalue())
        config = (setup.home / ".ssh/config").read_text()
        self.assertIn("HostKeyAlias swarm-new-mac", config)
        self.assertIn("--port 22 -- New.local lan.local", config)
        self.assertEqual((setup.home / ".ssh/known_hosts").read_text(), "swarm-new-mac ssh-ed25519 KEY\n")

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
