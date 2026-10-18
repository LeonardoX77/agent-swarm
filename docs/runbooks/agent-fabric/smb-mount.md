# Montaje SMB entre equipos

`fabric-smb-mount` consulta, monta y desmonta **un recurso SMB concreto** de otro Mac. Usa las credenciales ya guardadas en el llavero de macOS: no admite, guarda ni muestra contraseñas.

## Preparación inicial

En la sesión gráfica del Mac que realizará el montaje:

1. En Finder, elija **Ir > Conectarse al servidor** e introduzca la dirección SMB del recurso.
2. Autentíquese con la cuenta correspondiente y marque **«Recordar contraseña en el llavero»**.
3. Desmonte el recurso de Finder si quiere comprobar luego el script.

Para el Mac mini, el recurso operativo es:

- host: `MacBookLeo.local`
- recurso: `agent-projects`
- usuario: `leo`
- punto esperado: `/Volumes/agent-projects`

Ese recurso expone solamente `/Users/leo/projects`; no se debe montar el disco completo.

## Uso

Ejecute el script desde el repositorio:

```bash
automation/agent-fabric/bin/fabric-smb-mount status --host MacBookLeo.local --share agent-projects --user leo
automation/agent-fabric/bin/fabric-smb-mount mount --host MacBookLeo.local --share agent-projects --user leo
automation/agent-fabric/bin/fabric-smb-mount unmount --host MacBookLeo.local --share agent-projects --user leo
```

La salida es JSON. `mount` es idempotente: si ya existe exactamente `//leo@MacBookLeo.local/agent-projects`, informa el punto ya montado. `unmount` sólo actúa sobre ese origen exacto; no desmonta otros recursos SMB. Si macOS elige, por ejemplo, `/Volumes/agent-projects-1`, la salida incluye `unexpected_mount_point`.

## Montaje persistente

Sí, se puede mantener el montaje. Añada `--persistent` al primer montaje:

```bash
automation/agent-fabric/bin/fabric-smb-mount mount \
  --host MacBookLeo.local --share agent-projects --user leo --persistent
```

Esto instala un LaunchAgent de usuario que intenta montar al iniciar sesión y cada 300 segundos. No conserva una contraseña: el proceso sigue usando el llavero de la sesión gráfica. Para poder funcionar aunque el recurso aún no esté montado, el script se copia de forma local a `~/.local/agent-fabric/bin/fabric-smb-mount`.

Los archivos instalados son:

- LaunchAgent: `~/Library/LaunchAgents/com.mac-agent-fabric.smb.MacBookLeo-local.agent-projects.plist`
- copia local: `~/.local/agent-fabric/bin/fabric-smb-mount`
- registros: `~/Library/Logs/mac-agent-fabric/`

Para retirar el montaje y el LaunchAgent (sin borrar la copia local ni los registros):

```bash
automation/agent-fabric/bin/fabric-smb-mount unmount \
  --host MacBookLeo.local --share agent-projects --user leo --remove-persistent
```

## Ejecución por SSH

`osascript` necesita una sesión gráfica de macOS, por lo que un `mount` iniciado por SSH normalmente no puede mostrar la interacción de montaje. Con `--persistent`, el script instala y usa el LaunchAgent por SSH precisamente porque `osascript` necesita la sesión gráfica; lo activa y espera el resultado, con `"via": "launchagent"` en la salida.
