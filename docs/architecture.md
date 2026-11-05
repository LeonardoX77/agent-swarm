# Agent Swarm architecture

Agent Swarm delegates a Pi task between registered Macs. The origin sends an envelope over SSH; at the destination, `swarm-herdr-task` creates its own Herdr tab and Pi session and obtains the result from that session's JSONL. It coordinates transport and lifecycle; it is not a model or sandbox.

## Outcome and scope

A registered host can request work from another registered host through `swarm-delegate`. Every task uses a UUID, a project relative to the destination catalog, and an envelope with a goal and acceptance criteria. The destination runs Pi under its own local account through Herdr.

The contract excludes copying credentials, automated logins, SSH access without a verified fingerprint, remote configuration without a human present, distributed exactly-once guarantees, and concurrent-writer arbitration.

## Topology

| Element | Responsibility |
| --- | --- |
| Hub | Defines the SMB-published catalog and is the registry's `hub`. |
| Spoke | Uses the catalog mounted at `/Volumes/<share.name>` when it needs the shared project. |
| Registry | `config/hosts.json` (local, Git-ignored; template: `config/hosts.example.json`) defines the share and each host's hostname prefix, role, SSH alias, address, catalog, checkout, PATH, GUI cwd, and runtimes. |
| SSH | Connects a `swarm-<target>` alias in each direction. A person verifies fingerprints; dedicated keys disable forwarding but do not make SSH a sandbox. |
| SMB | Carries only the approved catalog; credentials stay in the Keychain of the mounting Mac. |
| Herdr + Pi | The destination creates and controls only its own resources: one tab, Pi agent, and private session per task. |
| Skill | `agent-swarm-remote` defines how to validate, delegate, recover, and close task envelopes. |

Names, paths, and endpoints always come from the registry. The same user name on two hosts does not share `HOME`, Keychain, tokens, configuration, sessions, or caches.

## Task flow

1. The origin runs `swarm-delegate list` and confirms the registered destination; `self` identifies the local host.
2. `preflight <target>` checks SSH and the catalog. If a spoke reports `catalog_missing`, mount its SMB catalog before sending work.
3. The origin sends an envelope on stdin containing exactly `task_id`, `origin_host`, `project`, `goal`, `acceptance`, and `mode: executor`.
4. `swarm-delegate` uses batch-mode SSH to run `swarm-herdr-task submit` in the checkout declared by the destination.
5. The adapter reserves the UUID in a durable ledger, creates a private session and unfocused Herdr tab, then starts Pi with closed argv.
6. The adapter sends Pi the exact envelope; `recover` reads only its own session JSONL until it finds the final answer.
7. After a verifiable result, `close` closes only that task's tab. Ambiguous states are retained for recovery; the prompt is not resent.

## Task contract

| Field | Rule |
| --- | --- |
| `task_id` | A new UUID per job. On ambiguity, retain and reuse the same envelope. |
| `origin_host` | Registered host name that started the task. |
| `project` | Path relative to the destination's `catalog_root`; never absolute. |
| `goal` and `acceptance` | Non-empty, self-contained text that bounds the work and result. |
| `mode` | Exactly `executor`. |

`submit` accepts the envelope only through stdin. `recover` and `close` take the UUID. Connection errors make state unknown from the origin; recover later rather than assuming the task never started.

## Onboarding lifecycle

`swarm-setup add-host` coordinates resumable onboarding from a registered host. Its phases validate the origin, wait for Remote Login, verify fingerprints and keys in both directions, check runtimes, mount the spoke SMB catalog, update the registry, install the skill, configure local updates, and run Herdr + Pi acceptance.

Remote Login, fingerprint, Pi login, and first SMB-mount pauses are local human decisions. Re-running the same command retains state and resumes the pending phase; it never substitutes invented registry paths or names.

## Operational boundaries

- `StrictHostKeyChecking` is mandatory; do not accept fingerprints without a reliable comparison.
- Secrets never travel in the envelope, registry, commands, or shared logs.
- The ledger persists intent before remote effects. A timeout, nonzero exit, or unparseable response becomes `unknown` and prevents automatic resend.
- The adapter does not use the user's session directory: every task keeps a private, restrictive-permission directory.
- Two tasks can contend for one worktree. Coordination, review, and conflict resolution are human responsibilities.
- Test evidence is not deployment acceptance. Read [validation](runbooks/agent-swarm/validation.md) before operating.

## Review checklist

- [ ] The registry lists exactly the intended hosts and share.
- [ ] Every SSH direction has an alias, verified fingerprint, and dedicated key.
- [ ] The SMB catalog is restricted to the approved share and available where needed.
- [ ] Pi, gentle-pi, and Herdr are installed and authenticated locally at every destination.
- [ ] The envelope uses a UUID and relative project; ambiguity is recovered, not resent.
- [ ] Only resources created by the identified task are closed.
