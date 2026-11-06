# Evidencia histórica de pruebas de Agent Swarm

> **Estado:** registro histórico, no protocolo de producción ni aceptación de un despliegue. La comprobación vigente está en [validación](validation.md).

## Cómo interpretar la evidencia

- **PASS** confirma únicamente la observación descrita en el entorno y momento anotados.
- **FAIL**, **BLOCKED**, **SKIP** e **INCONCLUSIVE** no deben reinterpretarse como una capacidad disponible.
- Los nombres de tabs, panes, PIDs, nonces y rutas temporales son identificadores históricos, no valores reutilizables.
- Las observaciones no sustituyen el registro actual, una huella verificada, login de Pi, un montaje SMB ni una aceptación del canal.

## Evidencia Linux/WSL

Observaciones reales comunicadas por el responsable de la prueba en este host: Ubuntu 24.04, kernel 6.18 WSL2 y `systemd --user` en ejecución. El alcance de cada prueba se distingue a continuación; una delegación real hacia WSL no valida la aceptación bidireccional de dos máquinas.

| Área | Resultado observado | Alcance |
| --- | --- | --- |
| `swarm-update` | **PASS**: install/run/status/uninstall mediante systemd de usuario real; calendario de prueba retirado al terminar. | Valida el ciclo del servicio, no todas las actualizaciones de componentes. |
| `swarm-smb-mount` | **PASS**: status, mount `--persistent`, status, lectura, escritura, unmount y `--remove-persistent`, sin sudo en la herramienta. El timer volvió a montar tras desmontar. | Recurso Samba temporal en loopback, con cifs-utils y Samba instalados; `127.0.0.1:1445` porque Windows ocupaba 445. Se usó la línea de `fstab-line` añadiendo `port=1445` para la prueba; la preparación privilegiada fue externa a la herramienta. |
| Rechazo seguro SMB | **PASS**: un montaje sin entrada fstab falló con `fstab_entry_required`. | No demuestra compatibilidad con cualquier servidor SMB. |
| Identificación de host | **PASS**: el prefijo `5CG6031YZW` coincidió en forma exacta, minúsculas, mayúsculas y FQDN; nombres ajenos no coincidieron. | Comprueba la comparación sin distinguir mayúsculas, no una delegación. |

### Alta real por SSH y delegación hacia este WSL

Evidencia comunicada por el responsable de la ejecución real (no repetida por los tests simulados):

- **PASS parcial, fases 1–9:** `swarm-setup add-host` por SSH real a este WSL con `--ssh-port 2222 --origin-ssh-port 2222` completó la comprobación de huella, el paso humano de `authorized_keys`, la instalación de Herdr 0.9.5 por `--install-missing`, el montaje CIFS real mediante la fase de montaje del setup contra un recurso Samba temporal en loopback, la entrada de registro con catálogo `/mnt/agent-projects`, la copia de la skill y el timer systemd de actualización. Hubo dos pasos humanos adicionales: arrancar el servidor Herdr y hacer visible `pi`. El cambio posterior añade diagnóstico de probes, instrucciones de arranque y descubrimiento de `$HOME/.pi/agent/bin` junto a `$HOME/.local/bin` en setup y swarm-update.
- **FAIL esperado, fase 10:** la aceptación falló con `SELF_TARGET` porque origen y destino eran el mismo host. La aceptación bidireccional **no** está validada mediante este loopback de un solo host.
- **PASS, delegación real separada:** `swarm-delegate submit/recover/close` desde el hub al nodo Linux devolvió el nonce exacto y cerró sólo su propia tab. Antes de instalar la integración oficial Herdr Pi, submit devolvió `unknown` y el prompt nunca fue entregado (comportamiento documentado del adaptador, no éxito de envío).
- **Hallazgo SSH:** Windows OpenSSH ocupaba TCP 22 en todas las direcciones locales del host; por eso se añadieron `--ssh-port` y `--origin-ssh-port`, sin cambiar sus valores predeterminados de 22.
- **Prerrequisito de propiedad:** `herdr integration install pi` instala `~/.pi/agent/extensions/herdr-agent-state.ts`; `herdr integration status` permite comprobarlo. Sin esa integración Herdr no aporta `agent_session` de tipo `path`, fuente `herdr:pi`, necesario para demostrar propiedad antes de enviar el prompt. El setup ahora lo sondea como `herdr-pi-integration` y `--install-missing` puede instalarlo en ambas plataformas; dry-run sólo informa.
- **Arranque headless:** `herdr tab list` devolvía `server_not_running`. Herdr 0.9.5 rechazó una terminal de tamaño cero con `cannot attach without a usable terminal: terminal reported a zero-sized grid`. Se puede iniciar con `herdr` en una terminal normal y desacoplar, o con una pty de filas y columnas no nulas; el servidor sobrevive a la salida del cliente. No existe `herdr server start`: esa versión sólo ofrece `server stop` y `server reload-config`.

**No validado:** aceptación bidireccional entre dos máquinas reales; ejecución nativa del código nuevo en macOS (sólo tests simulados y comparación diferencial contra `origin/main`); un nodo Linux alcanzado por una red real desde un hub macOS; servidores cuyo dialecto SMB mínimo sea 3.1.1 (la línea fstab generada usa `vers=3.0`).

## Observaciones útiles de Herdr + Pi

| Área | Observación histórica | Límite |
| --- | --- | --- |
| Sesión propia | Una tab y un agente Pi propios pudieron responder un nonce y limpiarse sin cerrar recursos preexistentes. | No demuestra aislamiento completo ni garantía de producción. |
| Arranque de Pi | **Reproducido en el nodo WSL real:** a las `21:53:53.068` `tab.create` generó el pane 3; `agent.start` devolvió error a `.080`, devolvió `ok` a `.183`, y Pi sólo se registró a `.622`. El ledger quedó `unknown` en `start_intent` y no se envió ningún prompt. El adaptador ahora consulta `herdr agent get <pane_id>` aproximadamente cada 0,5 segundos, con un límite de espera para el arranque, antes de declarar `unknown`; registra `started` y envía el prompt sólo después de confirmar la identidad estricta de propiedad. | Esto protege frente a la carrera de registro observada sin reintentar `agent start` ni reenviar un prompt a ciegas. Validar el comportamiento acotado frente a futuras versiones de runtime de Herdr/Pi. |
| Resultado JSONL | El adaptador encontró el mensaje exacto de usuario y una respuesta final descendiente en el JSONL de la sesión propia. | Los snapshots de pantalla no correlacionan por sí mismos un turno. |
| Ledger | Persistir intención antes de crear, iniciar, enviar y cerrar permitió conservar estados ambiguos para recuperación. | No aporta exactly-once distribuido ni autoriza reenvío automático. |
| Envelope | El contrato correcto contiene seis campos y `mode: executor`; entradas extra o modos no admitidos se rechazan. | La validación no sustituye el control humano del alcance. |
| Cierre | Un cierre verificado conserva el resultado y confirma `tab_not_found` para la tab propia. | No autoriza cerrar tabs, agentes o sesiones ajenos. |
| Límites JSONL | Se observó una línea de sistema cercana a 99 KiB; el lector admite hasta 1 MiB por línea y 8 MiB por archivo. | Son límites del adaptador, no una promesa sobre futuros formatos de Pi. |

## Comunicación y recuperación

Las pruebas históricas mostraron que una desconexión controlada del cliente SSH o un timeout de espera no prueban la cancelación del trabajo remoto. La recuperación segura conserva el UUID y consulta el estado; no crea un segundo trabajo ni reenvía un prompt ante ambigüedad.

También se observó que Herdr puede emitir errores tipados por stdout o stderr, y que `herdr agent prompt` rechaza `--timeout` sin `--wait`. El adaptador envía el prompt sin esas opciones y analiza ambos canales de error.

## Límites que permanecen abiertos

1. Probar fallas generales de red y servidor con recuperación sin reenvío ciego.
2. Verificar en cada despliegue el catálogo SMB limitado, aliases, huellas y ambas direcciones SSH.
3. Mantener login y credenciales de Pi locales al host; una observación de GUI no demuestra autenticación no interactiva distinta.
4. Coordinar escritores humanos: el canal no implementa locks ni resolución de conflictos.
5. Volver a validar la carrera reproducida entre el registro de Pi y `herdr agent start` al desplegar un runtime nuevo de Herdr o Pi; el adaptador ahora espera identidad estricta mediante sondeo acotado de `agent get`, nunca reintenta `agent start` y nunca envía un prompt antes de confirmar la propiedad.
6. Evaluar cualquier cambio de runtime o protocolo como trabajo nuevo, con evidencia nueva.

## Evidencia local disponible

Las pruebas deterministas del adaptador se ejecutan con fixtures y no abren una GUI viva ni configuran hosts:

```sh
python3 -m unittest automation/agent-swarm/test/test_herdr_task.py
python3 -m unittest discover -s automation/agent-swarm/test
```

Antes de operar, siga [validación](validation.md), [Canal SSH](ssh-channel.md) y [Montaje SMB](smb-mount.md). Para el contrato de tareas, consulte [Tareas Herdr + Pi](herdr-tasks.md).
