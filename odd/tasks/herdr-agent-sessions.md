# Sesiones de agente persistentes sobre Herdr

## Objetivo y estado

Añadir un canal alternativo para conversar con agentes locales de otros Macs mediante SSH y Herdr: abrir un agente cuando falte, conservar contexto durante una tarea, esperar sus respuestas y terminarlo cuando ya no se necesite.

**Estado: diseño y experimentación; canal no implementado.** Las guías actuales permiten preparar la v1 one-shot, pero no configuran este canal de principio a fin. Las pruebas manuales no equivalen a una implementación ni a una guía reproducible.

La implementación actual y su plan de continuidad se documentan en [Pi Herdr adapter](pi-herdr-adapter.md).

## Canales distintos

- **v1 existente:** SSH restringido a `fabric-runner`, solicitud JSON, ejecución one-shot de Pi/OpenCode/Claude.
- **Herdr propuesto:** runner remoto controla un agente interactivo y su conversación; requiere un contrato nuevo, no comandos SSH arbitrarios del cliente.
- **Gentle Pi:** `orchestrator_list` y `orchestrator_send_message` descubren sesiones del perfil local y usan sockets Unix locales. No tienen transporte directo entre equipos en la implementación inspeccionada. Una aceptación es encolado, no confirmación de lectura.
- **RPC de Pi:** proceso persistente controlado por JSONL en stdin/stdout. Puede estudiarse un transporte SSH explícito; no permite por sí solo adjuntarse a una terminal Pi existente.
- **`aiconnect`:** función local en `~/.zshrc`: `macmini` conecta a `leo@MacMiniLeo.local`; `bea` a `beatrizdelcampo@MacBookBea.local`. Solo abre SSH normal; no instala componentes ni inicia agentes.

## Diseño revisado (pendiente de implementar)

- No se requiere una allowlist manual de panes. Fabric registra los identificadores de los recursos que crea y solo controla esos recursos; un nombre `fabric` no demuestra propiedad.
- Una conversación pertenece a una tarea y mantiene contexto entre mensajes. Cada mensaje necesita identidad y correlación con su resultado.
- Un agente atiende una tarea a la vez. Una reserva atómica local evita mezclar conversaciones; no es un lock del repositorio. No se reenvían mensajes a ciegas tras errores o cortes de SSH.
- Apertura, envío, finalización de tarea, reset y terminación son operaciones distintas. `close` no debe significar implícitamente reset.
- Reutilizar un agente caliente entre tareas es una optimización pendiente de medir. El primer alcance conserva el agente durante la tarea y lo termina al finalizar; reset y reutilización requieren evidencia verificable por runtime.
- El estado `idle` entre mensajes no significa que la tarea haya terminado. La limpieza no debe destruir una conversación vigente por una pausa del usuario.
- Herdr `prompt --wait` espera estados, no turnos; `agent read` devuelve snapshots de terminal, no respuestas estructuradas. `blocked` no es éxito. Correlación y extracción de respuestas siguen sin resolver para producción.
- El runner mantiene argv cerrados y validación de runtime/workspace. El contrato v1 no acepta acciones de sesión ni un tercer host; deben diseñarse separadamente sin romper v1.
- La topología e instalación pertenecen a la arquitectura y guías de host. Moshi solo será requisito si se define y valida su función; no fue necesario en la prueba de mensajería Herdr.

## Infraestructura observada (histórica; no inventario actual)

| Momento de la evidencia | Host | Cuenta observada | Endpoint usado | Observación Herdr |
|---|---|---|---|---|
| Antes de la observación posterior | MacBook | `leo` | host originador | Binario 0.9.3; servidor observado 0.7.5 tras actualizar. |
| Antes de la observación posterior | Mac mini | `leo` | `100.127.117.94` / `MacMiniLeo.local` | Binario 0.9.3; servidor observado 0.8.0 e incompatibilidad declarada. |
| Prueba exitosa | MacBookBea | `beatrizdelcampo` | `100.117.32.84` / `MacBookBea.local` | Cliente y servidor 0.9.3 compatibles. |
| Evidencia posterior suministrada | Mac mini y MacBook | no especificada | no especificado | Servidores observados en 0.9.3, protocolo 22, compatibles. |

La última fila es evidencia suministrada, no una comprobación realizada en esta tarea ni una garantía de estado futuro. Solo se probó acceso saliente desde MacBook; no se demostró una malla bidireccional. La disponibilidad de Bea varió entre intentos. La configuración vigente usa la cuenta existente `leo` en la Mac mini y dos hosts. Esto resuelve el drift de cuenta; la reconciliación pendiente de la topología autorizada y la participación de Bea no queda resuelta por ese cambio. El PATH del SSH del mini no encontró Pi/Claude: no demuestra ausencia de instalación.

## Evidencia de la prueba delegada en MacBookBea

Experimento aislado por runtime, en `/Users/beatrizdelcampo/tmp`, sin intervenir sesiones existentes, instalar software ni reiniciar servidores.

| Fase | Pi | Claude |
|---|---|---|
| Crear tab y arrancar agente | PASS: tab `w1:t6`, pane `w1:p6`, `pi --no-tools --no-context-files` | PASS: tab `w1:t7`, pane `w1:p7`, `claude --restricted` |
| Dar nonce y pedir ACK | PASS | PASS |
| Pedir nonce en segundo mensaje | PASS: recordó el dato exacto | PASS: recordó el dato exacto |
| Reset nativo | `/new`: nueva ruta de sesión y aviso `New session started` | `/clear`: historial visual vaciado y cambio de título/revisión; sin ID de sesión expuesto |
| Pedir nonce sin revelarlo después del reset | PASS: `UNKNOWN` | PASS: `UNKNOWN` |
| Terminar y cerrar recursos propios | PASS: salida con Ctrl+D y cierre de tab | PASS: salida con Ctrl+D y cierre de tab |

Después de la limpieza, las listas solo mostraron las tabs/agentes originales `w1:t1` y `w1:t2`. Los identificadores anteriores son evidencia histórica, no destinos reutilizables.

**Limitaciones:** ambos resets devolvieron `agent_prompt_stalled` pese a ejecutarse. No se reenviaron. La ayuda de Herdr 0.9.3 exige observar actividad en cinco segundos y declara que no correlaciona turnos. Las respuestas se observaron en snapshots; no existe aquí una prueba de extracción estructurada, aislamiento de memoria externa, deduplicación, concurrencia o resistencia a cortes. Resetear conversación no revierte archivos ni procesos.

## Comprobación de mensajería propia entre equipos

La inspección delegada encontró una sesión Pi viva en el mini y su socket bajo `/private/tmp/gentle-pi-501/.../*.sock`. En `gentle-pi/lib/agents-session-transport.ts`, la presencia se enumera en el directorio del perfil local, el endpoint se restringe al directorio local de sockets y las conexiones usan `node:net` sobre paths Unix. Las herramientas se registran como mensajería del `trusted local profile`.

**Resultado:** no hay comunicación directa cross-host por las herramientas instaladas. No se envió un ping fingiendo ese transporte mediante Herdr, archivos de cola o sockets manipulados. Bea no estaba accesible durante esa inspección; eso no cambia el límite local confirmado. Un puente SSH/RPC sería una funcionalidad distinta que aún no existe en Fabric.

## Auditoría de las guías para una máquina nueva

**Resultado: insuficientes para el canal persistente pretendido.**

- `docs/architecture.md` y `fabric-runner` describen/implementan solo one-shot.
- Setup/config definen `leo` en ambos hosts, dos hosts y aliases que no incluyen Bea.
- Preflight no valida Herdr cliente/servidor, integración, socket ni PATH efectivo del canal.
- No hay procedimiento reproducible de apertura, conversación, reset, terminación y recuperación.
- No hay semántica implementada para respuesta correlacionada, mensaje ambiguo, reserva de agente o propiedad de tabs.
- Rollback no cubre recursos Herdr.
- La preparación privilegiada, huellas SSH y autenticación de proveedores requieren intervención humana local; un agente no puede prometer configuración autónoma total.

## Tareas y aceptación

### Unidad autorizada: cuenta del Mac mini

- [x] Escritor: sustituir la cuenta `jarvis` por la cuenta existente `leo` en configuración, instalador, pruebas y guías; no crear ni modificar cuentas en los hosts.
- [x] Verificación independiente: controles de identidad confirmados; 45 pruebas OK y `git diff --check` limpio. Sin cambios en hosts ni commit.

### Unidad autorizada: guía con intervención humana intercalada

- [x] Escritor: documentar pasos automatizables, pausas humanas, verificaciones y reanudación; distinguir v1 de Herdr pendiente. Comprobación estructural local de enlaces y flags realizada.
- [x] Verificación independiente estructural: flags y límites coherentes con el código, 23 enlaces locales comprobados y `git diff --check` limpio. No equivale a despliegue en una máquina nueva.

### Unidad futura: skill global para tareas remotas

**Estado: artefactos fuente de skill y bootstrap creados; instalación en hosts, activación automática, verificación independiente y canal de retorno siguen sin implementar o verificar.** No se presume descubrimiento global, carga automática ni mensajería nativa entre hosts.

- [x] Escritor documental: añadió la fase de diseño, sus STOP/reanudación y enlaces desde ambas guías de host, condicionado a comprobaciones estructurales locales.
- [x] Verificación independiente: revisar enlaces, alcance pasivo y que la guía no afirme rutas, flags, despliegue o activación no validados. Superada: comprobación documental de T11; los enlaces, comandos y límites se conciliaron con `odd/tasks/pi-herdr-adapter.md`.
- [x] Crear los artefactos fuente de la skill global y el bloque de bootstrap en el repositorio Git; comprobaciones estructurales locales realizadas. No implica instalación en ningún host.
- [x] Instalar la skill en la Mac mini por copia local (`scp`, no clon: los artefactos aún no están commiteados) en `~/.pi/agent/skills/` y `~/.claude/skills/`; nunca SMB. Bloque de bootstrap añadido una sola vez a `~/.pi/agent/AGENTS.md` (nuevo) y `~/.claude/CLAUDE.md` (backup `CLAUDE.md.pre-fabric.bak`). Falta instalar en el MacBook y reemplazar la copia por un clon cuando exista commit.
- [ ] Consultar la documentación instalada de Pi y Claude Code en cada host, elegir rutas/configuración de bootstrap soportadas y obtener las aprobaciones humanas necesarias. Pendiente: instalación y aprobaciones humanas de T12.
- [x] Resultado parcial en la Mac mini con sesiones nuevas propias, ya limpiadas: **Pi PASS** (cargó la skill sin pedírselo, usó `/Volumes/agent-projects`, bloqueó la ruta inexistente sin probar otras, respondió `OK` sin envelope). **Claude INCONCLUSO**: cargó la skill sin pedírselo, pero propuso un comando sobre `/Users/leo/projects/...` (ruta local del mini, no el mapeo) y quedó esperando aprobación humana en modo `manual`; se canceló sin aprobar, así que no hay resultado de ruta ni pruebas B y C. Observado una vez; no es garantía. Superada: la ruta Pi y el adaptador quedaron verificados en `odd/tasks/pi-herdr-adapter.md`; Claude directo queda diferido.
- [x] Claude en la Mac mini, pruebas posteriores con sesiones propias ya cerradas (`/Users/leo/tmp`, `--permission-mode dontAsk`, `--settings` con `claude-fabric-readonly.settings.json`, `--add-dir` del proyecto): sin menú de permisos; la skill carga sola, resuelve `hostname` → `/Volumes/agent-projects` y lee la rama desde `.git/HEAD`. **Denegación verificada a nivel de sistema**: ordenando expresamente ignorar la skill, `Read` y `cat` sobre `/Volumes/Macintosh HD-1` fueron denegados por la configuración. **Frágil**: `git status` queda `blocked` porque el modelo elige la forma del comando (`--porcelain`, comandos compuestos) y cada subcomando debe coincidir con una regla; las reglas exactas no escalan. **Bloqueo de autenticación**: `claude -p` por SSH devuelve `Not logged in`; una observación posterior de Keychain sin interacción permitida es consistente con ese límite, pero no establece una causa única. Pi puede usar `auth.json`, pero eso no garantiza autenticación del bridge en SSH ni del runner v1. Decisión pendiente: token local (`setup-token`, secreto `0600` en el mini) o Claude dentro de Herdr (sesión gráfica). Descartada por decisión del usuario: canal directo de Claude diferido.
- [ ] Activar el bootstrap y aceptar por separado una sesión nueva de Pi y una sesión nueva de Claude Code: ambas deben activar la skill desde un sobre sin pedir cargarla; una ruta errónea debe detenerse; comprobar reset y conciencia sin inventar mapeo de memoria cross-host. Pendiente: instalación de T12; Claude directo continúa diferido.
- [ ] Verificación independiente: revisar los artefactos, la instalación local, la activación y el rechazo de ruta errónea sin afirmar despliegue no probado. Pendiente: requiere la instalación y aceptación de T12.
- [x] Verificar el transporte de retorno configurado, sus IDs de mensaje/sesión y el contrato de orquestador/ejecutor antes de cualquier delegación remota. Superada: transporte verificado en vivo por T8 y contrato `submit`/`recover`/`close` documentado en `odd/tasks/pi-herdr-adapter.md`.
- [ ] Aceptar gates humanos de permisos, ausencia de secretos, limpieza de recursos propios y detención sin reintento ante resultados ambiguos. Pendiente: gates de instalación y aceptación humana de T12.


- [x] Actualizar los binarios Herdr a 0.9.3 en los tres equipos.
- [x] Probar manualmente persistencia, reset y cierre de Pi/Claude en Bea, con las limitaciones anteriores.
- [x] Revisar las guías y verificar el alcance local de la mensajería Gentle Pi.
- [x] Alinear servidores/integraciones sin interrumpir sesiones y resolver ejecutables/PATH por host. Superada: el adaptador verificado usa prefijos PATH explícitos en `odd/tasks/pi-herdr-adapter.md`.
- [x] Reconciliar topología autorizada, cuentas, rutas y participación de Bea en arquitectura/config/setup. Descartada por decisión del usuario: Bea fuera de alcance por ahora.
- [x] Comparar RPC de Pi con snapshots Herdr y definir cómo confirmar cada respuesta. Superada: comparación realizada en T4 de `odd/tasks/pi-herdr-adapter.md`.
- [x] Diseñar contrato de conversaciones/mensajes, acciones, correlación, reserva, recuperación y cierre. Superada: contrato por tarea del adaptador documentado y verificado en `odd/tasks/pi-herdr-adapter.md`.
- [x] Implementar adaptador y dispatch/preflight con pruebas deterministas, sin romper v1. Superada: adaptador implementado y verificado en T1–T3 de `odd/tasks/pi-herdr-adapter.md`.
- [x] Documentar instalación, operación, validación y rollback reproducibles por host. Superada: índice y runbooks documentados en `odd/tasks/pi-herdr-adapter.md`.
- [x] Validar el canal implementado en mini y Bea, incluyendo cortes, duplicados, reset fallido y limpieza segura. Descartada por decisión del usuario: Bea fuera de alcance por ahora; el adaptador del mini se verificó en `odd/tasks/pi-herdr-adapter.md`.
- [x] Medir latencia y decidir reutilización caliente entre tareas; no es condición del primer alcance. Descartada por decisión del usuario: no se necesita reutilización caliente porque las llamadas son esporádicas.

## Pi one-shot validation (current scope)

Claude direct invocation is deferred. User authorized SSH-session Node activation and isolated Pi probes; no commits, SSH key installation, mount changes, or existing-session changes.

- [x] Run isolated Pi SSH probes with nvm activated: Node v24.19.0 and Pi 1.0.2 PASS. Ordinary request and explicit bridge request fail `Not logged in`; defaultProvider is claude-bridge, so this is NOT evidence of native Pi provider failure. Scratch request also failed before creation (exact path absent). Fresh Herdr Pi tab w1:tV/pV reached bridge but hit five-hour rate limit (reported reset 06:40 Europe/Madrid), so envelope/missing-project/scratch GUI probes were skipped, not passed. Own tab closed; p1/p2 preserved; t3 was already absent. Route: delegated verifier. Descartada por decisión del usuario: el canal directo de Claude queda diferido; el adaptador Herdr cubre el alcance actual.
- [x] Inspect reverse transport without installing keys; test timeout/disconnect only with bounded owned processes and cleanup evidence. Reverse connectivity remains skipped: Mini has no `~/.ssh/config` or installed Fabric config. Se observó una desconexión deliberada del cliente SSH local durante un turno propio y reconexión por IDs retenidos sin reenvío; no equivale a una falla general de red/servidor ni valida transporte inverso. El timeout de espera tampoco canceló el turno observado. Runner `subprocess.run` no gestiona explícitamente descendientes. Route: delegated verifier.
- [x] Inspect actual v1 execution and forced-key setup. Runner fixed SAFE_PATH excludes nvm and Homebrew; temporary SSH-session nvm activation does not fix its sanitized child environment. Runner/preflight fix remains pending. Existing deterministic suite: 45 tests PASS. Unknown workspace runner check: INVALID_INPUT before activity write. No valid-workspace live runner invocation, key installation, configuration writes, mounts, or commits.

### Repeat validation

- NVM activation in SSH session PASS: Node v24.19.0, Pi 1.0.2; defaultProvider claude-bridge. Bounded one-shot ordinary request failed in 1.47s with `Not logged in`; no auth changes.
- Existing suite repeated: 45 tests PASS (0.620s).
- GUI/Herdr probes NOT repeated: verifier encountered operational guidance from `herdr --skill` requiring HERDR_ENV=1; SSH value unset. This is not an observed technical CLI refusal. No environment spoofing or control mutations attempted. Prior SSH Herdr success remains valid evidence; no fresh quota observation.
- Scratch/envelope/missing-project GUI probes skipped. No new tab or scratch file. Baseline Pi p1 and Claude p2 untouched.
- Owned sleep-group cancellation probe returned EPERM; later PID/group absent. Cause unresolved; no cuenta como PASS de cancelación de grupo. Evidencia posterior distinta sí cubrió la terminación controlada del cliente SSH local durante un turno Herdr propio; no prueba una falla general de red.
- Reverse SSH/Fabric configuration still absent in inspected locations. No setup changes or commits.

### Successful GUI repeat (explicit user-authorized remote owned controls)

- [x] Fresh Pi in own Herdr tab w1:tB/pB, cwd /Users/leo/tmp, loaded default claude-sonnet-5-5 via bridge without /model or config changes. Ordinary nonce replies before/after envelopes matched; no auth/quota/control refusal.
- [x] Envelope resolved MacMiniLeo.local and /Volumes/agent-projects/leo/mac-agent-fabric; actual git tools observed branch main and existing dirty state (16 tracked modifications, 3 untracked paths). Read-only task changed nothing.
- [x] Nonexistent unique project returned BLOCKED without fallback.
- [x] Unique scratch .fabric-pi-probe-c0cc0602-6d30-4c00-ab82-30ca3e971144.txt initially absent, created/read by Pi with FABRIC_NONCE_c0cc0602 plus newline; external hex verified 22 bytes. Initial verifier assertion expected23 incorrectly; corrected local assertion matches captured bytes. Exact file removed, absence spot-checked.
- [x] Own tab closed; absence spot-checked; original t1/t2/t3 preserved. No source/config/key/mount changes or commits.
- Skill appeared in startup registry and behavior matched routing; no captured automatic SKILL.md read/tool event, so automatic file reading is not newly proven.
- These are manual Herdr transport probes, not production correlation/dedup/disconnect recovery or sandbox verification. SSH bridge authentication and runner PATH remain pending.

### Prueba posterior de desconexión local y timeout (evidencia suministrada)

- [x] A/B secuenciales (`completion_seq: 86` / `completion_seq: 88`): el snapshot de B mostró A visible. Los IDs que contienen `20260307` son opacos, no fechas.
- [x] D: se observó `agent_status: working`, `state_change_seq: 89`; se terminó el cliente SSH local PID `2814`, se esperó 255 y se reconectó con los mismos IDs, sin reenvío. El snapshot mostró `agent_status: done`, `completion_seq: 90` y el nonce exacto de D tras 8.1 s. Esto es continuidad observada mediante snapshots tras desconectar el cliente local, no un protocolo de respuesta ni una prueba de falla general de red/servidor.
- [x] T: `--wait --timeout 2000` devolvió `timeout` con exit 1; sin reintento, el snapshot posterior mostró `agent_status: done`, `completion_seq: 92` y el nonce exacto de T 10 s después. El timeout no demuestra cancelación ni correlación estructurada.
- [x] Limpieza: se cerraron los recursos propios `tC`/`pC`; `t1`/`t2`/`t3` y `p1`/`p2` se preservaron, se eliminó el archivo temporal local de captura SSH; `/Users/leo/tmp` no se eliminó y no se observó cambio de auth/cuota.
- [ ] Siguen pendientes fallas generales de red, transporte inverso, correlación/deduplicación y límites de seguridad; no declarar listo para producción. Pendiente: requieren pruebas remotas adicionales fuera de esta tarea documental.

## Consolidation and remaining probes

User authorized documenting all historical tests and continuing isolated probes. No commits, key installation, mount/config changes, production adapter implementation, or unrelated-session control.

- [x] Consolidate historical PASS/FAIL/BLOCKED/SKIP results and corrections in docs/runbooks/agent-fabric/test-evidence.md; link from validation.md and reconcile historical tracker claims. Evidencia posterior de desconexión/timeout incorporada; documentación pasiva, sin RED significativo. Route: delegated writer (multi-file docs).
- [x] Observar IDs secuenciales y desconectar el cliente SSH local mientras continuaba un turno Pi propio; reconectar por IDs retenidos sin reenvío, confirmar en snapshot y limpiar recursos propios. Resultado limitado: no prueba fallas generales de red ni fiabilidad de producción. Route: delegated verifier (remote tests).
- [x] Registrar la comprobación documental final: enlaces Markdown locales y `git diff --check` limpios. Persisten transporte inverso, auth del bridge/runner y sandbox como pendientes; no declarar listo para producción. Route: delegated verifier plus parent synthesis.

## Verificación pendiente de implementación

Runner existente: `python3 -m unittest discover -s automation/agent-fabric/test`. No se ejecutó esa suite en la actualización documental.

Antes de declarar listo el canal: guías y config coherentes; cliente/servidor compatibles; respuesta correlacionada por mensaje; estados ambiguos sin retry ciego; contexto conservado dentro de tarea; reset comprobado o recreación segura; cierre solo de recursos propios; recuperación y rollback probados. La prueba de nonce es evidencia acotada, no cierre de esas condiciones.
