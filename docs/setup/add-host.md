# Agregar un equipo al canal Agent Fabric

Esta guía conecta un Mac nuevo al canal **Herdr + Pi** desde cualquier Mac ya registrado. El modelo es de hub: el host con rol `hub` comparte los proyectos y el Mac nuevo es un `spoke` que monta ese recurso. No cambia hosts por sí sola: cada paso indica quién puede ejecutarlo y dónde debe detenerse una persona.

## Resultado esperado y requisitos

Al terminar, el nuevo equipo figura en `config/hosts.json`, puede recibir y originar tareas mediante Herdr + Pi, y monta el catálogo compartido del hub.

| Requisito | Condición |
| --- | --- |
| Sistema y cuenta | macOS; la misma cuenta de usuario del canal existente o una cuenta elegida explícitamente para este host. |
| Red | Una ruta verificable por LAN o Tailscale entre ambos equipos. |
| Runtimes | **Pi y gentle-pi son obligatorios; Claude es opcional.** Herdr es obligatorio porque aloja la Pi. |
| Autenticación | Pi debe tener un proveedor de modelos funcional, autenticado desde la sesión GUI del nuevo Mac. Puede ser cualquier proveedor; `claude-bridge` es sólo una opción y necesita el llavero de esa sesión GUI. |
| Proyecto | El repositorio debe existir localmente en el hub y ser visible en el spoke mediante el montaje SMB. Las skills no se comparten por SMB. |

## 1. Elegir nombres antes de configurar

**Agente — en el Mac registrado que coordina el alta.** Elija un nombre de registro único, por ejemplo `studio-mac`, que cumpla `[a-z0-9-]`. Su alias será `fabric-studio-mac`. En el Mac nuevo, obtenga el prefijo de nombre de host que irá en el registro:

```sh
scutil --get LocalHostName || hostname
```

Anote también el usuario elegido, la dirección LAN o Tailscale y la ruta local que tendrá el repositorio en ese Mac. No copie rutas de otro host.

**Verificación:** el nombre de registro, `fabric-<name>`, usuario, dirección y `hostname_prefix` están decididos y no contradicen una entrada existente de `config/hosts.json`.

## 2. Preparar el Mac nuevo y la sesión gráfica

**Persona — en el Mac nuevo.** Active **System Settings → General → Sharing → Remote Login** para la cuenta elegida. Instale Homebrew, Node, Pi, gentle-pi y Herdr siguiendo sus instaladores/documentación aprobados localmente. Con Pi ya instalado, instale gentle-pi:

```sh
pi install npm:gentle-pi
```

Abra Pi **en la sesión GUI** y complete el login del proveedor que use; haga una consulta inocua y confirme que responde. Abra Herdr en esa misma sesión GUI.

**STOP:** contraseñas, login de proveedor, aprobaciones del sistema, instalación de software o acceso al llavero requieren a la persona. No los introduzca ni los automatice por SSH.

**Cómo verificar:** Remote Login muestra la cuenta autorizada; `pi --version` funciona en la cuenta elegida; una consulta GUI de Pi recibe respuesta; Herdr está abierto en esa sesión.

**Cómo reanudar:** tras completar o aprobar cada intervención, vuelva a ejecutar sólo la comprobación correspondiente y continúe con el paso 3. Si Pi dice `Not logged in`, vuelva a la sesión GUI, no al SSH.

## 3. Crear los dos canales SSH

Configure un canal **en cada dirección**: `host registrado → nuevo` y `nuevo → host registrado` (normalmente, el hub). Puede reutilizar una clave que ya funcione para un alias; para una dirección nueva use una clave dedicada. El procedimiento completo por dirección está en el [runbook del canal SSH](../runbooks/agent-fabric/ssh-channel.md).

### 3.1 Clave, huella y autorización

**Agente — en el origen de cada dirección, después de autorización.** Cree una clave ed25519 dedicada sin sobrescribir una existente. Para el destino `studio-mac`:

```sh
if [ -e ~/.ssh/agent_fabric_studio_mac ] || [ -e ~/.ssh/agent_fabric_studio_mac.pub ]; then
  echo 'La clave ya existe; no se modifica.' >&2
else
  ssh-keygen -t ed25519 -f ~/.ssh/agent_fabric_studio_mac -N '' -C agent-fabric-to-studio-mac
fi
```

**Persona — delante de la pantalla local del destino.** Lea la huella del host **localmente en el destino**; puede comunicarla por un canal ya confiable:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

**STOP:** no acepte una clave de host ni autorice una clave pública hasta que la persona compare la huella local con el escaneo del origen.

**Cómo verificar:** en el origen, ejecute y compare visualmente ambos resultados:

```sh
ssh-keyscan -t ed25519 <host> | ssh-keygen -lf -
```

Deben coincidir exactamente en tipo y huella.

**Cómo reanudar:** sólo con coincidencia, el agente añade esa clave escaneada a `~/.ssh/known_hosts`; con diferencia, cancele el alta, investigue la red/nombre en el destino y repita la lectura local. Nunca use `StrictHostKeyChecking=no`.

**Agente — en el destino, con aprobación ya dada.** Haga una copia de seguridad de `~/.ssh/authorized_keys` y agregue la clave pública del origen, sin reemplazar las líneas existentes. La línea agregada debe comenzar exactamente así, seguida de la clave pública original en una sola línea:

```text
no-agent-forwarding,no-port-forwarding,no-X11-forwarding
```

**Verificación:** la copia de seguridad existe, la clave pública aparece una sola vez con esas restricciones y los permisos de SSH siguen siendo aceptados por macOS.

### 3.2 Alias del origen

**Agente — en el origen.** Añada al `~/.ssh/config` local un bloque por destino (sustituya los marcadores):

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

Si se reutiliza una clave que ya funciona, conserve su `IdentityFile` y cree sólo el alias con los demás controles. Repita 3.1 y 3.2 en sentido inverso, con otra clave dedicada si no hay una reutilizable.

**Verificación:** desde cada origen, `ssh fabric-<target> hostname` devuelve el nombre del destino sin prompt de contraseña ni aceptación interactiva de huella.

## 4. Montar el catálogo del hub en el spoke

**Persona — en la sesión GUI del spoke.** Conéctese primero desde Finder a `smb://<share.host>/<share.name>`, autentíquese como `<share.user>` y marque **«Recordar contraseña en el llavero»**. Los tres valores se leen de `share` en `config/hosts.json` del hub.

**STOP:** la contraseña SMB y el acceso al llavero son exclusivamente humanos y GUI.

**Cómo verificar:** Finder muestra el recurso esperado y la carpeta del repositorio bajo `/Volumes/<share.name>`.

**Cómo reanudar:** si la conexión falla, confirme la publicación del recurso y las credenciales en Finder; no ponga contraseñas en comandos ni archivos. Cuando Finder funcione, continúe.

**Agente — en el spoke, después de la conexión GUI.** Instale el montaje persistente con los valores exactos del registro:

```sh
python3 <repo>/automation/agent-fabric/bin/fabric-smb-mount mount \
  --host <share.host> --share <share.name> --user <share.user> --persistent
```

**Verificación:** la salida JSON indica `mounted: true`; el repo se ve en la raíz `catalog_root` que se registrará. El montaje persistente permite recuperarlo después de iniciar sesión; sigue dependiendo del llavero de la sesión GUI.

## 5. Registrar el equipo en el hub

**Agente — en el clon del repositorio del hub.** Añada el nuevo host a `config/hosts.json`; no cambie la sección `share` al agregar un spoke. Complete todos los campos:

| Campo | Significado |
| --- | --- |
| `hostname_prefix` | Prefijo de `LocalHostName`/`hostname` usado para identificar el host. |
| `role` | `hub` para quien publica proyectos; `spoke` para quien los monta. El nuevo Mac de este flujo es `spoke`. |
| `ssh_alias` | Alias local del destino: `fabric-<name>`. |
| `catalog_root` | Raíz local del catálogo: en un spoke, normalmente el punto SMB `/Volumes/<share.name>`. |
| `repo` | Ruta local de este repositorio en ese host, bajo `catalog_root` en un spoke. |
| `path` | PATH saneado que permite localizar Python, Pi y Herdr al ejecutar remotamente. |
| `gui_cwd` | Directorio de trabajo existente y permitido para la tab GUI que crea Herdr. |
| `runtimes` | Runtimes declarados: incluya `pi`; `claude` sólo si se ofrece opcionalmente. |

Ejemplo ficticio de spoke (adapte rutas, usuario y PATH):

```json
"studio-mac": {
  "hostname_prefix": "StudioMac",
  "role": "spoke",
  "ssh_alias": "fabric-studio-mac",
  "catalog_root": "/Volumes/agent-projects",
  "repo": "/Volumes/agent-projects/leo/mac-agent-fabric",
  "path": "/opt/homebrew/bin:/usr/bin:/bin",
  "gui_cwd": "/Users/leo/tmp",
  "runtimes": ["pi"]
}
```

Valide antes de cerrar el cambio:

```sh
automation/agent-fabric/bin/fabric-delegate list
```

Después, haga el commit del registro **en el hub** según el flujo de Git aprobado. El spoke verá esa versión mediante SMB.

**Verificación:** `list` incluye el nuevo nombre, alias y rol esperados; el commit queda disponible para los hosts que consumen el catálogo compartido.

## 6. Instalar skill y bootstrap en cada host

**Agente — en el hub.** Cree un enlace simbólico desde `~/.pi/agent/skills/agent-fabric-remote` al directorio `skills/agent-fabric-remote` del repositorio local. Opcionalmente, cree el enlace equivalente en `~/.claude/skills/`.

**Agente — en cada spoke.** Copie `skills/agent-fabric-remote` al directorio local `~/.pi/agent/skills/agent-fabric-remote`; opcionalmente también a `~/.claude/skills/`. Las skills **no** se comparten por SMB: recópielas después de cada cambio de la skill. Conserve copias antiguas fuera de directorios de skills para que no sean cargadas.

**Agente — en cada host, con la ruta `repo` de ese host.** Instale una vez el contenido de `skills/agent-fabric-remote/assets/bootstrap-block.md` en `~/.pi/agent/AGENTS.md`, reemplazando `<REPO_PATH>` por el valor local de `repo`. Opcionalmente repita en `~/.claude/CLAUDE.md`. Si ya existen los marcadores `BEGIN/END AGENT-FABRIC-REMOTE-BOOTSTRAP`, reemplace sólo el bloque entre ellos; nunca lo duplique.

**Verificación:** una búsqueda de los marcadores devuelve exactamente un bloque por archivo de bootstrap, su ruta de repositorio es local a ese host y sólo existe una instalación activa de la skill por runtime.

## 7. Aceptación bidireccional

**Agente — desde el hub.** Ejecute:

```sh
automation/agent-fabric/bin/fabric-delegate preflight <new>
```

**Agente — desde el Mac nuevo.** Ejecute contra el hub:

```sh
<repo>/automation/agent-fabric/bin/fabric-delegate preflight <hub>
```

**Verificación:** ambos preflight identifican un host registrado, alcanzable y con catálogo disponible. Si aparece `catalog_missing`, vuelva al paso 4.

**Persona — en ambos Macs.** Abra una Pi nueva en cada lado y asegúrese de que las pestañas existentes quedan registradas como línea base.

**STOP:** abrir Herdr/Pi en la sesión GUI, aprobar permisos del proveedor y observar pestañas son acciones humanas; no cierre pestañas ajenas.

**Cómo verificar:** en una Pi nueva de cada lado, pida en lenguaje natural: `Pedile a la Pi de <name> que responda exactamente ACCEPT_<hex> y nada más`. El resultado debe contener exactamente el token solicitado. Después compruebe que las pestañas del destino volvieron a la línea base.

**Cómo reanudar:** si falta login, vuelva al paso 2; si falla preflight, vuelva a los pasos 3–5; si hay una tarea ambigua, use `recover` con el mismo `task_id`, no envíe un token nuevo ni cierre recursos ajenos.

## Reversión

**Agente — con autorización del propietario de cada host.** Retire, en orden y sólo los artefactos de este alta: la entrada del registro y su commit en el hub; los bloques de alias SSH; las líneas añadidas a `authorized_keys` (restaure la copia de seguridad si sólo contiene este cambio); las claves dedicadas; y en el spoke:

```sh
python3 <repo>/automation/agent-fabric/bin/fabric-smb-mount unmount \
  --host <share.host> --share <share.name> --user <share.user> --remove-persistent
```

Retire la skill instalada o enlace y el bloque bootstrap marcado, sin tocar otras skills ni bloques. Una persona confirma antes de eliminar un artefacto compartido o una copia de seguridad que pudiera contener cambios ajenos.

## Problemas frecuentes

| Síntoma | Acción segura |
| --- | --- |
| `unreachable` (salida 3) | El otro Mac está apagado o no es alcanzable. Compruebe red, energía, Remote Login y alias; recupere después, no cree una tarea nueva ante ambigüedad. |
| `catalog_missing` | En un spoke falta el montaje o no contiene el catálogo. Vuelva a Finder y al paso 4; use `--persistent`. |
| `UNSUPPORTED_HOST` | El nombre no está en el registro que usa el comando. Revise y publique `config/hosts.json`; no invente rutas ni aliases. |
| Límite de nombre de agente Herdr | El adaptador ya adapta los nombres a los límites de Herdr; use el nombre de registro normal. |
| `Not logged in` | El proveedor de Pi sólo quedó autenticado fuera de la sesión GUI o no está autenticado. Inicie sesión desde la GUI; `claude-bridge` necesita su Keychain GUI. |
| El montaje se pierde | Confirme el llavero desde Finder y vuelva a montar con `--persistent`. |

## Referencias

- [Canal SSH bidireccional](../runbooks/agent-fabric/ssh-channel.md)
- [Montaje SMB entre equipos](../runbooks/agent-fabric/smb-mount.md)
- [Tareas Pi mediante Herdr](../runbooks/agent-fabric/herdr-tasks.md)
