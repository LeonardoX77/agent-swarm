# Montaje SMB entre equipos

`swarm-smb-mount` consulta, monta y desmonta **un recurso SMB concreto** de otro Mac. Usa las credenciales guardadas en el llavero de macOS: no admite, guarda ni muestra contraseñas. Durante el alta, `swarm-setup` toma `share.host`, `share.name` y `share.user` de `config/hosts.json`; no copie valores de otro equipo.

## Preparación inicial

En la sesión gráfica del Mac que realizará el montaje:

1. Consulte `share.host`, `share.name` y `share.user` en `config/hosts.json`. Confirme que el recurso publica únicamente el catálogo autorizado, no un disco o directorio más amplio.
2. En Finder, elija **Ir > Conectarse al servidor** y use `smb://<share.user>@<share.host>/<share.name>`, sustituyendo los tres marcadores por esos valores.
3. Autentíquese allí y marque **«Recordar contraseña en el llavero»**. No transmita la contraseña al agente ni la incluya en comandos, archivos o logs.
4. Confirme que el catálogo aparece en `/Volumes/<share.name>`. Si quiere probar un montaje nuevo desde el script, desmonte primero el recurso desde Finder.

## Uso

Sustituya los marcadores con valores de `config/hosts.json` antes de ejecutar los comandos desde el repositorio:

```bash
automation/agent-swarm/bin/swarm-smb-mount status --host <share.host> --share <share.name> --user <share.user>
automation/agent-swarm/bin/swarm-smb-mount mount --host <share.host> --share <share.name> --user <share.user>
automation/agent-swarm/bin/swarm-smb-mount unmount --host <share.host> --share <share.name> --user <share.user>
```

La salida es JSON. `mount` es idempotente: si ya existe exactamente `//<share.user>@<share.host>/<share.name>`, informa el punto ya montado. `unmount` sólo actúa sobre ese origen exacto; no desmonta otros recursos SMB. Si macOS elige `/Volumes/<share.name>-1` en vez del punto esperado, la salida incluye `unexpected_mount_point`: compruebe qué ocupa el punto original antes de actuar.

## Montaje persistente

`swarm-setup` instala el montaje persistente durante el alta de un `spoke`. Para instalarlo manualmente, añada `--persistent` al primer montaje:

```bash
automation/agent-swarm/bin/swarm-smb-mount mount \
  --host <share.host> --share <share.name> --user <share.user> --persistent
```

Esto instala un LaunchAgent de usuario que intenta montar al iniciar sesión y cada 300 segundos. No conserva una contraseña: usa el llavero de la sesión gráfica. Para funcionar aunque el recurso aún no esté montado, el script se copia a `~/.local/agent-swarm/bin/swarm-smb-mount`.

Los artefactos son:

- LaunchAgent: `~/Library/LaunchAgents/com.mac-agent-swarm.smb.<identificador-del-recurso>.plist` (compruebe el nombre real en el host).
- Copia local: `~/.local/agent-swarm/bin/swarm-smb-mount`.
- Registros: `~/Library/Logs/mac-agent-swarm/`.

Para retirar el montaje y su LaunchAgent, sin borrar la copia local ni los registros:

```bash
automation/agent-swarm/bin/swarm-smb-mount unmount \
  --host <share.host> --share <share.name> --user <share.user> --remove-persistent
```

## Ejecución por SSH

`osascript` necesita una sesión gráfica de macOS: un montaje iniciado sólo por SSH normalmente no puede mostrar la interacción. Con `--persistent`, el script instala y usa el LaunchAgent en la sesión gráfica, lo activa y espera el resultado; la salida indica `"via": "launchagent"`.

Si el alta se detiene en `mount`, conecte primero desde Finder y guarde la contraseña en Keychain; reanude **el mismo comando** de `swarm-setup`. Si la primera copia por SCP informa que falta el directorio de destino, use una versión de `swarm-setup` que cree el padre remoto antes de copiar; no reubique manualmente los archivos fuera del directorio previsto.
