# Actualización automática del host

`fabric-update` comprueba y actualiza sin `sudo` los componentes locales del canal: Herdr, `mosh` (incluido `mosh-server`), `moshi-hook`, Pi y las extensiones de Pi. Es un CLI Python autocontenido: se copia durante la instalación a `~/.local/agent-fabric/bin/fabric-update` y no instala dependencias.

## Instalación y calendario

Instale el agente desde el checkout del repositorio:

```bash
automation/agent-fabric/bin/fabric-update install
```

El valor predeterminado es una vez al día a las 04:30. Se puede cambiar en la instalación, por ejemplo:

```bash
automation/agent-fabric/bin/fabric-update install --hour 3 --minute 15 --components herdr,mosh,moshi-hook,pi,pi-extensions
```

La instalación crea el LaunchAgent `com.mac-agent-fabric.update`. `launchd` ejecuta una tarea de calendario que se perdió mientras el Mac dormía cuando el equipo vuelve a despertar; no es necesario dejarlo encendido a la hora programada. El comando no debe ejecutarse como root y nunca usa `sudo`.

## Operación

```bash
fabric-update check             # sólo lectura; no ejecuta brew update
fabric-update check --refresh   # también actualiza los metadatos de Homebrew
fabric-update run               # actualiza si pasaron al menos 20 horas
fabric-update run --force       # omite esa espera
fabric-update status
fabric-update uninstall         # retira sólo el LaunchAgent
```

La salida normal es un resumen en inglés, una línea por componente. `--verbose` añade cada comando, su código de salida y su salida recortada; `--json` emite el informe para automatización. Un fallo de un componente no impide intentar los demás, pero hace que `run` termine con código 1.

El archivo `~/.config/agent-fabric/update.json` contiene `enabled`, hora, minuto, componentes y el `PATH` que usa el agente. Para desactivar las actualizaciones sin retirar la configuración, cambie estrictamente `"enabled"` a `false`; para retirar el LaunchAgent use `fabric-update uninstall`. Las ejecuciones se registran en `~/Library/Logs/mac-agent-fabric/fabric-update.log` y el último resultado queda en `~/.local/state/agent-fabric/update/last-run.json`.

## Comportamiento por componente

Herdr y mosh se actualizan con Homebrew. `moshi-hook` prefiere su fórmula Homebrew cuando existe y, si no, usa su actualizador autónomo; después reinicia sólo su propio servicio si el CLI anuncia esa operación. Pi usa `pi update --self` y las extensiones `pi update --extensions`.

La actualización de Herdr **no reinicia nunca el servidor Herdr**: hacerlo cerraría pestañas activas. Tras actualizar el binario, el informe indica que el reinicio queda pendiente. Reinicie el LaunchAgent de Herdr manualmente y sólo cuando sea conveniente para las pestañas activas, siguiendo el procedimiento específico del host (por ejemplo, el servicio Homebrew o `dev.herdr.server`).
