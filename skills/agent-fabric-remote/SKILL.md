---
name: agent-fabric-remote
description: "Trigger: Agent Fabric task envelope, delegate, send or run work on the other Mac, Mac mini, MacBook, remote Pi. Safely receive or delegate bounded Agent Fabric work."
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.1"
---

## Activation Contract

Activate only when (1) a request contains an explicit Agent Fabric task envelope with non-empty `task_id`, `origin_host`, `goal`, `project`, and `acceptance`, plus `mode: executor` or `mode: orchestrator`; or (2) the user explicitly asks to delegate work to the other Mac. Otherwise behave normally.

## Hard Rules

- Run `hostname` first. Receiving work: `MacMiniLeo*` uses `/Volumes/agent-projects`; `MacBookLeo*` uses `/Users/leo/projects`. Resolve `project` only below that root; on the mini never use `/Users/leo/projects`; any other hostname: stop and report.
- This skill is behavioral guidance, not a sandbox; SMB-share scope and OS permissions impose access limits. Never use `/Volumes/Macintosh HD-1` or another broad mount. If the project mount/path is absent, stop and report; never guess a path. Read before writing, stay within the resolved project, goal, and acceptance, and do not disclose secrets.
- Respect permission prompts; never bypass or self-approve them. A pending approval is `blocked`, never success.
- For delegation, create one UUID `task_id` once per piece of work. Never create another for that work after ambiguity; the same envelope is idempotent.

## Decision Gates

| Situation | Action |
| --- | --- |
| Invalid/missing envelope; no explicit delegation request | Behave normally. |
| Project mount/path unavailable | Stop with `blocked` and the observed path condition. |
| Receiving `executor` envelope | Perform bounded local work and collect sanitized evidence. |
| Receiving `orchestrator` envelope | Delegate only through a verified configured transport; otherwise query state or report the required local work. |
| Delegation request | Use the target, preflight, envelope, and lifecycle below. |
| SSH exits 255 / target unreachable | Tell the user the other Mac is off or unreachable; use local subagents instead. Never disable host-key checking. |

## Receiving Side

1. Parse and retain the envelope identifiers; select the mode and verify the host-local project path before project operations.
2. In executor mode, inspect relevant files, make only accepted changes, and collect sanitized evidence.
3. In orchestrator mode, verify transport before contacting the origin MacBook agent; native gentle-pi orchestrator tools use local-profile Unix sockets and provide no cross-host messaging.
4. On uncertain delivery, query transport/task state before further action.

## Delegating Side

### Targets

| Local `hostname` | Target | Adapter and prefix | Submit option |
| --- | --- | --- | --- |
| `MacBookLeo*` | `ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 leo@MacMiniLeo.local` | `/Volumes/agent-projects/leo/mac-agent-fabric/automation/agent-fabric/bin/fabric-herdr-task`; `PATH=/opt/homebrew/bin:$HOME/.nvm/versions/node/v24.19.0/bin:/usr/bin:/bin /usr/bin/python3` | `--project-root /Volumes/agent-projects` |
| `MacMiniLeo*` | `ssh agent-fabric-macbook` | `/Users/leo/projects/leo/mac-agent-fabric/automation/agent-fabric/bin/fabric-herdr-task`; `PATH=/opt/homebrew/bin:/usr/bin:/bin /usr/bin/python3` | none (hostname detects it) |

1. Preflight with `ssh <target> 'test -x <adapter>'`. If the mini is the target and its adapter is missing, run on the mini `ssh <target> '/usr/bin/python3 ~/.local/agent-fabric/bin/fabric-smb-mount status --host MacBookLeo.local --share agent-projects --user leo'`; if not mounted, run the same command with `mount` once. Re-run the preflight; if still missing, stop and report.
2. Write a local temporary `envelope.json` with **exactly** `task_id`, `origin_host`, `project`, `goal`, `acceptance`, and `mode`. Set `mode` to `executor` (the adapter rejects `orchestrator`), `origin_host` to the short local name (`MacBookLeo` or `MacMiniLeo`), and `project` relative to the catalog (for example `leo/mac-agent-fabric`). Make `goal` fully self-contained: remote Pi has no conversation history. One task creates one fresh remote Pi; a follow-up needs a new task with its needed context.
3. Submit: `ssh <target> '<prefix> <adapter> submit [--project-root ...]' < envelope.json`; expect `submitted`.
4. Recover: `ssh <target> '<prefix> <adapter> recover <task_id>'`. It waits up to 120 seconds by default; use `--wait N` up to 900 for long tasks. Repeat while `pending` or `timed_out`; on `done`, read `resulttext`.
5. Close: `ssh <target> '<prefix> <adapter> close <task_id>'`; expect `closed`.

| Result | Required action |
| --- | --- |
| SSH 255 or no submit output | Re-run submit with the **identical** envelope file, or recover; never re-prompt or mint a new `task_id`. |
| `unknown` | Report `last_error` to the user; do not resubmit. |
| `failed` with `diagnostic_code` | Fix the input (for example `INVALID_ENVELOPE` or `PROJECT_MISMATCH`), then submit as a **new** task. |
| `close` is `refused` or `unknown` | Leave it open and report it. |
| Long task | Raise `--wait` within the 900-second limit. |

## Output Contract

Receiving side: return `task_id`, status (`done`, `blocked`, `failed`, or `unknown`), sanitized evidence, files touched, and pending approvals or unavailable paths.

Delegating side: report the remote host, `task_id`, status, remote `resulttext`, and anything left open.

## References

Relative paths are from the repository skill directory. The repository is `/Users/leo/projects/leo/mac-agent-fabric` on the MacBook and `/Volumes/agent-projects/leo/mac-agent-fabric` on the mini; installed copies may not resolve them.

- `assets/bootstrap-block.md` — startup instruction.
- `../../docs/setup/agent-guided-setup.md` — host-local installation and acceptance guidance.
- `../../docs/runbooks/agent-fabric/herdr-tasks.md` — adapter contract and lifecycle.
- `../../docs/runbooks/agent-fabric/return-transport.md` — mini-to-MacBook SSH transport.
- `../../docs/runbooks/agent-fabric/smb-mount.md` — mini project-mount recovery.
