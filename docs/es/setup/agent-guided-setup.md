# Instalación guiada de Agent Swarm

La ruta de alta es `swarm-setup add-host` desde un nodo macOS o Linux/WSL ya registrado. El proceso configura el canal Herdr + Pi de forma reanudable y se detiene para las decisiones que sólo puede tomar una persona en el host correspondiente. Linux/WSL ejecuta las mismas diez fases con CIFS y timers systemd de usuario; se ha probado una delegación real hacia este WSL, pero la aceptación bidireccional entre dos máquinas sigue sin validarse.

## Camino rápido

1. Confirme que el origen figura en `config/hosts.json` (registro local no versionado; cree uno desde `config/hosts.example.json` si falta) y ejecute el comando desde su checkout local.
2. Ejecute el procedimiento descrito en [Agregar un equipo](add-host.md#camino-rápido) con el nombre, dirección y usuario del equipo nuevo. Para Linux/WSL, siga primero [la preparación](add-host.md#linuxwsl-preparación).
3. Complete las pausas locales: acceso SSH, comparación de huella y login de Pi; para SMB, Finder/Keychain en macOS o fstab y credenciales locales en Linux.
4. Repita el mismo comando con las mismas opciones hasta que la aceptación bidireccional termine correctamente.
5. Antes de delegar trabajo, ejecute `swarm-delegate preflight <destino>` y siga el [runbook de validación](../runbooks/agent-swarm/validation.md).

El registro es la fuente de verdad. Sus campos `hosts`, `share` y roles determinan alias, endpoints, usuarios, catálogo, repositorio y rutas. No reemplace esos datos por nombres de equipos, IPs o rutas de otro despliegue. Un host puede tener además `fallback_addresses` ordenadas para SSH y `share_hosts` para su montaje SMB; ambas son opcionales, por lo que los registros existentes siguen siendo válidos.

## Candidatos de dirección y failover

Use `--address` para la dirección SSH preferida y repita `--fallback-address` en orden para los candidatos posteriores. `--origin-address` proporciona de igual modo sólo el alias inverso y sustituye los candidatos del registro del origen para ese alias. Un spoke puede repetir `--share-host` para hosts SMB en orden de preferencia; un hub rechaza esa opción. Los candidatos deben empezar por un carácter alfanumérico, contener sólo letras, dígitos, puntos y guiones, y no contener duplicados (ni puede la dirección principal ser un fallback).

Use MagicDNS de Tailscale primero y LAN después. Tailscale usa la LAN directamente cuando puede, así que el candidato LAN protege principalmente frente a que Tailscale no esté disponible o a que una herramienta de rutas capture un subrango de Tailscale (por ejemplo, Twingate al enrutar `100.96.0.0/12` dentro de `100.64.0.0/10`). En Windows/WSL, trate con cuidado una regla de firewall limitada a la LAN: un perfil Wi-Fi Público puede seguir usando ese rango LAN.

SSH prueba los candidatos en orden; un candidato inalcanzable añade como máximo su timeout de conexión por candidato. El fallback SMB ocurre sólo durante el montaje: vuelva a montar para cambiar el host activo.

## Linux/WSL antes del alta

- Prepare SSH, Node, Python 3 y Pi; deje disponible el servidor Herdr y complete el login de Pi localmente. `--install-missing` puede añadir Herdr con el instalador oficial de https://herdr.dev/install.sh (descargado a un archivo temporal y ejecutado solo si la descarga tuvo éxito; requiere curl) y gentle-pi mediante Pi. No se requiere Homebrew.
- En ambas plataformas es obligatoria la integración oficial de Herdr para Pi: `herdr integration status` debe confirmar Pi instalado. `--install-missing` ejecuta `herdr integration install pi` si Herdr está disponible (dry-run sólo anuncia el plan); instala `~/.pi/agent/extensions/herdr-agent-state.ts`. Sin ella falta la prueba de propiedad `agent_session` de tipo `path` y fuente `herdr:pi`: submit puede quedar `unknown` sin entregar el prompt.
- Para arrancar Herdr sin GUI en Linux, ejecute `herdr` en una terminal normal y desacople el cliente, o use una pty con filas y columnas no nulas. El servidor sobrevive a la salida del cliente. Herdr 0.9.5 rechaza una terminal con cuadrícula cero (`cannot attach without a usable terminal: terminal reported a zero-sized grid`) y no tiene `herdr server start` (sólo `server stop` y `server reload-config`). Compruebe `herdr tab list`; `server_not_running` indica que falta arrancarlo. La espera muestra los nombres de probes ausentes y las instrucciones de arranque cuando falta `herdr-server`.
- Setup y swarm-update descubren `$HOME/.pi/agent/bin`, donde instala Pi su instalador, inmediatamente después de `$HOME/.local/bin`; conservan las demás rutas y su orden.
- Para un spoke, use `swarm-smb-mount fstab-line --host H --share S --user U`. Una persona añade la línea exacta a `/etc/fstab` como root, crea `/mnt/<share>` y crea `~/.config/agent-swarm/smb-credentials` con modo `0600`. La herramienta nunca usa sudo ni maneja contraseñas. El setup monta y configura un timer de usuario cada 300 s; si no hay `systemctl --user`, advierte que no activó la persistencia.
- La actualización diaria usa `agent-swarm-update.timer`, salvo `--no-auto-update`. En WSL, habilite `[boot]` / `systemd=true` en `/etc/wsl.conf`; los timers requieren sesión de usuario salvo que active `loginctl enable-linger $USER`.
- Un hub Linux debe publicar manualmente el catálogo mediante su propio servidor SMB (por ejemplo Samba); el setup no lo configura. Windows puede ocupar el puerto TCP 445 en loopback: use otro puerto para una prueba SMB local.

Consulte [los detalles de preparación](add-host.md#linuxwsl-preparación) y [la evidencia y sus límites](../runbooks/agent-swarm/test-evidence.md#evidencia-linuxwsl) antes de delegar.

## Pausas humanas

Las verificaciones de huella y login son comunes. Las acciones SSH y SMB dependen de la plataforma:

| Momento | Acción local | Confirmación segura |
| --- | --- | --- |
| Acceso remoto | Active Remote Login en macOS o un `sshd` en Linux para la cuenta registrada; confirme la red. | El puerto SSH responde desde el origen. |
| Huella SSH | Compare la huella vista en el host con el escaneo desde el origen. | Coinciden; `StrictHostKeyChecking` sigue activo. |
| Runtimes y login | Instale lo aprobado y complete el login de Pi desde la GUI cuando se solicite. | Los checks encuentran Pi, gentle-pi, Herdr, su servidor y la integración oficial Pi. |
| SMB | macOS: Finder y Keychain. Linux: entrada fstab y archivo de credenciales protegido; ejecute el montaje indicado. | El catálogo registrado aparece en el spoke. |
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
