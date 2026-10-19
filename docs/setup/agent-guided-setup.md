# Instalación guiada por agente (v1)

Para configurar el canal **Herdr + Pi** entre un hub y un Mac nuevo, siga [Agregar un equipo al canal Agent Fabric](add-host.md). El resto de esta guía cubre el runner v1.

Esta es la secuencia canónica para preparar Agent Fabric v1 entre la MacBook y la Mac mini. Intercala comprobaciones que un agente **ya autorizado** puede hacer con pausas que requieren una persona en el host correcto. No concede permisos: que una acción sea automatizable no autoriza instalaciones, red, `sudo` ni cambios persistentes. La v1 es one-shot; el canal persistente de Herdr sigue sin implementar.

**Fuera de alcance:** Bea (`beatrizdelcampo`) es evidencia experimental, no un host ni una cuenta soportados por v1. No se crea ninguna cuenta ni se usa `tmux`.

## Progreso seguro

Marcá esta lista en la conversación o ticket de trabajo, no en archivos de host. Conservá sólo evidencia saneada (estado, versión, ruta y código de salida), nunca contraseñas, tokens, claves privadas, JSON de tareas ni logs con prompts. Repetir una comprobación de sólo lectura es seguro; **no** repitas una aplicación ni cierres/reinicies procesos o agentes preexistentes para “arreglar” un resultado.

- [ ] Inventario e identidad de ambos hosts confirmados.
- [ ] Descubrimiento de software, PATH efectivo y autenticación humana confirmados.
- [ ] SMB opcional de v1 listo, si se usará el workspace compartido.
- [ ] Remote Login, firewall/Tailscale, huellas SSH y claves restringidas aprobados localmente.
- [ ] Plan del runtime revisado y aplicación autorizada en cada host.
- [x] Artefactos fuente de la skill global de tareas remotas y su bloque de bootstrap creados y comprobados estructuralmente; instalación y activación por runtime siguen pendientes.
- [ ] Preflight, rechazo de shell y despachos inocuos verificados.
- [ ] Herdr documentado como experimento aislado o detenido en su barrera de implementación.

## Secuencia ordenada

### 1. Inventariar la topología

**Actor:** agente autorizado (lectura) y persona responsable de cada host.

En la MacBook y en la Mac mini, comprobá localmente:

```sh
whoami
id -un leo
```

La identidad esperada de v1 es `leo` en ambos equipos: la MacBook es autoridad de `/Users/leo/projects` y la Mac mini usa su cuenta existente `leo`. Confirmá también cuál es el endpoint LAN o Tailscale real de cada equipo; no inventes nombres.

**Éxito:** ambos resultados identifican a `leo` y la persona confirma los dos endpoints. **STOP:** identidad distinta, cuenta inexistente o endpoint no verificable. No crees cuentas: corregí la decisión de topología y reanudá este mismo paso. Para detalles por host, consultá [MacBook](macbook.md#prerrequisitos-y-preflight-seguro) y [Mac mini](mac-mini.md#prerrequisitos-y-preflight-seguro).

### 2. Descubrir software; instalar y autenticar sólo con autorización

**Actor:** agente autorizado para descubrimiento; persona para instalaciones, red y autenticación de proveedor.

En cada host y en la terminal que usará Fabric, ejecutá:

```sh
command -v pi opencode claude
pi --version
opencode --version
claude --version
```

Esto distingue un binario instalado de un servidor o sesión actualmente en ejecución. Un PATH de SSH que no encuentre un CLI no prueba que esté ausente: compará el PATH efectivo de esa sesión con la terminal local antes de instalar nada. El preflight v1 sólo comprueba binarios, no login ni configuración interna.

Las instalaciones pueden necesitar red y aprobación explícita; no las inicies por el mero hecho de poder automatizarlas. La persona completa cada flujo local de proveedor (en Pi, abrir `pi` y usar `/login` si lo solicita), hace un prompt inocuo y confirma éxito sin mostrar secretos. No copiés HOME, Keychain, credenciales, sesiones ni skills por SMB.

**Éxito:** las versiones y los prompts inocuos funcionan bajo `leo` en cada host. **STOP:** falta binario, PATH ambiguo, red o autorización, o falla la autenticación; registrá sólo el diagnóstico saneado y reanudá aquí tras la intervención. No uses contraseñas mediante el agente.

### 3. Decidir y preparar el workspace SMB (sólo si v1 lo requiere)

**Actor:** persona local; el agente sólo puede inspeccionar lo ya autorizado.

v1 requiere el workspace compartido `agent-projects`: MacBook publica sólo `/Users/leo/projects` y Mac mini lo monta en `/Volumes/agent-projects`. Antes de cualquier cambio, seguí la [publicación SMB de MacBook](macbook.md#publicar-el-único-share-smb) y el [montaje SMB de Mac mini](mac-mini.md#montar-el-workspace-por-smb), en ese orden. La contraseña SMB se introduce interactivamente en Finder/Keychain, nunca en comandos, archivos o logs.

**Éxito:** el montaje existe y contiene `/Volumes/agent-projects/leo/mac-agent-fabric`. **STOP:** share ajeno, permisos inesperados o montaje ausente; no cambies ACLs ajenas ni reprovisiones el share. Inspeccioná y reanudá este paso; no continúes al runtime sin el montaje requerido.

### 4. Aprobar acceso local y SSH restringido

**Actor:** persona presente en cada host; agente sólo verifica después de autorización.

En ambos hosts, la persona activa **System Settings → General → Sharing → Remote Login**, selecciona “Only these users” y añade sólo `leo`; revisa también firewall y la autenticación/conectividad Tailscale o LAN local. No habilita Remote Management, forwarding de puertos ni un shell SSH general.

Creá una clave Fabric dedicada por dirección y fusioná —sin sobrescribir— la plantilla SSH correspondiente: [MacBook → mini](macbook.md#clave-y-ssh-de-despacho) y [mini → MacBook](mac-mini.md#clave-y-alias-ssh). Verificá la huella del host por un canal fiable antes de aceptarla. Las claves Fabric son restringidas a `fabric-runner`; son distintas de las claves personales que puedan alimentar `aiconnect`, cuya función sólo abre shells SSH normales y no forma parte de v1. Conservá `StrictHostKeyChecking yes`; nunca uses `StrictHostKeyChecking=no`.

**Éxito:** ambas huellas están verificadas y cada configuración conserva modo batch, sin PTY ni forwarding. **STOP:** huella cambia/no puede verificarse, falta autorización de GUI/firewall/Tailscale o hay una clave personal propuesta para Fabric. Detenete, investigá localmente y reanudá este paso; no borres ni reemplaces claves o agentes existentes.

### 5. Planificar y aplicar el runtime, host por host

**Actor:** agente para `--plan` si está autorizado; persona para revisar y autorizar cada `--apply` y la edición manual de `authorized_keys`.

Desde el clon local, ejecutá primero en cada host su plan exacto:

```sh
python3 automation/agent-fabric/bin/fabric-install-runtime --plan --role macbook --peer-public-key ~/Downloads/agent-fabric-mac-mini-to-macbook.pub
python3 automation/agent-fabric/bin/fabric-install-runtime --plan --role mac-mini --peer-public-key ~/Downloads/agent-fabric-macbook-to-mac-mini.pub
```

Ejecutá **sólo la línea que corresponde al host actual**. El plan no sustituye autorización de aplicación. Tras revisar el JSON saneado y recibir autorización explícita, seguí el `--apply` y la incorporación manual de la línea `authorized_keys_line` en la sección [MacBook](macbook.md#instalar-runtime-y-autorizar-el-peer) o [Mac mini](mac-mini.md#runtime-y-comando-forzado). No pegues claves privadas ni edites la línea generada.

**Éxito:** el plan corresponde al rol, workspace y peer público correctos; tras aplicación aprobada, sólo existe el runtime esperado bajo `~/.local/agent-fabric`. **STOP:** plan inesperado, peer incorrecto, falta autorización o conflicto en `authorized_keys`. No ejecutes `--apply` de nuevo ni reviertas a ciegas; inspeccioná y reanudá desde el plan de este paso.

### 6. Instalar y aceptar la skill global para tareas remotas

**Actor:** persona responsable del runtime; agente autorizado sólo para comprobaciones y cambios expresamente aprobados en el host correcto.

Los artefactos fuente ya existen en este repositorio: [`skills/agent-fabric-remote/SKILL.md`](../../skills/agent-fabric-remote/SKILL.md) y su [bloque de bootstrap](../../skills/agent-fabric-remote/assets/bootstrap-block.md). La skill (v1.2) recibe sobres con `task_id`, `origin_host`, `goal`, `project`, `acceptance` y `mode`, y también explica cómo delegar a otro equipo registrado con `fabric-delegate`. Toma las rutas y los equipos de `config/hosts.json`, detiene rutas o montajes ausentes y no concede privilegios ni sandbox.

**Estado: instalada y verificada en el MacBook y la Mac mini** (delegación en lenguaje normal en ambos sentidos). El procedimiento de instalación por equipo —enlace al repositorio en el hub, copia local en cada spoke y bloque de bootstrap con la ruta del repositorio— está en [Agregar un equipo](add-host.md). No cargues skills por SMB y no compartas HOME.

Toda delegación del orquestador requiere un transporte de retorno configurado y verificado, con IDs de mensaje/sesión. Las herramientas de orquestador de gentle-pi usan sockets Unix del perfil local, no mensajería entre hosts. Sin transporte verificado, indicá qué debe ejecutarse en la MacBook y no afirmes haber delegado. Ante entrega ambigua, consultá estado antes de reintentar. Respeta puertas humanas de permisos y nunca incluyas secretos.

**Aceptación pendiente:** una sesión nueva de Pi y otra nueva de Claude deben recibir un sobre válido y activar la skill sin que se les ordene cargarla; una solicitud con ruta incorrecta debe detenerse. Verificá también que reset y conciencia de sesión no inventen memoria entre hosts. **STOP:** documentación/ruta no verificada, transporte no verificado, falta aprobación humana, o cualquiera de esas pruebas falla. Conservá evidencia saneada; no adivines ni reintentes a ciegas.

### 7. Comprobar disponibilidad y límite del runner

**Actor:** agente autorizado para comprobaciones; persona para interpretar cambios de red/host.

En cada host, ejecutá el preflight con el config local y después el rechazo de shell de la guía correspondiente:

```sh
python3 automation/agent-fabric/bin/fabric-host-preflight --config config/macbook/host.json
python3 automation/agent-fabric/bin/fabric-host-preflight --config config/mac-mini/host.json
```

Ejecutá sólo el config del host actual. Luego seguí [validación MacBook](macbook.md#validación-y-reversión-local) o [validación Mac mini](mac-mini.md#validación-y-reversión-local): `ssh … true` debe ser rechazado por el comando forzado, no abrir una shell. Finalmente, una persona aprueba despachos JSON inocuos por cada runtime permitido.

**Éxito:** preflight devuelve `succeeded`, el shell genérico se rechaza y los despachos aprobados usan el workspace local correcto. **STOP:** cualquier diagnóstico, shell abierto o salida que pueda contener datos sensibles. No reintentes tareas ni cambies allowlists automáticamente; conservá evidencia saneada y reanudá esta comprobación tras corregir localmente.

### 8. Mantener Herdr como experimento aislado

**Actor:** persona y experimentador autorizado.

La referencia de estado es [sesiones Herdr](../../odd/tasks/herdr-agent-sessions.md). La versión observada `0.9.3` es un ejemplo histórico, no una orden de instalar “latest” ni un pin permanente. Cliente y servidor Herdr deben ser compatibles **en el host probado**; un binario instalado no prueba que su servidor esté corriendo, sea compatible ni que el PATH de SSH lo encuentre.

La única actividad permitida antes de implementación es una prueba manual aislada que no toque sesiones preexistentes, no instale software y no reinicie Herdr. Guardá evidencia separada y saneada. Detenete en la barrera: Fabric no implementa canal persistente, correlación de respuestas ni polling de estado como respuesta garantizada. No inventes comandos de producción, no reenvíes mensajes ambiguos y no implementes `tmux`.

**Éxito:** se documenta la evidencia limitada o la barrera de implementación. **STOP:** si se pretende operar, reiniciar un servidor, cerrar un agente existente o prometer respuestas persistentes; abrí el trabajo de diseño/implementación y no continúes como v1.

## Reanudación y referencias

Tras una pausa, volvé al **mismo número de paso**, repetí sólo su comprobación de lectura y usá la evidencia saneada para decidir si sigue pendiente. No supongas que un `--apply`, un montaje, una huella aceptada o una prueba de sesión es idempotente. Los artefactos fuente de la fase 6 no autorizan despliegue hasta completar instalación local, bootstrap y aceptación independientes. Para arquitectura y límites v1, prevalece [la arquitectura](../architecture.md); para operación posterior, usá el [runbook de validación](../runbooks/agent-fabric/validation.md).
