# Instalación guiada de Agent Fabric

La única ruta de alta es `fabric-setup add-host` desde un Mac ya registrado. El proceso configura el canal Herdr + Pi de forma reanudable y se detiene para las decisiones que sólo puede tomar una persona en el host correspondiente.

## Camino rápido

1. Confirme que el origen figura en `config/hosts.json` y ejecute el comando desde su checkout local.
2. Ejecute el procedimiento descrito en [Agregar un equipo](add-host.md#camino-rápido) con el nombre, dirección y usuario del Mac nuevo.
3. Complete las pausas locales: Remote Login, comparación de huella, login GUI de Pi y primer acceso SMB.
4. Repita el mismo comando con las mismas opciones hasta que la aceptación bidireccional termine correctamente.
5. Antes de delegar trabajo, ejecute `fabric-delegate preflight <destino>` y siga el [runbook de validación](../runbooks/agent-fabric/validation.md).

El registro es la fuente de verdad. Sus campos `hosts`, `share` y roles determinan alias, endpoints, usuarios, catálogo, repositorio y rutas. No reemplace esos datos por nombres de equipos, IPs o rutas de otro despliegue.

## Pausas humanas

| Momento | Acción local | Confirmación segura |
| --- | --- | --- |
| Acceso remoto | Active Remote Login para la cuenta registrada y confirme la red elegida. | El puerto SSH responde desde el origen. |
| Huella SSH | Compare la huella vista en el host con el escaneo desde el origen. | Coinciden; `StrictHostKeyChecking` sigue activo. |
| Runtimes y login | Instale lo aprobado y complete el login de Pi desde la GUI cuando se solicite. | Los checks encuentran Pi, gentle-pi y Herdr. |
| SMB | En Finder, conecte a la URL que muestra el setup; guarde la contraseña sólo en Keychain si corresponde. | El catálogo registrado aparece en el spoke. |
| Aceptación | Resuelva `Not logged in` desde la GUI indicada y reanude el mismo setup. | Preflight y aceptación terminan en ambos sentidos. |

## Límites

- El setup no autoriza cambios de red, `sudo`, credenciales ni instalaciones ajenas a sus fases.
- Los perfiles, Keychain, sesiones, cachés y directorios personales permanecen en cada Mac.
- La skill se copia mediante el mecanismo local del setup; SMB no transporta credenciales ni directorios personales.
- Guarde sólo estado, fase, versión y código de salida saneados. No guarde contraseñas, tokens, claves privadas ni sobres de tarea en tickets o logs compartidos.
- Si el resultado es ambiguo, consulte el estado persistido antes de reintentar. No reinicie sesiones existentes para forzar una recuperación.

## Operación posterior

Use `fabric-delegate list` para ver los destinos, `self` para identificar el origen y `preflight <destino>` antes de enviar una tarea. El [runbook de tareas Herdr + Pi](../runbooks/agent-fabric/herdr-tasks.md) describe `submit`, `recover` y `close`, incluido el requisito de conservar el mismo UUID tras un fallo de transporte.

Para un diagnóstico de fases, opciones, estado y recuperación, consulte [Agregar un equipo](add-host.md). Para SSH y SMB, use respectivamente [Canal SSH](../runbooks/agent-fabric/ssh-channel.md) y [Montaje SMB](../runbooks/agent-fabric/smb-mount.md).
