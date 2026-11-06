# Linux/WSL support: validation and gaps

Branch `feat/linux-wsl-support`, created from `main` after merging `feat/linux-installation`.
The WSL branch already implements the Linux code paths; this feature closes what it left unvalidated.

## Specs

- **S1** — "Implementar soporte WSL/Linux: modificar Agent Swarm para que el alta de Linux/WSL sea una capacidad oficial y repetible."
- **S2** — "soporte de puerto SSH configurable (2222, no sólo 22)"
- **S3** — "detección de Linux en vez de asumir macOS"
- **S4** — "montaje SMB Linux —por ejemplo, bajo /mnt/agent-projects— sin Finder, Keychain ni launchd"
- **S5** — "rutas y entorno correctos para WSL"
- **S6** — "pruebas, documentación y validación de Pi/Herdr en Linux"
- **S7** — "yo diría de activar o usar todas las opciones posibles, desde la mas fiable/rápida hasta la mas lenta, es decir, tenerlas todas activas y si falla una usar la otra." Agreed design (L5): ordered address candidates, Tailscale MagicDNS first, LAN as fallback; no reverse tunnel.

## Tasks

- **T1** — S6 — inline — done — Make the two macOS-only test failures hermetic (resolved tmp symlink, host `pi` shadowing); full suite 159 OK, 1 skipped on macOS.
- **T2** — S2–S5 — inline — pending — Audit the merged code against S2–S5 and list real gaps (evidence is `odd/tasks/linux-installation.md`).
- **T3** — S1, S6 — pending — Live bidirectional acceptance MacBook (hub) ↔ `wsl-leo` using the T4–T5 candidates. Needs user authorization: it writes SSH keys/config, the registry and a WSL mount.
- **T4** — S7 — delegated worker — done — SSH address candidates in `swarm-setup`: one `swarm-<name>` alias that tries candidates in order (`Match exec` or `ProxyCommand`), `HostKeyAlias` so the host key is verified identically on every path, both directions (origin→new and new→origin), registry support, idempotent re-runs, tests. Risk: item 2 (SSH trust and host-key verification). Verified independently (see L7); suite 192 OK, 1 skipped. Commits: helper and setup, see L8.
- **T5** — S7 — delegated worker — done — SMB host candidates for the Linux CIFS mount: try candidates in order at mount time only (no live failover), tests. Suite 167 OK, 1 skipped. Open: `mount //HOST/SHARE` fstab selection must be confirmed on the real WSL (T3). Commit: `728989a`.
- **T6** — S7 — delegated worker — done — Docs (English canonical + `docs/es` mirror) for candidates, failover order and the Public Wi-Fi firewall caveat.
- **T7** — S7 — shared-file WSL operator — pending — WSL `sshd` on `0.0.0.0:2222` and firewall for `100.64.0.0/10` + `192.168.0.0/24`. Needs confirmation in the WSL session.

## Log

- **L1** — "mergea los cambios que ha enviado el nodo wsl

después crea nueva rama e implementa esto:
 ### 1. Implementar soporte WSL/Linux
 [...] soporte de puerto SSH configurable (2222, no sólo 22); detección de Linux en vez de asumir macOS; montaje SMB Linux —por ejemplo, bajo /mnt/agent-projects— sin Finder, Keychain ni launchd; rutas y entorno correctos para WSL; pruebas, documentación y validación de Pi/Herdr en Linux."
- **L2** — Merge of `feat/linux-installation` committed on `main` as `9af53e4`; not pushed.
- **L3** — The WSL branch reports NOT validated: bidirectional acceptance between two machines, native macOS runs of the new code, a macOS hub reaching a Linux node over a real network.
- **L4** — Evidence: Twingate on the MacBook routed `100.96.0.0/12` and captured the Windows Tailscale IP `100.101.64.75`; with Twingate off, Windows and WSL reach the MacBook over Tailscale on 22 and 445, and `macbookleo` resolves via MagicDNS. MacBook → WSL works over LAN `192.168.0.21:2222` (fingerprint `SHA256:Gr4/UVLC0PBCdzizcP2elrJkTlkJOvz6gOU4CEzV6V8`). mDNS `.local` from/to WSL and a real SMB mount from WSL are untested.
- **L5** — "no necesito tener Twingate activo en el MacBook habitualmente" then "si" to: implement in `feat/linux-wsl-support` ordered address candidates for the SSH alias, mount-time SMB fallback, tests and docs.
- **L6** — Design decisions (parent): (a) a single candidate keeps today's alias bytes and known_hosts format, so existing aliases stay valid; (b) two or more candidates write `HostKeyAlias swarm-<name>` plus a `ProxyCommand` to an installed helper (`~/.local/agent-swarm/bin/swarm-ssh-connect`, stdlib Python) that connects to the first reachable candidate; known_hosts is keyed by the alias, so a candidate that presents another key fails closed; (c) setup: at least one candidate must be reachable, and every reachable candidate must present the human-verified key; unreachable candidates are reported, not trusted separately; (d) registry: optional host keys `fallback_addresses` (ordered list) and `share_hosts` (ordered SMB hosts for that spoke; default global `share.host`); (e) CLI: repeatable `--fallback-address`, `--origin-address` (reverse alias candidates, overrides the origin registry addresses), `--share-host`; (f) `swarm-smb-mount` Linux: repeatable `--host` in preference order, mount-time fallback only, `fstab-line` returns one line per host; macOS rejects more than one host.
- **L7** — T4 evidence. Parent found the helper broke under real OpenSSH (connect timeout kept on the socket; blocking buffered stdin read); fixed with raw-fd relay and real-ssh tests. Empirical: with `HostKeyAlias` and `Port 2222`, OpenSSH looks up the plain `swarm-<name>` line; a wrong key under the alias gives `Host key verification failed`. Independent verifier found 3 blockers (stale alias key appended instead of failing closed; leading-hyphen candidates reaching the helper as options; unquoted multi-candidate `IdentityFile` with spaces in HOME), all fixed test-first; re-verification found the stale-key check missing in the reverse direction, fixed and checked by the parent. Single-candidate alias and known_hosts bytes are identical to `main`. Follow-up (pre-existing on `main`, out of scope): the single-candidate alias also leaves `IdentityFile` unquoted, so a HOME with spaces breaks it.
- **L8** — Delivery: "no hay PR, un unico merge a main" (delivery_strategy=single local merge, no push) and "configura ya el wsl-leo" (authorizes the live setup T3). Branch total ~1,000 authored lines in 5 commits; the user accepts the review load.
- **L9** — WSL finding: Windows rule `Tailscale-In` allows any inbound port from any source to `100.101.64.75`, so a WSL `sshd` listening on Tailscale would be reachable from every tailnet device (key-only). T7 stays open as a separate user decision. Candidate order chosen (see L10 for the live run): MacBook → WSL LAN `192.168.0.21` first, Tailscale `5cg6031yzw.tail3eebf8.ts.net` second (only LAN answers today); WSL → MacBook and SMB Tailscale `macbookleo.tail3eebf8.ts.net` first, LAN `192.168.0.10` second (both proven).
- **L10** — Live `swarm-setup add-host wsl-leo` (from `main`). Real defects found and fixed test-first, each merged to `main`: (1) the alias-keyed known_hosts line was built from the `ssh-keyscan` comment line `# host:port SSH-2.0-...` and the authorization probe lacked `HostKeyAlias`, so phase 3 waited forever (`98a4b44`, merge `0a5cb85`); the garbage line was removed from `~/.ssh/known_hosts` with a backup; (2) the reverse ProxyCommand rendered the origin's interpreter `/Users/leo/miniconda3/bin/python3` into the WSL config (`17b5e58`). Phases 1-4 OK (forward alias works through the helper over LAN; herdr Pi integration installed). Phase 5 failed on defect (2). The bad `Host swarm-macbook` block is still in the WSL `~/.ssh/config` and must be removed (backup first) before resuming. Advisory: OpenSSH `UpdateHostKeys` added RSA/ECDSA keys under `swarm-wsl-leo`; the stale-key check would treat them as stale on a fresh setup. Then the WSL became unreachable: LAN `192.168.0.21:2222` times out, Tailscale shows the Windows node via DERP relay `mad` (no longer direct), `tailscale ping` no reply.
- **L11** — Independent verification (Risk: item 2) of `98a4b44` and `5daf80c`: keyscan parsing PASS, HostKeyAlias probe PASS, stale check PASS with the UpdateHostKeys ADVISORY; BLOCKER in `5daf80c` (any absolute-looking one-line interpreter output accepted, and reverse remote writes could start before failing). Fixed test-first on `fix/reverse-python-validation` (strict path pattern plus remote `test -x`, resolved before the first reverse write); independent re-verification PASS on all five items, 195 OK, 1 skipped.
