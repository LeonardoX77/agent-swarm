# Linux installation support

Objective: Adapt Agent Swarm installation for Linux on branch `feat/linux-installation`.
Delivery strategy: single-pr. Test runner: `python3 -m unittest discover -s automation/agent-swarm/test`.

## Specs

S1. "crea una nueva rama y adapta la instalacion de agent-swarm en linux"
S2. "se supone que había que adaptar swaagents-swarm a linux, cambia lo que sea necesario" (replaces the manual `--linux-catalog-root` contract: Linux must behave as close to macOS as possible.)
S3. "swarm-smb-mount y swarm-update siguen siendo solo macOS. << adaptalos"
S4. "swarm-delegate fija /usr/bin/python3 en el destino." (user: "arreglalo" implied by the list; macOS behavior must stay identical.)
S5. "La coincidencia de hostname_prefix con hostname -s en WSL (mayúsculas/minúsculas) no está probada. << pruebala"
S6. "4 pruebalo. pruebalo todo y que sea lo más parecido a la version macos" (gui_cwd = $HOME/tmp must be tested; test everything.)
S7. "6 quita las redundancias" (redundant tests), "7 arregla lo que creas" (normalize paths), "8 arreglalo" (SyntaxWarning), "3 ok" (neutral Remote Login message), "5. da igual , arregla lo que sea en proximos commits y commitea".

S8. "No validado: un swarm-setup add-host real por SSH, la delegación de tareas hacia Linux y la ejecución en un macOS real. ... << adelante!" (run the real add-host and delegation test; add whatever is needed for it to work on this WSL.)

## Tasks

- T1 | S1 | delegated | done | Portable Linux/WSL setup core and OS-matrix regression coverage verified (50 focused tests, 1 skipped); commit: `a13062a`.
- T2 | S1 | delegated | done | Manual Linux/WSL catalog boundary and platform-specific service avoidance verified (59 focused tests, 1 skipped); commit: `82a4818`.
- T3 | S1 | delegated | done | Linux/WSL documentation and full-suite test isolation/platform expectations verified (131 tests passed, 1 skipped); commit: `38dd25a`.
- T4 | S2,S6,S7 | delegated | done | Linux SMB mount (swarm-smb-mount Linux backend + setup integration replacing `--linux-catalog-root`), Linux update phase, neutral Remote Login text, SyntaxWarning, redundant-test cleanup, gui_cwd tests; commit: `2456b75`.
- T5 | S3 | delegated | done | swarm-update Linux backend (systemd --user timer), identical CLI/JSON contract; commit: `bbf1e12`.
- T6 | S4,S5 | delegated | done | swarm-delegate python resolution and case-insensitive hostname_prefix matching with real hostname tests; commit: `c39e95d`.
- T7 | S2,S3 | delegated | done | Linux/WSL documentation updated to the new design (7 files); commit: `324927a`.
- T8 | S6 | inline | done | Real verification on this WSL: swarm-update via real systemd --user (installed, run, status, uninstalled), swarm-smb-mount against a temporary loopback Samba share (port 1445 because Windows owns 445) with persistence and full revert, real hostname resolution for 5CG6031YZW. Not run: real swarm-setup add-host over SSH (consent unanswered), delegation to Linux. Packages cifs-utils and samba remain installed; commit: `no code change`.
- T9 | S2,S8 | delegated | done | `--ssh-port` / `--origin-ssh-port` in swarm-setup (Windows owns TCP 22 on this WSL; its sshd is on 127.0.0.1:2222); verified independently (one blocker found and fixed: explicit `--origin-ssh-port 22` must conflict with an existing non-default reverse alias); commit: `94f8144`.
- T10 | S8 | inline+delegated | done | Real add-host over SSH (:2222) and real delegation on this WSL, then full revert verified against a baseline; real findings fixed (pi PATH discovery, wait text, herdr Pi integration probe/install); code commit: `94f8144`, docs commit: `4b49e7a`.

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
- L17 | User corrections (verbatim, 2026-11-03): "1 ok
2  El rechazo a macOS llega tarde. --linux-catalog-root contra << no se de que va esto. se supone que había que adaptar swaagents-swarm a linux, cambia lo que sea necesario
3 ok
4 pruebalo. pruebalo todo y que sea lo más parecido a la version macos
5. da igual , arregla lo que sea en proximos commits y commitea
6 quita las redundancias
7 arregla lo que creas
8 arreglalo
 - swarm-delegate fija /usr/bin/python3 en el destino.
 - swarm-smb-mount y swarm-update siguen siendo solo macOS. << adaptalos
- La coincidencia de hostname_prefix con hostname -s en WSL (mayúsculas/minúsculas) no está probada. << pruebala"
- L18 | Decision: item 1 (untrack this doc) was REVERTED: the repo already tracks nine other `odd/tasks/*.md` files, so keeping it tracked follows the project convention (my earlier review claim was wrong). Design: Linux SMB uses cifs via a user-mountable fstab entry (human adds it with root, credentials file mode 600 created by the human; tool never uses sudo or handles passwords), mount point `/mnt/<share>`, persistence through systemd --user timer degrading with a warning when unavailable; `--linux-catalog-root` is removed. Facts: this WSL has sudo -n, systemd --user running, no cifs-utils/samba/herdr; herdr ships a Linux installer (`curl -fsSL https://herdr.dev/install.sh | sh`).
- L19 | T4-T7 implemented by workers; parent reviewed each diff. Host-write test could not be delegated (worker refused: write boundary limited to the evidence file), so the parent ran the real SMB test inline after the user answered "Sí, instalar y probar". Independent verifier for T4-T6 still pending at this point. Parent fix: restored the original behavior of identical hostname prefixes in `host_registry` (only case-variant ambiguity is rejected).
- L20 | Interim verifier findings (task mw1vaqdx-3-35nh, offline `systemd-analyze verify` on scratch units): BLOCKER in `swarm-smb-mount` Linux units: `StandardOutput=append:"/abs/path"` / `StandardError` are emitted with quotes so systemd warns `path is not absolute` and the documented log files are ignored; with a home containing space, `%` and `$`, ExecStart argv[0] keeps `$$` (systemd does not dollar-expand the executable) and the command is not executable. ADVISORY pending severity: `unmount --remove-persistent` returns ok/persistent_removed true and deletes units even when `systemctl --user disable --now` fails. `swarm-update` units verify clean. Fixes to be applied by the T4 worker after the final verdict.
- L21 | Independent verification (tasks mw1vaqdx-3-35nh then mw1vqkcm-5-ltm5): T5 and T6 PASS; T4 had 4 blockers (dry-run ran installers, SMB unit log directives invalid, `$` in HOME broke ExecStart, setup hid the persistence warning) plus a remove-persistent advisory, all fixed (worker mw1vj0k4-4-185x) and re-verified: dry-run never installs on Linux or macOS (macOS `brew install herdr` also ran in dry-run at origin/main, now fixed on both), systemd-analyze verify clean (exit 0, empty stderr) for normal and `space % $ home` HOME, warning surfaced, failed disable keeps units. T7 docs fixed after the re-verification (journald fallback, README persistence degradation, installer wording). Final full suite with `-W error::SyntaxWarning`: 146 tests OK, 1 skipped (`/bin/zsh` absent). Real checks on this WSL (all reverted): swarm-update via systemd --user, swarm-smb-mount against a temporary loopback Samba share (port 1445), SMB unit logs written, hostnames. Not validated: real `swarm-setup add-host` over SSH, delegation to a Linux host, native macOS runs. cifs-utils and samba remain installed on this WSL.
- L22 | User: "<< adelante!" for the real add-host/delegation test; also asked why the packages are installed, how to find the hub data, and to wait with push/PR. First real attempt aborted at phase 3 with `SSH host fingerprint mismatch` (the safety check worked): 127.0.0.1:22 and every other local address on port 22 belong to the Windows host (OpenSSH_for_Windows; bind to 10.255.255.254:22 fails with EADDRINUSE), while this WSL sshd only listens on 127.0.0.1:2222; swarm-setup hardcodes port 22. Decision: add `--ssh-port` and `--origin-ssh-port` (default 22, alias gets `Port` only when not 22) instead of reconfiguring sshd. A stray key `~/.ssh/agent_swarm_wsl_spoke` from the aborted run was removed.
- L23 | Real run results (all state reverted and verified against /tmp baseline): add-host over real SSH :2222 completed phases 1-9 (fingerprint check, human authorized_keys step, herdr installed by --install-missing, real CIFS mount via the setup mount phase, registry /mnt/agent-projects, skill, systemd update timer); phase 10 acceptance failed SELF_TARGET (single host, NOT validated). Delegation hub->Linux node: first task `unknown` because `herdr agent get` has no `agent_session` without the herdr Pi integration; after `herdr integration install pi` a new task returned the exact nonce and close closed only its own tab. Fixes: `$HOME/.pi/agent/bin` PATH discovery, runtimes wait text lists missing probes and a headless herdr start hint, `herdr-pi-integration` probe/install (dry-run never installs). Independent verifier (mw2bv9b9-8-7g2c) found one blocker (explicit `--origin-ssh-port 22` silently kept a `Port 2200` reverse alias); fixed by tracking whether the origin port was explicit; the fix was validated by the verifier's own regression test plus the full suite (158 tests OK, 1 skipped, -W error::SyntaxWarning) but NOT re-verified by a second independent run. Still NOT validated: bidirectional acceptance between two machines, native macOS runs of the new code, a macOS hub reaching a Linux node over a real network. cifs-utils and samba remain installed on this WSL (user asked why; decision pending). Push and PR deliberately not done (user: esperamos).
