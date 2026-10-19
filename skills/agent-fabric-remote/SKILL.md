---
name: agent-fabric-remote
description: "Trigger: Agent Fabric task envelope, delegate, send or run work on the other Mac, remote Pi, or a registered Mac. Safely receive or delegate bounded Agent Fabric work."
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.2"
---

## Activation Contract

Activate only for an explicit Agent Fabric task envelope with non-empty `task_id`, `origin_host`, `project`, `goal`, `acceptance`, and `mode`, or when the user explicitly asks to delegate work to the other Mac, remote Pi, or a registered Mac. Otherwise behave normally.

## Hard Rules

- Find `<repo>` in the Agent Fabric bootstrap in startup instructions: `Agent Fabric repository on this host: <REPO_PATH>`. If it is missing, stop and ask; do not guess paths.
- The registry is `<repo>/config/hosts.json`. Run `<repo>/automation/agent-fabric/bin/fabric-delegate self` to identify this host, then use its registry entry for `catalog_root`. An unknown host stops and is reported.
- Resolve `project` only below this host's registry `catalog_root`; never use a mount other than the registry catalog root.
- Read before writing, stay within the resolved project, goal, and acceptance, and do not disclose secrets. Respect permission prompts; pending approval is `blocked`, never success.
- A target requires Pi and gentle-pi. Claude is optional.
- Create one fresh UUID `task_id` once per work item. After ambiguity, retain the identical envelope and never mint a replacement ID.

## Receiving Side

1. Validate and retain the six envelope fields; identify the local registry entry and catalog root before project operations.
2. For `mode: executor`, perform only accepted local work and return sanitized evidence.
3. For `mode: orchestrator`, use only verified configured transport; otherwise query state or report the required local work.
4. On uncertain delivery, query task state before further action.

## Delegating Side

1. Run `<repo>/automation/agent-fabric/bin/fabric-delegate list`; choose the target the user means by name or role. Ask if that remains ambiguous.
2. Run `<repo>/automation/agent-fabric/bin/fabric-delegate preflight <target>`.
3. If preflight returns `catalog_missing` for a spoke, report it or mount once on that target, using registry `share.host`, `share.name`, and `share.user`:

   ```bash
   ssh <alias> '/usr/bin/python3 ~/.local/agent-fabric/bin/fabric-smb-mount mount --host <share.host> --share <share.name> --user <share.user>'
   ```

   Re-run preflight. Stop and report if it is not ready.
4. Write `envelope.json` with exactly `task_id`, `origin_host`, `project`, `goal`, `acceptance`, and `mode`. Set `mode` to `executor`; make `origin_host` this host's registry name; make `project` catalog-relative; make `goal` self-contained.
5. Submit, then recover and close:

   ```bash
   <repo>/automation/agent-fabric/bin/fabric-delegate submit <target> < envelope.json
   <repo>/automation/agent-fabric/bin/fabric-delegate recover <target> <task_id> [--wait N]
   <repo>/automation/agent-fabric/bin/fabric-delegate close <target> <task_id>
   ```

| Result | Required action |
| --- | --- |
| `unreachable` (exit 3) | The other Mac is off or unreachable. Recover later, re-run submit with the identical envelope, or use local subagents. Never mint a new `task_id` after ambiguity. |
| `unknown` | Report `last_error`; do not resubmit. |
| `failed` | Fix input, then create and submit a new task. |
| `close` refused or unknown | Leave it open and report it. |

## Output Contract

Receiving side: return `task_id`, status (`done`, `blocked`, `failed`, or `unknown`), sanitized evidence, files touched, and pending approvals or unavailable paths.

Delegating side: return target, `task_id`, status, remote `resulttext`, and anything left open.

## References

- `assets/bootstrap-block.md` — startup instruction and host-local repository path.
- `../../docs/runbooks/agent-fabric/herdr-tasks.md` — lifecycle and adapter contract.
