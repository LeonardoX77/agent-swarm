"""Single-process, resumable setup for a new Agent Fabric Mac."""
from __future__ import annotations

import getpass
import hashlib
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from pathlib import Path

from host_registry import HostRegistry, RegistryError

NAME = re.compile(r"^[a-z0-9-]+$")
ADDRESS = re.compile(r"^[A-Za-z0-9.-]+$")
RESTRICTIONS = "no-agent-forwarding,no-port-forwarding,no-X11-forwarding "
PHASES = ("local-preflight", "remote-login", "ssh-to-new", "runtimes", "ssh-to-origin",
          "mount", "registry", "skill", "auto-update", "acceptance")


class SetupError(Exception):
    pass


class Waiting(SetupError):
    pass


class Setup:
    """Coordinate setup.  ``runner`` is deliberately the sole command boundary."""
    def __init__(self, name, address, user, *, role="spoke", host_fingerprint=None,
                 origin_user=None, auto_update=True, update_time="04:30", install_missing=False,
                 skip_live=False, dry_run=False, no_wait=False, wait_timeout=30, verbose=False,
                 registry=None, registry_path=None, runner=None, home=None, nodename=None,
                 tty=None, uid=None, output=None, sleep=None, clock=None, reader=None):
        self.name, self.address, self.user, self.role = name, address, user, role
        self.host_fingerprint, self.origin_user = host_fingerprint, origin_user
        self.auto_update, self.update_time, self.install_missing = auto_update, update_time, install_missing
        self.skip_live, self.dry_run, self.no_wait, self.wait_timeout, self.verbose = skip_live, dry_run, no_wait, wait_timeout, verbose
        self.registry = registry or HostRegistry(registry_path)
        self.runner = runner or self._subprocess
        self.home = Path(home) if home is not None else Path.home()
        self.nodename = nodename if nodename is not None else os.uname().nodename
        self.tty, self.uid = (sys.stdin.isatty() if tty is None else tty), (os.getuid() if uid is None else uid)
        self.output, self.sleep, self.clock = output or sys.stdout, sleep or time.sleep, clock or time.time
        self.reader = reader or input
        self.changed, self.results, self.phase_names = [], [], list(PHASES)
        self.remote_home = None
        self.state_path = self.home / ".local/state/agent-fabric/setup" / (name + ".json")
        self.log_path = self.home / "Library/Logs/mac-agent-fabric" / ("fabric-setup-" + name + ".log")
        self.state = self._read_state()

    @staticmethod
    def _subprocess(argv, **kwargs):
        kwargs.setdefault("text", True)
        kwargs.setdefault("capture_output", True)
        kwargs.setdefault("shell", False)
        return subprocess.run(argv, timeout=kwargs.pop("timeout", 45), **kwargs)

    def _read_state(self):
        try: return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError): return {"name": self.name, "phases": {}}

    @staticmethod
    def _atomic(path, data, mode=0o600):
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as target:
                target.write(data); target.flush(); os.fsync(target.fileno())
            os.chmod(temporary, mode); os.replace(temporary, str(path))
        finally:
            if os.path.exists(temporary): os.unlink(temporary)

    def _save_state(self):
        if not self.dry_run:
            self.state_path.parent.mkdir(parents=True, exist_ok=True); os.chmod(str(self.state_path.parent), 0o700)
            self._atomic(self.state_path, json.dumps(self.state, indent=2, sort_keys=True) + "\n")

    def _log(self, text):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as log:
            log.write(text + "\n")
            log.flush()

    def emit(self, text):
        self.output.write(text + "\n")
        self.output.flush()
        self._log(text)

    def command(self, argv, timeout=45, input=None):
        rendered = "$ " + " ".join(shlex.quote(str(x)) for x in argv)
        self._log(rendered)
        if self.verbose:
            self.output.write(rendered + "\n")
            self.output.flush()
        try: result = self.runner(argv, timeout=timeout, text=True, capture_output=True, input=input)
        except (OSError, subprocess.TimeoutExpired) as error: result = type("Result", (), {"returncode": 1, "stdout": "", "stderr": str(error)})()
        detail = "exit %s: %s" % (result.returncode, ((result.stdout or "") + (result.stderr or "")).strip()[:1000])
        self._log(detail)
        if self.verbose:
            self.output.write(detail + "\n")
            self.output.flush()
        return result

    def remote(self, command, timeout=60, input=None):
        return self.command(["ssh", "fabric-" + self.name, command], timeout, input)

    def tool_command(self, command):
        return "PATH=%s %s" % (self.remote_path, command) if getattr(self, "remote_path", None) else command

    def remote_tool(self, command, timeout=60, input=None):
        return self.remote(self.tool_command(command), timeout, input)

    def remote_python(self, program, args=()):
        """Run a reviewed Python 3.9 program remotely; values are JSON argv, never shell code."""
        command = "PYTHONDONTWRITEBYTECODE=1 python3 - " + " ".join(shlex.quote(json.dumps(x)) for x in args)
        return self.remote_tool(command, 60, program)

    def discover_remote_path(self):
        """Find user-tool directories without relying on an interactive shell profile."""
        program = """# agent-fabric-path
paths=''
add_path() { [ -d "$1" ] && paths="${paths:+$paths:}$1"; }
add_path /opt/homebrew/bin
add_path /usr/local/bin
nvm="$HOME/.nvm"; nvm_bin=''
if [ -f "$nvm/alias/default" ]; then
 version=$(tr -d '\\n' < "$nvm/alias/default")
 [ -d "$nvm/versions/node/$version/bin" ] && nvm_bin="$nvm/versions/node/$version/bin"
fi
if [ -z "$nvm_bin" ]; then
 best=''
 for candidate in "$nvm"/versions/node/*/bin; do
  [ -d "$candidate" ] || continue
  version=${candidate%/bin}; version=${version##*/}; version=${version#v}
  key=$(printf '%s' "$version" | awk -F. '{printf "%03d%03d%03d", $1, $2, $3}')
  if [ -z "$best" ] || [ "$key" \> "$best" ]; then best="$key"; nvm_bin="$candidate"; fi
 done
fi
[ -n "$nvm_bin" ] && add_path "$nvm_bin"
add_path "$HOME/.hermes/node/bin"
add_path "$HOME/.local/bin"
printf '%s\\n' "${paths:+$paths:}/usr/bin:/bin:/usr/sbin:/sbin"
"""
        result = self.remote(program)
        path = result.stdout.strip()
        if result.returncode or not path: raise SetupError("Could not discover remote PATH")
        self.remote_path = path; self.state["remote_path"] = path
        return path

    def remote_home_path(self, suffix=""):
        if self.remote_home is None:
            result = self.remote('printf %s "$HOME"')
            if result.returncode or not result.stdout.strip() or not result.stdout.strip().startswith("/"):
                raise SetupError("Could not determine remote home")
            self.remote_home = result.stdout.strip()
        return self.remote_home + suffix

    def socket_check(self, address, port=22):
        try:
            connection = socket.create_connection((address, port), timeout=3); connection.close(); return True
        except OSError: return False

    def wait_for(self, text, condition):
        """Poll every five seconds in this process; non-TTY is not a reason to stop."""
        self.emit(text)
        if self.no_wait: raise Waiting(text)
        deadline = self.clock() + self.wait_timeout * 60
        while True:
            if condition(): return
            if self.clock() >= deadline: raise Waiting(text)
            self.sleep(5)

    def mark(self, phase, status, detail=""):
        self.state["phases"][phase] = {"status": status, "timestamp": int(self.clock()), "last_error": detail or None}; self._save_state()
        self.emit("[%2d/10] %-15s %-8s %s" % (self.phase_names.index(phase) + 1, phase, status.upper(), detail))
        self.results.append((phase, status, detail))
        if status == "changed": self.changed.append(phase)

    @staticmethod
    def result(status, detail): return status, detail

    def local_preflight(self):
        if not NAME.fullmatch(self.name) or not ADDRESS.fullmatch(self.address) or not self.user: raise SetupError("Invalid host name, address, or user")
        self.origin = self.registry.self_host(self.nodename)
        if not self.origin: raise SetupError("This Mac is not the registry self_host")
        existing = self.registry.hosts.get(self.name)
        if existing and existing["address"] != self.address: raise SetupError("Existing host address does not match")
        for tool in ("ssh", "ssh-keygen", "ssh-keyscan"):
            if shutil.which(tool) is None: raise SetupError("Required tool is missing: " + tool)
        self.origin_user = self.origin_user or self.origin.get("user") or getpass.getuser()
        return self.result("ok", "origin preflight passed")

    def remote_login(self):
        if not self.socket_check(self.address): self.wait_for("On %s: System Settings > General > Sharing > Remote Login: ON for user %s" % (self.name, self.user), lambda: self.socket_check(self.address))
        return self.result("ok", "Remote Login reachable")

    def fingerprint(self, scan=False, remote=False):
        if scan:
            result = self.remote("ssh-keyscan -t ed25519 " + shlex.quote(self.origin["address"])) if remote else self.command(["ssh-keyscan", "-t", "ed25519", self.address])
            if result.returncode: raise SetupError("Could not scan SSH host key")
            result = self.remote("printf %s | ssh-keygen -lf -" % shlex.quote(result.stdout)) if remote else self.command(["ssh-keygen", "-lf", "-"], input=result.stdout)
        else: result = self.command(["ssh-keygen", "-lf", "/etc/ssh/ssh_host_ed25519_key.pub"])
        match = re.search(r"(SHA256:[A-Za-z0-9+/=]+)", result.stdout or "")
        if result.returncode or not match: raise SetupError("SSH fingerprint was not available")
        return match.group(1)

    def write_alias(self, config, alias, address, user, key):
        block = ("Host %s\n  HostName %s\n  User %s\n  IdentityFile %s\n  IdentitiesOnly yes\n  BatchMode yes\n  StrictHostKeyChecking yes\n  ConnectTimeout 15\n  ServerAliveInterval 15\n  ServerAliveCountMax 4\n  ForwardAgent no\n" % (alias, address, user, key))
        prior = config.read_text(encoding="utf-8") if config.exists() else ""
        found = re.search(r"(?ms)^Host " + re.escape(alias) + r"\s*$.*?(?=^Host |\Z)", prior)
        if found:
            if found.group(0).strip() != block.strip(): raise SetupError("SSH alias conflict for " + alias)
            return False
        if self.dry_run: return True
        config.parent.mkdir(parents=True, exist_ok=True); os.chmod(str(config.parent), 0o700)
        if config.exists(): config.with_name(config.name + ".fabric-setup-%s.bak" % int(self.clock())).write_text(prior, encoding="utf-8")
        with config.open("a", encoding="utf-8") as target: target.write(("\n" if prior and not prior.endswith("\n") else "") + block)
        os.chmod(str(config), 0o600); return True

    def ssh_to_new(self):
        if self.command(["ssh", "-o", "BatchMode=yes", "fabric-" + self.name, "true"]).returncode == 0: return self.result("ok", "SSH alias already configured")
        key = self.home / ".ssh" / ("agent_fabric_" + self.name.replace("-", "_")); changed = False
        if not key.exists():
            if self.dry_run: changed = True
            else:
                key.parent.mkdir(parents=True, exist_ok=True); os.chmod(str(key.parent), 0o700)
                if self.command(["ssh-keygen", "-t", "ed25519", "-f", str(key), "-N", "", "-C", "agent-fabric-to-" + self.name]).returncode: raise SetupError("Could not create SSH key")
                changed = True
        observed = self.fingerprint(scan=True)
        if self.host_fingerprint and observed != self.host_fingerprint: raise SetupError("SSH host fingerprint mismatch")
        if not self.host_fingerprint:
            hint = "Re-run with --host-fingerprint %s" % observed
            if not self.tty: raise Waiting("Host-key confirmation requires a TTY. " + hint)
            answer = self.reader("Type the fingerprint shown on %s (or yes): " % self.name).strip()
            if answer not in ("yes", observed): raise SetupError("SSH host fingerprint mismatch")
        if self.dry_run: return self.result("changed", "would configure SSH channel")
        scan = self.command(["ssh-keyscan", "-t", "ed25519", self.address]); known = self.home / ".ssh/known_hosts"
        lines = [line for line in scan.stdout.splitlines() if line]
        if scan.returncode or not lines: raise SetupError("Could not scan SSH host key")
        prior = known.read_text(encoding="utf-8") if known.exists() else ""
        missing_lines = [line for line in lines if line not in prior.splitlines()]
        if missing_lines:
            known.parent.mkdir(parents=True, exist_ok=True)
            with known.open("a", encoding="utf-8") as target: target.write(("" if not prior or prior.endswith("\n") else "\n") + "\n".join(missing_lines) + "\n")
            os.chmod(str(known), 0o600); changed = True
        public = key.with_suffix(".pub")
        try: line = RESTRICTIONS + public.read_text(encoding="utf-8").strip()
        except OSError: raise SetupError("Could not read SSH public key")
        authorization = "mkdir -p ~/.ssh && chmod 700 ~/.ssh && { touch ~/.ssh/authorized_keys && grep -qxF %s ~/.ssh/authorized_keys || printf '%%s\\n' %s >> ~/.ssh/authorized_keys; } && chmod 600 ~/.ssh/authorized_keys" % (shlex.quote(line), shlex.quote(line))
        instruction = "On %s run this exact command, then continue:\n%s" % (self.name, authorization)
        self.wait_for(instruction, lambda: self.command(["ssh", "-i", str(key), "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", self.user + "@" + self.address, "true"]).returncode == 0)
        changed = self.write_alias(self.home / ".ssh/config", "fabric-" + self.name, self.address, self.user, str(key)) or changed
        return self.result("changed" if changed else "ok", "configured SSH channel" if changed else "SSH alias already configured")

    def runtimes(self):
        self.discover_remote_path()
        probes = {"brew": "command -v brew", "herdr": "command -v herdr", "node": "command -v node", "pi": "command -v pi", "python3": "command -v python3", "gentle-pi": "pi list 2>/dev/null | grep -F gentle-pi", "herdr-server": "herdr tab list"}
        def missing(): return [n for n, command in probes.items() if self.remote_tool(command).returncode != 0]
        absent = missing(); changed = []
        if self.install_missing and "herdr" in absent and "brew" not in absent and self.remote_tool("brew install herdr", 1200).returncode == 0: changed.append("installed herdr")
        if self.install_missing and "gentle-pi" in absent and "pi" not in absent and self.remote_tool("pi install npm:gentle-pi", 600).returncode == 0: changed.append("installed gentle-pi")
        if missing(): self.wait_for("On %s: install missing runtimes and log Pi in once from the GUI" % self.name, lambda: not missing())
        return self.result("changed" if changed else "ok", ", ".join(changed) or "required runtimes available")

    def _remote_copy(self, source, destination, mode="700"):
        if self.dry_run: return
        destination = self.remote_home_path(destination[len("~"):] if destination.startswith("~") else destination)
        temporary = destination + ".fabric-setup-%s.tmp" % int(self.clock())
        if self.command(["scp", str(source), "fabric-" + self.name + ":" + temporary], 120).returncode: raise SetupError("Could not copy " + str(source))
        command = "mkdir -p %s && chmod %s %s && mv %s %s" % tuple([shlex.quote(str(Path(destination).parent)), mode, shlex.quote(temporary), shlex.quote(temporary), shlex.quote(destination)])
        if self.remote_tool(command).returncode: raise SetupError("Could not install remote file " + destination)

    def ssh_to_origin(self):
        if self.remote("ssh -o BatchMode=yes fabric-%s true" % self.origin["name"]).returncode == 0: return self.result("ok", "reverse SSH already configured")
        if self.dry_run: return self.result("changed", "would configure reverse SSH channel")
        home, key = self.remote_home_path(), None
        key = home + "/.ssh/agent_fabric_" + self.origin["name"].replace("-", "_")
        if self.remote("test -f %s || ssh-keygen -t ed25519 -f %s -N '' -C %s" % (shlex.quote(key), shlex.quote(key), shlex.quote("agent-fabric-to-" + self.origin["name"]))).returncode: raise SetupError("Could not create reverse SSH key")
        if self.fingerprint() != self.fingerprint(scan=True, remote=True): raise SetupError("Origin SSH host fingerprint mismatch")
        origin_scan = self.remote("ssh-keyscan -t ed25519 " + shlex.quote(self.origin["address"]))
        origin_lines = [line for line in origin_scan.stdout.splitlines() if line]
        if origin_scan.returncode or not origin_lines: raise SetupError("Could not scan origin SSH host key")
        known_program = """import json,pathlib,sys
p=pathlib.Path(json.loads(sys.argv[1])); lines=json.loads(sys.argv[2]); s=p.read_text() if p.exists() else ''; existing=s.splitlines(); missing=[line for line in lines if line not in existing]
if missing:
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(s+('' if not s or s.endswith('\\n') else '\\n')+'\\n'.join(missing)+'\\n')
"""
        if self.remote_python(known_program, (home + "/.ssh/known_hosts", origin_lines)).returncode: raise SetupError("Could not configure origin known hosts")
        public = self.remote("cat " + shlex.quote(key + ".pub"))
        if public.returncode: raise SetupError("Could not read reverse SSH public key")
        authorized = self.home / ".ssh/authorized_keys"; line = RESTRICTIONS + public.stdout.strip(); previous = authorized.read_text() if authorized.exists() else ""
        if line not in previous.splitlines():
            authorized.parent.mkdir(parents=True, exist_ok=True)
            if authorized.exists(): authorized.with_name("authorized_keys.fabric-setup-%s.bak" % int(self.clock())).write_text(previous)
            with authorized.open("a") as target: target.write(("" if not previous or previous.endswith("\n") else "\n") + line + "\n")
        alias = "fabric-" + self.origin["name"]
        block = "Host %s\n  HostName %s\n  User %s\n  IdentityFile %s\n  IdentitiesOnly yes\n  BatchMode yes\n  StrictHostKeyChecking yes\n  ConnectTimeout 15\n  ServerAliveInterval 15\n  ServerAliveCountMax 4\n  ForwardAgent no\n" % (alias, self.origin["address"], self.origin_user, key)
        program = """import json,pathlib,re,sys,time
p=pathlib.Path(json.loads(sys.argv[1])); block=json.loads(sys.argv[2]); s=p.read_text() if p.exists() else ''
m=re.search(r'(?ms)^Host '+re.escape(json.loads(sys.argv[3]))+r'\\s*$.*?(?=^Host |\\Z)',s)
if m and m.group(0).strip()!=block.strip(): raise SystemExit(9)
if not m:
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists(): p.with_name(p.name+'.fabric-setup-'+str(int(time.time()))+'.bak').write_text(s)
 p.write_text(s+('\\n' if s and not s.endswith('\\n') else '')+block)
"""
        result = self.remote_python(program, (home + "/.ssh/config", block, alias))
        if result.returncode == 9: raise SetupError("SSH alias conflict for " + alias)
        if result.returncode: raise SetupError("Could not configure reverse SSH alias")
        if self.remote("ssh -o BatchMode=yes fabric-%s true" % self.origin["name"]).returncode: raise SetupError("Reverse SSH verification failed")
        return self.result("changed", "configured reverse SSH channel")

    def mount(self):
        if self.role != "spoke": return self.result("skipped", "skipped for hub role")
        share = self.registry.share; vals = tuple(shlex.quote(share[x]) for x in ("host", "name", "user")); tool = self.remote_home_path("/.local/agent-fabric/bin/fabric-smb-mount")
        check = "%s status --host %s --share %s --user %s" % ((shlex.quote(tool),) + vals)
        if self.remote_tool(check).returncode == 0 and '"mounted": true' in self.remote_tool(check).stdout.lower(): return self.result("ok", "catalog already mounted")
        if self.dry_run: return self.result("changed", "would install persistent SMB mount")
        self._remote_copy(Path(__file__).resolve().parents[3] / "automation/agent-fabric/bin/fabric-smb-mount", "~/.local/agent-fabric/bin/fabric-smb-mount")
        command = "%s mount --host %s --share %s --user %s --persistent" % ((shlex.quote(tool),) + vals)
        if self.remote_tool(command, 120).returncode:
            self.wait_for("On %s, connect in Finder to smb://%s@%s/%s and save the password" % (self.name, share["user"], share["host"], share["name"]), lambda: self.remote_tool(check).returncode == 0 and '"mounted": true' in self.remote_tool(check).stdout.lower())
        if self.remote_tool("test -d " + shlex.quote("/Volumes/" + share["name"])).returncode: raise SetupError("Catalog is not visible after mount")
        return self.result("changed", "mounted catalog")

    def remote_facts(self):
        hostname = self.remote_tool("scutil --get LocalHostName").stdout.strip(); paths = []
        for tool in ("pi", "herdr", "python3"):
            value = self.remote_tool("command -v " + tool).stdout.strip()
            if not value: raise SetupError("Remote tool missing: " + tool)
            paths.append(str(Path(value).parent))
        return {"hostname_prefix": hostname, "path": self.remote_path, "claude": self.remote_tool("command -v claude").returncode == 0}

    def build_registry_entry(self):
        facts = self.remote_facts(); root = self.origin["catalog_root"]; relative = os.path.relpath(self.origin["repo"], root); catalog = "/Volumes/" + self.registry.share["name"] if self.role == "spoke" else root
        return {"hostname_prefix": facts["hostname_prefix"], "role": self.role, "ssh_alias": "fabric-" + self.name, "address": self.address, "catalog_root": catalog, "repo": str(Path(catalog) / relative), "path": facts["path"], "gui_cwd": "/Users/%s/tmp" % self.user, "runtimes": ["pi"] + (["claude"] if facts["claude"] else [])}

    def registry_phase(self):
        entry = self.build_registry_entry(); self.generated_registry_entry = entry; existing = self.registry.hosts.get(self.name)
        if existing and {k:v for k,v in existing.items() if k != "name"} == entry: return self.result("ok", "registry entry already configured")
        if self.dry_run: return self.result("changed", "would update registry entry")
        if self.remote_tool("mkdir -p " + shlex.quote(entry["gui_cwd"])).returncode: raise SetupError("Could not create remote GUI directory")
        raw = json.loads(self.registry.path.read_text(encoding="utf-8")); raw["hosts"][self.name] = entry; temporary = self.registry.path.with_name("." + self.registry.path.name + ".fabric-setup.tmp")
        temporary.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        try: HostRegistry(temporary)
        except RegistryError: raise SetupError("Generated registry entry is invalid")
        os.replace(str(temporary), str(self.registry.path)); self.registry = HostRegistry(self.registry.path)
        return self.result("changed", "registry changed: commit config/hosts.json")

    @staticmethod
    def canonical_digest(root):
        digest = hashlib.sha256()
        for item in sorted(p for p in root.rglob("*") if p.is_file()):
            digest.update(item.relative_to(root).as_posix().encode() + b"\0" + item.read_bytes() + b"\0")
        return digest.hexdigest()

    def skill(self):
        repository = Path(__file__).resolve().parents[3]; source = repository / "skills/agent-fabric-remote"; source_hash = self.canonical_digest(source)
        remote_program = """import hashlib,json,pathlib,sys
r=pathlib.Path(json.loads(sys.argv[1])); h=hashlib.sha256()
for p in sorted((x for x in r.rglob('*') if x.is_file()),key=lambda x:x.relative_to(r).as_posix()): h.update(p.relative_to(r).as_posix().encode()+b'\\0'+p.read_bytes()+b'\\0')
print(h.hexdigest())
"""
        runtimes = [("pi", "/.pi/agent/skills/agent-fabric-remote", "/.pi/agent/AGENTS.md")]
        target = self.registry.hosts.get(self.name, getattr(self, "generated_registry_entry", None))
        if target is None: raise SetupError("Registry entry is unavailable for skill installation")
        if "claude" in target["runtimes"]: runtimes.append(("claude", "/.claude/skills/agent-fabric-remote", "/.claude/CLAUDE.md"))
        if self.dry_run:
            inspect_program = """import hashlib,json,pathlib,re,sys
r=pathlib.Path(json.loads(sys.argv[1])); a=pathlib.Path(json.loads(sys.argv[2])); b=json.loads(sys.argv[3]); h=hashlib.sha256()
for p in sorted((x for x in r.rglob('*') if x.is_file()),key=lambda x:x.relative_to(r).as_posix()): h.update(p.relative_to(r).as_posix().encode()+b'\\0'+p.read_bytes()+b'\\0')
s=a.read_text() if a.exists() else ''; matches=re.findall(r'(?s)<!-- BEGIN AGENT-FABRIC-REMOTE-BOOTSTRAP -->.*?<!-- END AGENT-FABRIC-REMOTE-BOOTSTRAP -->',s)
print(json.dumps({'digest':h.hexdigest(),'bootstrap':len(matches)==1 and matches[0].strip()==b.strip()}))
"""
            changes = []
            for runtime, suffix, agents_suffix in runtimes:
                destination = self.remote_home_path(suffix); agents = self.remote_home_path(agents_suffix)
                block = (source / "assets/bootstrap-block.md").read_text(encoding="utf-8").replace("<REPO_PATH>", target["repo"]).rstrip() + "\n"
                inspected = self.remote_python(inspect_program, (destination, agents, block))
                try: status = json.loads(inspected.stdout)
                except (TypeError, ValueError): raise SetupError("Could not inspect remote %s skill" % runtime)
                if inspected.returncode or status.get("digest") != source_hash: changes.append("would copy %s skill" % runtime)
                if not status.get("bootstrap"): changes.append("would update %s bootstrap" % runtime)
            return self.result("changed" if changes else "ok", ", ".join(changes) or "skill and bootstrap already configured")
        changed = []
        for runtime, suffix, agents_suffix in runtimes:
            destination = self.remote_home_path(suffix); agents = self.remote_home_path(agents_suffix)
            remote_hash = self.remote_python(remote_program, (destination,)).stdout.strip()
            if remote_hash != source_hash:
                if self.dry_run: changed.append("would copy %s skill" % runtime)
                else:
                    backup = self.remote_home_path("/.local/state/agent-fabric/skill-backups/%s-agent-fabric-remote-%s" % (runtime, int(self.clock())))
                    if self.remote_tool("test ! -e %s || { mkdir -p %s && mv %s %s; }" % tuple(shlex.quote(x) for x in (destination, str(Path(backup).parent), destination, backup))).returncode: raise SetupError("Could not back up skill")
                    archive = self.home / (".local/state/agent-fabric/setup/skill-%s.tar" % runtime); archive.parent.mkdir(parents=True, exist_ok=True)
                    if self.command(["tar", "-cf", str(archive), "-C", str(source.parent), source.name]).returncode: raise SetupError("Could not package skill")
                    staged = "~/.local/state/agent-fabric/setup/" + archive.name; self._remote_copy(archive, staged, "600")
                    stage = self.remote_home_path("/.local/state/agent-fabric/setup")
                    if self.remote_tool("mkdir -p %s && tar -xf %s -C %s" % tuple(shlex.quote(x) for x in (str(Path(destination).parent), stage + "/" + archive.name, str(Path(destination).parent)))).returncode: raise SetupError("Could not install skill")
                    changed.append("copied %s skill" % runtime)
            if self.dry_run: continue
            block = (source / "assets/bootstrap-block.md").read_text(encoding="utf-8").replace("<REPO_PATH>", target["repo"]).rstrip() + "\n"
            program = """import json,pathlib,re,sys,time
p=pathlib.Path(json.loads(sys.argv[1])); b=json.loads(sys.argv[2]); s=p.read_text() if p.exists() else ''; pat=r'(?s)<!-- BEGIN AGENT-FABRIC-REMOTE-BOOTSTRAP -->.*?<!-- END AGENT-FABRIC-REMOTE-BOOTSTRAP -->\\s*'; n,c=re.subn(pat,b,s)
if c>1: raise SystemExit(9)
if not c: n=s+('\\n' if s and not s.endswith('\\n') else '')+b
if n!=s:
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists(): p.with_name(p.name+'.fabric-setup-'+str(int(time.time()))+'.bak').write_text(s)
 p.write_text(n)
"""
            result = self.remote_python(program, (agents, block))
            if result.returncode == 9: raise SetupError("Multiple bootstrap blocks in " + agents)
            if result.returncode: raise SetupError("Could not install bootstrap")
        return self.result("changed" if changed else "ok", ", ".join(changed) or "skill and bootstrap already configured")

    def auto_update_phase(self):
        if not self.auto_update: return self.result("skipped", "skipped by --no-auto-update")
        hour, minute = self.update_time.split(":"); executable = self.remote_home_path("/.local/agent-fabric/bin/fabric-update"); status = self.remote_tool(shlex.quote(executable) + " status")
        if status.returncode == 0 and ('"hour": %d' % int(hour)) in status.stdout and ('"minute": %d' % int(minute)) in status.stdout and '"loaded": true' in status.stdout.lower(): return self.result("ok", "daily update already configured")
        if self.dry_run: return self.result("changed", "would install daily update at " + self.update_time)
        self._remote_copy(Path(__file__).resolve().parents[3] / "automation/agent-fabric/bin/fabric-update", "~/.local/agent-fabric/bin/fabric-update")
        if self.remote_tool(shlex.quote(executable) + " install --hour %s --minute %s" % (hour, minute), 120).returncode: raise SetupError("Could not install auto-update")
        return self.result("changed", "installed daily update at " + self.update_time)

    def acceptance(self):
        if self.dry_run:
            configured = self.state["phases"].get("acceptance", {}).get("status") == "ok" and not self.changed
            return self.result("ok" if configured else "changed", "acceptance already configured" if configured else "would run live acceptance (no prior accepted state or other phases would change)")
        local = Path(__file__).resolve().parents[3] / "automation/agent-fabric/bin/fabric-delegate"
        if self.command([str(local), "preflight", self.name]).returncode: raise SetupError("Origin preflight failed")
        remote_delegate = self.registry.get(self.name)["repo"] + "/automation/agent-fabric/bin/fabric-delegate"
        if self.remote_tool(shlex.quote(remote_delegate) + " preflight " + shlex.quote(self.origin["name"])).returncode: raise SetupError("Remote preflight failed")
        if self.skip_live or (self.state["phases"].get("acceptance", {}).get("status") == "ok" and not self.changed): return self.result("skipped", "live acceptance skipped")
        # Delegates own task lifecycle; reject every response that does not return the nonce.
        new_host = self.registry.get(self.name)
        directions = (
            (self.name, self.origin["name"], os.path.relpath(self.origin["repo"], self.origin["catalog_root"]),
             [str(local), "submit", self.name], [str(local), "recover", self.name], [str(local), "close", self.name]),
            (self.origin["name"], self.name, os.path.relpath(new_host["repo"], new_host["catalog_root"]),
             ["ssh", "fabric-" + self.name, self.tool_command(shlex.quote(remote_delegate) + " submit " + shlex.quote(self.origin["name"]))],
             ["ssh", "fabric-" + self.name, self.tool_command(shlex.quote(remote_delegate) + " recover " + shlex.quote(self.origin["name"]))],
             ["ssh", "fabric-" + self.name, self.tool_command(shlex.quote(remote_delegate) + " close " + shlex.quote(self.origin["name"]))]),
        )
        for target, origin_host, project, submit, recover, close in directions:
            nonce, task_id = "ACCEPT_" + uuid.uuid4().hex, str(uuid.uuid4())
            envelope = json.dumps({"task_id": task_id, "origin_host": origin_host, "project": project,
                                   "goal": "Reply with exactly %s and nothing else." % nonce,
                                   "acceptance": "Return the exact nonce.", "mode": "executor"})
            response = self.command(submit, input=envelope)
            response_text = ((response.stdout or "") + (response.stderr or "")).strip()
            if "Not logged in" in response_text:
                # A GUI login cannot be probed safely; re-run after completing it.
                raise Waiting("Log Pi in from the GUI on %s" % target)
            if response.returncode:
                diagnostic = "REMOTE_FAILURE"
                for raw in (response.stdout, response.stderr):
                    try: report = json.loads(raw)
                    except (TypeError, ValueError): continue
                    if isinstance(report, dict) and isinstance(report.get("diagnostic_code"), str):
                        diagnostic = report["diagnostic_code"]; break
                raise SetupError("Acceptance submit failed for %s: %s; remote output: %s" % (target, diagnostic, response_text[:500]))
            # The remote delegate command is a single SSH argument, so append its task args there.
            recovery = recover + [task_id, "--wait", "120"] if recover[0] != "ssh" else recover[:2] + [recover[2] + " " + shlex.quote(task_id) + " --wait 120"]
            recovered = self.command(recovery, 180)
            if recovered.returncode or nonce not in ((recovered.stdout or "") + (recovered.stderr or "")): raise SetupError("Acceptance nonce mismatch for " + target)
            closing = close + [task_id] if close[0] != "ssh" else close[:2] + [close[2] + " " + shlex.quote(task_id)]
            if self.command(closing).returncode: raise SetupError("Could not close acceptance task for " + target)
        return self.result("ok", "bidirectional acceptance passed")

    def run(self):
        if self.uid == 0: self.emit("FAILED Refusing to run as root"); return 2
        methods = (self.local_preflight, self.remote_login, self.ssh_to_new, self.runtimes, self.ssh_to_origin, self.mount, self.registry_phase, self.skill, self.auto_update_phase, self.acceptance)
        try:
            for phase, method in zip(PHASES, methods):
                status, detail = method(); self.mark(phase, status, detail)
            self.emit("Summary: %s; changed phases: %s" % ("dry run complete" if self.dry_run else "setup complete", ", ".join(self.changed) or "none"))
            return 4 if self.dry_run and self.changed else 0
        except Waiting as error:
            phase = PHASES[len(self.results)]; self.mark(phase, "waiting", str(error)); self.emit("Waiting for a person: %s. Re-run the same command to resume." % error); return 10
        except (SetupError, RegistryError) as error:
            phase = PHASES[min(len(self.results), len(PHASES)-1)]; self.mark(phase, "failed", str(error)); return 1
        except Exception as error:
            phase = PHASES[min(len(self.results), len(PHASES)-1)]; self.mark(phase, "failed", "Unexpected %s (see log)" % error.__class__.__name__)
            self._log(traceback.format_exc().rstrip())
            self.emit("Log: " + str(self.log_path)); return 1
