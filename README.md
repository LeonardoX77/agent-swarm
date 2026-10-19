# Agent Fabric

Agent Fabric conecta por SSH dos hosts macOS para despachar tareas entre sí. Es infraestructura de transporte y ejecución restringida: **no es un agente ni un modelo, y no selecciona uno automáticamente**. Cada solicitud elige explícitamente `runtime: pi`, `opencode` o `claude`; el host destino decide de forma independiente cuáles permite. El espacio de trabajo se comparte por SMB; la identidad, las credenciales y la ejecución siguen siendo locales al host que corre el CLI.

> **Arquitectura autoritativa:** [docs/architecture.md](docs/architecture.md). Este README es el punto de entrada; ante una diferencia, prevalece la arquitectura.

## Camino rápido

1. Seguí la [instalación guiada por agente](docs/setup/agent-guided-setup.md): es la secuencia canónica de comprobaciones automatizables, pausas humanas y reanudación segura.
2. Leé la [topología y los límites](docs/architecture.md#topología-y-responsabilidades).
3. Instalá y autenticá localmente los runtimes que vayas a usar; no copies `HOME`, Keychain, credenciales ni sesiones. Para el canal Herdr + Pi sólo son obligatorios Pi y gentle-pi (Claude es opcional); el runner v1 necesita además los runtimes que habilites en cada host (OpenCode, Claude Code). Para sumar un equipo nuevo seguí [Agregar un equipo](docs/setup/add-host.md).
4. Configurá SMB, las claves SSH restringidas y los aliases locales siguiendo la [secuencia de instalación](docs/architecture.md#secuencia-de-instalación), con presencia humana para cada cambio de host.
5. Seguí el [runbook de validación](docs/runbooks/agent-fabric/validation.md) antes de operar.
6. Creá y despachá una solicitud JSON con la [guía de operación bidireccional](docs/runbooks/agent-fabric/operation.md). Elegí explícitamente el runtime; el host destino ejecuta el CLI permitido bajo **su propia** cuenta local.

Para retirar únicamente los recursos creados por Fabric, seguí la [guía de reversión controlada](docs/runbooks/agent-fabric/rollback.md).

## Canal entre agentes (Herdr + Pi)

Es el canal verificado de punta a punta en ambas direcciones. Un agente de un Mac se conecta por SSH al otro y ejecuta `fabric-herdr-task`, que abre una Pi propia en Herdr, le envía la tarea una sola vez y lee la respuesta del historial de sesión de Pi.

## Índice de documentación

| Documento | Para qué |
|---|---|
| [Arquitectura](docs/architecture.md) | Topología, límites y entregables (autoritativo) |
| [Agregar un equipo al canal Agent Fabric](docs/setup/add-host.md) | Alta genérica de un Mac como spoke del hub Herdr + Pi |
| [Instalación guiada por agente](docs/setup/agent-guided-setup.md) | Secuencia de instalación con pausas humanas |
| [Setup MacBook](docs/setup/macbook.md) / [Setup Mac mini](docs/setup/mac-mini.md) | Pasos por host |
| [Tareas Herdr + Pi](docs/runbooks/agent-fabric/herdr-tasks.md) | Cómo funciona y cómo se usa el adaptador `fabric-herdr-task` |
| [Canal SSH bidireccional](docs/runbooks/agent-fabric/ssh-channel.md) | Clave dedicada por dirección, verificación de huella, `authorized_keys`, alias y reversión |
| [Montaje SMB](docs/runbooks/agent-fabric/smb-mount.md) | `fabric-smb-mount`: montar, desmontar y montaje permanente |
| [Skill de tareas remotas](skills/agent-fabric-remote/SKILL.md) | Formato del sobre de tarea y reglas para el agente que la recibe |
| [Operación v1](docs/runbooks/agent-fabric/operation.md) | Runner one-shot por clave restringida |
| [Validación](docs/runbooks/agent-fabric/validation.md) | Checklist antes de operar |
| [Reversión](docs/runbooks/agent-fabric/rollback.md) | Retirar recursos creados por Fabric |
| [Evidencia de pruebas](docs/runbooks/agent-fabric/test-evidence.md) | Qué se probó, resultados, métodos de comunicación y límites |
| [Plan del adaptador](odd/tasks/pi-herdr-adapter.md) | Decisiones, tareas y evidencia del trabajo en curso |

## Decisiones de v1

| Tema | Decisión |
|---|---|
| MacBook | Usuario `leo`; raíz local `/Users/leo/projects`; recurso SMB `agent-projects`. |
| Mac mini | Usuario existente `leo`; montaje `/Volumes/agent-projects`. El mismo nombre en ambos hosts no comparte HOME, credenciales ni estado local. |
| Red | LAN y Tailscale con `agent-fabric-macbook` y `agent-fabric-mac-mini`; sin reenvío de puertos del router. |
| Ejecución | SSH bidireccional hacia un runner de comando forzado; la solicitud selecciona `pi`, `opencode` o `claude` y el allowlist local del destino la acepta o rechaza. |
| Privilegios | `sudo` interactivo sólo para configuración en el host local; nunca se envían contraseñas ni se delega `sudo` remoto. |
| Concurrencia | No hay locks. `fabric-activity` es un registro local saneado y sólo observacional. |
| Estado sensible | HOME, Keychain, credenciales, configuración, sesiones, cachés y logs permanecen locales. |
| Skills compartidas | Git y clones locales independientes; nunca SMB. |

## Límites operativos

- La Mac mini autentica SMB contra la MacBook como `leo`; la contraseña se carga interactivamente en Keychain de la Mac mini.
- Cualquiera de los hosts puede iniciar un despacho, pero el agente remoto conserva la autoridad del usuario destino: `leo` en cada host. El nombre coincidente no comparte HOME, credenciales, Keychain, sesiones ni configuración entre hosts.
- El comando SSH forzado elimina el shell SSH genérico y restringe el protocolo al runner. **No es un sandbox para los agentes**: las herramientas permitidas a cada CLI bajo la cuenta destino conservan esa capacidad.
- El runner arma argv desde una tabla cerrada, sin shell ni flags aportados por la solicitud: Pi `pi -p --approve --name fabric-<request_id> -- <prompt>`; OpenCode `opencode run -- <prompt>`; Claude Code `claude -p --permission-prompts none -- <prompt>`. La identidad, configuración, credenciales, sesiones y permisos siguen siendo locales al destino.
- La primera versión no requiere RPC. RPC es una opción futura, no una dependencia ni un reemplazo de `pi -p` en v1.

## Mapa de entregables

La arquitectura define los entregables exactos y su orden de creación en el [mapa de entregables](docs/architecture.md#mapa-de-entregables). v1 ya entrega runtime, configuración, setup y runbooks; este trabajo de repositorio no aplicó ninguna configuración en los hosts.
