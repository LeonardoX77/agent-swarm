# Configurar la MacBook (`leo`)

Esta guía deja a `leo` como autoridad del workspace y como destino SSH restringido. Hacé cada paso localmente en la MacBook; los comandos marcados **privilegiado** piden `sudo` interactivo y no deben ejecutarse desde un despacho.

## Camino rápido

1. Confirmá el preflight y la instalación local de Pi + Gentle Pi.
2. Publicá sólo `agent-projects`, montá las claves SSH dedicadas y copiá el runtime bajo `HOME`.
3. Probá el comando forzado y una solicitud inocua antes de despachar trabajo real.

## Prerrequisitos y preflight seguro

- La cuenta local es `leo` y el árbol existe en `/Users/leo/projects`.
- La Mac mini ya tiene la cuenta humana `jarvis` y conectividad LAN o Tailscale.
- Tené la clave pública de `jarvis` disponible como un archivo local; nunca copies claves privadas, contraseñas SMB ni tokens al repositorio.

```sh
whoami                         # debe imprimir leo
id -un leo
[ -d /Users/leo/projects ]
python3 automation/agent-fabric/bin/fabric-host-preflight --help
pi --version
```

Instalá Pi y Gentle Pi sólo con el método aprobado para `leo`, desde una terminal local. Para verificar la autenticación sin imprimir tokens, abrí `pi` de forma interactiva y usá `/login` si Pi lo solicita o necesitás seleccionar un proveedor; luego salí y ejecutá este chequeo inocuo en modo print:

```sh
pi -p "Respondé únicamente: verificación local correcta."
```

Pi no documenta `pi auth status`; repetí `pi --version` y este flujo local en su lugar. Gentle Pi, sus sesiones, cachés, skills y Keychain permanecen locales; las skills compartidas se clonan por Git localmente.

## Publicar el único share SMB

No modifiques shares existentes no relacionados. Primero inspeccioná el estado:

```sh
sharing -l
man sharing
```

Usá la sintaxis local de `sharing(8)`: `-a <path>` agrega el share, `-S <smb-name>` le asigna su nombre SMB y `-g 000 -R 0` aplica la configuración de acceso indicada por esa herramienta. Este comando es **privilegiado**; leelo, confirmá que no existe ya un share ajeno con ese nombre y ejecutalo localmente:

```sh
sudo sharing -a /Users/leo/projects -S agent-projects -s 001 -g 000 -R 0
sharing -l
```

El resultado buscado es un único share nuevo llamado `agent-projects`, con ruta `/Users/leo/projects`. `sharing` no configura ACLs por usuario: el acceso de `leo` y de cualquier otro usuario se controla por separado mediante la autenticación SMB y los permisos POSIX/ACL del filesystem sobre `/Users/leo/projects`. Revisá y ajustá esos permisos por la política local, sin cambiar ACLs de otros shares ni otorgar acceso guest.

En **System Settings → General → Sharing → Remote Login**, activá Remote Login y elegí “Only these users”, agregando sólo `leo`. Esta acción es **privilegiada** y local. Verificá que no se habilitaron Remote Management ni forwarding de puertos.

## Clave y SSH de despacho

Creá una clave exclusiva para MacBook → Mac mini; no reutilices tu clave personal:

```sh
ssh-keygen -t ed25519 -f ~/.ssh/agent-fabric-macbook-to-mac-mini -C agent-fabric-macbook-to-mac-mini
chmod 700 ~/.ssh
chmod 600 ~/.ssh/agent-fabric-macbook-to-mac-mini
chmod 644 ~/.ssh/agent-fabric-macbook-to-mac-mini.pub
```

Entregá **sólo** `~/.ssh/agent-fabric-macbook-to-mac-mini.pub` a `jarvis` por un canal que puedas verificar. Recibí a cambio su clave pública y guardala, por ejemplo, en `~/Downloads/agent-fabric-mac-mini-to-macbook.pub`; no la agregues al repositorio.

No sobrescribas `~/.ssh/config`. Fusioná manualmente el contenido de `config/macbook/ssh_config.template` con la configuración existente, conservando el alias `agent-fabric-mac-mini`; o guardá la plantilla como un archivo dedicado, por ejemplo `~/.ssh/config.d/agent-fabric.conf`, y agregá una sola directiva `Include ~/.ssh/config.d/*.conf` a tu configuración existente. Reemplazá `<MAC_MINI_LAN_OR_TAILSCALE_ENDPOINT>` por una dirección LAN alcanzable o el nombre/IP Tailscale real de la Mac mini, y verificá su fingerprint al primer contacto. No inventes un hostname para la Mac mini. La plantilla fuerza `BatchMode`, `IdentitiesOnly`, host key estricto, sin forwarding y sin PTY.

## Instalar runtime y autorizar el peer

El helper no usa `sudo`, no toca `authorized_keys`, SSH, SMB ni launch services. Desde el clon local del repositorio:

```sh
python3 automation/agent-fabric/bin/fabric-install-runtime --plan --role macbook --peer-public-key ~/Downloads/agent-fabric-mac-mini-to-macbook.pub
python3 automation/agent-fabric/bin/fabric-install-runtime --apply --role macbook --peer-public-key ~/Downloads/agent-fabric-mac-mini-to-macbook.pub
```

El JSON de salida contiene `authorized_keys_line`, construido exactamente por `ssh_policy.py`, con el runner y config bajo `~/.local/agent-fabric`. Revisalo y sólo entonces agregalo manualmente como una línea nueva:

```sh
mkdir -p ~/.ssh && chmod 700 ~/.ssh
# Pegá el valor exacto de authorized_keys_line; no lo edites ni uses una clave privada.
editor ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

## Validación y reversión local

```sh
python3 -m unittest discover -s automation/agent-fabric/test
ssh -o BatchMode=yes -o RequestTTY=no agent-fabric-mac-mini true
```

El segundo comando suministra intencionalmente un comando remoto (`true`): el comando forzado debe rechazarlo y nunca abrir una shell. La ruta de éxito es enviar por stdin una solicitud JSON válida mediante `fabric-dispatch`, con un prompt inocuo; eso valida el flujo completo. Confirmá que `/Users/leo/projects/leo/mac-agent-fabric` existe y que la actividad queda en `~/.local/state/agent-fabric/activity.jsonl`.

Para retirar sólo los archivos que instaló el helper en esta cuenta:

```sh
python3 automation/agent-fabric/bin/fabric-install-runtime --revert
```

La reversión no borra workspace, Keychain, claves, `authorized_keys`, configuración SSH, SMB ni Remote Login. Revertí esos cambios privilegiados manualmente y localmente después de inspeccionarlos.
