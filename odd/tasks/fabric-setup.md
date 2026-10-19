# Single-process host setup and daily auto-update

One command sets up a new Mac end to end through all phases, pausing only where a person must act, and can install a daily, sudo-free auto-update of Herdr, Moshi, mosh-server, Pi and Pi extensions.
Builds on odd/tasks/generic-hosts.md (registry, fabric-delegate, add-host guide). Branch feat/pi-herdr-adapter. No push or merge.

## Specs

- S1. "quiero tambien comprobar que si herdr, moshi, moshi server, pi o sus extensiones están desactualizados se actualicen solos (configurable desde el setup, no requiere sudo) comprobando una vez al dia"
- S2. "tiene que se un solo proceso, es decir, el setup tiene que comenzar con el script, y desde ahi deben ejecutarse todas las fases hasta que termine."
- S3. "debe proporcionar información resumida en inglés y detallada (con por ejemplo --verbose) para detectar errores imprevistos"
- S4. Registry values (e.g. the hub `share`) are read by the script, never copied by hand into commands.
- S5. Human-only steps (Remote Login, first Pi login in the GUI, first SMB connection with the password, host-key confirmation) pause the same process with exact instructions and continue when the condition is met; an interrupted run resumes from the first unfinished phase.
- S6. Re-running setup against an already configured host changes nothing and reports every phase as already done.

## Tasks

| ID | Specs | Route | Commit |
|---|---|---|---|
| T1 | S1, S3 | Delegated writer: `bin/fabric-update` (check/update components, daily LaunchAgent, config file, status, dry-run) with tests | done — `python3 -m unittest automation/agent-fabric/test/test_fabric_update.py` GREEN; full test discovery, CLI help, read-only verbose check, and `git diff --check` recorded in the delivery handoff |
| T2 | S2–S6 | Delegated writer: `bin/fabric-setup` + `lib/fabric_setup.py`, 10 phases, state/resume, polling waits, summary + `--verbose` + log | done — 28 setup tests (17 unit + 11 two-Mac scenarios with a stateful fake that executes the remote programs against a temp home); full suite 138 PASS on Python 3.12 and 3.9. Parent review found D1–D9 (non-TTY waits exited, literal `~` remote dirs, literal `\n` in known_hosts, change classification, registry compare, etc.); scenarios found 5 more (skill archive path, self-move, missing remote known_hosts, dry-run registry KeyError, dry-run acceptance exit 4). All fixed. |
| T3 | S2, S5 | Delegated writer: `docs/setup/add-host.md` rewritten around `fabric-setup`; README and runbooks updated | done — canonical one-command flow, 10 exact phases, human wait/resume details, status/log/exit-code diagnostics, manual troubleshooting appendix; README and guided-setup pointers mention `fabric-setup` |
| T4 | S2, S3, S6 | Delegated verifier: tests, help/docs consistency, live idempotent run of `fabric-setup` against the already configured Mac mini (must change nothing), `fabric-update --dry-run` on both Macs | pending |
| T5 | S1 | Enable the daily auto-update on the MacBook and the Mac mini — only after the user confirms | pending |

## Log

- L1. User: "quiero tambien comprobar que si herdr, moshi, moshi server, pi o sus extensiones están desactualizados se actualicen solos (configurable desde el setup, no requiere sudo) comprobando una vez al dia" / "El detalle: hoy el agente copia esos valores del registro a mano << de que hablas?" / "¿Lo armo? << si, pero tiene que se un solo proceso, es decir, el setup tiene que comenzar con el script, y desde ahi deben ejecutarse todas las fases hasta que termine. debe proporcionar información resumida en inglés y detallada (con por ejemplo --verbose) para detectar errores imprevistos"
- L2. Inventory (read-only): Herdr 0.9.3 via Homebrew on both Macs, server as a LaunchAgent (`homebrew.mxcl.herdr` on the MacBook, `dev.herdr.server` on the mini). Moshi = `moshi-hook`: Homebrew tap `rjyo/moshi` on the mini, standalone binary in `~/.local/bin` on the MacBook (has `moshi-hook update`, `service`). mosh 1.4.0 via Homebrew on both (`mosh-server`). Pi: MacBook wrapper `/opt/homebrew/bin/pi` -> `~/.hermes/node/...` (1.3.0); mini nvm global (1.2.0); `pi update --all` updates Pi and packages. No component needs sudo.
- L3. Interpretation: "moshi server" covers both `mosh-server` (mosh) and the `moshi-hook` daemon. Updating the Herdr binary does not restart the running Herdr server; restarting it would end live tabs, so the updater never restarts it automatically and reports the pending restart instead.
- L4. Decision: setup runs on an existing registered Mac (the origin) and drives the new Mac over SSH. Human waits poll their condition inside the same process; `--no-wait` exits with a resume hint instead.
- L5. T2: first writer passes left placeholders and too few tests; split into smaller units (harness + one scenario at a time) which surfaced real bugs. The registry gained a required `address` field so the new Mac can reach the origin.
- L6. T4 live verification found B1–B3: `fabric-setup` passed duplicate subprocess keyword arguments, causing every default-runner command to fail; its runner now applies defaults only when absent and real-subprocess smoke tests cover setup, update, and delegate help/default wrappers. `fabric-update check` and `status` did not establish the configured or non-interactive-discovered tool `PATH`; all subcommands now use configured `path` or self-contained discovery of Homebrew, nvm, Hermes, and local bins, with verbose PATH reporting. The update runbook now notes that `check` does not change installed software while Homebrew may refresh its local API cache.
