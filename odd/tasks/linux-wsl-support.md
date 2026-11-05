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

## Tasks

- **T1** — S6 — inline — done — Make the two macOS-only test failures hermetic (resolved tmp symlink, host `pi` shadowing); full suite 159 OK, 1 skipped on macOS.
- **T2** — S2–S5 — inline — pending — Audit the merged code against S2–S5 and list real gaps (evidence is `odd/tasks/linux-installation.md`).
- **T3** — S1, S6 — pending — Live bidirectional acceptance MacBook (hub) ↔ `wsl-leo` over LAN `192.168.0.21:2222`. Needs user authorization: it writes SSH keys/config, the registry and a WSL mount.

## Log

- **L1** — "mergea los cambios que ha enviado el nodo wsl

después crea nueva rama e implementa esto:
 ### 1. Implementar soporte WSL/Linux
 [...] soporte de puerto SSH configurable (2222, no sólo 22); detección de Linux en vez de asumir macOS; montaje SMB Linux —por ejemplo, bajo /mnt/agent-projects— sin Finder, Keychain ni launchd; rutas y entorno correctos para WSL; pruebas, documentación y validación de Pi/Herdr en Linux."
- **L2** — Merge of `feat/linux-installation` committed on `main` as `9af53e4`; not pushed.
- **L3** — The WSL branch reports NOT validated: bidirectional acceptance between two machines, native macOS runs of the new code, a macOS hub reaching a Linux node over a real network.
