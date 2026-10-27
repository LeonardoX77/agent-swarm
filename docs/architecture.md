# Arquitectura de Agent Swarm

Agent Swarm delega una tarea Pi entre Macs registrados. El origen transporta un sobre por SSH hacia el destino; allí `swarm-herdr-task` crea una tab y una sesión Pi propias en Herdr, y obtiene el resultado desde el JSONL de esa sesión. Es coordinación de transporte y ciclo de vida, no un modelo ni un sandbox.

## Resultado y alcance

El canal vigente permite que un host registrado solicite una tarea en otro host registrado mediante `swarm-delegate`. Cada tarea usa un UUID, un proyecto relativo al catálogo del destino y un sobre con objetivo y criterios de aceptación. El destino ejecuta Pi mediante Herdr bajo su propia cuenta local.

Quedan fuera del contrato: copiar credenciales, automatizar logins, acceso SSH sin validar huella, configuración remota sin presencia humana, garantía distribuida de exactamente una vez y arbitraje de escritores concurrentes.

## Topología

| Elemento | Responsabilidad |
| --- | --- |
| Hub | Define el catálogo que publica SMB y figura como `hub` en el registro. |
| Spoke | Usa el catálogo montado en `/Volumes/<share.name>` cuando requiere el proyecto compartido. |
| Registro | `config/hosts.json` (local, ignorado por Git; plantilla en `config/hosts.example.json`) fija el share y, por host, prefijo de hostname, rol, alias SSH, dirección, catálogo, checkout, PATH, cwd GUI y runtimes. |
| SSH | Conecta un alias `swarm-<destino>` por dirección. La persona verifica huellas; las claves dedicadas deshabilitan reenvíos pero no convierten SSH en sandbox. |
| SMB | Transporta sólo el catálogo aprobado; las credenciales se mantienen en Keychain del Mac que monta. |
| Herdr + Pi | El destino crea y controla exclusivamente recursos propios: una tab, un agente Pi y una sesión privada por tarea. |
| Skill | `agent-swarm-remote` define cómo validar, delegar, recuperar y cerrar sobres de tarea. |

Los nombres, rutas y endpoints se consultan siempre en el registro. Un mismo nombre de usuario en dos hosts no comparte `HOME`, Keychain, tokens, configuración, sesiones ni cachés.

## Flujo de una tarea

1. El origen consulta `swarm-delegate list` y confirma el destino registrado; `self` identifica el host local.
2. `preflight <destino>` comprueba SSH y el catálogo. Si un spoke informa `catalog_missing`, se resuelve su montaje SMB antes de enviar trabajo.
3. El origen envía por stdin un sobre con exactamente `task_id`, `origin_host`, `project`, `goal`, `acceptance` y `mode: executor`.
4. `swarm-delegate` usa SSH en modo batch y ejecuta `swarm-herdr-task submit` en el checkout declarado por el destino.
5. El adaptador reserva el UUID en un ledger durable, crea una sesión privada, crea una tab Herdr sin foco e inicia Pi con argv cerrado.
6. El adaptador envía el sobre exacto a Pi y `recover` lee solamente el JSONL de la sesión propia hasta encontrar la respuesta final.
7. Tras un resultado verificable, `close` cierra únicamente la tab de esa tarea. Si el estado es ambiguo, se conserva para recuperación; no se reenvía el prompt.

## Contrato de tarea

| Campo | Regla |
| --- | --- |
| `task_id` | UUID nuevo por trabajo. Ante ambigüedad se conserva y se reutiliza el mismo sobre. |
| `origin_host` | Nombre de host registrado que inició la tarea. |
| `project` | Ruta relativa bajo `catalog_root` del destino; nunca una ruta absoluta. |
| `goal` y `acceptance` | Texto no vacío y autocontenido que acota el trabajo y su resultado. |
| `mode` | Exactamente `executor`. |

`submit` acepta el sobre sólo por stdin. `recover` y `close` reciben el UUID. Los errores de conexión dejan el estado desconocido desde el origen: la acción segura es recuperar más tarde, no suponer que la tarea no se inició.

## Ciclo de alta

`swarm-setup add-host` coordina una alta reanudable desde un host ya registrado. Sus fases validan el origen, esperan Remote Login, verifican huellas y claves en ambas direcciones, comprueban runtimes, realizan el montaje SMB del spoke, actualizan el registro, instalan la skill, configuran actualización local y ejecutan aceptación Herdr + Pi.

Las pausas de Remote Login, huella, login de Pi y primer montaje SMB son decisiones humanas locales. Repetir el mismo comando conserva el estado y reanuda la fase pendiente; no se sustituyen valores del registro por rutas o nombres inventados.

## Límites operativos

- `StrictHostKeyChecking` es obligatorio; no se aceptan huellas sin comparación fiable.
- Los secretos no viajan en el sobre, el registro, los comandos ni los logs compartidos.
- El ledger persiste intenciones antes de efectos remotos. Un timeout, salida no cero o respuesta no interpretable deja `unknown` y bloquea el reenvío automático.
- El adaptador no usa el directorio de sesiones del usuario: cada tarea conserva su directorio privado y permisos restrictivos.
- Dos tareas pueden competir por el mismo árbol de trabajo. La coordinación, revisión y resolución de conflictos son humanas.
- La evidencia de pruebas no equivale a un despliegue. Consulte [validación](runbooks/agent-swarm/validation.md) antes de operar.

## Checklist de revisión

- [ ] El registro contiene exactamente los hosts y el share que se pretende usar.
- [ ] Cada dirección SSH tiene alias, huella verificada y clave dedicada.
- [ ] El catálogo SMB está limitado al recurso aprobado y disponible donde se necesita.
- [ ] Pi, gentle-pi y Herdr están instalados y autenticados localmente en cada destino.
- [ ] El sobre usa un UUID y un proyecto relativo; ante ambigüedad se recupera, no se reenvía.
- [ ] Sólo se cierran recursos creados por la tarea identificada.
