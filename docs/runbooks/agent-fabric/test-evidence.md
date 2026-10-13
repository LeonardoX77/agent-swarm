# Evidencia histórica de pruebas de Agent Fabric

> **Estado:** historial documental; no es un protocolo de producción ni una aceptación de despliegue. Resume observaciones previas y el estado de diseño de Herdr/Pi. La validación de v1 vigente está en [validation.md](validation.md).

## Cómo leer este informe

- **PASS** confirma sólo la observación concreta descrita, en el entorno y momento indicados.
- **FAIL** es un resultado observado que no alcanzó el comportamiento buscado.
- **BLOCKED** indica que un control, autenticación o política impidió continuar; no diagnostica por sí solo la causa única.
- **SKIP** es una prueba que deliberadamente no se ejecutó; no es un resultado favorable.
- **INCONCLUSIVE** recoge evidencia insuficiente o ambigua.
- Una **observación** no es una garantía, una configuración actual ni una capacidad de producción. La columna de fuente separa el contenido del tracker de la evidencia aportada en conversación; esta última no aporta fecha, duración ni artefacto adicional salvo donde se dice expresamente.

Los nombres de tabs, panes, PIDs, nonces y rutas temporales son identificadores históricos. No son destinos que se puedan reutilizar.

## Resumen para revisión

| Área | Estado histórico | Lo que sí se observó | Lo que no queda garantizado |
|---|---|---|---|
| Herdr en Bea | PASS con límites | continuidad del nonce, reset y limpieza de recursos propios | correlación por turno, recuperación, deduplicación y aislamiento de memoria externa |
| Pi en Mac mini por Herdr | PASS acotado | sesión GUI propia resolvió un envelope y trabajó en el mount esperado | autenticación del runner SSH, sandbox y fiabilidad de transporte |
| Claude en Mac mini | INCONCLUSIVE / BLOCKED | carga de skill y límites de lectura en experiencias separadas | ejecución SSH autenticada y una política de permisos robusta |
| v1 runner local | PASS histórico | 45 pruebas deterministas y rechazo de workspace desconocido | despacho válido extremo a extremo y manejo seguro de descendientes |
| Red/SMB/SSH | PASS limitado / INCONCLUSIVE | desconexión del cliente SSH local y espera con timeout preservaron un turno propio en una prueba | montaje aceptado, fallas generales de red, transporte inverso y operación bidireccional |

## Fuentes y alcance

| Etiqueta | Procedencia | Uso en este informe |
|---|---|---|
| **Tracker** | [`odd/tasks/herdr-agent-sessions.md`](../../../odd/tasks/herdr-agent-sessions.md) | Estado de diseño, límites y resultados anotados allí. |
| **Conversación suministrada** | Evidencia histórica proporcionada para esta consolidación | Aporta resultados posteriores o precisión adicional; se etiqueta así, sin convertirla en garantía. |
| **Documentación vigente** | [arquitectura](../../architecture.md), [operación](operation.md) y [validación](validation.md) | Define v1 actual; no prueba que un host esté configurado. |

No hubo comprobación de red durante esta documentación. Las instantáneas descritas no son un protocolo de producción.

## Línea de evidencia

### Herdr, binarios y servidores

| Evidencia | Estado | Fuente | Lectura acotada |
|---|---|---|---|
| Actualización de binarios Herdr a 0.9.3 en tres equipos. | PASS | Tracker | Actualizar un binario no reinició por sí solo los servidores existentes. |
| MacBook: binario 0.9.3 y servidor observado 0.7.5; Mac mini: binario 0.9.3 y servidor observado 0.8.0, con incompatibilidad declarada. | INCONCLUSIVE | Tracker | Es una tabla **histórica**, no un inventario ni estado actual. |
| Servidores de Mac mini observados después en 0.9.3, protocolo 22, compatibles con MacBook. | PASS | Conversación suministrada | Confirma esa observación posterior; no demuestra una malla, reinicios controlados ni compatibilidad futura. |
| SSH anterior a Bea desde MacBook. | PASS acotado | Tracker | Sólo se probó acceso saliente; no demuestra conectividad bidireccional. |

### Bea: continuidad, reset y limpieza

Experimento aislado en `/Users/beatrizdelcampo/tmp`, sin instalar software, reiniciar servidores ni intervenir sesiones existentes. Pi usó `pi --no-tools --no-context-files`; Claude usó `claude --restricted`.

| Caso | Pi | Claude | Estado y límites |
|---|---|---|---|
| Crear tab/agente y pedir ACK de nonce | `w1:t6` / `w1:p6` respondió | `w1:t7` / `w1:p7` respondió | PASS histórico; los IDs no son reutilizables. |
| Segundo mensaje pidió el nonce sin repetirlo | Recordó el valor exacto | Recordó el valor exacto | PASS de continuidad dentro de esa conversación. |
| Reset nativo | `/new` creó una ruta de sesión nueva y mostró `New session started` | `/clear` vació el historial visual y cambió título/revisión; no expuso ID | PASS del efecto observado, no de semántica interna equivalente entre runtimes. |
| Pedir el nonce tras reset sin revelarlo | `UNKNOWN` | `UNKNOWN` | PASS de olvido del dato en el experimento. |
| Terminar recursos propios | Ctrl+D y cierre de tab | Ctrl+D y cierre de tab | PASS; después sólo se observaron tabs/agentes originales `w1:t1` y `w1:t2`. |
| Resultado de los resets | `agent_prompt_stalled` pese al efecto anterior | `agent_prompt_stalled` pese al efecto anterior | FAIL para completar el prompt/confirmación; no se reenvió el mensaje. Herdr 0.9.3 observaba actividad en cinco segundos y no correlacionaba turnos. |

**No garantizado:** `agent read` entrega snapshots de terminal, no respuestas estructuradas. No se probó correlación de resultado por mensaje, deduplicación, concurrencia, cortes, extracción estructurada ni reversión de archivos/procesos causados antes de un reset. El estado `idle` no equivale al final de tarea.

### Mensajería Gentle Pi

| Evidencia | Estado | Fuente | Límite |
|---|---|---|---|
| En el mini se encontró una sesión Pi viva y socket bajo `/private/tmp/gentle-pi-501/.../*.sock`; el transporte inspeccionado enumera sockets del perfil local y usa `node:net`/Unix sockets. | PASS | Tracker | Confirma alcance local del perfil observado. |
| `orchestrator_list` y `orchestrator_send_message` comunican entre hosts de forma nativa. | FAIL | Tracker | No se encontró transporte cross-host directo. Una aceptación sólo implica encolado, no lectura. |
| Usar Herdr, colas o sockets manipulados como ping de sustitución. | SKIP | Tracker | No se fingió un transporte inexistente. Un puente SSH/RPC sería trabajo distinto. |

### Skill, bootstrap y hostname

| Evidencia | Estado | Fuente | Lectura acotada |
|---|---|---|---|
| Artefactos fuente de la skill y bloque de bootstrap creados en el repositorio; comprobaciones estructurales locales. | PASS | Tracker | No implica instalación, descubrimiento global ni activación automática. |
| Copia local de la skill a rutas de Pi y Claude de la Mac mini y bootstrap en `AGENTS.md`/`CLAUDE.md`; no SMB. | PASS histórico | Tracker | Fue una instalación de host, no una prueba de instalación reproducible actual ni de MacBook. |
| Pi en sesión propia cargó la skill, usó `/Volumes/agent-projects`, bloqueó una ruta inexistente y respondió `OK` sin envelope. | PASS histórico | Tracker | No se capturó lectura específica de `SKILL.md`; no se garantiza carga automática por archivo. |
| Claude inicial en modo `manual` propuso `/Users/leo/projects/...`, esperó aprobación y se canceló. | INCONCLUSIVE | Tracker | No hubo resultado de ruta ni pruebas posteriores B/C en ese intento. |
| Claude posterior con `dontAsk`, settings de sólo lectura y `--add-dir`: resolvió `hostname` a `/Volumes/agent-projects` y leyó rama desde `.git/HEAD`. | PASS histórico | Tracker | Es una observación de la forma concreta de invocación y confianza, no una política general. |
| Al ordenar ignorar la skill, `Read` y órdenes `Bash` directas sobre el mount amplio `/Volumes/Macintosh HD-1` fueron denegadas. | PASS histórico | Tracker y conversación suministrada | Denegación observada a nivel de sistema/configuración; no prueba un sandbox completo ni hace seguro un mount amplio. |
| Reglas de permiso para `git status`. | FAIL / frágil | Tracker | El modelo eligió variantes (`--porcelain`, compuestos) que requieren reglas exactas; el enfoque no escala. |
| Bootstrap/skill instala o activa un canal de retorno. | SKIP | Tracker | Sigue pendiente transporte con IDs de mensaje/sesión y su contrato. |

### Pi y Claude: GUI frente a SSH

| Caso | Estado | Fuente | Evidencia y límite |
|---|---|---|---|
| Sesión SSH con nvm activado | PASS | Tracker | Node v24.19.0 y Pi 1.0.2 presentes; la activación temporal no corrige el entorno saneado del runner. |
| Pi one-shot SSH ordinario y con bridge explícito | BLOCKED | Tracker y conversación suministrada | `defaultProvider` fue `claude-bridge`; ambos devolvieron `Not logged in`. La ejecución de un disparo falló en 1.47 s. Esto no prueba falla del proveedor Pi nativo. |
| Claude directo por SSH 2.1.295 | BLOCKED | Conversación suministrada | `Not logged in`, y `security` reportó Keychain con interacción de usuario no permitida. No se atribuye una causa única definitiva. |
| Reinicio autorizado de Claude en el mini | PASS acotado | Conversación suministrada | Reinició su sesión existente `p2`; versión observada 2.1.289 → 2.1.292. No prueba continuidad semántica, autenticación SSH ni control de sesiones ajenas. |
| Pi GUI Herdr propia `w1:tB/pB`, cwd `/Users/leo/tmp`, bridge Claude Sonnet 5.5 por defecto | PASS | Tracker y conversación suministrada | Respuestas de nonce ordinarias y con envelope; no se cambió `/model` ni configuración. La continuidad requerida de Claude queda diferida: usar el Claude predeterminado de forma transparente o `/model` sólo si hiciera falta. |
| Cuota GUI anterior con reset 06:40 Europe/Madrid | HISTÓRICO | Conversación suministrada | Es una observación pasada, no una promesa de disponibilidad futura. |
| HERDR_ENV en intento posterior | SKIP operacional | Tracker | `herdr --skill` dio guía operativa y el valor SSH estaba ausente; no fue una negativa técnica observada. No se alteró el entorno. |

### Envelope, workspace, git y scratch de Pi GUI

| Caso | Estado | Fuente | Evidencia y límite |
|---|---|---|---|
| Envelope de proyecto | PASS | Tracker | Resolvió `MacMiniLeo.local` y `/Volumes/agent-projects/leo/mac-agent-fabric`. |
| Estado Git observado | PASS observacional | Tracker | Rama `main`, 16 modificaciones tracked y 3 rutas untracked; la tarea de sólo lectura no cambió nada. No es una aserción de árbol limpio. |
| Proyecto inexistente único | BLOCKED | Tracker | Se devolvió `BLOCKED` sin fallback. |
| Scratch propio ausente, escritura/lectura y limpieza | PASS | Tracker y conversación suministrada | `.fabric-pi-probe-c0cc0602-6d30-4c00-ab82-30ca3e971144.txt` contenía exactamente `FABRIC_NONCE_c0cc0602\n`; verificación hexadecimal externa: 22 bytes. La expectativa inicial de 23 bytes fue errónea y se corrigió. Se eliminó el archivo y se comprobó su ausencia. |
| Limpieza de sesión propia | PASS | Tracker | Se cerró la tab propia; se preservaron `t1`/`t2`/`t3` existentes (con `t3` ya ausente en una observación anterior). |

### SSH, runner, SMB y cancelación

| Caso | Estado | Fuente | Evidencia y límite |
|---|---|---|---|
| Suite determinista existente | PASS | Tracker | 45 pruebas pasaron; repetición registrada en 0.620 s. No invoca agentes reales, SSH ni configura hosts. |
| Guía con intervención humana y artefactos de skill | PASS estructural histórico | Tracker | Se comprobaron 23 enlaces locales y `git diff --check`; no es una instalación, activación ni despliegue en host. |
| Workspace desconocido en runner | PASS | Tracker | `INVALID_INPUT` antes de escribir actividad. No hubo invocación válida de runner contra workspace real. |
| PATH del runner | FAIL de preparación | Tracker | `SAFE_PATH` fijo excluye nvm y Homebrew; la activación nvm de una sesión SSH no llega al hijo saneado. Sigue pendiente corrección/preflight. |
| `auth.json` de Pi garantiza autenticación del bridge SSH | INCONCLUSIVE / no afirmar | Tracker y conversación suministrada | Que exista `auth.json` para Pi no demuestra que autentique el bridge ni que el runner SSH pueda usarlo; la autenticación depende del proveedor. La autenticación del bridge sigue pendiente. |
| SMB limitado al workspace | INCONCLUSIVE | Documentación vigente y tracker | La arquitectura exige publicar sólo `/Users/leo/projects`, pero no hubo comprobación de red/mount en esta consolidación. Un mount amplio expone más de lo previsto y no debe aceptarse como equivalente. |
| Transporte inverso | SKIP | Tracker | No había `~/.ssh/config` ni configuración Fabric en las ubicaciones inspeccionadas del mini; no se instalaron claves. |
| Cancelación de primer grupo propio | PASS | Tracker | SIGTERM y comprobación posterior indicaron grupo ausente. No prueba desconexión SSH real. |
| Segundo probe de grupo propio | INCONCLUSIVE | Tracker | Devolvió `EPERM`; más tarde PID/grupo estaban ausentes. Causa no resuelta, no cuenta como PASS de cancelación. |
| Desconexión del cliente SSH local durante turno propio | PASS limitado | Conversación suministrada | En `D`, se observó actividad (`agent_status: working`, `state_change_seq: 89`); se terminó el **cliente SSH local** PID `2814`, se esperó 255 y se reconectó con los mismos IDs, sin reenviar. El snapshot posterior mostró `agent_status: done`, `completion_seq: 90` y el nonce exacto de D tras dormir 8.1 s. Esto no prueba una falla general de red, del servidor ni del protocolo de Fabric. |
| Espera Herdr con timeout corto | PASS limitado | Conversación suministrada | `--wait --timeout 2000` devolvió `timeout`, exit 1; sin reintento, un snapshot posterior mostró `agent_status: done`, `completion_seq: 92` y el nonce exacto de T 10 s después. El timeout del cliente no demuestra que se cancelara el trabajo ni aporta correlación estructurada por turno. |
| Secuencia y continuidad en snapshots | PASS limitado | Conversación suministrada | A/B secuenciales (`completion_seq: 86` / `completion_seq: 88`) mostraron A visible en el snapshot de B. Los identificadores que contienen `20260307`, y cualquier otro ID de la prueba, son opacos; no se interpretan como fechas. Los snapshots no son un protocolo de mensajes ni una garantía de correlación. |
| Limpieza de la prueba de desconexión/timeout | PASS | Conversación suministrada | Se cerraron sólo `tC`/`pC`; se preservaron `t1`/`t2`/`t3` y `p1`/`p2`; se eliminó el archivo temporal local de captura SSH. `/Users/leo/tmp` fue el directorio de trabajo y no se eliminó. No hubo cambio de autenticación ni cuota observado. |
| Desconexión SSH real mientras sigue turno propio | PASS limitado | Conversación suministrada | La prueba anterior cubre una desconexión deliberada del cliente SSH local y una reconexión por IDs retenidos, no una falla de red general. `subprocess.run` del runner sigue sin gestionar explícitamente descendientes. |

## Métodos de comunicación probados

| Método | Cómo funciona | Resultado |
|---|---|---|
| Runner v1 | Clave SSH restringida → `fabric-runner` → `pi -p` one-shot. | No se probó extremo a extremo porque no se instaló una clave restringida. Una ejecución SSH no interactiva de `pi -p --no-tools --no-session "reply OK"` devolvió `Not logged in` con `claude-bridge` como proveedor predeterminado. Según lo informado por el usuario, una sesión SSH interactiva (`aiconnect macmini`) inicia `pi`, pero abrir la UI no prueba por sí solo que el modelo responda; además, `pi -p` sin prompt espera entrada. No se repitió la prueba. Se descartó como objetivo el login de Claude por SSH directo. |
| Herdr y lectura de pantalla | `herdr agent prompt` seguido de `herdr agent read`. | PASS limitado: funciona, pero los snapshots mezclan respuestas antiguas y nuevas y no prueban qué turno terminó. |
| Herdr y JSONL de sesión de Pi | Adaptador `fabric-herdr-task`: envía por Herdr y lee el JSONL de la sesión propia. | PASS extremo a extremo; la evidencia de la ejecución en vivo se resume a continuación. |
| Claude directo en Herdr con `dontAsk` | Claude se ejecuta en Herdr con el modo de permisos indicado. | Parcial; el usuario lo difirió. |
| Gentle Pi `orchestrator_send_message` | Sockets Unix del perfil local. | No es cross-host: sólo funciona localmente. |
| Modo RPC de Pi | `pi --mode rpc`, JSONL por stdin/stdout. | Sólo estudiado; queda pendiente una prueba solicitada por el usuario. |

## Historial E2E en vivo del adaptador

| Hallazgo o ejecución | Resultado y corrección |
|---|---|
| Nombre del agente Herdr | En vivo se detectó el límite de 1–32 caracteres `[a-z0-9_-]`, con letra inicial. El nombre pasó a ser `p` más los primeros 31 caracteres hexadecimales del UUID de tarea. |
| Sobre válido | El controlador exigía erróneamente un séptimo campo `executor` y `mode: host-local`, por lo que rechazaba todo sobre real de seis campos con `INVALID_ENVELOPE`. Ahora acepta exactamente `task_id`, `origin_host`, `project`, `goal`, `acceptance` y `mode: executor`; `orchestrator` se rechaza como `UNSUPPORTED_MODE`. |
| Envío de prompt | `herdr agent prompt ... --timeout` sin `--wait` fallaba localmente con rc 2 (`--timeout requires --wait`) y no enviaba nada. El prompt se envía sin ambos flags. |
| Límites del JSONL | Pi 1.0.2 guarda el prompt de sistema en una línea `role: system` de aproximadamente 99 KB, superior al límite anterior de 64 KiB. Los límites son ahora 1 MiB por línea y 8 MiB por archivo. |
| Errores tipados de Herdr | Con salida no cero, pueden llegar por stdout o stderr; ahora se leen ambos. |
| Resultado tras cierre | `recover` y `close` después de cerrar devolvían sólo la fase; ahora devuelven el resultado almacenado. |
| Ejecución final (tarea `57c5cca9`) | PASS: un `submit` y su repetición idempotente crearon una sola tab; Pi respondió el nonce exacto; `recover` devolvió `done` desde el JSONL de sesión con IDs coincidentes de entradas de usuario/asistente; `close` devolvió `closed` con el error tipado crudo `tab_not_found`; `recover` y `close` sobre la tarea cerrada devolvieron el resultado almacenado; se restauró la línea base de tabs. Pasaron 71 pruebas deterministas. La herramienta de revisión nativa no estaba disponible (faltaba el binario local del paquete); se usaron agentes verificadores independientes. |

## Pendientes antes de cualquier afirmación de producción

1. Diseñar y probar contrato de mensajes: identidad, correlación de respuesta, deduplicación, reserva por tarea, recuperación y cierre.
2. Probar fallas generales de red/servidor y recuperación sin reenvío ciego; la evidencia actual cubre sólo la terminación controlada del cliente SSH local.
3. Resolver PATH efectivo del runner y autenticar cada runtime localmente; no inferir bridge SSH desde `auth.json`.
4. Verificar mount SMB limitado, aliases/huellas y ambos sentidos con los gates humanos de [validation.md](validation.md).
5. Medir y decidir reutilización caliente; reset/reutilización no están aceptados sólo por snapshots.
6. Mantener Claude directo diferido; para Pi/Herdr, usar el Claude predeterminado de forma transparente y sólo elegir `/model` si la evidencia futura lo requiere.

## Relación con v1

La v1 documentada sigue siendo one-shot, con SSH restringido y selección explícita de runtime. Esta evidencia no implementa Herdr, no configura hosts, no instala claves, no monta SMB, no cambia credenciales y no autoriza despliegue. Para el checklist operativo y los gates humanos, consultá [validation.md](validation.md); para el contrato y límites de v1, [docs/architecture.md](../../architecture.md).
