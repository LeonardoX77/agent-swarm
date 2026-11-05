# Add a Mac to the Agent Swarm channel

The canonical way to add a new Mac is to run **one command** from an already registered Mac. `swarm-setup` coordinates ten phases, pauses only for human actions, and preserves state so the same operation can resume.

## Quick path

### Requirements

- The origin Mac is already registered in `config/hosts.json` and you run the command from its repository checkout. This file is local and unversioned: if absent, copy `config/hosts.example.json` and replace examples with real values.
- The new Mac runs macOS and a person can sit in front of it for GUI steps.
- **Pi and gentle-pi are required; Claude is optional; Herdr is required.**
- LAN or Tailscale connectivity to `<host>.local` exists and the new Mac's `<user>` account is known.

From the registered Mac, run:

```sh
automation/agent-swarm/bin/swarm-setup add-host \
  --name <name> --address <host>.local --user <user> \
  [--host-fingerprint SHA256:...] [--install-missing] \
  [--update-time 04:30 | --no-auto-update] [--verbose]
```

The default installs daily updates at `04:30`; use `--no-auto-update` to leave that schedule disabled. This does not install an update check on first remote use: that is separate functionality. Agent Swarm neither manages nor guarantees package notices Pi may show when it starts. `--install-missing` uses existing tools and attempts only Herdr and gentle-pi when their base CLIs are available; it does not reinstall the entire Mac. The process prints a brief English summary, for example:

```text
[ 1/10] local-preflight OK       origin preflight passed
...
[10/10] acceptance      OK       bidirectional acceptance passed
Summary: setup complete; changed phases: ssh-to-new, registry, skill, auto-update
```

On success it exits `0`. Review the entry setup added to `config/hosts.json`. That Git-ignored file is not committed; if its structure must be shared, update `config/hosts.example.json` with generic values. Do not copy `share` values by hand: the script reads them from the registry.

> If interrupted or waiting for a person, run **the same command with the same options** again from the origin. It rechecks every phase and preserves completed configuration; do not generate another fingerprint or accept a different one without local verification.

## The ten phases

The following phase names are printed by the program exactly.

| Phase | What the script does | Who acts | Exact stop message |
| --- | --- | --- | --- |
| `local-preflight` | Validates name, address, SSH tools, and that the origin is the registry `self_host`. | Agent | Does not wait for a person. |
| `remote-login` | Checks that the new Mac's SSH port is reachable. | Person | `On <name>: System Settings > General > Sharing > Remote Login: ON for user <user>` |
| `ssh-to-new` | Creates or reuses the origin→new key, verifies fingerprint, configures `known_hosts`, authorizes the key, and creates `swarm-<name>`. | Person and agent | TTY fingerprint: `Type the fingerprint shown on <name> (or yes): `; key: `On <name> add the displayed public key to ~/.ssh/authorized_keys, then continue.` |
| `runtimes` | Checks Homebrew, Node, Python, Herdr, Pi, gentle-pi, and the Herdr server; with `--install-missing`, attempts only Herdr and gentle-pi when prerequisites already exist. | Person | `On <name>: install missing runtimes and log Pi in once from the GUI` |
| `ssh-to-origin` | Configures the reverse new→origin SSH channel, including the origin fingerprint and remote alias. | Agent | Does not wait for a person. A fingerprint or alias conflict fails safely. |
| `mount` | On a `spoke`, copies the mount utility and installs persistent SMB mounting using registry `share`. | Person | `On <name>, connect in Finder to smb://<share.user>@<share.host>/<share.name> and save the password` |
| `registry` | Discovers new-host data and writes its `config/hosts.json` entry. | Agent | Does not wait for a person. |
| `skill` | Copies the `agent-swarm-remote` skill and bootstrap block to the new Mac. | Agent | Does not wait for a person. |
| `auto-update` | Installs `swarm-update` and its daily LaunchAgent unless `--no-auto-update` is set. | Agent | Does not wait for a person. |
| `acceptance` | Runs preflight in both directions and Herdr + Pi acceptance tests. | Person and agent | If Pi lacks a session: `Log Pi in from the GUI on <target>` |

`<name>`, `<user>`, `<share.user>`, `<share.host>`, `<share.name>`, and `<target>` are concrete values substituted by the script.

## Human interventions

The process checks conditions every **5 seconds** for `--wait-timeout` minutes (30 by default). No button press is required after intervention: the process continues when it detects the condition. If time expires, or `--no-wait` was used, it exits with a resumption hint; run the same command again. **`--no-wait` does not poll again for a condition that just failed**: even after a person intervenes, a phase can end in `WAITING` without a second check. To resume, omit the option or use `--wait-timeout 0` to check once without extended waiting.

### Remote Login

**The script displays:** `On <name>: System Settings > General > Sharing > Remote Login: ON for user <user>`.

**The person does:** On the new Mac, open **System Settings → General → Sharing → Remote Login**, enable it, and authorize `<user>`. Also confirm the selected network.

**Continues when:** port 22 responds from the origin.

### Host fingerprint

**The script displays:** in a TTY, `Type the fingerprint shown on <name> (or yes): `. Without a TTY it cannot request confirmation and waits with `Re-run with --host-fingerprint SHA256:...`.

**The person does:** Read the local fingerprint on the new Mac:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Compare it to the fingerprint observed from the origin. Supply the previously verified value noninteractively with `--host-fingerprint SHA256:...`; in a TTY you may also enter that exact fingerprint or `yes` after local verification. Never disable `StrictHostKeyChecking`.

**Continues when:** the supplied fingerprint matches the SSH scan.

### Authorize the origin key

**The script displays:** a single-line command containing the origin public key with prefix `no-agent-forwarding,no-port-forwarding,no-X11-forwarding `.

**The person does:** Review and run exactly that command on the new Mac. It creates `~/.ssh` mode `700`, adds the restricted line only when absent, and leaves `authorized_keys` mode `600`.

**Continues when:** key authentication from the origin works; the script polls it automatically.

### Runtimes and GUI login

**The script displays:** `On <name>: install missing runtimes and log Pi in once from the GUI`.

**The person does:** Install Homebrew, Node, Pi, gentle-pi, and Herdr if absent; open Herdr and Pi in the GUI session to complete provider login. Claude is not required. With `--install-missing`, the script attempts `brew install herdr` only if Homebrew responds and `pi install npm:gentle-pi` only if Pi responds: it does not install Homebrew, Node, or Pi.

**Continues when:** remote checks find `brew`, `node`, `python3`, `herdr`, `pi`, gentle-pi, and `herdr tab list` works.

> For noninteractive SSH, the script discovers common tool directories, including `nvm` `default` (or the highest installed Node version), and uses that `PATH` for checks and later tools.

### Initial SMB mount and Keychain

**The script displays:** `On <name>, connect in Finder to smb://<share.user>@<share.host>/<share.name> and save the password`.

**The person does:** In the new Mac GUI, open Finder, connect to that SMB URL, authenticate, and save the password in Keychain. Do not write the password in commands, files, or logs.

**Continues when:** the mount is available and the catalog is visible at `/Volumes/<share.name>`. Confirm the share and user in `config/hosts.json` (`share.host`, `share.name`, `share.user`); do not substitute a particular path or password in this guide.

### Pi login during acceptance

**The script displays:** `Log Pi in from the GUI on <target>` when acceptance receives `Not logged in`.

**The person does:** Open Pi in the indicated host's GUI, sign in with the provider, and confirm a harmless query.

**Continues when:** run the same command again after login. This waiting condition cannot be polled automatically; resumption runs acceptance again.

## Options, state, and diagnosis

| Option | Use |
| --- | --- |
| `--name`, `--address`, `--user` | Required: new Mac registry name, address, and account. |
| `--role {hub,spoke}` | New-host role; default `spoke`. |
| `--host-fingerprint SHA256:...` | Previously verified fingerprint; skips the TTY prompt. |
| `--origin-user USER` | Account the reverse channel uses to reach the origin. |
| `--install-missing` | Attempts only Herdr and gentle-pi when Homebrew/Pi already exist. |
| `--auto-update` / `--no-auto-update` | Enables (default) or omits the daily LaunchAgent. |
| `--update-time HH:MM` | Daily time; default `04:30`. |
| `--skip-live` | Skips live task acceptance tests but keeps preflight checks. |
| `--dry-run` | Does not write state or configuration; reports phases that would change and exits `4` if changes exist. |
| `--no-wait` | Does not wait for human intervention: records the phase as pending and exits `10`. |
| `--wait-timeout MINUTES` | Wait limit from 0 to 1440; default 30. |
| `--verbose` | Adds commands, exit codes, and truncated output to diagnostics. |
| `--registry PATH` | Uses an alternate registry. |

Exit codes: `0` complete or already configured; `1` setup or unexpected error; `2` invalid input or root execution; `4` `--dry-run` detected changes; `10` awaits human action or wait expiration.

Inspect persistent state with:

```sh
automation/agent-swarm/bin/swarm-setup status --name <name>
```

State is in `~/.local/state/agent-swarm/setup/<name>.json`, and the log is in `~/Library/Logs/mac-agent-swarm/swarm-setup-<name>.log`. On an unexpected error, inspect that log and, if necessary, resume with `--verbose` and the same options; share only sanitized diagnostics because logs can contain **public** keys, paths, and user names. Normal output is summarized in English; `--verbose` records every command, exit code, and truncated output. If setup exits `0`, also confirm `automation/agent-swarm/bin/swarm-delegate preflight <name>` returns `"status": "ready"`. Do not mistake `WAITING` or partial SSH success for final acceptance.

Re-running against an already configured host is safe: phases whose condition already holds report `OK` and do not alter configuration. An existing name with a different address, fingerprint, or SSH alias fails rather than being overwritten.

## Manual procedure (reference)

Use this appendix only to diagnose a phase that cannot be completed through `swarm-setup`.

1. On the new Mac, enable Remote Login for the selected account; prepare Homebrew, Node, Pi, gentle-pi, and Herdr; complete Pi login and open Herdr in the GUI.
2. Configure both SSH directions with dedicated keys, locally verified fingerprints, `known_hosts`, restricted `authorized_keys`, and `swarm-<target>` aliases. Follow the [SSH channel runbook](../runbooks/agent-swarm/ssh-channel.md).
3. In the spoke Finder, perform initial SMB access, save the password in Keychain, and install persistent mounting. Follow [SMB mounting](../runbooks/agent-swarm/smb-mount.md).
4. Register the host with correct local values, install the skill and bootstrap block, validate preflight in both directions, and commit the registry according to the approved workflow.

## Rollback

`swarm-setup` has no rollback subcommand. With owner authorization, remove only artifacts created for this onboarding: the registry entry and commit, dedicated SSH aliases and keys, added authorized lines, the new host's skill/bootstrap, and persistent SMB mount. Do not delete reused keys, backups, or entries containing unrelated changes. For exact procedures see [SSH channel](../runbooks/agent-swarm/ssh-channel.md#per-direction-rollback) and [SMB mounting](../runbooks/agent-swarm/smb-mount.md).

## Common problems

| Symptom | Safe action |
| --- | --- |
| `Not logged in` | Sign in to Pi from the indicated host's **GUI**; do not authenticate it over SSH. Then rerun the same command. |
| The script waits for runtimes although Pi works in Terminal | Review the default or installed `nvm` version, noninteractive `PATH` directories, and CLI results over SSH. A remote `zsh` shell without `nvm` versions must not abort on a nonmatching glob; if `no matches found` appears, use a setup version containing that fix. |
| Fingerprint mismatch | Stop onboarding. Compare the local reading and network scan again; do not use `StrictHostKeyChecking=no`. |
| Authorization command fails | Verify it ran in full on the new Mac and did not alter the restricted public key printed by the script. |
| Initial remote copy fails with `scp: dest open ... No such file or directory` | The destination parent directory does not yet exist. Use a setup version that creates it before `scp`; do not redirect the destination to an unrelated folder or broaden permissions to work around it. |
| SMB mount does not appear | Connect first in Finder, save the password in Keychain, and follow the SMB runbook; never put the password in the terminal. |
| Name already exists with another address | It is not overwritten: correct the registry decision or use the correct host. |
| A phase reports `WAITING` after completing the action | If you used `--no-wait`, repeat without it (or with `--wait-timeout 0`); verify the condition, persistent state, and log before concluding authorization failed. |

## References

- [Automatic updates](../runbooks/agent-swarm/auto-update.md)
- [Bidirectional SSH channel](../runbooks/agent-swarm/ssh-channel.md)
- [SMB mounting between machines](../runbooks/agent-swarm/smb-mount.md)
