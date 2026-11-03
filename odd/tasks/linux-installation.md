# Linux installation support

Objective: Adapt Agent Swarm installation for Linux on branch `feat/linux-installation`.
Delivery strategy: single-pr. Test runner: `python3 -m unittest discover -s automation/agent-swarm/test`.

## Specs

S1. "crea una nueva rama y adapta la instalacion de agent-swarm en linux"

## Tasks

- T1 | S1 | delegated | done | Portable Linux/WSL setup core and OS-matrix regression coverage verified (50 focused tests, 1 skipped); commit: `a13062a`.
- T2 | S1 | delegated | done | Manual Linux/WSL catalog boundary and platform-specific service avoidance verified (59 focused tests, 1 skipped); commit: `82a4818`.
- T3 | S1 | delegated | done | Linux/WSL documentation and full-suite test isolation/platform expectations verified (131 tests passed, 1 skipped); commit: HEAD.

## Log

- L1 | User request: "crea una nueva rama y adapta la instalacion de agent-swarm en linux
como obtengo esos datos?
 Necesito estos tres datos del hub/catálogo:

 ```text
   Hub name:
   SMB host and share:      # ej. 100.x.x.x / shared-projects
   SMB user:
 ```
cual es el primer paso?"
- L2 | Branch `feat/linux-installation` created from `main`. Exploration found the setup is macOS-specific; scope excludes inventing SMB credentials, provisioning CIFS, systemd services, or changing delegation runtime behavior without topology data.
- L3 | T1 delegated because the parent reached the context backstop. Allowed edit surfaces are `automation/agent-swarm/bin/swarm-setup`, `automation/agent-swarm/lib/swarm_setup.py`, and focused setup tests.
- L4 | Independent verifier: T1 has no change-caused blockers. Focused setup suite passed (47 tests, 1 skipped). Full suite currently has baseline environment/platform failures; T3 must document or correct their test isolation. Verifier recommends explicit local/remote OS matrix regression coverage before committing T1.
- L5 | T1 hardening added explicit four-way local/remote OS coverage, Darwin Homebrew-install preservation, and invalid-platform fail-closed coverage. Focused setup suite: 50 tests passed, 1 skipped (`/bin/zsh` unavailable).
- L6 | Work-unit commit could not be created because Git has no author identity for this repository. The intended T1 changes are staged but uncommitted; no staged content was discarded.
- L7 | User supplied a repository-local Git author identity: `Leo-LinuxWSL <leonardox77@linuxwsl.com>`.
- L8 | T1 committed as `a13062a feat(setup): support Linux runtime preflight` (264 authored changed lines).
- L9 | Independent verifier found T2 blocker: `--linux-catalog-root` was silently ignored for a macOS target. T2 must fail closed when that Linux/WSL-spoke-only option is supplied to a macOS target or a hub.
- L10 | The silent-ignore defect and role rejection are fixed, but a fresh macOS target is only detectable after SSH bootstrap; the current setup creates origin SSH key/config artifacts before then. Need a product policy: preserve first-time bootstrap with late rejection, or require pre-existing SSH for strict pre-write platform detection.
- L11 | User decision: "Preservar el alta inicial (recomendado)". For an incompatible macOS target, reject after SSH is authenticated; local SSH bootstrap artifacts may remain, while SMB, registry, and remote host changes must not occur.
- L12 | T2 committed as `82a4818 feat(setup): require pre-mounted Linux catalogs` (238 authored changed lines). The feature has 500 authored changed lines across two commits; delivery shape is now required before the next commit.
- L13 | User delivery decision: "Un único PR" (`delivery_strategy=single-pr`). The user accepts the increased review load; no chain will be created.
- L14 | T3 documentation review and `git diff --check` passed. Full suite ran 130 tests: 15 errors caused by missing ignored `config/hosts.json` in `test_herdr_task`, 2 `test_smb_mount` failures because Linux returns `unsupported_platform`, 1 skipped (`/bin/zsh` unavailable). Earlier baseline comparison identified the same failure families; no documentation change caused them. Scope decision required before treating T3 as verified.
- L15 | User decision: "Corregir la suite ahora (recomendado)". Scope expands to repair the failing test isolation and platform expectations before closing.
- L16 | T3 documentation was reviewed. Test fixture repairs were observed RED then GREEN. Final checks: `git diff --check` passed; full suite passed with 131 tests and 1 skip (`/bin/zsh` unavailable). Existing warnings: `SyntaxWarning` in `swarm_setup.py`, importlib `DeprecationWarning`, and tarfile `DeprecationWarning`.
