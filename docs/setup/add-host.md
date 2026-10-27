# Agregar un equipo al canal Agent Swarm

El camino canónico para incorporar un Mac nuevo es ejecutar **un único comando** desde un Mac ya registrado. `swarm-setup` coordina las diez fases, se detiene sólo ante acciones humanas y conserva el estado para reanudar la misma operación.

## Camino rápido

### Requisitos

- El Mac de origen ya está registrado en `config/hosts.json` y se ejecuta el comando desde su checkout del repositorio. Ese archivo es local y no se versiona: si no existe, copie `config/hosts.example.json` y sustituya los valores de ejemplo por los reales.
- El Mac nuevo usa macOS y la persona puede sentarse delante de él para algunos pasos GUI.
- **Pi y gentle-pi son obligatorios; Claude es opcional; Herdr es obligatorio.**
- Hay conectividad LAN o Tailscale hacia `<host>.local` y se conoce la cuenta `<user>` del Mac nuevo.

Desde el Mac registrado, ejecute:

```sh
automation/agent-swarm/bin/swarm-setup add-host \
  --name <name> --address <host>.local --user <user> \
  [--host-fingerprint SHA256:...] [--install-missing] \
  [--update-time 04:30 | --no-auto-update] [--verbose]
```

El valor predeterminado instala la actualización diaria a las `04:30`; use `--no-auto-update` si no quiere activar ese calendario. Esto no instala un chequeo de actualizaciones al primer uso remoto: es una funcionalidad distinta. Agent Swarm no gestiona ni garantiza los avisos de paquetes que pueda mostrar Pi al iniciarse. `--install-missing` aprovecha las herramientas ya instaladas y sólo intenta añadir Herdr y gentle-pi cuando sus CLI base están disponibles: no reinstala todo el Mac. El proceso muestra un resumen breve en inglés; por ejemplo:

```text
[ 1/10] local-preflight OK       origin preflight passed
...
[10/10] acceptance      OK       bidirectional acceptance passed
Summary: setup complete; changed phases: ssh-to-new, registry, skill, auto-update
```

Al completar con éxito termina con salida `0`. Revise la entrada que el setup añadió a `config/hosts.json`. Ese archivo está ignorado por Git: no se comitea; si necesita compartir su estructura, actualice `config/hosts.example.json` con valores genéricos. No copie manualmente valores de `share`: el script los lee del registro.

> Si se interrumpe o espera a una persona, ejecute **el mismo comando con las mismas opciones** otra vez desde el origen. Comprueba de nuevo cada fase y conserva lo ya configurado; no genere otra huella ni acepte una distinta sin verificarla localmente.

## Las diez fases

Los nombres de fase siguientes son los que imprime el programa exactamente.

| Fase | Qué hace el script | Quién actúa | Si se detiene, texto exacto que muestra |
| --- | --- | --- | --- |
| `local-preflight` | Valida nombre, dirección, herramientas SSH y que el origen sea el `self_host` del registro. | Agente | No espera a una persona. |
| `remote-login` | Comprueba que el puerto SSH del Mac nuevo sea alcanzable. | Persona | `On <name>: System Settings > General > Sharing > Remote Login: ON for user <user>` |
| `ssh-to-new` | Crea o reutiliza la clave origen→nuevo, verifica la huella, configura `known_hosts`, autoriza la clave y crea `swarm-<name>`. | Persona y agente | Huella en TTY: `Type the fingerprint shown on <name> (or yes): `; clave: `On <name> add the displayed public key to ~/.ssh/authorized_keys, then continue.` |
| `runtimes` | Comprueba Homebrew, Node, Python, Herdr, Pi, gentle-pi y el servidor Herdr; con `--install-missing` intenta instalar sólo Herdr y gentle-pi cuando sus precondiciones ya existen. | Persona | `On <name>: install missing runtimes and log Pi in once from the GUI` |
| `ssh-to-origin` | Configura el canal SSH inverso nuevo→origen, incluida la huella del origen y el alias remoto. | Agente | No espera a una persona. Un conflicto de huella o alias falla de forma segura. |
| `mount` | En un `spoke`, copia la utilidad de montaje e instala el montaje SMB persistente usando `share` del registro. | Persona | `On <name>, connect in Finder to smb://<share.user>@<share.host>/<share.name> and save the password` |
| `registry` | Descubre datos del nuevo host y escribe su entrada en `config/hosts.json`. | Agente | No espera a una persona. |
| `skill` | Copia la skill `agent-swarm-remote` y su bloque bootstrap al Mac nuevo. | Agente | No espera a una persona. |
| `auto-update` | Instala `swarm-update` y su LaunchAgent diario, salvo `--no-auto-update`. | Agente | No espera a una persona. |
| `acceptance` | Ejecuta preflight en ambos sentidos y pruebas de aceptación Herdr + Pi. | Persona y agente | Si Pi no tiene sesión: `Log Pi in from the GUI on <target>` |

`<name>`, `<user>`, `<share.user>`, `<share.host>`, `<share.name>` y `<target>` son valores concretos sustituidos por el script.

## Intervenciones de la persona

El proceso comprueba las condiciones cada **5 segundos**, hasta `--wait-timeout` minutos (30 por defecto). Tras la intervención no hay que pulsar nada: el proceso continúa al detectar la condición. Si vence el tiempo, o se usó `--no-wait`, termina con una pista para reanudar; vuelva a ejecutar el mismo comando para continuar. **`--no-wait` evita sondear de nuevo una condición que acaba de fallar**: aunque la persona ya haya intervenido, una fase puede terminar en `WAITING` sin comprobar por segunda vez la condición. Para reanudar, omita esa opción o use `--wait-timeout 0` para comprobar la condición una vez y salir sin espera prolongada.

### Remote Login

**El script muestra:** `On <name>: System Settings > General > Sharing > Remote Login: ON for user <user>`.

**La persona hace:** en el Mac nuevo abre **System Settings → General → Sharing → Remote Login**, lo activa y autoriza a `<user>`. También confirma que la red elegida es la correcta.

**Continúa cuando:** el puerto 22 responde desde el origen.

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

**El script muestra:** `On <name>: install missing runtimes and log Pi in once from the GUI`.

**La persona hace:** instala Homebrew, Node, Pi, gentle-pi y Herdr si faltan; abre Herdr y abre Pi en la sesión GUI para completar el login del proveedor. Claude no es requisito. Con `--install-missing`, el script sólo intenta `brew install herdr` si Homebrew ya responde y `pi install npm:gentle-pi` si Pi ya responde: no instala Homebrew, Node ni Pi.

**Continúa cuando:** las comprobaciones remotas encuentran `brew`, `node`, `python3`, `herdr`, `pi`, gentle-pi y `herdr tab list` funciona.

> Para SSH no interactivo, el script descubre directorios de herramientas habituales, incluido el `default` de `nvm` (o la versión Node instalada más alta), y usa ese `PATH` para las comprobaciones y herramientas posteriores.

### Primer montaje SMB y Keychain

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
| `--name`, `--address`, `--user` | Obligatorios: nombre de registro, dirección y cuenta del nuevo Mac. |
| `--role {hub,spoke}` | Rol del nuevo host; el predeterminado es `spoke`. |
| `--host-fingerprint SHA256:...` | Huella previamente verificada; evita la pregunta de TTY. |
| `--origin-user USER` | Cuenta que usará el canal inverso hacia el origen. |
| `--install-missing` | Intenta instalar sólo Herdr y gentle-pi cuando Homebrew/Pi ya existen. |
| `--auto-update` / `--no-auto-update` | Activa (predeterminado) o omite el LaunchAgent diario. |
| `--update-time HH:MM` | Hora diaria; el predeterminado es `04:30`. |
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

El estado está en `~/.local/state/agent-swarm/setup/<name>.json` y el log en `~/Library/Logs/mac-agent-swarm/swarm-setup-<name>.log`. Ante un error inesperado, consulte ese log y, si hace falta, reanude con `--verbose` y las mismas opciones; comparta sólo diagnóstico saneado, pues los logs pueden incluir claves **públicas**, rutas y nombres de usuario. La salida normal es resumida en inglés; `--verbose` registra cada comando, código de salida y salida recortada. Si el setup termina con salida `0`, confirme además `automation/agent-swarm/bin/swarm-delegate preflight <name>`: debe devolver `"status": "ready"`. No confunda el estado `WAITING` ni un éxito parcial de SSH con la aceptación final.

Volver a ejecutar el comando contra un host ya configurado es seguro: las fases que ya cumplen su condición informan `OK` y no cambian configuración. Un nombre existente con otra dirección, una huella distinta o un alias SSH diferente falla en vez de sobrescribirlo.

## Procedimiento manual (referencia)

Use este apéndice sólo para diagnosticar una fase que no pueda completarse con `swarm-setup`.

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
| El montaje SMB no aparece | Conéctese primero desde Finder, guarde la contraseña en Keychain y siga el runbook SMB; no ponga la contraseña en la terminal. |
| El nombre ya existe con otra dirección | No se sobrescribe: corrija la decisión de registro o use el host correcto. |
| Una fase informa `WAITING` tras completar la acción | Si usó `--no-wait`, repita sin esa opción (o con `--wait-timeout 0`); verifique la condición, el estado persistido y el log antes de concluir que falló la autorización. |

## Referencias

- [Actualización automática](../runbooks/agent-swarm/auto-update.md)
- [Canal SSH bidireccional](../runbooks/agent-swarm/ssh-channel.md)
- [Montaje SMB entre equipos](../runbooks/agent-swarm/smb-mount.md)
