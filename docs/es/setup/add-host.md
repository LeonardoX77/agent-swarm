# Agregar un equipo al canal Agent Swarm

El camino canónico para incorporar un equipo macOS o Linux/WSL es ejecutar **un único comando** desde un nodo ya registrado. `swarm-setup` coordina las diez fases, se detiene ante acciones humanas y conserva el estado para reanudar la misma operación. Linux/WSL ejecuta las mismas diez fases, con CIFS y timers systemd de usuario; se ha probado una delegación real hacia este WSL, pero no la aceptación bidireccional entre dos máquinas (véase la evidencia enlazada abajo).

## Camino rápido

### Requisitos

- El nodo de origen (macOS o Linux/WSL) ya está registrado en `config/hosts.json` y se ejecuta el comando desde su checkout del repositorio. Ese archivo es local y no se versiona: si no existe, copie `config/hosts.example.json` y sustituya los valores de ejemplo por los reales.
- Para el camino macOS siguiente, el equipo nuevo usa macOS y la persona puede sentarse delante de él para algunos pasos GUI. Para Linux/WSL, siga [la preparación](#linuxwsl-preparación).
- **Pi y gentle-pi son obligatorios; Claude es opcional; Herdr es obligatorio.**
- Hay conectividad LAN o Tailscale hacia `<host>.local` y se conoce la cuenta `<user>` del Mac nuevo.

Desde el Mac registrado, ejecute:

```sh
automation/agent-swarm/bin/swarm-setup add-host \
  --name <name> --address <host>.local --user <user> \
  [--host-fingerprint SHA256:...] [--install-missing] \
  [--update-time 04:30 | --no-auto-update] [--verbose]
```

El valor predeterminado instala la actualización diaria a las `04:30`; use `--no-auto-update` si no quiere activar ese calendario. Esto no instala una comprobación de actualizaciones en el primer uso remoto: es una función distinta. Agent Swarm no gestiona ni garantiza los avisos de paquetes que pueda mostrar Pi al iniciarse. `--install-missing` usa las herramientas existentes e intenta añadir sólo Herdr, gentle-pi y la integración oficial de Herdr para Pi cuando sus CLI base están disponibles; no reinstala todo el Mac.

### Candidatos de dirección y ejemplo WSL

`--address` es el primer candidato de dirección SSH. Añada `--fallback-address ADDR` repetidamente, en orden de preferencia, para candidatos posteriores. `--origin-address ADDR` también es repetible, pero se aplica sólo en la dirección inversa: sustituye la dirección del registro del origen y cualquier `fallback_addresses` para ese alias inverso. Para un `spoke`, `--share-host HOST` puede repetirse para establecer hosts SMB ordenados; se rechaza en un `hub`.

Cada dirección o host de recurso debe comenzar por un carácter alfanumérico y contener después sólo letras, dígitos, puntos o guiones. Se rechazan los valores duplicados de fallback, origen o share-host; la dirección principal de `--address` tampoco puede ser un fallback.

Para un nodo WSL, priorice su nombre MagicDNS de Tailscale y use su dirección LAN en segundo lugar. Por ejemplo:

```sh
automation/agent-swarm/bin/swarm-setup add-host \
  --name wsl-leo --user <user> \
  --address 5cg6031yzw.tail3eebf8.ts.net \
  --fallback-address 192.168.0.21 --ssh-port 2222 \
  --origin-address macbookleo.tail3eebf8.ts.net \
  --origin-address 192.168.0.10 \
  --share-host macbookleo.tail3eebf8.ts.net \
  --share-host 192.168.0.10
```

Tailscale ya usa la LAN directamente cuando puede, de modo que el candidato LAN cubre sobre todo que Tailscale esté caído. Las herramientas de enrutamiento también pueden capturar peers de Tailscale; por ejemplo, una ruta de Twingate para `100.96.0.0/12` captura parte del rango `100.64.0.0/10` de Tailscale y puede romper esa ruta. El fallback LAN cubre ese caso. En Windows/WSL, un perfil Wi-Fi puede ser Público, por lo que una regla de firewall limitada al rango LAN también se aplica en redes públicas que usan ese rango. El proceso muestra un resumen breve en inglés; por ejemplo:

```text
[ 1/10] local-preflight OK       origin preflight passed
...
[10/10] acceptance      OK       bidirectional acceptance passed
Summary: setup complete; changed phases: ssh-to-new, registry, skill, auto-update
```

Al completar con éxito termina con salida `0`. Revise la entrada que el setup añadió a `config/hosts.json`. Ese archivo está ignorado por Git: no se comitea; si necesita compartir su estructura, actualice `config/hosts.example.json` con valores genéricos. No copie manualmente valores de `share`: el script los lee del registro.

> Si se interrumpe o espera a una persona, ejecute **el mismo comando con las mismas opciones** otra vez desde el origen. Comprueba de nuevo cada fase y conserva lo ya configurado; no genere otra huella ni acepte una distinta sin verificarla localmente.

## Requisitos de runtime (macOS y Linux)

La integración oficial de Herdr para Pi es obligatoria, no basta con gentle-pi. Compruébela con `herdr integration status` (`pi: not installed` no está listo), o instálela con `herdr integration install pi`. Instala `~/.pi/agent/extensions/herdr-agent-state.ts`. El adaptador prueba la propiedad mediante `agent_session` (tipo `path`, origen `herdr:pi`); sin esa integración, `submit` puede devolver `unknown` sin entregar el prompt. `--install-missing` la instala cuando herdr está disponible e informa `installed herdr pi integration`; el modo dry-run sólo informa de la instalación prevista.

En Linux sin interfaz gráfica, inicie el servidor ejecutando `herdr` en una terminal normal y desacoplando después el cliente, o use una pty con una cuadrícula de filas y columnas distinta de cero. Herdr 0.9.5 rechaza una terminal de tamaño cero con `cannot attach without a usable terminal: terminal reported a zero-sized grid`. El servidor sobrevive a la salida del cliente. En esa versión no existe el comando `herdr server start` (`server` sólo ofrece `stop` y `reload-config`). Compruebe la disponibilidad con `herdr tab list`; `server_not_running` significa que el servidor aún debe iniciarse. El setup nunca lo inicia ni lo reinicia automáticamente.

Tanto setup como swarm-update detectan `$HOME/.pi/agent/bin` (el instalador propio de Pi) inmediatamente después de `$HOME/.local/bin`, y conservan los directorios existentes de Homebrew, nvm, Hermes y del sistema, así como su orden. No se necesita un perfil de shell interactivo.

## Linux/WSL: preparación

Active SSH y prepare Node, Python 3 y Pi en el destino, con login de Pi local y el servidor Herdr disponible (`herdr tab list`). Homebrew no es requisito. Con `--install-missing`, el setup puede instalar Herdr mediante el instalador oficial de https://herdr.dev/install.sh (lo descarga a un archivo temporal con `curl -fsSL`, lo ejecuta solo si la descarga tuvo éxito y borra el archivo; requiere curl), y gentle-pi mediante `pi install npm:gentle-pi` si existe Pi; no instala Node, Python ni Pi.

En WSL, Windows OpenSSH suele ocupar el puerto 22: si el `sshd` de WSL escucha, por ejemplo, en `127.0.0.1:2222`, use `--address 127.0.0.1 --ssh-port 2222` desde un origen que pueda alcanzar esa dirección. Use `--origin-ssh-port 2222` si el destino debe volver al origen por ese puerto. Ambos valores predeterminados son 22. El alias de SSH config lleva el puerto (`Port` sólo si no es 22); el esquema del registro no cambia. Reanude con los mismos puertos: cambiarlos provoca un error de conflicto de alias, nunca una sobrescritura silenciosa.

Para un spoke, prepare el acceso CIFS siguiendo [Montaje SMB](../runbooks/agent-swarm/smb-mount.md#linuxwsl-preparación): `swarm-smb-mount fstab-line --host H --share S --user U` imprime la línea exacta y la plantilla de credenciales. En Linux, repita `--host` en orden de preferencia al usar candidatos SMB; `fstab-line` devuelve `fstab_lines`, una línea fstab por host. La elección de fallback ocurre sólo al montar: un recurso ya montado no cambia de host en vivo, así que vuelva a montarlo para cambiarlo. El estado informa del candidato activo. La selección de una entrada fstab por origen (`mount //HOST/SHARE`) cuando varias entradas usan el mismo punto de montaje aún no se ha verificado en Linux real. Una persona añade la línea a `/etc/fstab` como root, crea `/mnt/<share>` y crea `~/.config/agent-swarm/smb-credentials` con modo `0600`. La herramienta nunca usa sudo ni maneja contraseñas. El setup ejecuta el montaje y activa un timer de usuario cada 300 s; si `systemctl --user` no está disponible, el montaje puede funcionar pero la persistencia se degrada con una advertencia.

El catálogo del spoke es `/mnt/<share>` (macOS: `/Volumes/<share>`). El registro conserva la ruta del proyecto relativa al catálogo del origen: por ejemplo, `/srv/projects/agent-swarm` bajo `/srv/projects` pasa a `/mnt/shared-projects/agent-swarm`. El registro usa `gui_cwd` = `$HOME/tmp` del destino y crea ese directorio; los prefijos de hostname se comparan sin distinguir mayúsculas. `swarm-delegate` prefiere `/usr/bin/python3` y, si no es ejecutable, resuelve `python3` en el `PATH` del registro.

La fase de actualización instala `agent-swarm-update.timer` de systemd de usuario a las 04:30 salvo `--no-auto-update`; a diferencia de la persistencia SMB, falla si el gestor de usuario no está disponible. Los logs de actualización Linux están en `~/.local/state/agent-swarm/logs`. Los servicios de montaje SMB escriben allí salvo que la ruta del HOME no se pueda expresar en una directiva de systemd; en ese caso usan el journal de usuario (`journalctl --user -u <label>.service`).

En WSL, habilite systemd en `/etc/wsl.conf`:

```ini
[boot]
systemd=true
```

Los timers de usuario sólo funcionan mientras haya una sesión del usuario, salvo que se habilite `loginctl enable-linger $USER`. Un hub Linux debe publicar manualmente su catálogo con un servidor SMB propio, por ejemplo Samba; el setup no configura el servidor. Windows puede ocupar TCP 445 en loopback: una prueba SMB local necesita otro puerto. Consulte [la evidencia y los límites](../runbooks/agent-swarm/test-evidence.md#evidencia-linuxwsl).

## Las diez fases

Los nombres de fase siguientes son los que imprime el programa exactamente. Ambas plataformas ejecutan las diez fases; `mount` se omite para un hub y `auto-update` sólo se omite con `--no-auto-update`.

| Fase | Qué hace el script | Quién actúa | Si se detiene, texto exacto que muestra |
| --- | --- | --- | --- |
| `local-preflight` | Valida nombre, dirección, herramientas SSH y que el origen sea el `self_host` del registro. | Agente | No espera a una persona. |
| `remote-login` | Comprueba que el puerto SSH del equipo nuevo sea alcanzable. | Persona | `On <name>: enable macOS Remote Login or a running sshd on Linux for user <user>` |
| `ssh-to-new` | Crea o reutiliza la clave origen→nuevo, verifica la huella, configura `known_hosts`, autoriza la clave y crea `swarm-<name>`. | Persona y agente | Huella en TTY: `Type the fingerprint shown on <name> (or yes): `; clave: `On <name> run this exact command, then continue:` seguido del comando de autorización. |
| `runtimes` | Comprueba Node, Python, Herdr, Pi, gentle-pi, la integración Herdr Pi, el servidor Herdr y, sólo en macOS, Homebrew; `--install-missing` puede añadir Herdr, gentle-pi y la integración. | Persona | macOS conserva `On <name>: install missing runtimes and log Pi in once from the GUI` y añade `; missing probes: <nombres>`; Linux usa `locally` en vez de `from the GUI` y añade instrucciones de arranque si falta `herdr-server`.  |
| `ssh-to-origin` | Configura el canal SSH inverso nuevo→origen, incluida la huella del origen y el alias remoto. | Agente | No espera a una persona. Un conflicto de huella o alias falla de forma segura. |
| `mount` | En un `spoke`, copia la utilidad de montaje e instala el montaje SMB persistente usando `share` del registro. | Persona | macOS: `On <name>, connect in Finder to smb://<share.user>@<share.host>/<share.name> and save the password`; Linux: instrucciones fstab y credenciales generadas para el destino. |
| `registry` | Descubre datos del nuevo host y escribe su entrada en `config/hosts.json`. | Agente | No espera a una persona. |
| `skill` | Copia la skill `agent-swarm-remote` y su bloque bootstrap al equipo nuevo. | Agente | No espera a una persona. |
| `auto-update` | Instala `swarm-update` y su LaunchAgent (macOS) o timer systemd de usuario (Linux), salvo `--no-auto-update`. | Agente | No espera a una persona. |
| `acceptance` | Ejecuta preflight en ambos sentidos y pruebas de aceptación Herdr + Pi. | Persona y agente | Si Pi no tiene sesión: `Log Pi in from the GUI on <target>` |

`<name>`, `<user>`, `<share.user>`, `<share.host>`, `<share.name>` y `<target>` son valores concretos sustituidos por el script.

## Intervenciones de la persona

El proceso comprueba las condiciones cada **5 segundos**, hasta `--wait-timeout` minutos (30 por defecto). Tras la intervención no hay que pulsar nada: el proceso continúa al detectar la condición. Si vence el tiempo, o se usó `--no-wait`, termina con una pista para reanudar; vuelva a ejecutar el mismo comando para continuar. **`--no-wait` evita sondear de nuevo una condición que acaba de fallar**: aunque la persona ya haya intervenido, una fase puede terminar en `WAITING` sin comprobar por segunda vez la condición. Para reanudar, omita esa opción o use `--wait-timeout 0` para comprobar la condición una vez y salir sin espera prolongada.

### Remote Login

**El script muestra:** `On <name>: enable macOS Remote Login or a running sshd on Linux for user <user>`.

**La persona hace:** en el Mac nuevo abre **System Settings → General → Sharing → Remote Login**, lo activa y autoriza a `<user>`. En Linux, prepara un `sshd` en ejecución para esa cuenta. También confirma que la red elegida es la correcta.

**Continúa cuando:** el puerto elegido con `--ssh-port` (22 por defecto) responde desde el origen.

### Huella del host

**El script muestra:** en una terminal con TTY, `Type the fingerprint shown on <name> (or yes): `. Sin TTY no puede pedir confirmación y termina esperando, indicando `Re-run with --host-fingerprint SHA256:...`.

**La persona hace:** en el Mac nuevo lee la huella local:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Compárela con la huella observada desde el origen. Puede pasar el valor ya verificado sin interacción con `--host-fingerprint SHA256:...`; en una TTY también puede escribir esa huella exacta o `yes` después de verificarla localmente. Nunca desactive `StrictHostKeyChecking`.

**Continúa cuando:** la huella entregada coincide con el escaneo SSH.

### Autorizar la clave del origen

**El script muestra:** un comando de una línea que contiene la clave pública del origen con el prefijo `no-agent-forwarding,no-port-forwarding,no-X11-forwarding `.

**La persona hace:** revisa y ejecuta exactamente ese comando en el Mac nuevo; crea `~/.ssh` con modo `700`, añade la línea restringida sólo si falta y deja `authorized_keys` con modo `600`.

**Continúa cuando:** la conexión por clave desde el origen funciona; el script la sondea automáticamente.

### Runtimes y login GUI

**El script muestra:** en macOS, `On <name>: install missing runtimes and log Pi in once from the GUI; missing probes: <nombres>`. En Linux, indica login local y cómo arrancar Herdr si falta el servidor. Los nombres de probes son `herdr`, `node`, `pi`, `python3`, `gentle-pi`, `herdr-server`, `herdr-pi-integration` y, sólo en macOS, `brew`.

**La persona hace:** instala Node, Python 3, Pi, gentle-pi y Herdr si faltan (Homebrew sólo en macOS); abre Herdr y abre Pi en la sesión GUI para completar el login del proveedor. Claude no es requisito. Con `--install-missing`, el script intenta `brew install herdr` en macOS si Homebrew responde, el instalador oficial de Herdr en Linux si curl responde y `pi install npm:gentle-pi` si Pi responde: no instala Homebrew, Node ni Pi.

**Continúa cuando:** las comprobaciones remotas encuentran `node`, `python3`, `herdr`, `pi`, gentle-pi (y `brew` sólo en macOS), `herdr integration status` confirma la integración Pi, y `herdr tab list` funciona.

> Para SSH no interactivo, el script descubre directorios de herramientas habituales, incluido el `default` de `nvm` (o la versión Node instalada más alta), y usa ese `PATH` para las comprobaciones y herramientas posteriores.

### Primer montaje SMB y Keychain (macOS)

En Linux, siga la preparación CIFS anterior y ejecute el comando de montaje que imprime el setup; la espera continúa cuando detecta el montaje.

**El script muestra:** `On <name>, connect in Finder to smb://<share.user>@<share.host>/<share.name> and save the password`.

**La persona hace:** en la GUI del Mac nuevo abre Finder, se conecta a esa URL SMB, se autentica y guarda la contraseña en Keychain. La contraseña no se escribe en comandos, archivos ni logs.

**Continúa cuando:** el montaje está disponible y el catálogo se ve en `/Volumes/<share.name>`. Compruebe el recurso y el usuario en `config/hosts.json` (`share.host`, `share.name`, `share.user`); no sustituya una ruta o contraseña particular en la guía.

### Login de Pi durante la aceptación

**El script muestra:** `Log Pi in from the GUI on <target>` cuando la aceptación recibe `Not logged in`.

**La persona hace:** abre Pi en la GUI del host indicado, inicia sesión con el proveedor y confirma una consulta inocua.

**Continúa cuando:** vuelva a ejecutarse el mismo comando después del login. La condición de esa espera no se puede sondear automáticamente; la reanudación ejecuta otra vez la aceptación.

## Opciones, estado y diagnóstico

| Opción | Uso |
| --- | --- |
| `--name`, `--address`, `--user` | Obligatorios: nombre de registro, dirección y cuenta del nuevo equipo. |
| `--role {hub,spoke}` | Rol del nuevo host; el predeterminado es `spoke`. |
| `--host-fingerprint SHA256:...` | Huella previamente verificada; evita la pregunta de TTY. |
| `--origin-user USER` | Cuenta que usará el canal inverso hacia el origen. |
| `--ssh-port PORT` | Puerto del sshd del destino; entero de 1 a 65535, predeterminado 22. |
| `--origin-ssh-port PORT` | Puerto del sshd del origen al que se conecta el destino; entero de 1 a 65535, predeterminado 22. |
| `--fallback-address ADDR` | Candidato SSH repetible después de `--address`, en orden. |
| `--origin-address ADDR` | Candidato SSH repetible para el alias inverso; sustituye los candidatos del registro del origen sólo para ese alias. |
| `--share-host HOST` | Host SMB ordenado y repetible para un `spoke`; se rechaza para un `hub`. |
| `--install-missing` | Herdr: Homebrew en macOS o instalador oficial vía curl en Linux; gentle-pi: mediante Pi; integración Pi: `herdr integration install pi`, en ambas plataformas. |
| `--auto-update` / `--no-auto-update` | Activa (predeterminado) u omite el calendario diario: launchd en macOS, systemd de usuario en Linux. |
| `--update-time HH:MM` | Hora diaria en ambas plataformas; el predeterminado es `04:30`. |
| `--skip-live` | Omite las pruebas de tareas vivas de aceptación, pero conserva los preflight. |
| `--dry-run` | No escribe estado ni configuración; informa qué fases cambiarían y devuelve `4` si habría cambios. |
| `--no-wait` | No espera intervención humana: guarda la fase como pendiente y devuelve `10`. |
| `--wait-timeout MINUTOS` | Límite de espera; de 0 a 1440, predeterminado 30. |
| `--verbose` | Añade comandos, códigos de salida y salida recortada al diagnóstico. |
| `--registry RUTA` | Usa un registro alternativo. |

Códigos de salida: `0` completado o ya configurado; `1` error de setup o error inesperado; `2` entrada inválida o ejecución como root; `4` `--dry-run` detectó cambios; `10` espera una acción humana o venció la espera.

Consulte el estado persistido con:

```sh
automation/agent-swarm/bin/swarm-setup status --name <name>
```

El estado está en `~/.local/state/agent-swarm/setup/<name>.json`. El log está en `~/Library/Logs/mac-agent-swarm/swarm-setup-<name>.log` para un origen macOS y en `~/.local/state/agent-swarm/logs/swarm-setup-<name>.log` para un origen Linux/WSL. Ante un error inesperado, consulte ese log y, si hace falta, reanude con `--verbose` y las mismas opciones; comparta sólo diagnóstico saneado, pues los logs pueden incluir claves **públicas**, rutas y nombres de usuario. La salida normal es resumida en inglés; `--verbose` registra cada comando, código de salida y salida recortada. Si el setup termina con salida `0`, confirme además `automation/agent-swarm/bin/swarm-delegate preflight <name>`: debe devolver `"status": "ready"`. No confunda el estado `WAITING` ni un éxito parcial de SSH con la aceptación final.

Volver a ejecutar el comando contra un host ya configurado es seguro: las fases que ya cumplen su condición informan `OK` y no cambian configuración. Un nombre existente con otra dirección, huella, lista de candidatos o alias SSH diferente falla en vez de sobrescribirlo.

El registro acepta las claves de host opcionales y ordenadas `fallback_addresses` y `share_hosts`. `fallback_addresses` aporta candidatos SSH después de `address`; `share_hosts` aporta hosts SMB para ese spoke y, si falta, SMB usa el `share.host` global. Los registros sin ninguna de esas claves opcionales siguen siendo válidos.

## Procedimiento manual (referencia)

Use este apéndice macOS sólo para diagnosticar una fase que no pueda completarse con `swarm-setup`. Para Linux/WSL, siga [la preparación](#linuxwsl-preparación); Finder, Keychain y launchd no son aplicables.

1. En el Mac nuevo, active Remote Login para la cuenta elegida y prepare Homebrew, Node, Pi, gentle-pi y Herdr; complete el login de Pi y abra Herdr en la GUI.
2. Configure ambas direcciones SSH con clave dedicada, huella local verificada, `known_hosts`, `authorized_keys` restringido y alias `swarm-<target>`. Siga el [runbook del canal SSH](../runbooks/agent-swarm/ssh-channel.md).
3. En Finder del spoke, realice el primer acceso SMB, guarde la contraseña en Keychain e instale el montaje persistente. Siga [Montaje SMB](../runbooks/agent-swarm/smb-mount.md).
4. Registre el host con los valores locales correctos, instale la skill y el bloque bootstrap, valide preflight en ambos sentidos y haga el commit del registro según el flujo aprobado.

## Reversión

`swarm-setup` no ofrece un subcomando de reversión. Con autorización del propietario, retire sólo los artefactos creados para este alta: la entrada y el commit del registro, aliases y claves SSH dedicadas, las líneas autorizadas añadidas, la skill/bootstrap del host nuevo y el montaje SMB persistente. No borre claves reutilizadas, copias de seguridad ni entradas que contengan cambios ajenos. Para los procedimientos precisos consulte [Canal SSH](../runbooks/agent-swarm/ssh-channel.md#reversión-por-dirección) y [Montaje SMB](../runbooks/agent-swarm/smb-mount.md).

## Problemas frecuentes

| Síntoma | Acción segura |
| --- | --- |
| `Not logged in` | Inicie sesión en Pi desde la **GUI** del host indicado; no intente autenticarlo por SSH. Después reejecute el mismo comando. |
| El script espera runtimes aunque Pi funciona en Terminal | Revise la versión `nvm` predeterminada o instalada, los directorios del `PATH` no interactivo y el resultado de los CLI bajo SSH. Un shell remoto `zsh` sin versiones `nvm` no debe abortar por un glob sin coincidencias; si aparece `no matches found`, compruebe que usa una versión del setup con esa corrección. |
| La huella no coincide | Detenga el alta. Compare de nuevo la lectura local y el escaneo de red; no use `StrictHostKeyChecking=no`. |
| El comando de autorización falla | Revise que se ejecutó completo en el Mac nuevo y que no se modificó la clave pública restringida que imprimió el script. |
| La primera copia remota falla con `scp: dest open ... No such file or directory` | El directorio padre del destino todavía no existe. Use una versión del setup que lo cree antes de `scp`; no cambie el destino a una carpeta ajena ni dé permisos amplios para sortear el error. |
| El montaje SMB no aparece | En macOS, conecte desde Finder y guarde la contraseña en Keychain; en Linux, revise fstab y el archivo de credenciales. Siga el runbook SMB; no ponga la contraseña en la terminal. |
| El nombre ya existe con otra dirección | No se sobrescribe: corrija la decisión de registro o use el host correcto. |
| Una fase informa `WAITING` tras completar la acción | Si usó `--no-wait`, repita sin esa opción (o con `--wait-timeout 0`); verifique la condición, el estado persistido y el log antes de concluir que falló la autorización. |

## Referencias

- [Actualización automática](../runbooks/agent-swarm/auto-update.md)
- [Canal SSH bidireccional](../runbooks/agent-swarm/ssh-channel.md)
- [Montaje SMB entre equipos](../runbooks/agent-swarm/smb-mount.md)
