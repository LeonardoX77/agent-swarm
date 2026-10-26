# Retire Runner v1 from the repository
Branch: feat/pi-herdr-adapter | Delivery strategy: single-pr (owner choice; no PR or push authorized) | Test runner: python3 -m unittest discover -s automation/agent-fabric/test
Forecast: >400 authored changed lines, primarily deletion of isolated legacy code and its tests; preserve pre-existing uncommitted setup fixes, host registry, and documentation edits.

## Specs
S1. User request, verbatim: "Elimina Runner v1 y ruedas las referencias que haya". Acceptance: no active Runner v1 executable, helper, schema, example, config, test, or operational reference remains; active Herdr + Pi channel continues to work.
S2. User scope selection: "Sólo repositorio (recomendado)". Acceptance: do not inspect, uninstall, or delete installed runtime, SSH keys, aliases, or configuration on either Mac.

## Tasks
T1 [S1-S2] Map v1-only versus active files and pre-existing edits; route inline; done; commit none (read-only).
T2 [S1-S2] Delete repository-only v1 code, configs, examples, schemas, and dedicated tests; route inline; done (47 active setup/delegate tests pass); commit 0bea55b.
T3 [S1] Replace active README, architecture, setup and runbooks with the current Herdr + Pi contract; preserve historical ODD records as records, not active instructions; route delegated/parent; done (structural links and CLI help checks); commit 0bea55b.
T4 [S1-S2] Validate surviving commands, links, tests, and absence of active v1 references; route inline; done (110 suite tests, 36 links, no active references, staged diff check); commit 0bea55b plus final tracking record.

## Log
L1. Elimina Runner v1 y ruedas las referencias que haya
L2. Scope selected: "Sólo repositorio (recomendado)". Installed host artifacts are excluded; source worktree already has unrelated uncommitted setup fixes, host registration, and generic documentation.
L3. Inventory: v1-only scripts (fabric-runner, fabric-dispatch, fabric-host-preflight, fabric-install-runtime, fabric-activity), seven support libraries, two schemas, an example, four legacy config files, eleven dedicated tests. Active stack (fabric-setup, fabric-delegate, fabric-herdr-task, fabric-smb-mount, fabric-update and their libraries/tests) is separate. README/architecture and several runbooks still misleadingly describe v1 as current; historical odd/tasks records are not executable instructions.
L4. Deleted only the enumerated repository v1 paths. Focused active regression: `python3 -m unittest automation/agent-fabric/test/test_fabric_delegate.py automation/agent-fabric/test/test_fabric_setup.py automation/agent-fabric/test/test_fabric_setup_scenarios.py` exit 0, 47 tests OK. No meaningful RED for deleting an unused legacy path; verify absence structurally and survival via active public CLI/tests.
L5. Parent removed three exclusively legacy manuals; bounded worker rewrote README, architecture and surviving setup/runbooks. Worker verified relative links and active CLI help; parent search found no v1/removed CLI references in README, docs, skill, active automation or config. Historical `odd/tasks` records retain original evidence and are not instructions. Cumulative diff exceeds 400 lines; delivery shape requires owner choice before commit.
L6. `python3 -m unittest discover -s automation/agent-fabric/test` exit 0 (110 tests, one Python deprecation warning). `git diff --check` passed; 11 active docs have 36 internal links and no broken targets/anchors; no removed CLI/Runner v1 references in active docs/code/skill/config; `fabric-delegate list` still recognizes three registered hosts. Native assess unavailable (package-local binary missing), with no independent-verifier escalation.
L7. Owner selected `single-pr` for the oversized cohesive removal; this is a delivery shape only, not permission to publish, push, or create a PR. The deletion cannot be honestly made small by stripping tests/docs. Existing unrelated source fixes and registry edits remain unstaged.
L8. Committed cohesive repository-only removal as `0bea55b` (`refactor(agent-fabric): retire legacy one-shot runner`): 41 files, 255 additions, 2291 deletions. `git diff --cached --check` passed; unrelated setup fixes, host registry and three previously edited runbooks remain unstaged. Committed-range native assessment with `baseRef: HEAD^` was unassessable due to package-local binary missing; no native review outcome or authority asserted. No push/PR/merge.
