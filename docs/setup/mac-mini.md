# Configurar la Mac mini (`jarvis`)

Esta guía prepara a `jarvis` como nodo de ejecución y cliente SMB. Hacé cada paso en la Mac mini; las acciones marcadas **privilegiado** requieren presencia humana y `sudo` local.

## Camino rápido

1. Confirmá la cuenta humana `jarvis`, Pi + Gentle Pi locales y el montaje SMB autenticado de forma interactiva.
2. Creá la clave SSH dedicada, configurá el alias a la MacBook e instalá el runtime bajo `HOME`.
3. Instalá manualmente la línea de comando forzado y validá ambos sentidos sin obtener una shell.

## Prerrequisitos y preflight seguro

`jarvis` es una cuenta creada por una persona antes de esta guía; este procedimiento no crea usuarios ni administra contraseñas.

```sh
whoami                         # debe imprimir jarvis
id -un jarvis
[ -d /Volumes ]
pi --version
```

Instalá Pi y Gentle Pi como `jarvis` mediante el flujo local aprobado. Para verificar la autenticación sin imprimir tokens, abrí `pi` de forma interactiva y usá `/login` si Pi lo solicita o necesitás seleccionar un proveedor; luego salí y ejecutá este chequeo inocuo en modo print:

```sh
pi -p "Respondé únicamente: verificación local correcta."
```

Pi no documenta `pi auth status`; repetí `pi --version` y este flujo local en su lugar. No copies HOME, Keychain, credenciales, sesiones, cachés ni configuración desde la MacBook. Si compartís skills, cloná su repositorio Git en una ruta local de `jarvis`.

## Montar el workspace por SMB

La MacBook debe haber publicado previamente `agent-projects`. En Finder, elegí **Go → Connect to Server…** e ingresá exactamente:

```
smb://leo@<MACBOOK_LAN_OR_TAILSCALE_ENDPOINT>/agent-projects
```

Elegí autenticarte como usuario registrado, escribí el usuario de MacBook `leo` y su contraseña **interactivamente**, y permití que Keychain la recuerde si la persona lo aprueba. Seleccioná `/Volumes/agent-projects` como montaje esperado y verificá:

```sh
mount | grep 'agent-projects'
[ -d /Volumes/agent-projects/leo/mac-agent-fabric ]
```

No pongas la contraseña SMB en scripts, JSON, archivos de configuración ni logs. Para reconectar al iniciar sesión, agregá el volumen montado a **System Settings → General → Login Items → Open at Login**. Keychain gestiona la credencial; ningún script debe almacenarla.

En **System Settings → General → Sharing → Remote Login**, activá Remote Login y elegí “Only these users”, agregando sólo `jarvis`. Esto es **privilegiado**, local y necesario para el despacho inverso desde MacBook. No habilites Remote Management ni shell general para la clave del fabric.

## Clave y alias SSH

Creá una identidad exclusiva para Mac mini → MacBook:

```sh
ssh-keygen -t ed25519 -f ~/.ssh/agent-fabric-mac-mini-to-macbook -C agent-fabric-mac-mini-to-macbook
chmod 700 ~/.ssh
chmod 600 ~/.ssh/agent-fabric-mac-mini-to-macbook
chmod 644 ~/.ssh/agent-fabric-mac-mini-to-macbook.pub
```

Entregá sólo `~/.ssh/agent-fabric-mac-mini-to-macbook.pub` a `leo`. Recibí su archivo público como, por ejemplo, `~/Downloads/agent-fabric-macbook-to-mac-mini.pub`; no registres ninguna clave privada en Git.

No sobrescribas `~/.ssh/config`. Fusioná manualmente el contenido de `config/mac-mini/ssh_config.template` con la configuración existente; o guardá la plantilla como un archivo dedicado, por ejemplo `~/.ssh/config.d/agent-fabric.conf`, y agregá una sola directiva `Include ~/.ssh/config.d/*.conf` a tu configuración existente. Reemplazá `<MACBOOK_LAN_OR_TAILSCALE_ENDPOINT>` por la IP LAN o nombre/IP Tailscale real de la MacBook. El alias primario es `agent-fabric-macbook`; la plantilla fija `BatchMode`, `IdentitiesOnly`, host key estricto, sin forwarding y sin PTY.

## Runtime y comando forzado

Desde el clon local del repositorio, el helper instala únicamente archivos runtime en `~/.local/agent-fabric`; no usa `sudo` y no modifica SSH, `authorized_keys`, SMB ni launch services:

```sh
python3 automation/agent-fabric/bin/fabric-install-runtime --plan --role mac-mini --peer-public-key ~/Downloads/agent-fabric-macbook-to-mac-mini.pub
python3 automation/agent-fabric/bin/fabric-install-runtime --apply --role mac-mini --peer-public-key ~/Downloads/agent-fabric-macbook-to-mac-mini.pub
```

Revisá el campo `authorized_keys_line`. Es la línea exacta generada por `ssh_policy.py` y fuerza `~/.local/agent-fabric/bin/fabric-runner --config ~/.local/agent-fabric/config/host.json`. Agregala manualmente, después de aprobarla:

```sh
mkdir -p ~/.ssh && chmod 700 ~/.ssh
# Pegá el valor exacto de authorized_keys_line; no lo modifiques.
editor ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

## Validación y reversión local

```sh
python3 -m unittest discover -s automation/agent-fabric/test
ssh -o BatchMode=yes -o RequestTTY=no agent-fabric-macbook true
```

El segundo comando suministra intencionalmente un comando remoto (`true`): el comando forzado debe rechazarlo y nunca abrir una shell. Antes de operar, la ruta de éxito es enviar por stdin con `fabric-dispatch` una solicitud JSON válida con prompt inocuo y verificar que el runner use `/Volumes/agent-projects/leo/mac-agent-fabric`, timeout máximo de 900 segundos y el log local `~/.local/state/agent-fabric/activity.jsonl`.

Para eliminar sólo los archivos que instaló el helper para `jarvis`:

```sh
python3 automation/agent-fabric/bin/fabric-install-runtime --revert
```

Esto no elimina el montaje SMB, entradas de Keychain, claves, SSH config, `authorized_keys`, el share de MacBook ni Remote Login. Cualquier reversión privilegiada se inspecciona y ejecuta manualmente en su host.
