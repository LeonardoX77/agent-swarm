# Actualización automática del host

`swarm-update` comprueba y actualiza sin `sudo` los componentes locales del canal en macOS y Linux/WSL. Usa launchd en macOS y un timer systemd de usuario en Linux; `mosh` se omite en Linux porque lo gestiona el sistema. Es un CLI Python autocontenido: se copia durante la instalación a `~/.local/agent-swarm/bin/swarm-update` y no instala dependencias.

## Instalación y calendario

Instale el agente desde el checkout del repositorio:

```bash
automation/agent-swarm/bin/swarm-update install
```

El valor predeterminado es una vez al día a las 04:30. Se puede cambiar en la instalación, por ejemplo:

```bash
automation/agent-swarm/bin/swarm-update install --hour 3 --minute 15 --components herdr,mosh,moshi-hook,pi,pi-extensions
```

| Plataforma | Calendario y requisitos |
| --- | --- |
| macOS | LaunchAgent `com.mac-agent-swarm.update`; launchd recupera la tarea perdida mientras el Mac dormía al despertar. |
| Linux/WSL | `~/.config/systemd/user/agent-swarm-update.service` y `agent-swarm-update.timer`, con `OnCalendar` y `Persistent=true`. Requiere `systemctl --user` disponible; la instalación falla si no lo está. |

El comando rechaza root y nunca usa `sudo`. En WSL, habilite systemd con `[boot]` / `systemd=true` en `/etc/wsl.conf`. Los timers de usuario sólo funcionan mientras haya una sesión del usuario salvo que se habilite `loginctl enable-linger $USER`.

## Operación

```bash
swarm-update check             # sólo lectura; no ejecuta brew update
swarm-update check --refresh   # macOS: también actualiza metadatos Homebrew; Linux: sin efecto extra
swarm-update run               # actualiza si pasaron al menos 20 horas
swarm-update run --force       # omite esa espera
swarm-update status
swarm-update uninstall         # retira el LaunchAgent o las unidades systemd de usuario
```

La salida normal es un resumen en inglés, una línea por componente. `--verbose` añade el `PATH` usado y cada comando, su código de salida y su salida recortada; `--json` emite el informe para automatización. Un fallo de un componente no impide intentar los demás, pero hace que `run` termine con código 1. `check` no cambia software instalado, pero Homebrew puede actualizar su caché local de API.

El archivo `~/.config/agent-swarm/update.json` contiene `enabled`, hora, minuto, componentes y el `PATH` que usa el agente. Para desactivar las actualizaciones sin retirar la configuración, cambie estrictamente `"enabled"` a `false`; para retirar el calendario use `swarm-update uninstall` (conserva configuración, copia local y logs). Las ejecuciones se registran en `~/Library/Logs/mac-agent-swarm/swarm-update.log` en macOS o `~/.local/state/agent-swarm/logs/swarm-update.log` en Linux. El último resultado queda en `~/.local/state/agent-swarm/update/last-run.json`.

## Comportamiento por componente

| Componente | macOS | Linux/WSL |
| --- | --- | --- |
| Herdr | Homebrew | `herdr update` si está instalado; no instala Herdr ausente |
| mosh / mosh-server | Homebrew | Omitido: gestionado por el gestor de paquetes del sistema |
| moshi-hook | Fórmula Homebrew si existe; si no, actualizador autónomo | Actualizador autónomo `moshi-hook update` |
| Pi | `pi update --self` | Igual |
| Extensiones Pi | `pi update --extensions` | Igual |

El actualizador autónomo de moshi-hook reinicia sólo su propio servicio si el CLI anuncia esa operación. Linux no ejecuta Homebrew. Para Herdr, Pi y los actualizadores autónomos, `check` detecta la instalación; no garantiza que haya una versión nueva: deja que el actualizador la compruebe al ejecutar `run`.

La actualización de Herdr **no reinicia nunca el servidor Herdr**: hacerlo cerraría pestañas activas. Tras actualizar el binario, el informe indica que el reinicio queda pendiente. Reinicie Herdr manualmente y sólo cuando sea conveniente para las pestañas activas, siguiendo el procedimiento específico del host (en macOS, por ejemplo, el servicio Homebrew o `dev.herdr.server`).
