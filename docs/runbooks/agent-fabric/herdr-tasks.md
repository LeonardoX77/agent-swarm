# Tareas Pi mediante Herdr (host-local)

`fabric-herdr-task` crea recursos exclusivos de Herdr para una tarea Pi y conserva una evidencia JSONL verificable. El adaptador se ejecuta en el host que controla Herdr; puede invocarse por SSH normal desde el Mac de origen. No despliega nada ni sustituye el transporte v1.

## Cómo funciona

- `lib/herdr_ledger.py` mantiene un ledger privado por tarea. Sus fases son `reserved` → `create_intent` → `created` → `start_intent` → `started` → `submit_intent` → `submitted` → `result` → `cleanup_intent` → `closed`; también existen `unknown` y `recover_intent`. Cada intención se persiste con `fsync` antes del efecto remoto y no hay camino de vuelta hacia `submit`.
- `lib/pi_session_result.py` lee el JSONL propio de la sesión: localiza el mensaje de usuario exacto y sigue `parentId` hasta la hoja de asistente con `stopReason: "stop"`.
- `lib/herdr_task.py` implementa el controlador y `bin/fabric-herdr-task` expone `submit`, `recover` y `close`.
- `submit` reserva en el ledger, crea un archivo de sesión privado con header v3, ejecuta `herdr tab create --cwd <gui_cwd-del-registro> --no-focus` e inicia `herdr agent start <nombre> --kind pi --pane <pane> -- --session <archivo>`. Luego verifica la identidad con `herdr agent get`: Herdr 0.9.3 no aporta `agent_id`, por lo que el pane es el selector.
- El controlador envía `herdr agent prompt <pane> <JSON exacto del sobre>`. `recover` sólo lee el JSONL y nunca reenvía. `close` cierra únicamente la tab propia y exige el error tipado `tab_not_found`.

Ante ambigüedad, el estado es `unknown` y nunca hay reenvío automático. El adaptador ofrece como máximo un intento local, no ejecución distribuida exactamente una vez.

## Invocación entre Macs

Use `automation/agent-fabric/bin/fabric-delegate` desde el Mac de origen: `list` muestra destinos, `self` identifica el host local, `preflight <destino>` sólo comprueba SSH y el catálogo, y `submit <destino>`, `recover <destino> <UUID> [--wait SEGUNDOS]` y `close <destino> <UUID>` realizan la operación remota. Por ejemplo: `cat envelope.json | automation/agent-fabric/bin/fabric-delegate submit mac-mini`. La respuesta JSON remota se conserva sin cambios. Si el preflight de un spoke informa `catalog_missing`, ejecute manualmente `fabric-smb-mount mount` en ese host; el delegado nunca lo monta.

La fuente única es `config/hosts.json`: define alias SSH, catálogo, repositorio, PATH y cwd GUI por host. `fabric-herdr-task --registry RUTA` permite usar otro registro validado (por ejemplo, en pruebas); sin esa opción usa el registro del repositorio. Después invoque `recover` hasta obtener el resultado final y, por último, `close`. `recover` espera y consulta cada 2 segundos durante 120 s de forma predeterminada; use `--wait SEGUNDOS` (0–900) para ajustarlo, o `--wait 0` para una sola lectura. Si uno de los Macs está apagado, este canal simplemente no se usa y se emplean subagentes locales. El procedimiento del canal de retorno está en [Transporte de retorno: Mac mini → MacBook](return-transport.md). Para montar el recurso SMB de proyectos de forma controlada, consulte [Montaje SMB entre equipos](smb-mount.md).

## Uso rápido

En el equipo que controla la GUI de Herdr, envíe el sobre JSON por entrada estándar:

```bash
printf '%s' '{"task_id":"550e8400-e29b-41d4-a716-446655440000","origin_host":"MacBookLeo","project":"leo/mac-agent-fabric","goal":"Revise el cambio.","acceptance":"Devuelva hallazgos.","mode":"executor"}' \
 | automation/agent-fabric/bin/fabric-herdr-task submit --project-root /Users/leo/projects
```

Recupere sin volver a enviar el prompt, o cierre sólo un resultado final verificado:

```bash
automation/agent-fabric/bin/fabric-herdr-task recover 550e8400-e29b-41d4-a716-446655440000
automation/agent-fabric/bin/fabric-herdr-task close 550e8400-e29b-41d4-a716-446655440000
```

## Contrato y límites

| Área | Decisión |
|---|---|
| Identidad | El sobre tiene exactamente `task_id`, `origin_host`, `project`, `goal`, `acceptance` y `mode: executor`; `task_id` es UUID y `project` es una ruta relativa bajo el catálogo. El host se identifica por el prefijo de nodename en el registro; `--project-root` selecciona el catálogo, no el proyecto final. Un host desconocido falla salvo un catálogo explícito, existente y seguro. |
| Ejecución | El binario `herdr` se resuelve de forma explícita (`--herdr`) o con `shutil.which`; cada llamada usa argv cerrado, sin shell, argumentos extra ni entorno inyectado. `--timeout` está limitado a 1–300 segundos. |
| Recursos | Crea un tab sin foco con el cwd GUI validado del registro y un único agente Pi nombrado, con `pi --session <ruta-propia>`. Sólo continúa cuando tab, pane, runtime, nombre y los campos requeridos de `agent_session` coinciden con el ledger; el selector estable es el pane porque el probe no aporta un id de agente separado. |
| Estado | `--state-dir` es privado; sesiones en `sessions/<UUID>/session.jsonl` son 0700/0600. El header Pi v3 con timestamp se crea con exclusión y fsync antes de iniciar Pi; un archivo existente es ambiguo y queda en `unknown`. Nunca se usa el directorio de sesiones del usuario. |
| Reintentos | Un timeout, salida no cero o JSON inválido después de una intención durable queda en `unknown`. No se busca por nombre, no se reenvía el prompt y no hay garantía distribuida de exactly-once. |
| Recuperación | `recover` sólo hace lecturas de identidad y JSONL. Devuelve `pending` hasta encontrar el prompt exacto y un asistente descendiente final con `stopReason: "stop"`, con agente `idle` o `done`. |

El prompt se envía sin `--wait` ni `--timeout`, porque Herdr rechaza `--timeout` sin `--wait`. Las sesiones pueden contener una línea larga con el prompt de sistema: el lector acepta líneas de hasta 1 MiB y archivos de hasta 8 MiB. Un informe `unknown` puede incluir `last_error` para diagnóstico; los rechazos del parser aparecen en `last_error.session_error`, y `recover` lee el JSONL de sesión sin reenviar el prompt.
| Cierre | `close` rechaza agentes activos, identidades ajenas o resultados incompletos. Persiste `cleanup_intent` antes de un solo cierre de tab y sólo marca `closed` después de que una lectura posterior devuelva el error tipado `tab_not_found`; cualquier otro resultado queda `unknown` y conserva el historial y la sesión. |

Herdr puede devolver errores tipados tanto por stdout como por stderr. Tras cerrar, `recover` y `close` devuelven el resultado almacenado, leído de la sesión retenida.

La respuesta final incluye `task_id`, `status`, `resubmit: false` y, cuando existe, `resulttext`, `userentry` y `assistantentry`. Un informe válido (incluso `pending`, `unknown` o `timed_out`) sale con código 0; una entrada inválida o fallo sale con código 2.

## Errores y cortes

Para el agente llamador se recomiendan las opciones SSH `-o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=4`. Una salida SSH 255 significa que la conexión falló y el estado de la tarea es desconocido desde el llamador. La alternativa segura es ejecutar más tarde `recover <task_id>`, o repetir `submit` con el sobre **IDÉNTICO**: es idempotente y nunca vuelve a enviar el prompt. Nunca cree un `task_id` nuevo para el mismo trabajo después de un fallo ambiguo. `recover` espera 120 s por defecto; ajuste ese límite con `--wait`.

## Verificación local

```bash
python3 -m unittest automation/agent-fabric/test/test_herdr_task.py
python3 -m unittest discover -s automation/agent-fabric/test
```

Las pruebas usan fixtures de Herdr. No prueban una GUI viva ni constituyen despliegue.
