# Guided Agent Swarm setup

The only onboarding path is `swarm-setup add-host` from an already registered Mac. It configures the Herdr + Pi channel resumably and pauses for decisions that only a person at the relevant host can make.

## Quick path

1. Confirm the origin appears in `config/hosts.json` (an unversioned local registry; create one from `config/hosts.example.json` if absent) and run the command from its local checkout.
2. Follow [Add a host](add-host.md#quick-path) with the new Mac's name, address, and user.
3. Complete local pauses: Remote Login, fingerprint comparison, Pi GUI login, and initial SMB access.
4. Repeat exactly the same command and options until bidirectional acceptance completes.
5. Before delegating work, run `swarm-delegate preflight <target>` and follow the [validation runbook](../runbooks/agent-swarm/validation.md).

The registry is the source of truth. Its `hosts`, `share`, and role fields determine aliases, endpoints, users, catalog, repository, and paths. Do not replace them with computer names, IPs, or paths from another deployment.

## Human pauses

| Moment | Local action | Safe confirmation |
| --- | --- | --- |
| Remote access | Enable Remote Login for the registered account and confirm the selected network. | The SSH port responds from the origin. |
| SSH fingerprint | Compare the fingerprint shown at the host with the scan from the origin. | They match; `StrictHostKeyChecking` remains enabled. |
| Runtimes and login | Install approved software and complete Pi GUI login when requested. | Checks find Pi, gentle-pi, and Herdr. |
| SMB | In Finder, connect to the URL shown by setup; save the password only in Keychain when appropriate. | The registered catalog appears on the spoke. |
| Acceptance | Resolve `Not logged in` in the indicated GUI and resume the same setup. | Preflight and acceptance finish both ways. |

## Boundaries

- Setup does not authorize network changes, `sudo`, credentials, or installations outside its phases.
- Profiles, Keychain, sessions, caches, and home directories stay on each Mac.
- The skill is copied through setup's local mechanism; SMB carries neither credentials nor home directories.
- Store only sanitized state, phase, version, and exit code. Do not store passwords, tokens, private keys, or task envelopes in shared tickets or logs.
- If a result is ambiguous, consult persistent state before retrying. Do not restart existing sessions to force recovery.

## Subsequent operation

Use `swarm-delegate list` to see destinations, `self` to identify the origin, and `preflight <target>` before submitting a task. The [Herdr + Pi tasks runbook](../runbooks/agent-swarm/herdr-tasks.md) documents `submit`, `recover`, and `close`, including retaining the same UUID after a transport failure.

For phase, option, state, and recovery diagnosis, read [Add a host](add-host.md). For SSH and SMB, use [SSH channel](../runbooks/agent-swarm/ssh-channel.md) and [SMB mount](../runbooks/agent-swarm/smb-mount.md), respectively.
