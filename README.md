# Agent Fabric

Agent Fabric coordina tareas de Pi entre Macs registrados sin compartir identidades, credenciales ni sesiones. El canal activo combina SSH entre hosts registrados, un catálogo de proyectos compartido por SMB cuando un *spoke* lo necesita, y Herdr para crear una sesión Pi propia en el host que ejecuta la tarea.

> La referencia autoritativa es la [arquitectura](docs/architecture.md). Este README resume el camino vigente; no documenta ni conserva un runner anterior.

## Camino rápido

1. Consulte el [registro de hosts](config/hosts.json) y trabaje desde un checkout local del repositorio.
2. Para incorporar un Mac, siga la [instalación guiada](docs/setup/agent-guided-setup.md) y ejecute `fabric-setup add-host` desde un host ya registrado.
3. Verifique el canal con `fabric-delegate preflight <destino>`; el destino debe figurar en el registro y, si es un *spoke*, tener disponible el catálogo SMB.
4. Envíe tareas mediante `fabric-delegate`, que invoca `fabric-herdr-task` en el host destino. Recupere el resultado con el mismo UUID y cierre únicamente la tab que creó la tarea.

La incorporación y toda configuración de hosts requieren presencia humana para Remote Login, huellas SSH, login de Pi y el primer acceso SMB. Agent Fabric no copia `HOME`, Keychain, tokens ni configuraciones de runtime.

## Componentes activos

| Componente | Responsabilidad |
| --- | --- |
| `config/hosts.json` | Fuente de verdad versionada: hub, share SMB y datos por host (alias SSH, catálogo, checkout, PATH, cwd GUI y runtimes). |
| `fabric-setup` | Alta reanudable de un Mac: coordina SSH, runtime, montaje, registro, skill, actualización y aceptación. |
| `fabric-delegate` | Selecciona un destino registrado y transporta por SSH `submit`, `recover` y `close` hacia el adaptador remoto. |
| `fabric-herdr-task` | Crea una tab y una sesión Pi propias, persiste un ledger y obtiene el resultado desde el JSONL de esa sesión. |
| `fabric-smb-mount` | Consulta, monta o desmonta exclusivamente el share SMB registrado usando Keychain de macOS. |
| `skills/agent-fabric-remote` | Contrato para recibir o delegar un sobre de tarea de forma acotada y sin reenviar ante ambigüedad. |

## Límites de seguridad

- SSH usa aliases y claves dedicadas por dirección. `StrictHostKeyChecking` permanece activo; la clave reduce reenvíos, pero una conexión SSH no es un sandbox.
- SMB comparte sólo el catálogo aprobado. Las credenciales se introducen en Finder y permanecen en Keychain local.
- Pi, Herdr, sus sesiones y sus credenciales permanecen en el host que los ejecuta.
- Una tarea tiene un UUID. Ante una entrega ambigua se usa `recover` o se repite `submit` con el mismo sobre; no se crea otro UUID para el mismo trabajo.
- No hay coordinación automática de escritores: las tareas que modifican un proyecto requieren coordinación y revisión humanas.

## Documentación

| Documento | Uso |
| --- | --- |
| [Arquitectura](docs/architecture.md) | Topología, contratos y límites del canal activo. |
| [Instalación guiada](docs/setup/agent-guided-setup.md) | Alta reanudable con `fabric-setup`. |
| [Agregar un equipo](docs/setup/add-host.md) | Fases, pausas humanas y diagnóstico de la alta. |
| [Tareas Herdr + Pi](docs/runbooks/agent-fabric/herdr-tasks.md) | Contrato de `fabric-herdr-task` y de `fabric-delegate`. |
| [Validación](docs/runbooks/agent-fabric/validation.md) | Comprobaciones antes de usar el canal. |
| [Reversión](docs/runbooks/agent-fabric/rollback.md) | Alcance seguro para retirar un alta actual. |
| [Canal SSH](docs/runbooks/agent-fabric/ssh-channel.md) | Claves, huellas, aliases y reversión por dirección. |
| [Montaje SMB](docs/runbooks/agent-fabric/smb-mount.md) | Uso y montaje persistente del share registrado. |
| [Skill remota](skills/agent-fabric-remote/SKILL.md) | Sobre, recuperación y reglas del agente. |
| [Evidencia de pruebas](docs/runbooks/agent-fabric/test-evidence.md) | Observaciones históricas y sus límites. |
