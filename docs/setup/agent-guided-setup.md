# Guided Agent Swarm setup

The onboarding path is `swarm-setup add-host` from an already registered macOS or Linux/WSL node. It configures the Herdr + Pi channel resumably and pauses for decisions only a person at the relevant host can make. Linux/WSL runs the same ten phases; shared-catalog spokes use CIFS and systemd user mount timers, while local-only spokes skip SMB. A real delegation to WSL has been tested, but bidirectional acceptance between two machines remains unvalidated.

## Quick path

1. Confirm the origin appears in `config/hosts.json` (an unversioned local registry; create one from `config/hosts.example.json` if absent) and run the command from its local checkout.
2. Follow [Add a machine](add-host.md#quick-path) with the new machine's name, address, and user. For Linux/WSL, first follow [preparation](add-host.md#linuxwsl-preparation).
3. Complete local pauses: SSH access, fingerprint comparison, and Pi login; in default shared mode, SMB uses Finder/Keychain on macOS or fstab and local credentials on Linux. A local-only spoke instead requires its catalog and Agent Swarm checkout to be pre-provisioned.
4. Repeat the same command with the same options until bidirectional acceptance completes successfully.
5. Before delegating work, run `swarm-delegate preflight <target> --project <catalog-relative-project>` and follow the [validation runbook](../runbooks/agent-swarm/validation.md).

The registry is the source of truth. Its `hosts`, `share`, role, and `catalog_mode` (default `smb`) fields determine aliases, endpoints, users, catalog, repository, and paths. A `local` spoke uses paired absolute `--local-catalog-root` and `--local-repo` paths (repo inside root), skips SMB without installing or copying its mount tool, and trades shared-catalog access for reduced exposure. Consult `swarm-setup add-host --help` for the exact options. Do not replace them with machine names, IP addresses, or paths from another deployment. A host can additionally have ordered `fallback_addresses` for SSH and `share_hosts` for its SMB mount; both are optional, so existing registries remain valid.

## Address candidates and failover

Use `--address` for the preferred SSH address and repeat `--fallback-address` in order for later candidates. `--origin-address` similarly supplies the reverse alias only and replaces that alias's origin-registry candidates. A spoke can repeat `--share-host` for SMB hosts in preference order; a hub rejects that option. Candidates must begin alphanumerically, contain only letters, digits, dots, and hyphens, and contain no duplicates (nor may the primary address be a fallback).

Use Tailscale MagicDNS first and LAN second. Tailscale itself uses LAN directly when possible, so the LAN candidate primarily protects against Tailscale being unavailable or against a route tool capturing a Tailscale sub-range (for example, Twingate routing `100.96.0.0/12` within `100.64.0.0/10`). On Windows/WSL, treat a LAN-scoped firewall rule carefully: a Public Wi-Fi profile can still use that LAN range.

SSH tries candidates in order; an unreachable candidate adds at most its per-candidate connect timeout. SMB fallback is mount-time only: remount to change an active host.

## Linux/WSL before onboarding

- Prepare SSH, Node, Python 3, and Pi; make the Herdr server available and complete Pi login locally. `--install-missing` can add Herdr with the official installer at https://herdr.dev/install.sh (downloaded to a temporary file and run only if the download succeeds; requires curl) and gentle-pi through Pi. Homebrew is not required.
- The official Herdr Pi integration is mandatory on both platforms: `herdr integration status` must confirm Pi is installed. `--install-missing` runs `herdr integration install pi` when Herdr is available (dry-run only reports the plan); it installs `~/.pi/agent/extensions/herdr-agent-state.ts`. Without it, the `agent_session` ownership proof of kind `path`, source `herdr:pi`, is absent: submit can become `unknown` without delivering the prompt.
- To start Herdr without a GUI on Linux, run `herdr` in a normal terminal and detach it, or use a pty with non-zero rows and columns. The server survives the client exiting. Herdr 0.9.5 rejects a zero-grid terminal (`cannot attach without a usable terminal: terminal reported a zero-sized grid`) and has no `herdr server start` (only `server stop` and `server reload-config`). Check `herdr tab list`; `server_not_running` means it must be started. The wait displays missing probe names and start instructions when `herdr-server` is missing.
- Setup and swarm-update discover `$HOME/.pi/agent/bin`, where Pi's installer installs, immediately after `$HOME/.local/bin`; they retain all other paths and their order.
- For a shared-mode spoke, run `swarm-smb-mount fstab-line --host H --share S --user U`. A local-only spoke must not install, copy, or mount SMB; provision its configured local catalog and executable checkout before setup. A person adds the exact line to `/etc/fstab` as root, creates `/mnt/<share>`, and creates `~/.config/agent-swarm/smb-credentials` with mode `0600`. The tool never uses sudo or handles passwords. Setup mounts and configures a user timer every 300 seconds; without `systemctl --user`, it warns that persistence was not enabled.
- Daily updates use `agent-swarm-update.timer` unless `--no-auto-update`. In WSL, enable `[boot]` / `systemd=true` in `/etc/wsl.conf`; timers require a user session unless `loginctl enable-linger $USER` is enabled.
- A Linux hub must publish its catalog manually through its own SMB server, such as Samba; setup does not configure it. Windows can occupy TCP port 445 on loopback, so use another port for a local SMB test.

Read [preparation details](add-host.md#linuxwsl-preparation) and the [evidence and limits](../runbooks/agent-swarm/test-evidence.md#linuxwsl-evidence) before delegating.

## Human pauses

Fingerprint and login checks are shared. SSH and SMB actions depend on the platform:

| Moment | Local action | Safe confirmation |
| --- | --- | --- |
| Remote access | Enable Remote Login on macOS or a Linux `sshd` for the registered account; confirm the network. | The SSH port responds from the origin. |
| SSH fingerprint | Compare the host fingerprint with the origin scan. | They match; `StrictHostKeyChecking` stays enabled. |
| Runtimes and login | Install approved software and complete local Pi login when requested. | Checks find Pi, gentle-pi, Herdr, its server, and official Pi integration. |
| SMB | macOS: Finder and Keychain. Linux: fstab entry and protected credential file; run the specified mount. | The registered catalog appears on the spoke. |
| Acceptance | Resolve `Not logged in` from the indicated GUI and resume the same setup. | Preflight and acceptance complete in both directions. |

## Boundaries

- Setup does not authorize network changes, `sudo`, credentials, or installations outside its phases.
- Profiles, sessions, caches, and home directories remain on each node; Keychain applies only to macOS.
- The skill is copied by setup's local mechanism; SMB carries neither credentials nor home directories.
- Save only sanitized state, phase, version, and exit code. Do not save passwords, tokens, private keys, or task envelopes in shared tickets or logs.
- If a result is ambiguous, inspect persistent state before retrying. Do not restart existing sessions to force recovery.

## Subsequent operation

Use `swarm-delegate list` to see destinations, `self` to identify the origin, and `preflight <target> --project <catalog-relative-project>` before submitting a task. `project_unavailable` means the target lacks that project; local-only mode requires local provisioning, not SMB. The [Herdr + Pi tasks runbook](../runbooks/agent-swarm/herdr-tasks.md) describes `submit`, `recover`, and `close`, including the requirement to retain the same UUID after a transport failure.

For phase, option, state, and recovery diagnosis, see [Add a machine](add-host.md). For SSH and SMB, use the [SSH channel](../runbooks/agent-swarm/ssh-channel.md) and [SMB mounting](../runbooks/agent-swarm/smb-mount.md), respectively.
