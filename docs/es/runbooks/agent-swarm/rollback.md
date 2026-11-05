# Reversión controlada de Agent Swarm

Retire sólo los artefactos que una alta actual de Agent Swarm creó y hágalo en el host local con autorización de su propietario. Esta guía no autoriza acceso remoto, cambios de SSH sin revisión ni borrado de datos compartidos.

## Antes de revertir

1. Coordine la detención de nuevas tareas y conserve el último resultado saneado de cada UUID abierto.
2. Identifique el alta concreta en el registro, el estado de `swarm-setup` y los artefactos que creó. Si no puede demostrar el origen de un recurso, no lo elimine.
3. Compruebe que no hay una tarea Herdr en curso. Una tarea ambigua se recupera antes de decidir su cierre.
4. Pida autorización humana antes de retirar Remote Login, claves, aliases, montajes o elementos de Keychain.

## Alcance permitido

| Recurso de la alta | Reversión local permitida |
| --- | --- |
| Registro local (`config/hosts.json`, no versionado) | Quite o corrija sólo la entrada aprobada; haga antes una copia y revise que no contenga cambios ajenos. |
| Clave y alias SSH dedicados | Retire únicamente el par de clave y el bloque `Host swarm-<target>` creados para esa dirección. Nunca borre una clave reutilizada. |
| `authorized_keys` | Quite sólo la línea añadida para la clave dedicada, conservando las demás entradas y copias de seguridad. |
| Montaje SMB persistente | Use `swarm-smb-mount unmount --remove-persistent` con los valores del share registrado; elimina sólo ese montaje y su LaunchAgent. |
| Skill y bootstrap | Retire únicamente la copia y el bloque bootstrap creados para el host nuevo, después de confirmar que no sirven a otro canal. |
| Actualización local | Retire sólo el LaunchAgent y los archivos creados por `swarm-update` para esa instalación. |
| Remote Login | Quite la autorización de la cuenta sólo si la alta la agregó y no hay otro uso aprobado. |

## Orden recomendado

1. Detenga nuevos envíos y recupere o cierre únicamente tareas propias que tengan resultado verificable.
2. Quite los aliases y claves dedicadas de cada origen y las líneas asociadas de cada destino, una dirección por vez.
3. Desmonte el share en los spokes que deje de necesitarlo y retire sólo su configuración persistente.
4. Retire la skill, bootstrap y actualización local si pertenecen exclusivamente al alta.
5. Actualice el registro local (copia previa incluida) y evalúe Remote Login al final.

## Nunca elimine

- Workspaces, repositorios ni contenido del catálogo o de `/Volumes/<share.name>`.
- Keychain completo, `HOME`, sesiones, cachés, logs generales o credenciales ajenas.
- Otros shares SMB, usuarios macOS, aliases SSH, claves, entradas de `authorized_keys` o configuración de SSH no atribuibles al alta.
- Tabs, panes o sesiones Herdr que no pertenezcan al UUID que está recuperando o cerrando.

Si un recurso es compartido, anterior al alta o de procedencia incierta, déjelo intacto y escale la decisión a la persona administradora.
