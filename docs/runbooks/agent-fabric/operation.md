# Operación bidireccional de Agent Fabric v1

Usá este runbook para despachar una tarea acotada a Pi + Gentle Pi, OpenCode o Claude Code **local** del otro host. Agent Fabric es infraestructura de transporte y ejecución restringida: no es un agente/modelo y no selecciona runtime automáticamente. La solicitud viaja por stdin; no pone prompts, rutas ni JSON en argumentos SSH.

## Camino rápido

1. Confirmá con la persona responsable que la tarea y el workspace pueden cambiarse; el dispatcher no coordina escritores.
2. Creá y revisá una solicitud JSON con un prompt explícitamente acotado.
3. Despachala al alias del otro host y leé sólo el resultado JSON saneado.

> **Gate humano:** cada solicitud declara `runtime: pi`, `opencode` o `claude`; el destino lo permite o rechaza con su `allowed_runtimes` local. No inicies un despacho sin revisar runtime, prompt, workspace y riesgo de concurrencia. El runner no acepta flags ni shell controlados por la solicitud.

## Crear una solicitud

Este ejemplo crea un archivo local; no configura hosts ni envía nada. Cambiá el UUID antes de cada despacho y conservá `initiator` según el host que inicia.

```sh
mkdir -p "$HOME/.local/share/agent-fabric/requests"
cp automation/agent-fabric/examples/task-request.example.json \
  "$HOME/.local/share/agent-fabric/requests/macbook-to-mini.json"
```

La solicitud debe contener exactamente `version`, `request_id`, `workspace`, `relative_path`, `prompt`, `runtime`, `initiator` y `timeout_seconds`. `runtime` es exactamente `pi`, `opencode` o `claude`; el host destino lo valida contra su propio `allowed_runtimes`. No agregues claves, rutas absolutas, flags, credenciales ni contenido de Keychain. El ejemplo es inocuo: pide un informe de sólo lectura.

## Despacho en ambos sentidos

### MacBook → Mac mini

En la MacBook, como `leo`, revisá que el archivo tenga `"initiator": "macbook"` y un `runtime` permitido por la Mac mini. El siguiente comando es un **despacho activo**: puede ejecutar la tarea remota.

```sh
python3 automation/agent-fabric/bin/fabric-dispatch \
  --config config/macbook/host.json \
  --target mac-mini \
  < "$HOME/.local/share/agent-fabric/requests/macbook-to-mini.json"
```

El dispatcher usa el alias local `agent-fabric-mac-mini`, que se autentica como `jarvis` y llega sólo al runner forzado.

### Mac mini → MacBook

En la Mac mini, como `jarvis`, creá la solicitud local con un UUID nuevo y un runtime permitido por la MacBook. Este comando sólo escribe el archivo de solicitud; revisalo antes de despacharlo.

```sh
cat > "$HOME/.local/share/agent-fabric/requests/mac-mini-to-macbook.json" <<'JSON'
{"version":1,"request_id":"b3b0a9d3-c3e5-4d5f-8b90-8fa6152e0e89","workspace":"mac-agent-fabric","relative_path":".","prompt":"Read only: report the current working directory and the repository name. Do not modify files, configuration, or network state.","runtime":"pi","initiator":"mac-mini","timeout_seconds":120}
JSON
```

Tras la revisión humana, este es un **despacho activo**:

```sh
python3 automation/agent-fabric/bin/fabric-dispatch \
  --config config/mac-mini/host.json \
  --target macbook \
  < "$HOME/.local/share/agent-fabric/requests/mac-mini-to-macbook.json"
```

El dispatcher usa `agent-fabric-macbook`, se autentica como `leo` y llega sólo al runner forzado.

## Mapeo de workspaces

El identificador lógico es el mismo en ambos hosts, pero el runner resuelve una ruta local. Nunca envíes una ruta del otro host.

| `workspace` | MacBook (`leo`) | Mac mini (`jarvis`) |
|---|---|---|
| `mac-agent-fabric` | `/Users/leo/projects/leo/mac-agent-fabric` | `/Volumes/agent-projects/leo/mac-agent-fabric` |

`relative_path` es `.` para la raíz o una ruta relativa sin `..`, symlinks ni prefijo `/`. El runner rechaza rutas ambiguas, escapes, workspaces ausentes, runtimes desconocidos y runtimes no autorizados antes de iniciar un CLI.

## Runtimes y ejemplos seguros

El destino construye el comando desde una tabla cerrada; la solicitud sólo elige `runtime` y aporta el prompt como argumento, sin shell ni flags controlados por quien solicita.

| `runtime` | Comando exacto en el destino | Ejemplo de prompt inocuo |
|---|---|---|
| `pi` | `pi -p --approve --name fabric-<request_id> -- <prompt>` | `Read only: report the repository name. Do not modify files.` |
| `opencode` | `opencode run -- <prompt>` | `Read only: list top-level files. Do not modify files.` |
| `claude` | `claude -p --permission-prompts none -- <prompt>` | `Read only: report the current working directory. Do not modify files.` |

Pi conserva la semántica actual de `--approve`; OpenCode no se inicia con `--auto`. En Claude Code, `--permission-prompts none` falla cerrado si una operación necesitaría un prompt sin respuesta; las políticas locales del host siguen gobernando. La identidad, configuración, credenciales, sesiones y permisos de los tres CLI permanecen locales al destino.

## Resultado acotado

El comando imprime un único JSON. Tratá `status` como el resultado operativo:

| Campo | Lectura |
|---|---|
| `status` | `succeeded`, `failed` o `cancelled`. |
| `diagnostic_code` | Motivo saneado para investigar localmente; no contiene secretos ni stderr crudo. |
| `exit_code` | Código del proceso cuando está disponible. |
| `output` | Salida truncada y saneada sólo cuando la tarea tuvo éxito. |
| `warnings` | Por ejemplo, `ACTIVITY_RECORD_FAILED`; la observabilidad falló y requiere revisión. |

No reintentes automáticamente. Ante `failed`, guardá el JSON saneado, verificá el preflight local y corregí la causa en el host correspondiente antes de una nueva autorización humana.

## Actividad y concurrencia

`fabric-activity` registra localmente inicio y resultado terminal saneados. Sirve para correlacionar `request_id`, host, workspace lógico, duración y diagnóstico; no revela prompts completos, credenciales ni contenido del repositorio.

**No hay locks.** El registro no autoriza, bloquea, serializa ni reserva un workspace. Dos despachos pueden escribir el mismo árbol por SMB al mismo tiempo. Coordiná la ventana de trabajo y revisá el árbol compartido con una persona antes de iniciar tareas que escriban.

## Fallas

| Señal | Acción segura |
|---|---|
| `INVALID_INPUT`, `TIMEOUT_EXCEEDED` o path rechazado | Corregí el JSON local; no intentes transportar rutas absolutas ni ampliar el timeout sin revisar la política local. |
| Alias, red o clave fallan | Ejecutá la lista de validación en el host iniciador. No abras un shell SSH ni cambies restricciones para diagnosticar. |
| `WORKSPACE_UNAVAILABLE` | Verificá el montaje SMB y el mapeo local; no crees directorios desde el runner. |
| El runtime elegido no está instalado, configurado o autenticado localmente | Detené el despacho. La persona resuelve el estado local del CLI en el host destino; nunca se envían credenciales ni se automatiza login. |
| Runtime desconocido o fuera de `allowed_runtimes` | Corregí sólo la selección de runtime o pedí que la persona ajuste el allowlist local del destino; no intentes enviar flags ni abrir un shell. |
| `ACTIVITY_RECORD_FAILED` | Conservá el resultado, inspeccioná el registro local y decidí con una persona si corresponde repetir. |

Para recuperación o eliminación controlada, seguí [rollback.md](rollback.md). Para preflight y pruebas de ida y vuelta, seguí [validation.md](validation.md).
