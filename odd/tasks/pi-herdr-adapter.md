# Pi Herdr adapter

## Authorization and scope

User authorized implementing automatic per-task Pi dispatch through Herdr, correlated responses and recovery without automatic resubmission. Preserve pre-existing sessions. No commits, key installation, global configuration, mounts, or production deployment. Existing v1 remains unchanged. Technical artifacts follow existing project language conventions; code in English.

## Decisions

- El llamador siempre es un agente; no se necesita un disparador autónomo.
- El adaptador se ejecuta desde el repositorio montado por SMB; no habrá una copia fija en el mini.
- Si uno de los Macs está apagado, se usan subagentes locales.
- Se descartó el login de Claude por SSH directo.
- Las fallas de red reciben manejo ordinario (errores y timeout predeterminado), sin lógica especial de recuperación.
- La clave restringida con comando forzado ya no es necesaria para este uso agente a agente; la documentación v1 se conserva sin cambios.

## Evidence and design

- Pi 1.0.2 / Herdr 0.9.3 live owned-resource probe returned agent_session.kind=path and stable session JSONL path.
- Owned session header type=session/version=3/id; entries type=message/id/parentId. User text content array; descendant assistant text with stopReason=stop. Structured persisted messages, not terminal snapshots.
- Session result must validate pinned path/header, exact submitted user content, parent-chain ancestry, final assistant stopReason=stop and matching owned agent identity. No result from idle/done alone.
- Dedicated per-task resources; no existing session attachment, pane allowlists or warm reuse. Durable local admission and pre-side-effect intent prevent automatic resubmission after ambiguity. This is at-most-one local attempt, not exactly-once distributed execution.
- Unknown creation/start outcome fails closed. Unknown ownership never authorizes cleanup. Timeout means pending/unknown, not cancellation.
- State and session files live on destination's local filesystem, outside SMB. Adapter is host-local; running it by SSH controls GUI Herdr. No forced-key deployment or v1 integration in this scope.

## Tasks

- [x] 1. Implement strict durable ledger and structured Pi session parser with deterministic test-first checks. Route: delegated writer (multi-file code). Allowed surfaces: lib/herdr_ledger.py, lib/pi_session_result.py, test/test_herdr_ledger.py, test/test_pi_session_result.py under automation/agent-fabric. Evidence: RED then GREEN; independent verifier confirmed fixes and 53 tests PASS. No commit (user constraint).
- [x] 2. Implement additive host-local fabric-herdr-task CLI/controller with closed argv, explicit owned IDs, submit/recover/close and no resubmit after intent; add mocked lifecycle tests and usage documentation. Route: delegated writer (multi-file code). Scope narrowed after unit1 readback. Evidence: RED/GREEN per fix; 71 tests PASS. Live E2E on the mini surfaced and fixed six defects that mocks hid: agent name over 32 chars; invented 'executor' envelope field and 'host-local' mode; `--timeout` without `--wait` (rc 2, nothing sent); parser MAX_LINE 64 KiB vs a ~99 KB role:system entry (now 1 MiB line / 8 MiB file); typed error envelopes on stdout vs stderr; stored result after close.
- [x] 3. Independently verify focused/full tests, safety boundaries and documentation; run isolated end-to-end probe only if no config/install changes required. Route: delegated verifier. Evidence: final live run on the mini PASS (task 57c5cca9): one submit + idempotent repeat created one tab; Pi replied with the exact nonce; recover returned status done from the structured session JSONL (user/assistant entry ids matched); close returned closed with raw typed tab_not_found; recover/close on the closed task returned the stored result with no new resources; final baseline equal (w1:t1, t2, t3, tG). Not covered: forced SSH key deployment, bridge auth over direct SSH, reverse transport, real network outage, concurrency across different tasks, cleanup of unknown-phase resources.
- [x] T4. Probar el modo RPC de Pi. Ruta: verificador delegado. Evidencia: protocolo funcional por SSH (response con id, message_end, agent_settled, salida 0); sin respuesta útil por autenticación (claude-bridge `Not logged in`; OpenAI 400 para modelos no admitidos por la cuenta ChatGPT/Codex). Contexto entre prompts sin verificar. Conclusión: RPC no reemplaza al adaptador Herdr mientras el modelo dependa del llavero de la sesión gráfica.
- [ ] T5. Probar el transporte de retorno mini → MacBook. Estado actual: el puerto 22 del MacBook está abierto y el mini lo alcanza, pero el mini no tiene entrada `known_hosts` para `MacBookLeo.local` ni clave privada; requiere verificación humana de la huella y una clave autorizada en el MacBook. Ruta: TBD. Evidencia: pendiente.
- [ ] T6. Probar dos tareas concurrentes. Ruta: verificador delegado. Bloqueado: la Mac mini perdió el montaje `/Volumes/agent-projects` (en `/Volumes` sólo queda `Macintosh HD`); remontar requiere al usuario. Ningún recurso creado.
- [x] T7. Añadir timeout predeterminado y manejo ordinario de errores para `recover`/`submit`. Ruta: implementación local (CLI/controlador/pruebas/documentación). Evidencia: RED `python3 -m unittest automation/agent-fabric/test/test_herdr_task.py automation/agent-fabric/test/test_herdr_task_cli.py` observó 19 pruebas, 4 errores esperados (sin `wait_recover` ni `--wait`); GREEN del mismo comando: 21 pruebas PASS. Suite completa `python3 -m unittest discover -s automation/agent-fabric/test`: 77 pruebas PASS; smoke Python 3.9 de módulos de lib y `git diff --check`: PASS.

## Checks and delivery

Applicable Python unittest behavior tests: observe RED then GREEN. Full suite: python3 -m unittest discover -s automation/agent-fabric/test. Native assessment/review only if available and user-owned switch enabled; missing assessment requires independent verification. No work-unit commits: explicit user no-commit constraint overrides default commit workflow. Do not mark delivery/deployment complete from mocked tests.

Review workload: two small units (core ledger/parser, lifecycle CLI). Estimated 500–750 authored diff lines per unit including tests; no PR requested. Keep each coherent and surface any scope expansion. Push/PR/install remain human decisions.

## Current state

Tasks 1-3 complete and verified live on the mini (manual invocation of the mounted source; nothing installed or deployed). Native assessment unavailable (package-local binary missing), so independent verification required. Existing uncommitted changes must be preserved. Historical probe IDs are evidence only, never reusable target IDs.
