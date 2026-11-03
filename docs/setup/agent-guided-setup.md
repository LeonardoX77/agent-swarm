# Instalación guiada de Agent Swarm

La ruta de alta es `swarm-setup add-host` desde un nodo macOS o Linux/WSL ya registrado. El proceso configura el canal Herdr + Pi de forma reanudable y se detiene para las decisiones que sólo puede tomar una persona en el host correspondiente. Linux/WSL requiere runtimes y catálogo aprovisionados manualmente; su delegación de extremo a extremo no se ha validado.

## Camino rápido

1. Confirme que el origen figura en `config/hosts.json` (registro local no versionado; cree uno desde `config/hosts.example.json` si falta) y ejecute el comando desde su checkout local.
2. Ejecute el procedimiento descrito en [Agregar un equipo](add-host.md#camino-rápido) con el nombre, dirección y usuario del equipo nuevo. Para Linux/WSL, siga primero el [aprovisionamiento manual](add-host.md#linuxwsl-aprovisionamiento-manual).
3. Complete las pausas locales: acceso SSH, comparación de huella y login de Pi; en macOS, también Remote Login y primer acceso SMB desde Finder.
4. Repita el mismo comando con las mismas opciones hasta que la aceptación bidireccional termine correctamente.
5. Antes de delegar trabajo, ejecute `swarm-delegate preflight <destino>` y siga el [runbook de validación](../runbooks/agent-swarm/validation.md).

El registro es la fuente de verdad. Sus campos `hosts`, `share` y roles determinan alias, endpoints, usuarios, catálogo, repositorio y rutas. No reemplace esos datos por nombres de equipos, IPs o rutas de otro despliegue.

## Linux/WSL antes del alta

- Preinstale Node, Python 3, Pi, gentle-pi y Herdr; deje disponible el servidor Herdr y complete el login de Pi en el destino. No se requiere Homebrew.
- Para un spoke, monte el catálogo por su cuenta y pase `--linux-catalog-root /mnt/shared-projects`. La ruta debe ser absoluta en el destino y contener el proyecto en la misma ruta relativa al catálogo que el repositorio de origen.
- El setup no monta SMB, no gestiona sus credenciales y no instala un servicio de actualización automática en Linux/WSL; mantenga esos recursos manualmente.

La opción sólo admite spokes Linux/WSL: otros roles fallan en el preflight local; un destino macOS falla después de autenticar SSH y detectar su plataforma. En ese último caso pueden quedar artefactos locales del bootstrap SSH, pero no se continúa con SMB, registro ni configuración remota del host. Consulte [los detalles](add-host.md#linuxwsl-aprovisionamiento-manual) antes de reintentar.

## Pausas humanas

La tabla siguiente describe macOS. En Linux/WSL, prepare SSH y el catálogo manualmente antes del alta; las verificaciones de huella y login siguen siendo necesarias.

| Momento | Acción local | Confirmación segura |
| --- | --- | --- |
| Acceso remoto | Active Remote Login para la cuenta registrada y confirme la red elegida. | El puerto SSH responde desde el origen. |
| Huella SSH | Compare la huella vista en el host con el escaneo desde el origen. | Coinciden; `StrictHostKeyChecking` sigue activo. |
| Runtimes y login | Instale lo aprobado y complete el login de Pi desde la GUI cuando se solicite. | Los checks encuentran Pi, gentle-pi y Herdr. |
| SMB | En Finder, conecte a la URL que muestra el setup; guarde la contraseña sólo en Keychain si corresponde. | El catálogo registrado aparece en el spoke. |
| Aceptación | Resuelva `Not logged in` desde la GUI indicada y reanude el mismo setup. | Preflight y aceptación terminan en ambos sentidos. |

## Límites

- El setup no autoriza cambios de red, `sudo`, credenciales ni instalaciones ajenas a sus fases.
- Los perfiles, sesiones, cachés y directorios personales permanecen en cada nodo; Keychain es exclusivo de macOS.
- La skill se copia mediante el mecanismo local del setup; SMB no transporta credenciales ni directorios personales.
- Guarde sólo estado, fase, versión y código de salida saneados. No guarde contraseñas, tokens, claves privadas ni sobres de tarea en tickets o logs compartidos.
- Si el resultado es ambiguo, consulte el estado persistido antes de reintentar. No reinicie sesiones existentes para forzar una recuperación.

## Operación posterior

Use `swarm-delegate list` para ver los destinos, `self` para identificar el origen y `preflight <destino>` antes de enviar una tarea. El [runbook de tareas Herdr + Pi](../runbooks/agent-swarm/herdr-tasks.md) describe `submit`, `recover` y `close`, incluido el requisito de conservar el mismo UUID tras un fallo de transporte.

Para un diagnóstico de fases, opciones, estado y recuperación, consulte [Agregar un equipo](add-host.md). Para SSH y SMB, use respectivamente [Canal SSH](../runbooks/agent-swarm/ssh-channel.md) y [Montaje SMB](../runbooks/agent-swarm/smb-mount.md).
