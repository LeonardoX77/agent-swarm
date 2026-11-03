# Linux installation support

Objective: Adapt Agent Swarm installation for Linux on branch `feat/linux-installation`.
Delivery strategy: ask-on-risk. Test runner: `python3 -m unittest discover -s automation/agent-swarm/test`.

## Specs

S1. "crea una nueva rama y adapta la instalacion de agent-swarm en linux"

## Tasks

- T1 | S1 | delegated | in_progress | Portable Linux/WSL setup core and OS-matrix regression coverage verified (50 focused tests, 1 skipped); creating its work-unit commit.
- T2 | S1 | delegated | pending | Add manual Linux/WSL catalog and service boundaries with scenario coverage; commit pending.
- T3 | S1 | inline | pending | Update Linux/WSL installation documentation and run the full suite; commit pending.

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
