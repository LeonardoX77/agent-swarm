# Montaje SMB entre equipos

`swarm-smb-mount` consulta, monta y desmonta **un recurso SMB concreto** en macOS y Linux/WSL. macOS usa Keychain; Linux usa CIFS con una entrada fstab montable por el usuario. La herramienta no admite, guarda ni muestra contraseñas, y nunca usa sudo. Durante el alta, `swarm-setup` toma `share.host`, `share.name` y `share.user` de `config/hosts.json`; no copie valores de otro equipo.

## Preparación inicial (macOS)

En la sesión gráfica del Mac que realizará el montaje:

1. Consulte `share.host`, `share.name` y `share.user` en `config/hosts.json`. Confirme que el recurso publica únicamente el catálogo autorizado, no un disco o directorio más amplio.
2. En Finder, elija **Ir > Conectarse al servidor** y use `smb://<share.user>@<share.host>/<share.name>`, sustituyendo los tres marcadores por esos valores.
3. Autentíquese allí y marque **«Recordar contraseña en el llavero»**. No transmita la contraseña al agente ni la incluya en comandos, archivos o logs.
4. Confirme que el catálogo aparece en `/Volumes/<share.name>`. Si quiere probar un montaje nuevo desde el script, desmonte primero el recurso desde Finder.

## Linux/WSL: preparación

Instale `cifs-utils` y disponga de `findmnt`, `mount` y `umount` mediante la administración del sistema. Desde la cuenta que montará el catálogo, genere las instrucciones (sustituya H, S y U por `share.host`, `share.name` y `share.user`):

```sh
automation/agent-swarm/bin/swarm-smb-mount fstab-line --host H --share S --user U
```

En Linux, repita `--host` en orden de preferencia para configurar fallback al montar. El JSON incluye `fstab_line` (la primera línea), `fstab_lines` (una línea por candidato), `credentials_file`, `credentials_mode` y `credentials_template`. Una persona debe:

1. Como root, crear `/mnt/<share>` y añadir la línea exacta a `/etc/fstab`. Incluye `cifs`, la ruta absoluta de credenciales, uid/gid locales y `vers=3.0,noauto,user,_netdev`; no la invente ni copie de otra cuenta.
2. Crear personalmente `~/.config/agent-swarm/smb-credentials` con modo `0600`, usando la plantilla `username=...` / `password=...`. No entregue la contraseña al agente ni la incluya en comandos o logs compartidos. La herramienta nunca crea ni lee ese archivo directamente: lo usa el montaje CIFS del sistema.
3. Ejecutar `mount` como usuario normal con las opciones de la sección siguiente. Sin entrada fstab montable por el usuario, un montaje nuevo falla de forma segura con `fstab_entry_required`.

El fallback ocurre sólo al montar: un recurso ya montado no cambia de host en vivo, así que desmóntelo y vuelva a montarlo para seleccionar otro candidato. Con varios hosts, `status` informa `active_host`. La selección de una entrada fstab por origen (`mount //HOST/SHARE`) cuando varias entradas comparten un punto de montaje aún no se ha verificado en Linux real.

El catálogo Linux está en `/mnt/<share>`; macOS conserva `/Volumes/<share>`. Un hub Linux debe publicar su catálogo manualmente con un servidor SMB propio (por ejemplo Samba); setup no configura ese servidor. En WSL, Windows puede ocupar TCP 445 en loopback: una prueba local necesita otro puerto (la prueba registrada usó `port=1445` en fstab). No hay una opción de puerto en este CLI. Los servidores que exigen SMB 3.1.1 no se han validado; la línea generada usa `vers=3.0`.

## Uso

Sustituya los marcadores con valores de `config/hosts.json` antes de ejecutar los comandos desde el repositorio:

```bash
automation/agent-swarm/bin/swarm-smb-mount status --host <share.host> --share <share.name> --user <share.user>
automation/agent-swarm/bin/swarm-smb-mount mount --host <share.host> --share <share.name> --user <share.user>
automation/agent-swarm/bin/swarm-smb-mount unmount --host <share.host> --share <share.name> --user <share.user>
```

Linux acepta valores `--host` repetidos y ordenados para los cuatro comandos. macOS acepta exactamente un `--host`; varios valores se rechazan.

La salida es JSON. `mount` es idempotente: informa el punto ya montado. macOS identifica el origen `//<share.user>@<share.host>/<share.name>`; Linux identifica el montaje CIFS por host y recurso, no por usuario. `unmount` usa esa misma identificación. No desmonta recursos de otro host o con otro nombre. Si macOS elige `/Volumes/<share.name>-1` en vez del punto esperado, la salida incluye `unexpected_mount_point`: compruebe qué ocupa el punto original antes de actuar.

## Montaje persistente

`swarm-setup` instala el montaje persistente durante el alta de un `spoke`. Para instalarlo manualmente, añada `--persistent` al primer montaje:

```bash
automation/agent-swarm/bin/swarm-smb-mount mount \
  --host <share.host> --share <share.name> --user <share.user> --persistent
```

El script se copia a `~/.local/agent-swarm/bin/swarm-smb-mount` para funcionar sin depender del catálogo montado.

| Plataforma | Persistencia cada 300 s | Artefactos y logs |
| --- | --- | --- |
| macOS | LaunchAgent al iniciar sesión; usa Keychain | `~/Library/LaunchAgents/com.mac-agent-swarm.smb.<identificador-del-recurso>.plist`; logs en `~/Library/Logs/mac-agent-swarm/` |
| Linux/WSL | Timer `systemd --user` | `.service` y `.timer` en `~/.config/systemd/user/`, con prefijo `com.mac-agent-swarm.smb.`; logs en `~/.local/state/agent-swarm/logs/<label>.out.log` y `.err.log`; si la ruta del HOME contiene espacios u otros caracteres que systemd no puede expresar en esas directivas, el servicio usa el journal (`journalctl --user -u <label>.service`) |

En Linux, si `systemctl --user` no está disponible o no puede activar el timer, el montaje devuelve una advertencia y `persistent: false`; no equivale a persistencia instalada. En WSL, habilite `[boot]` / `systemd=true` en `/etc/wsl.conf`. Los timers sólo funcionan mientras el usuario tiene una sesión, salvo que se habilite `loginctl enable-linger $USER`.

Para retirar el montaje y su LaunchAgent o timer, sin borrar la copia local ni los registros (ni fstab o credenciales en Linux):

```bash
automation/agent-swarm/bin/swarm-smb-mount unmount \
  --host <share.host> --share <share.name> --user <share.user> --remove-persistent
```

## Ejecución por SSH (macOS)

Linux usa la misma entrada fstab también por SSH; no necesita Finder ni una sesión gráfica.

`osascript` necesita una sesión gráfica de macOS: un montaje iniciado sólo por SSH normalmente no puede mostrar la interacción. Con `--persistent`, el script instala y usa el LaunchAgent en la sesión gráfica, lo activa y espera el resultado; la salida indica `"via": "launchagent"`.

Si el alta se detiene en `mount`, conecte primero desde Finder y guarde la contraseña en Keychain; reanude **el mismo comando** de `swarm-setup`. Si la primera copia por SCP informa que falta el directorio de destino, use una versión de `swarm-setup` que cree el padre remoto antes de copiar; no reubique manualmente los archivos fuera del directorio previsto.
