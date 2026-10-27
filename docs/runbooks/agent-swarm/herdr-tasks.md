# Tareas Pi mediante Herdr

`swarm-herdr-task` ejecuta una tarea Pi en el host que controla Herdr. Crea recursos exclusivos por UUID, guarda un ledger durable y obtiene la respuesta desde el JSONL de la sesión propia. `swarm-delegate` permite invocarlo desde otro Mac registrado por SSH.

## Ciclo de vida

1. `submit` recibe por stdin un sobre y reserva `task_id` en el ledger.
2. Crea una sesión privada con header Pi v3, una tab Herdr sin foco y un agente Pi con `--session` apuntando a esa sesión.
3. Persiste cada intención antes del efecto remoto y verifica tab, pane, runtime, nombre y sesión antes de enviar el sobre exacto.
4. `recover` sólo lee el JSONL propio: localiza el mensaje de usuario y sigue su cadena hasta una respuesta de asistente final con `stopReason: "stop"`.
5. `close` cierra únicamente la tab propia después de un resultado verificable. La ausencia tipada de esa tab confirma el cierre.

Las fases del ledger son `reserved`, `create_intent`, `created`, `start_intent`, `started`, `submit_intent`, `submitted`, `result`, `cleanup_intent` y `closed`; `unknown` y `recover_intent` representan recuperación. No hay camino automático de vuelta hacia `submit`.

## Delegación entre Macs

La fuente de verdad es `config/hosts.json`. Define alias SSH, catálogo, checkout, PATH y cwd GUI por host. Desde el origen:

```sh
automation/agent-swarm/bin/swarm-delegate list
automation/agent-swarm/bin/swarm-delegate self
automation/agent-swarm/bin/swarm-delegate preflight <destino>
automation/agent-swarm/bin/swarm-delegate submit <destino> < envelope.json
automation/agent-swarm/bin/swarm-delegate recover <destino> <UUID> [--wait SEGUNDOS]
automation/agent-swarm/bin/swarm-delegate close <destino> <UUID>
```

`<destino>` debe ser un nombre de `list`. `preflight` sólo comprueba SSH y el catálogo; si un spoke informa `catalog_missing`, monte el share siguiendo [Montaje SMB](smb-mount.md) antes de enviar la tarea. La respuesta remota se conserva sin cambios.

Una salida SSH 255 deja el estado desconocido desde el origen. Recupere más tarde o repita `submit` con el **mismo** sobre; nunca cree otro UUID para el mismo trabajo. Si un Mac está apagado, el canal no se usa y se emplean alternativas locales.

## Sobre y uso rápido

El sobre contiene exactamente `task_id`, `origin_host`, `project`, `goal`, `acceptance` y `mode: executor`. `task_id` es UUID; `project` es relativo al catálogo. Los marcadores siguientes deben sustituirse con valores del registro:

```sh
printf '%s' '{"task_id":"<UUID>","origin_host":"<host-de-origen>","project":"<proyecto-relativo>","goal":"Revise el cambio.","acceptance":"Devuelva hallazgos.","mode":"executor"}' \
 | automation/agent-swarm/bin/swarm-herdr-task submit --project-root <raíz-del-catálogo>

automation/agent-swarm/bin/swarm-herdr-task recover <UUID>
automation/agent-swarm/bin/swarm-herdr-task close <UUID>
```

`recover` espera y consulta cada dos segundos durante 120 segundos de forma predeterminada. `--wait` admite 0–900; `--wait 0` hace una sola lectura. `submit` sólo acepta stdin y limita su entrada; `swarm-herdr-task --registry RUTA` permite una fuente de registro validada para pruebas.

## Límites de seguridad y recuperación

| Área | Contrato |
| --- | --- |
| Identidad | Un host desconocido falla salvo un catálogo explícito, existente y seguro. |
| Ejecución | Herdr se resuelve explícitamente o mediante `PATH`; cada llamada usa argv cerrado, sin shell ni entorno inyectado. |
| Estado | Ledger, sesiones y directorios son privados; una sesión existente o un efecto ambiguo deja `unknown`. |
| Reintentos | No hay reenvío automático ni garantía distribuida de exactamente una vez. |
| Cierre | Se rechazan agentes activos, identidades ajenas y resultados incompletos. |

Un informe válido, incluso `pending`, `unknown` o `timed_out`, sale con código 0. Las entradas inválidas o fallos salen con código 2. La respuesta final incluye `task_id`, `status`, `resubmit: false` y, cuando existe, `resulttext`, `userentry` y `assistantentry`.

## Verificación local

```sh
python3 -m unittest automation/agent-swarm/test/test_herdr_task.py
python3 -m unittest discover -s automation/agent-swarm/test
```

Las pruebas usan fixtures de Herdr. No prueban una GUI viva ni constituyen un despliegue.
