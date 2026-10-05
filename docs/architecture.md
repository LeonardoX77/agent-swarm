# Arquitectura de Agent Fabric v1

Agent Fabric permite que dos hosts macOS ejecuten, a pedido del otro, un CLI local seleccionado explícitamente: Pi + Gentle Pi, OpenCode o Claude Code. Es infraestructura de transporte y ejecución restringida, no un agente ni un modelo: no elige runtime automáticamente. La v1 usa SMB sólo para el espacio de trabajo y SSH restringido sólo para transportar una solicitud de tarea al runner local del destino. No distribuye identidades ni estado sensible.

## Resultado y alcance

El resultado es un despacho bidireccional: la MacBook puede pedir trabajo a la Mac mini y viceversa. Cada solicitud declara `runtime: pi`, `runtime: opencode` o `runtime: claude`; el host destino valida tanto esa selección como su allowlist local `allowed_runtimes` y ejecuta sólo el CLI permitido con la cuenta local que le corresponde.

Quedan fuera de v1: RPC de Pi, shell SSH genérico, reenvío de puertos del router, delegación de `sudo`, contraseñas remotas, locks y sincronización de skills por SMB.

## Topología y responsabilidades

| Host | Cuenta | Rol local | Espacio de trabajo | Responsabilidades |
|---|---|---|---|---|
| MacBook | `leo` | Autoridad de `/Users/leo/projects` y servidor SMB | `/Users/leo/projects`; share `agent-projects` | Publicar únicamente el workspace, mantener Pi + Gentle Pi, OpenCode y Claude Code configurados localmente para `leo`, montar el runner SSH local y permitir sus runtimes locales elegidos. |
| Mac mini | `jarvis` | Nodo de ejecución y cliente SMB | `/Volumes/agent-projects` | La persona crea `jarvis` manualmente, monta el share como `leo`, mantiene Pi + Gentle Pi, OpenCode y Claude Code configurados localmente para `jarvis`, monta el runner SSH local y permite sus runtimes locales elegidos. |

Ambos hosts tienen conectividad por LAN y Tailscale. Sus configuraciones SSH locales exponen los aliases `agent-fabric-macbook` y `agent-fabric-mac-mini`; no se abre ni reenvía ningún puerto en el router.

Cada host instala, actualiza y autentica sus propios Pi + Gentle Pi, OpenCode y Claude Code. El preflight sólo comprueba la presencia de los binarios; durante el setup, una persona verifica por separado la autenticación y configuración local de cada CLI. El procedimiento no copia credenciales y no automatiza login. Nunca se copian entre hosts `HOME`, dotfiles, Keychain, credenciales, tokens, configuración de runtime, sesiones, cachés ni logs. Las skills compartidas viven en un repositorio Git y cada host las consume desde su clon local; SMB no transporta skills.

## Flujo de despacho

1. Una persona o agente local crea una solicitud JSON y elige el alias del host destino.
2. `fabric-dispatch` valida la forma y el mapeo local de la solicitud antes de enviarla por stdin a SSH en modo batch.
3. La clave dedicada autentica contra el destino. `authorized_keys` obliga a ejecutar `fabric-runner`; no hay shell, PTY ni forwarding disponible.
4. `fabric-runner` vuelve a validar la solicitud, resuelve el path local del destino, comprueba que `runtime` esté en `allowed_runtimes` de ese host y ejecuta su argv cerrado bajo la cuenta local de ese host.
5. El runner devuelve el resultado saneado y `fabric-activity` registra localmente inicio y resultado terminal. El registro no bloquea, autoriza ni coordina escritores.

El mecanismo inicial es deliberadamente simple: el runtime elegido recibe el prompt de la solicitud y produce una ejecución one-shot. Los únicos argv son: Pi `pi -p --approve --name fabric-<request_id> -- <prompt>`; OpenCode `opencode run -- <prompt>`; Claude Code `claude -p --permission-prompts none -- <prompt>`. No hay shell, ni flags controlados por la solicitud. OpenCode no se inicia con `--auto`; en Pi se conserva la semántica actual de `--approve`; y en Claude `--permission-prompts none` falla cerrado cuando una operación requeriría un prompt sin respuesta, aunque las políticas locales siguen gobernando. Una integración RPC puede evaluarse más adelante si hace falta conservar sesiones, streaming o control más rico; no forma parte del contrato ni de la instalación v1.

## Contrato de solicitud JSON

El único transporte de la solicitud es stdin. No se ponen prompts, rutas ni JSON en argumentos de shell.

```json
{
  "version": 1,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "workspace": "mac-agent-fabric",
  "relative_path": ".",
  "prompt": "Inspect the repository and report the focused findings.",
  "runtime": "pi",
  "initiator": "macbook",
  "timeout_seconds": 900
}
```

| Clave | Regla v1 |
|---|---|
| `version` | Entero exactamente `1`. Se rechazan claves desconocidas. |
| `request_id` | UUID usado para correlación local saneada; no concede autoridad ni funciona como lock. |
| `workspace` | Nombre de un workspace permitido por la configuración local del runner. No acepta una ruta absoluta. |
| `relative_path` | Ruta relativa POSIX dentro de ese workspace; no admite vacío, `/`, `.` inicial ambiguo, `..` ni escape mediante symlink. `.` sólo representa la raíz del workspace. |
| `prompt` | Texto UTF-8 no vacío pasado como único argumento de prompt al argv cerrado del runtime. No contiene secretos; el runner puede imponer límites de tamaño. |
| `runtime` | Exactamente `pi`, `opencode` o `claude`. Lo selecciona cada solicitud; no selecciona usuario, flags ni permisos. El destino lo rechaza si no figura en su `allowed_runtimes` local. |
| `initiator` | `macbook` o `mac-mini`, para observabilidad. No selecciona usuario ni amplía permisos. |
| `timeout_seconds` | Entero positivo dentro del máximo local del runner. El runner mata sólo su proceso hijo al vencer. |

El runner resuelve el workspace configurado y concatena únicamente un `relative_path` validado. Luego canoniza los ancestros existentes y rechaza cualquier resultado que salga de la raíz. La tabla de mapeo es local a cada host y debe contener el mismo identificador lógico, no rutas remotas suministradas por el llamador:

| `workspace` | MacBook (`leo`) | Mac mini (`jarvis`) |
|---|---|---|
| `mac-agent-fabric` | `/Users/leo/projects/leo/mac-agent-fabric` | `/Volumes/agent-projects/leo/mac-agent-fabric` |

El runner ejecuta el runtime elegido con su directorio de trabajo igual al path local resuelto. Por lo tanto, una solicitud nunca intenta usar `/Users/leo/...` en la Mac mini ni `/Volumes/...` en la MacBook.

## Límite de seguridad y confianza

La autenticación SSH usa claves dedicadas por dirección. Cada entrada restringida de `authorized_keys` aplica `command=".../fabric-runner"`, `no-port-forwarding`, `no-agent-forwarding`, `no-X11-forwarding` y `no-pty`. La configuración también debe deshabilitar cualquier forwarding no contemplado por la cuenta del runner. El comando forzado recibe sólo el JSON por stdin, ignora una orden SSH aportada por el cliente y rechaza cualquier entorno no permitido.

Esto crea un límite de **transporte**, no un sandbox de ejecución:

- La clave permite alcanzar sólo el runner forzado, no un shell SSH genérico.
- El runner limita el protocolo, el workspace y el directorio de trabajo.
- Una vez iniciado, el runtime remoto tiene la autoridad efectiva del usuario destino: `leo` en la MacBook o `jarvis` en la Mac mini.
- El comando forzado no puede restringir las herramientas que Pi, OpenCode o Claude Code ya pueden usar bajo esa cuenta. Si un runtime tiene permiso para leer, escribir o ejecutar algo, esa capacidad sigue existiendo dentro de los permisos de la cuenta y las políticas locales.
- No se delegan contraseñas, tokens, acceso al Keychain ni `sudo`. Toda configuración que requiera privilegios se ejecuta interactivamente y sólo en el host local.

Las claves privadas se guardan localmente con permisos restringidos y, si corresponde, se cargan mediante Keychain local. Los logs no incluyen prompt completo, JSON completo, credenciales, tokens, variables de entorno ni salida sin sanear.

## SMB y estado local

La MacBook publica `/Users/leo/projects` como `agent-projects`. La Mac mini monta ese share en `/Volumes/agent-projects` autenticándose como el usuario macOS `leo` de la MacBook. La persona introduce esas credenciales de forma interactiva en la Mac mini para que macOS las guarde en su Keychain local; nunca se ponen en archivos de configuración, JSON, logs ni comandos.

SMB transporta sólo el workspace aprobado. Aunque el montaje permita leer y escribir esos archivos según los permisos SMB, no reemplaza los límites de autoridad del runner ni sincroniza estado local. En particular, los siguientes elementos permanecen fuera del share: HOME, Keychain, credenciales, configuración de Pi/Gentle Pi, sesiones, cachés, logs, archivos de runtime y clones locales de skills.

## Actividad y concurrencia

No hay locks, fencing, coordinación automática ni exclusión mutua. Dos solicitudes pueden competir por el mismo árbol de trabajo; la coordinación y la revisión de cambios son humanas.

`fabric-activity` guarda sólo actividad local saneada: marca temporal, host, rol, `request_id` o hash correlacionable, workspace lógico, estado (`started`, `succeeded`, `failed`, `cancelled`), duración y código diagnóstico. Nunca determina si una tarea puede escribir, ni revela secretos, prompts completos, contenido del repositorio, rutas sensibles o stderr sin procesar.

## Comportamiento ante fallas

| Situación | Comportamiento requerido |
|---|---|
| Alias, Tailscale/LAN o SSH no disponibles | `fabric-dispatch` falla sin ejecutar localmente una sustitución y registra un diagnóstico saneado local. |
| Clave rechazada o comando SSH no esperado | El destino no abre shell; el despacho termina como `failed`. |
| JSON inválido, clave desconocida, runtime desconocido/no permitido, timeout fuera de rango o path inseguro | El runner rechaza antes de invocar un runtime. |
| Workspace o montaje ausente | El runner rechaza antes de invocar Pi; no crea directorios ni monta SMB. |
| Pi/Gentle Pi, OpenCode o Claude Code no instalados, configurados o autenticados localmente | El runner falla de forma explícita en el destino; el iniciador no intenta autenticarlos remotamente. |
| El runtime elegido excede el timeout o termina con error | El runner termina su hijo, devuelve estado de falla saneado y registra el resultado local. |
| Falla el log `fabric-activity` | La ejecución no gana autoridad ni se reintenta automáticamente; se informa la falla de observabilidad. |
| Dos escritores concurrentes | No hay arbitraje: se informa sólo la actividad local y la coordinación queda en manos humanas. |

Una recuperación nunca borra contenido del workspace, datos de Keychain, cuentas ni configuración no relacionada. El operador inspecciona primero el host y el árbol afectado; cualquier `sudo` de recuperación sigue siendo interactivo y local.

## Secuencia de instalación

La secuencia se ejecuta en este orden. Los pasos privilegiados requieren presencia humana en el host indicado y `sudo` interactivo local.

1. **Preparar identidades locales.** La persona crea `jarvis` en la Mac mini. Se instalan y autentican Pi + Gentle Pi, OpenCode y Claude Code por separado como `leo` y como `jarvis`; se verifican binarios y configuración local sin copiar credenciales ni automatizar login.
2. **Publicar y montar el workspace.** En la MacBook, configurar localmente el share SMB `agent-projects` para `/Users/leo/projects`. En la Mac mini, montar en `/Volumes/agent-projects` como `leo` e ingresar la autenticación SMB interactivamente para Keychain.
3. **Clonar skills.** Clonar el repositorio Git de skills en rutas locales de cada host y configurar cada instalación de Pi para usar su clon, sin apuntar a SMB.
4. **Crear identidad SSH restringida.** Generar claves dedicadas por dirección, instalar sus públicas con el comando forzado `fabric-runner` y las restricciones de forwarding/PTY, y resguardar cada privada sólo en el host originador.
5. **Configurar aliases SSH.** Definir `agent-fabric-macbook` y `agent-fabric-mac-mini` con la ruta de clave dedicada, destino LAN/Tailscale y modo batch; verificar ambos sentidos sin abrir un shell.
6. **Instalar los componentes v1.** Instalar `fabric-dispatch`, `fabric-runner`, `fabric-activity` y la configuración local de workspace en ambos hosts. Cada instalador valida host y cuenta antes de cambiar sólo su host local.
7. **Validar antes de operar.** Ejecutar pruebas de contrato y verificaciones de conexión, montaje y runner forzado, y un despacho inocuo para cada uno de Pi, OpenCode y Claude Code. Confirmar que no se usó `sudo` remoto, no hay forwarding ni shell general y que los logs están saneados.
8. **Operar con coordinación humana.** Despachar tareas pequeñas, revisar los cambios compartidos y tratar toda concurrencia como un riesgo operativo, no como un problema que resuelva infraestructura.

## Mapa de entregables

| Entregable | Ruta | Propósito |
|---|---|---|
| Punto de entrada | `README.md` | Resume v1 y dirige a esta arquitectura. |
| Arquitectura | `docs/architecture.md` | Contrato, límites, secuencia y decisiones autoritativas. |
| Configuración de host MacBook | `config/macbook/` | Define sólo la instalación local de `leo`, SMB y aliases/runner del host. |
| Configuración de host Mac mini | `config/mac-mini/` | Define sólo la instalación local de `jarvis`, el montaje y aliases/runner del host. |
| Dispatcher | `automation/agent-fabric/bin/fabric-dispatch` | Valida y envía JSON por stdin al alias SSH seleccionado. |
| Runner forzado | `automation/agent-fabric/bin/fabric-runner` | Valida JSON, allowlist y paths; ejecuta sólo el argv cerrado del runtime local elegido. |
| Registro de actividad | `automation/agent-fabric/bin/fabric-activity` | Escribe observabilidad local saneada sin locks. |
| Esquema y pruebas | `automation/agent-fabric/schema/` y `automation/agent-fabric/test/` | Fijan el contrato JSON, el rechazo de paths y las restricciones del runner. |
| Guía operativa | `docs/runbooks/agent-fabric/` | Describe operación bidireccional, validación, falla y reversión local. |

La única fuente de verdad para las decisiones de v1 es este documento. Los materiales archivados o de preflight anteriores son contexto histórico y no deben contradecir ni activar una configuración alternativa.

## Checklist de revisión

- [ ] Ambos hosts conservan Pi + Gentle Pi, OpenCode, Claude Code, HOME y credenciales locales; cada request declara su runtime y cada host conserva su `allowed_runtimes` independiente.
- [ ] SMB expone sólo `/Users/leo/projects` como `agent-projects`, y la Mac mini lo monta en `/Volumes/agent-projects` como `leo` mediante Keychain interactivo.
- [ ] Cada sentido SSH usa una clave dedicada y llega sólo al comando forzado sin PTY ni forwarding.
- [ ] El JSON no transporta rutas absolutas, secretos ni autoridad adicional.
- [ ] El runner ejecuta únicamente el argv cerrado de Pi, OpenCode o Claude Code con la cuenta del destino y valida runtime y path contra su configuración local.
- [ ] `fabric-activity` es saneado y observacional; no existen locks.
- [ ] RPC sigue documentado sólo como opción futura.
