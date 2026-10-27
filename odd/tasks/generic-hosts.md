# Generic host onboarding for the Agent Swarm channel

Make the Herdr + Pi channel generic so an agent on any Mac can add a new Mac and set up communication with it, with the MacBook as the hub that shares the projects.
Builds on odd/tasks/pi-herdr-adapter.md (adapter, skill v1.1, return transport, SMB mount script). Branch feat/pi-herdr-adapter. No push or merge.

## Specs

- S1. "está toda la documentacion y pasos para conectar nuevos agentes definidos de forma genérica para que un agente de cualquier máquina pueda configurar la comunicación con ese nuevo equipo ?" — an agent on any Mac must be able to follow one guide to connect a new Mac, with automated steps and human pauses clearly separated.
- S2. Hub model confirmed by the user ("si"): the MacBook shares the projects; every other Mac mounts that share.
- S3. "claude lo dejamos opcional, solo pi y gentle-pi es requisito" — Pi and gentle-pi are the only required runtimes on a new Mac; Claude is optional.
- S4. No host names or paths hard-coded in the adapter or the skill: they come from one host registry.
- S5. The existing MacBook ↔ Mac mini channel keeps working in both directions through the generic path.

## Tasks

| ID | Specs | Route | Commit |
|---|---|---|---|
| T1 | S4, S5 | Delegated writer: `config/hosts.json` registry, `bin/swarm-delegate` (origin-side helper: list, self, preflight, submit, recover, close), adapter reads catalog root and GUI cwd from the registry | complete — GREEN: `python3 -m unittest automation/agent-swarm/test/test_host_registry.py automation/agent-swarm/test/test_swarm_delegate.py automation/agent-swarm/test/test_herdr_task.py automation/agent-swarm/test/test_herdr_task_cli.py` (29 tests) |
| T2 | S1, S4 | Delegated writer: skill v1.2 uses the registry and `swarm-delegate` instead of fixed tables; bootstrap carries the host-local repository placeholder | complete — verified frontmatter; required command names appear in `swarm-delegate --help`; prohibited fixed identifiers absent; `git diff --check` passes |
| T3 | S1, S2, S3 | Delegated writer: generic guide `docs/setup/add-host.md`; generalize the SSH channel runbook; link from `agent-guided-setup.md` and README index | complete — evidencia: guía genérica con pasos Agente/Persona, pausas GUI y modelo hub/spoke; `ssh-channel.md` reemplaza el runbook direccional y conserva el registro histórico; enlaces Markdown de README, `docs/` y `skills/` resuelven; no quedan enlaces al runbook anterior; `swarm-delegate --help`, `python3 automation/agent-swarm/bin/swarm-smb-mount --help` y `git diff --check` pasan |
| T4 | S5 | Parent inline: SSH aliases `swarm-<name>` on MacBook and mini (with backups), re-copy skill to the mini | no repo change; evidence below |
| T5 | S1, S5 | Delegated verifier: independent review of the guide against S1–S3; live natural-language delegation in both directions through `swarm-delegate` | see L7 |

## Log

- L1. User: "está todo documentado y terminado? está toda la documentacion y pasos para conectar nuevos agentes definidos de forma genérica para que un agente de cualquier máquina pueda configurar la comunicación con ese nuevo equipo ?"
- L2. Finding: host names are hard-coded in `lib/herdr_task.py` (`_HOST_ROOTS`) and in the skill target table; `agent-guided-setup.md` covers only the v1 runner. Proposed: host registry + one onboarding guide + generic acceptance test, MacBook as hub.
- L3. User: "si" / "- Herdr y Pi instalados, con login de Claude en la sesión gráfica; << claude lo dejamos opcional, solo pi y gentle-pi es requisito"
- L4. Decision: SSH alias convention `swarm-<name>` per target, configured on each origin Mac; the MacBook → mini direction may reuse the user's existing key (already works); new directions use a dedicated key with fingerprint verification. The mini alias `agent-swarm-macbook` is renamed to `swarm-macbook`. Bea stays out of scope.
- L5. Decision: the Agent Swarm bootstrap block carries `Agent Swarm repository on this host: <REPO_PATH>`; installation fills it with the host-local repository path so the reusable skill neither guesses nor hard-codes a host path.
- L6. T4 done: MacBook `~/.ssh/config` created with `Host swarm-mac-mini` (existing key); mini alias renamed `agent-swarm-macbook` -> `swarm-macbook` (backup `~/.ssh/config.pre-swarm-rename.bak`); skill v1.2 linked on the MacBook and copied to the mini (v1.1 kept in `~/.local/state/agent-swarm/skill-backups/`); bootstrap filled with each host's repo path in `~/.pi/agent/AGENTS.md` and `~/.claude/CLAUDE.md` (backups `*.pre-swarm-1.2.bak`). `swarm-delegate preflight mac-mini` from the MacBook and `preflight macbook` from the mini both returned `ready`.
- L7. T5 done (independent verifier): S1 PASS, S2 PASS, S4 PASS, S5 PASS; S3 initially FAIL because README step 3 listed OpenCode and Claude as installs for both hosts — fixed to state Pi + gentle-pi required for the Herdr channel, Claude optional, other runtimes only for the v1 runner; stale `agent-guided-setup.md` skill status updated to point to add-host.md. Live: fresh MacBook Pi delegated to the mini in plain Spanish (token returned, mini ledger 789e70a4 closed, 26 s); fresh mini Pi in its own Herdr tab delegated to the MacBook (token returned, MacBook ledger 732d2ffa closed); baselines restored on both Macs. 102 tests PASS.
