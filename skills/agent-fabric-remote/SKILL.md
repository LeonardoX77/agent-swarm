---
name: agent-fabric-remote
description: "Trigger: Agent Fabric task envelope, remote executor, remote orchestrator. Safely handle explicitly enveloped Agent Fabric work across the MacBook and Mac mini."
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## Activation Contract

Activate **only** when the request contains an explicit Agent Fabric task envelope with non-empty `task_id`, `origin_host`, `goal`, `project`, and `acceptance`, plus `mode: executor` or `mode: orchestrator`. `project` must be a relative path below the shared project root. Otherwise, do nothing special and do not assume an executor role.

## Hard Rules

- Run `hostname` first and pick the project root by host: `MacMiniLeo*` uses `/Volumes/agent-projects`; `MacBookLeo*` uses `/Users/leo/projects`. Resolve `project` only under that root. On the Mac mini, never use `/Users/leo/projects`; any other hostname: stop and report.
- Never use `/Volumes/Macintosh HD-1` or any other broad mount. If `/Volumes/agent-projects` is absent, or the resolved project does not exist, stop and report; never guess a path.
- This skill is behavioral guidance, not a sandbox. SMB-share scope and OS permissions impose access limits.
- Read before writing. Stay inside the resolved project and the stated `goal` and `acceptance`. Do not disclose secrets.
- Respect permission prompts. Never bypass or self-approve them; a pending approval is `blocked`, never success.

## Decision Gates

| Situation | Action |
| --- | --- |
| Envelope missing or invalid | Behave normally; do not activate this skill. |
| Project mount/path unavailable | Stop with `blocked` and the observed path condition. |
| `mode: executor` | Perform bounded local work only. |
| `mode: orchestrator` with verified configured transport | Delegate only through that transport. |
| Transport absent, unverified, or delivery ambiguous | Do not delegate or blind-retry; query state first, or report the MacBook command/work to run. |

## Execution Steps

1. Parse and retain the envelope identifiers; select the mode.
2. Resolve and verify the host-local project path before any project operation.
3. In executor mode, inspect relevant files, make only accepted changes, and collect sanitized evidence.
4. In orchestrator mode, verify the configured transport before contacting the origin MacBook agent. Native gentle-pi orchestrator tools use local-profile Unix sockets and provide no cross-host messaging.
5. On uncertain delivery, query transport/task state before any further action.

## Output Contract

Return a framed result containing `task_id`, `status` (`done`, `blocked`, `failed`, or `unknown`), sanitized `evidence`, and `files touched`. State pending approvals, unavailable paths, or unverified transport plainly.

## References

- `assets/bootstrap-block.md` — startup instruction to install in each supported runtime.
- `../../docs/setup/agent-guided-setup.md` — host-local installation and acceptance guidance.
