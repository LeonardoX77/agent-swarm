# Add a machine to the Agent Swarm channel

The canonical path to add a macOS or Linux/WSL machine is to run **one command** from an already registered node. `swarm-setup` coordinates ten phases, pauses for human actions, and preserves state so the same operation can resume. Linux/WSL runs the same ten phases with CIFS and systemd user timers; a real delegation to this WSL has been tested, but not bidirectional acceptance between two machines (see the linked evidence below).

## Quick path

### Requirements

- The origin node (macOS or Linux/WSL) is already registered in `config/hosts.json`, and you run the command from its repository checkout. This file is local and unversioned: if absent, copy `config/hosts.example.json` and replace examples with real values.
- For the following macOS path, the new machine runs macOS and a person can sit in front of it for GUI steps. For Linux/WSL, follow [preparation](#linuxwsl-preparation).
- **Pi and gentle-pi are required; Claude is optional; Herdr is required.**
- LAN or Tailscale connectivity to `<host>.local` exists, and the new machine's `<user>` account is known.

From the registered Mac, run:

```sh
automation/agent-swarm/bin/swarm-setup add-host \
  --name <name> --address <host>.local --user <user> \
  [--host-fingerprint SHA256:...] [--install-missing] \
  [--update-time 04:30 | --no-auto-update] [--verbose]
```

The default installs daily updates at `04:30`; use `--no-auto-update` to leave that schedule disabled. This does not install an update check on first remote use: that is separate functionality. Agent Swarm neither manages nor guarantees package notices Pi may show when it starts. `--install-missing` uses existing tools and attempts only Herdr, gentle-pi, and the official Herdr Pi integration when their base CLIs are available; it does not reinstall the entire Mac. The process prints a brief English summary, for example:

```text
[ 1/10] local-preflight OK       origin preflight passed
...
[10/10] acceptance      OK       bidirectional acceptance passed
Summary: setup complete; changed phases: ssh-to-new, registry, skill, auto-update
```

On success it exits `0`. Review the entry setup added to `config/hosts.json`. That Git-ignored file is not committed; if its structure must be shared, update `config/hosts.example.json` with generic values. Do not copy `share` values by hand: the script reads them from the registry.

> If interrupted or waiting for a person, run **the same command with the same options** again from the origin. It rechecks every phase and preserves completed configuration; do not generate another fingerprint or accept a different one without local verification.

## Runtime prerequisites (macOS and Linux)

The official Herdr Pi integration is required, not just gentle-pi. Check it with `herdr integration status` (`pi: not installed` is not ready), or install it with `herdr integration install pi`. It installs `~/.pi/agent/extensions/herdr-agent-state.ts`. The adapter proves ownership through `agent_session` (kind `path`, source `herdr:pi`); without that integration, submit can return `unknown` without delivering the prompt. `--install-missing` installs it when herdr is available and reports `installed herdr pi integration`; dry-run only reports the planned install.

On headless Linux, start the server by running `herdr` in a normal terminal and then detaching, or use a pty with a non-zero grid (rows and columns). Herdr 0.9.5 rejects a zero-sized terminal with `cannot attach without a usable terminal: terminal reported a zero-sized grid`. The server survives the client exiting. There is no `herdr server start` command in that version (`server` only offers `stop` and `reload-config`). Check readiness with `herdr tab list`; `server_not_running` means the server still needs starting. Setup never starts or restarts it automatically.

Both setup and swarm-update discover `$HOME/.pi/agent/bin` (Pi's own installer) immediately after `$HOME/.local/bin`, retaining the existing Homebrew, nvm, Hermes, and system directories and their order. No interactive shell profile is needed.

## Linux/WSL: preparation

Enable SSH and prepare Node, Python 3, and Pi on the target, make the Herdr server available, and complete Pi login locally. With `--install-missing`, setup can install Herdr using the official installer at https://herdr.dev/install.sh (downloads it to a temporary file with `curl -fsSL`, runs it only if the download succeeds, and removes it; requires curl), and gentle-pi with `pi install npm:gentle-pi` if Pi exists; it does not install Node, Python, or Pi.

On WSL, Windows OpenSSH often occupies port 22: if WSL's `sshd` listens, for example, on `127.0.0.1:2222`, use `--address 127.0.0.1 --ssh-port 2222` from an origin that can reach that address. Use `--origin-ssh-port 2222` if the target must return to the origin through that port. Both default to 22. The SSH config alias includes the port (`Port` only if it is not 22); the registry schema does not change. Resume with the same ports: changing them causes an alias-conflict error, never a silent overwrite.

For a spoke, prepare CIFS as described in [SMB mounting](../runbooks/agent-swarm/smb-mount.md#linuxwsl-preparation): `swarm-smb-mount fstab-line --host H --share S --user U` prints the exact line and credentials template. A person adds the line to `/etc/fstab` as root, creates `/mnt/<share>`, and creates `~/.config/agent-swarm/smb-credentials` with mode `0600`. The tool never uses sudo or handles passwords. Setup mounts the catalog and enables a user timer every 300 seconds; if `systemctl --user` is unavailable, mounting can work but persistence degrades with a warning.

The spoke catalog is `/mnt/<share>` (macOS: `/Volumes/<share>`). The registry retains the project path relative to the origin catalog: for example, `/srv/projects/agent-swarm` below `/srv/projects` becomes `/mnt/shared-projects/agent-swarm`. The registry uses `gui_cwd` = `$HOME/tmp` on the target and creates that directory; hostname prefixes are compared case-insensitively. `swarm-delegate` prefers `/usr/bin/python3` and otherwise resolves `python3` from the registry PATH.

The update phase installs the systemd user `agent-swarm-update.timer` at 04:30 unless `--no-auto-update`; unlike SMB persistence, it fails if the user manager is unavailable. Linux update logs are in `~/.local/state/agent-swarm/logs`. SMB mount services write there unless HOME cannot be represented in a systemd directive; in that case, use the user journal (`journalctl --user -u <label>.service`).

In WSL, enable systemd in `/etc/wsl.conf`:

```ini
[boot]
systemd=true
```

User timers run only while the user has a session unless `loginctl enable-linger $USER` is enabled. A Linux hub must publish the catalog manually through its own SMB server, such as Samba; setup does not configure it. Windows can occupy TCP 445 on loopback, so local SMB testing needs another port. See the [evidence and limits](../runbooks/agent-swarm/test-evidence.md#linuxwsl-evidence).

## The ten phases

The following phase names are printed by the program exactly. Both platforms run all ten phases; `mount` is skipped for a hub and `auto-update` only with `--no-auto-update`.

| Phase | What the script does | Who acts | Exact stop message |
| --- | --- | --- | --- |
| `local-preflight` | Validates name, address, SSH tools, and that the origin is registry `self_host`. | Agent | Does not wait for a person. |
| `remote-login` | Checks that the new machine's SSH port is reachable. | Person | `On <name>: enable macOS Remote Login or a running sshd on Linux for user <user>` |
| `ssh-to-new` | Creates/reuses origin→new key, verifies fingerprint, configures `known_hosts`, authorizes the key, and creates `swarm-<name>`. | Person and agent | TTY: `Type the fingerprint shown on <name> (or yes): `; key: `On <name> run this exact command, then continue:` followed by the authorization command. |
| `runtimes` | Checks Node, Python, Herdr, Pi, gentle-pi, the Herdr Pi integration and server, plus Homebrew only on macOS; `--install-missing` can add Herdr, gentle-pi, and the integration. | Person | macOS retains `On <name>: install missing runtimes and log Pi in once from the GUI` and adds `; missing probes: <names>`; Linux uses `locally` instead of `from the GUI` and adds start instructions when `herdr-server` is missing. |
| `ssh-to-origin` | Configures reverse new→origin SSH, including origin fingerprint and remote alias. | Agent | Does not wait. Fingerprint or alias conflict fails safely. |
| `mount` | On a `spoke`, copies the mount utility and installs persistent SMB mounting from registry `share`. | Person | macOS: `On <name>, connect in Finder to smb://<share.user>@<share.host>/<share.name> and save the password`; Linux: target-specific generated fstab and credential instructions. |
| `registry` | Discovers new-host data and writes its `config/hosts.json` entry. | Agent | Does not wait. |
| `skill` | Copies the `agent-swarm-remote` skill and bootstrap block. | Agent | Does not wait. |
| `auto-update` | Installs `swarm-update` plus LaunchAgent (macOS) or systemd user timer (Linux), except with `--no-auto-update`. | Agent | Does not wait. |
| `acceptance` | Runs preflight in both directions and Herdr + Pi acceptance. | Person and agent | If Pi lacks a session: `Log Pi in from the GUI on <target>` |

`<name>`, `<user>`, `<share.user>`, `<share.host>`, `<share.name>`, and `<target>` are concrete values substituted by the script.

## Human interventions

The process checks conditions every **5 seconds**, up to `--wait-timeout` minutes (30 by default). It continues after detecting the condition; no button press is needed. If time expires, or `--no-wait` was used, it exits with a resumption hint; rerun the same command. **`--no-wait` does not poll again for a condition that just failed**. To resume, omit it or use `--wait-timeout 0` to check once without extended waiting.

### Remote Login, fingerprint, and origin key

The remote-login message is `On <name>: enable macOS Remote Login or a running sshd on Linux for user <user>`. On a Mac, open **System Settings → General → Sharing → Remote Login**, enable it, and authorize `<user>`; on Linux, run an `sshd` for that account. Continue when the chosen `--ssh-port` (22 by default) responds from the origin.

For a fingerprint, the script displays `Type the fingerprint shown on <name> (or yes): `. Without a TTY it waits with `Re-run with --host-fingerprint SHA256:...`. Read the local value with:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Compare it with the origin scan. Supply the verified value with `--host-fingerprint SHA256:...`, or enter it (or `yes`) in a TTY only after local verification. Never disable `StrictHostKeyChecking`.

The displayed authorization command contains the origin public key prefixed `no-agent-forwarding,no-port-forwarding,no-X11-forwarding `. Review and run it exactly on the new machine. It creates `~/.ssh` mode `700`, adds the restricted line only if absent, and leaves `authorized_keys` mode `600`. The phase continues when origin key authentication works.

### Runtimes, SMB, and Pi login

The probes are `herdr`, `node`, `pi`, `python3`, `gentle-pi`, `herdr-server`, `herdr-pi-integration`, and `brew` only on macOS. Install Node, Python 3, Pi, gentle-pi, and Herdr as needed (Homebrew only on macOS), open Pi locally to complete provider login, and start Herdr. With `--install-missing`, setup tries `brew install herdr` on macOS when Homebrew responds, the official Herdr installer on Linux when curl responds, and `pi install npm:gentle-pi` when Pi responds; it does not install Homebrew, Node, or Pi. For noninteractive SSH it discovers usual tool directories, including nvm `default` (or highest Node), and uses that PATH.

For macOS SMB, connect in Finder to `smb://<share.user>@<share.host>/<share.name>`, authenticate, and store the password in Keychain. It continues when the catalog is visible at `/Volumes/<share.name>`. On Linux, follow the CIFS preparation above and run the mount command setup prints; it continues when it detects the mount. Never put a password in a terminal, command, file, or log.

When acceptance reports `Not logged in`, it displays `Log Pi in from the GUI on <target>`. Sign in and run a harmless query in Pi on that host, then rerun the same command. This condition is not automatically polled.

## Options, state, and diagnosis

| Option | Use |
| --- | --- |
| `--name`, `--address`, `--user` | Required registry name, address, and account. |
| `--role {hub,spoke}` | New-host role; default `spoke`. |
| `--host-fingerprint SHA256:...` | Previously verified fingerprint; skips TTY prompt. |
| `--origin-user USER` | Account used by reverse channel. |
| `--ssh-port PORT` | Target sshd port, 1–65535; default 22. |
| `--origin-ssh-port PORT` | Origin sshd port used by target, 1–65535; default 22. |
| `--install-missing` | Herdr via Homebrew (macOS) or official curl installer (Linux); gentle-pi via Pi; Pi integration via `herdr integration install pi` on both. |
| `--auto-update` / `--no-auto-update` | Enables (default) or omits the daily schedule: launchd on macOS, systemd user service on Linux. |
| `--update-time HH:MM` | Daily time; default `04:30`. |
| `--skip-live` | Skips live task acceptance but retains preflight. |
| `--dry-run` | Writes no state/configuration; returns `4` if changes would occur. |
| `--no-wait` | Records a pending phase and returns `10` instead of waiting. |
| `--wait-timeout MINUTES` | 0–1440; default 30. |
| `--verbose` | Adds commands, exit codes, and truncated output. |
| `--registry PATH` | Uses an alternate registry. |

Exit codes: `0` complete/already configured; `1` setup or unexpected error; `2` invalid input/root execution; `4` `--dry-run` found changes; `10` awaits human action or timed out.

Inspect state with:

```sh
automation/agent-swarm/bin/swarm-setup status --name <name>
```

State is `~/.local/state/agent-swarm/setup/<name>.json`. The log is `~/Library/Logs/mac-agent-swarm/swarm-setup-<name>.log` for a macOS origin and `~/.local/state/agent-swarm/logs/swarm-setup-<name>.log` for Linux/WSL. Share only sanitized diagnostics: logs can contain **public** keys, paths, and usernames. If setup exits `0`, also confirm `automation/agent-swarm/bin/swarm-delegate preflight <name>` returns `"status": "ready"`. Do not mistake `WAITING` or partial SSH success for final acceptance. Rerunning an already configured host is safe: compliant phases report `OK`; a conflicting address, fingerprint, or SSH alias fails instead of overwriting it.

## Manual procedure (reference)

Use this macOS appendix only to diagnose a phase that cannot complete through `swarm-setup`; for Linux/WSL, follow [preparation](#linuxwsl-preparation).

1. On the new Mac, enable Remote Login; prepare Homebrew, Node, Pi, gentle-pi, and Herdr; complete Pi login and open Herdr in the GUI.
2. Configure both SSH directions with dedicated keys, locally verified fingerprints, `known_hosts`, restricted `authorized_keys`, and `swarm-<target>` aliases. Follow the [SSH channel runbook](../runbooks/agent-swarm/ssh-channel.md).
3. In the spoke Finder, perform first SMB access, save the password in Keychain, and install persistent mounting. Follow [SMB mounting](../runbooks/agent-swarm/smb-mount.md).
4. Register the host with correct local values, install the skill and bootstrap, validate preflight in both directions, and commit the registry through the approved workflow.

## Rollback

`swarm-setup` has no rollback subcommand. With owner authorization, remove only artifacts created for this onboarding: registry entry and commit, dedicated SSH aliases and keys, added authorization lines, new-host skill/bootstrap, and persistent SMB mount. Do not delete reused keys, backups, or entries containing unrelated changes. See [SSH channel](../runbooks/agent-swarm/ssh-channel.md#per-direction-rollback) and [SMB mounting](../runbooks/agent-swarm/smb-mount.md).

## Common problems

| Symptom | Safe action |
| --- | --- |
| `Not logged in` | Sign in to Pi from the indicated host's **GUI**; do not authenticate over SSH. Rerun the same command. |
| Setup waits for runtimes though Pi works in Terminal | Review nvm default/installed version, noninteractive PATH directories, and remote CLI results. A remote zsh without nvm versions must not fail on a nonmatching glob; if `no matches found` appears, use a setup version with that fix. |
| Fingerprint mismatch | Stop. Compare local reading and network scan; do not use `StrictHostKeyChecking=no`. |
| Authorization command fails | Verify it ran fully and did not alter the restricted public key printed by setup. |
| First remote copy fails with `scp: dest open ... No such file or directory` | The target parent directory does not exist. Use a setup version that creates it before `scp`; do not redirect the destination or broaden permissions. |
| SMB mount does not appear | On macOS use Finder/Keychain; on Linux inspect fstab and credentials. Follow the SMB runbook; do not place a password in the terminal. |
| Existing name has another address | It is not overwritten: correct the registry decision or use the correct host. |
| A phase reports `WAITING` after action | If `--no-wait` was used, rerun without it (or use `--wait-timeout 0`); verify the condition, state, and log. |

## References

- [Automatic updates](../runbooks/agent-swarm/auto-update.md)
- [Bidirectional SSH channel](../runbooks/agent-swarm/ssh-channel.md)
- [SMB mounting between machines](../runbooks/agent-swarm/smb-mount.md)
