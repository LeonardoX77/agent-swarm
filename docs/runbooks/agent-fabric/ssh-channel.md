# Canal SSH bidireccional entre hosts registrados

Este runbook configura **una dirección** del canal Agent Fabric: un host de origen se conecta a un host destino con un alias `fabric-<target>`. Repítalo para la dirección inversa. La clave dedicada no lleva frase de paso para que un agente pueda usarla sin atención humana; las restricciones de `authorized_keys` reducen reenvíos, pero **siguen permitiendo una shell** y no son un sandbox.

Use nombres y valores del registro `config/hosts.json`; no copie nombres de hosts, usuarios ni rutas de este documento.

## Plantilla por dirección

| Marcador | Valor que debe usarse |
| --- | --- |
| `<origin>` | Nombre del host que inicia SSH. |
| `<target>` | Nombre de registro del host destino (`[a-z0-9-]`). |
| `<host>` | Dirección LAN/Tailscale o nombre confirmado del destino. |
| `<user>` | Cuenta autorizada en el destino. |
| `<key>` | `~/.ssh/agent_fabric_<target>` en el origen. |

### 1. Activar acceso en el destino

**Persona — en la GUI del destino.** Active **Remote Login** para la cuenta `<user>` y confirme la red LAN o Tailscale.

**STOP:** el login de macOS, contraseña, firewall, Tailscale y aprobaciones de Sharing requieren intervención humana.

**Cómo verificar:** Remote Login muestra a `<user>` entre las cuentas autorizadas y el destino tiene la dirección `<host>` confirmada.

**Cómo reanudar:** tras la aprobación, repita esa comprobación local; no intente abrir SSH con una contraseña enviada por el agente.

### 2. Crear o reutilizar una clave en el origen

**Agente — en `<origin>`, con autorización.** Puede reutilizar una clave ya funcional para un alias; si no existe, cree una clave dedicada. Nunca sobrescriba una clave existente:

```sh
if [ -e ~/.ssh/agent_fabric_<target> ] || [ -e ~/.ssh/agent_fabric_<target>.pub ]; then
  echo 'La clave ya existe; no se modifica.' >&2
else
  ssh-keygen -t ed25519 -f ~/.ssh/agent_fabric_<target> -N '' -C agent-fabric-<origin>-to-<target>
fi
```

**Verificación:** existen ambos archivos de la clave nueva, o se documentó la clave previamente funcional que se reutiliza.

### 3. Verificar la huella de host antes de confiar

**Persona — delante de la pantalla local de `<target>`.** Lea la huella directamente en el destino y comuníquela por la pantalla o por un canal ya confiable:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

**STOP:** no agregue `known_hosts` ni acepte una conexión SSH hasta comparar esta lectura local con el escaneo del origen.

**Agente — en `<origin>`.** Obtenga la huella observada desde la red:

```sh
ssh-keyscan -t ed25519 <host> | ssh-keygen -lf -
```

**Cómo verificar:** tipo de clave y huella coinciden exactamente con la lectura local del destino.

**Cómo reanudar:** sólo ante coincidencia, agregue la clave escaneada a `~/.ssh/known_hosts`. Ante diferencia, detenga la configuración, verifique `<host>` localmente y repita ambas lecturas. Nunca desactive `StrictHostKeyChecking`.

### 4. Autorizar la clave pública en el destino

**Agente — en `<target>`, después de la autorización humana.** Haga una copia de seguridad de `~/.ssh/authorized_keys` y añada, sin sobrescribir líneas existentes, la clave pública del origen. La entrada debe ser una sola línea: el prefijo exacto y después la clave pública original.

```text
no-agent-forwarding,no-port-forwarding,no-X11-forwarding
```

**Verificación:** la copia de seguridad existe, la entrada aparece una sola vez, conserva toda la clave pública y las demás entradas permanecen intactas.

### 5. Crear el alias en el origen

**Agente — en `<origin>`.** Añada a `~/.ssh/config`:

```sshconfig
Host fabric-<target>
  HostName <host>
  User <user>
  IdentityFile ~/.ssh/agent_fabric_<target>
  IdentitiesOnly yes
  BatchMode yes
  StrictHostKeyChecking yes
  ConnectTimeout 15
  ServerAliveInterval 15
  ServerAliveCountMax 4
  ForwardAgent no
```

Al reutilizar una clave existente, conserve su `IdentityFile`; el resto de controles sigue siendo obligatorio.

**Verificación:** desde `<origin>`, ejecute:

```sh
ssh fabric-<target> hostname
```

Debe devolver el nombre del destino sin solicitar contraseña ni confirmar una huella. Repita los pasos 1–5 con origen y destino intercambiados para obtener comunicación en ambos sentidos.

## Uso con Agent Fabric

Una vez que ambas direcciones responden, confirme el registro y el catálogo con `fabric-delegate preflight <target>`. Si el destino es un spoke y informa `catalog_missing`, configure su montaje SMB antes de enviar tareas. Consulte [Agregar un equipo al canal Agent Fabric](../../setup/add-host.md) para el proceso completo y [Montaje SMB entre equipos](smb-mount.md) para el montaje persistente.

## Reversión por dirección

**Agente — con autorización.** Quite el bloque `Host fabric-<target>` del origen, la entrada que se añadió a `authorized_keys` en el destino (o restaure la copia de seguridad si sólo contiene este cambio), y el par de clave dedicada `agent_fabric_<target>` del origen. No elimine una clave reutilizada ni una copia de seguridad con cambios ajenos.

## Comprobación final

En cada dirección, compruebe que `ssh fabric-<target> hostname` funciona sin contraseña y que el alias coincide con el host definido en `config/hosts.json`. Desde un host registrado, `fabric-delegate preflight <target>` debe devolver `"status": "ready"` después de montar el catálogo en un `spoke`. Una conexión SSH exitosa por sí sola no demuestra que Pi, Herdr y la aceptación bidireccional funcionen: complete las fases de `fabric-setup` y consulte su estado.
