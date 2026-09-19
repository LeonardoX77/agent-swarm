# Inicialización de la infraestructura de agentes: diseño técnico

## Decisión

Este recorte agrega un **kit de repositorio no aplicable y comprobable** para preparar una infraestructura de agentes de dos Mac. Valida un plan declarativo, produce evidencia exclusivamente local y especifica el protocolo de bloqueo SSH que utilizará un despliegue posterior autorizado. No configura ningún host, crea identidad ni credencial, monta SMB, exporta un recurso compartido ni selecciona ajustes de SMB.

La estructura prevista es deliberadamente pequeña y separable en unidades de trabajo revisables (cada una estimada por debajo del presupuesto de revisión de 400 líneas):

| Unidad de trabajo | Rutas planificadas del repositorio | Propósito |
|---|---|---|
| Contrato y validador | `automation/agent-fabric/schema/fabric-plan.schema.json`, `automation/agent-fabric/lib/validate-plan.*`, `automation/agent-fabric/bin/fabric-preflight` | Analizar y rechazar planes inseguros sin cambiar configuración del host. |
| Evidencia y mediciones | `automation/agent-fabric/bin/fabric-measure`, `automation/agent-fabric/lib/records.*` | Capturar únicamente registros locales saneados. |
| Ayudante de bloqueo y pruebas de protocolo | `automation/agent-fabric/bin/fabric-lock`, `automation/agent-fabric/lib/lock.*` | Implementar la futura máquina de estados de bloqueo local de la MacBook y probarla con un fixture SSH local. |
| Manuales operativos | `docs/runbooks/agent-fabric/{macbook,mac-mini,orchestration,validation-recovery}.md` | Hacer explícitas la autorización posterior, operaciones, recuperación y reversión. |
| Pruebas y fixtures | `automation/agent-fabric/test/**` | Comprobaciones de unidad, contrato, subproceso y seguridad documental. |

El lenguaje de implementación debe usar la convención existente de scripting/runtime del repositorio. Debe usar un analizador JSON y API de procesos de biblioteca estándar; introducir un instalador privilegiado, daemon o dependencia nueva del host está fuera de alcance.

## Límite de seguridad y contrato de ejecución en seco

Todos los puntos de entrada de automatización aceptan `--config <path>` y por defecto usan `--dry-run`. `--apply` no debe existir; si se proporciona, el comando termina distinto de cero con `APPLY_NOT_IMPLEMENTED`. Las únicas escrituras permitidas en este recorte son archivos explícitos de evidencia local y directorios de bloqueo solo para pruebas:

- `fabric-preflight` lee configuración y puede escribir un informe únicamente con `--record <local-path>`.
- `fabric-measure` puede recopilar sondeos que no configuran y escribe únicamente con `--record <local-path>`.
- `fabric-lock` tiene una anulación `--state-root` aceptada únicamente para pruebas. Su protocolo de producción se documenta y prueba, pero no lo invocan comandos de configuración para crear estado persistente del host.
- Todo comando imprime `mode: dry-run` o `mode: non-configuring-measurement`; los comandos que requerirían `sudo`, `dscl`, `sharing`, `launchctl`, `mount`, `defaults`, cambios de firewall, creación de cuenta, generación de credenciales o cambios de autorización SSH se representan únicamente como entradas de lista de verificación `DEFERRED` en el manual.

Ninguna herramienta acepta contraseña, material de clave privada, token, elemento de Keychain o ruta de archivo secreto. SSH usa una configuración preexistente del agente SSH local/con respaldo de Keychain seleccionada por un alias de host no secreto; el modo batch evita solicitudes de contraseña. La configuración, los registros, los fixtures de prueba, los argumentos de comandos y la salida de error nunca deben contener valores de credenciales. Una `execution_identity` suministrada es un nombre de cuenta, no una credencial.

## Contrato de repositorio

### Archivo de plan

`fabric-plan.schema.json` valida un plan JSON versionado. Los campos desconocidos se rechazan para que un control de seguridad mal escrito no pueda debilitar silenciosamente la validación. El ejemplo incluido contiene únicamente marcadores de posición y nunca es una configuración de host utilizable.

```json
{
  "schema_version": 1,
  "macbook": {
    "ssh_host_alias": "agent-fabric-macbook",
    "workspace_share_root": "/Users/leo/projects",
    "future_share_name": "agent-workspaces",
    "lock_root": "/Users/Shared/agent-fabric/locks"
  },
  "mac_mini": {
    "ssh_host_alias": "agent-fabric-macbook",
    "future_mount_target": "/Volumes/agent-workspaces",
    "execution_identity": "<future-dedicated-account>"
  },
  "workspace_areas": [
    { "id": "coding-agent", "relative_path": "packages/coding-agent" }
  ],
  "skills": {
    "transport": "git",
    "repository_url": "https://example.invalid/org/shared-skills.git",
    "local_clone_roots": {
      "macbook": "/Users/leo/projects/shared-skills",
      "mac_mini": "/Users/leo/projects/shared-skills"
    }
  }
}
```

El esquema exige cadenas no vacías, una URL Git HTTPS o SSH sin información de usuario incrustada, ID de área únicos y una identidad de ejecución no marcadora de posición en un plan suministrado por el operador. Prohíbe claves con forma de credencial en todos los niveles (`password`, `secret`, `token`, `private_key`, `keychain` y variantes de mayúsculas/minúsculas o guiones bajos). El validador es la capa semántica autoritativa e impone las siguientes reglas:

| Campo/categoría | Regla de validación |
|---|---|
| Raíz del recurso compartido | `/Users/leo/projects` byte por byte; la ruta canonizada debe seguir siendo igual; rechazar todos los demás valores. |
| Destino de montaje | Absoluto, canónico, no dentro de `/Users/*`, la raíz del recurso compartido o categorías protegidas; el valor predeterminado propuesto es `/Volumes/agent-workspaces`. |
| Raíz de bloqueo | Absoluta, canónica, local a la MacBook, fuera de la raíz del recurso compartido y del árbol del espacio de trabajo; `/Users/Shared/agent-fabric/locks` es la raíz planificada. Nunca se exporta mediante SMB. |
| Áreas del espacio de trabajo | ID ASCII que coinciden con `[a-z0-9][a-z0-9-]{0,62}`; las rutas relativas no contienen componente vacío, `.`, ni `..`; las rutas resueltas permanecen bajo la raíz del recurso compartido; las áreas no pueden superponerse. |
| Habilidades | `transport` es exactamente `git`; las raíces de clon deben ser rutas locales y no rutas de montaje SMB; el transporte de habilidades SMB es un fallo de validación. |
| Rutas protegidas | Rechazar cualquier origen, destino, raíz o contenido solicitado en un directorio HOME, raíz de dotfile/directorio con punto, ubicación de Keychain, credenciales/secretos, cachés, sesiones, registros o configuración de tiempo de ejecución. |

La clasificación de rutas es conservadora: resuelve ancestros existentes con realpath, normaliza colas inexistentes léxicas y rechaza ante error de resolución o ambigüedad de symlink. El comparador de rutas protegidas incluye al menos `/Users`, `$HOME`, `~`, `.ssh`, `.aws`, `.config`, `.cache`, `Library/Keychains`, `Library/Caches`, `Library/Logs`, `Library/Application Support`, `Library/Containers`, `Library/Group Containers` y componentes denominados `secrets`, `credentials`, `sessions`, `logs` y `runtime`. Una ruta permitida como raíz de clon *local* continúa prohibida para exposición o montaje SMB. El manual registra la lista completa de clasificadores revisados para que extensiones futuras requieran una revisión explícita.

La validación emite diagnósticos estructurados `{code, field, category, message}` y termina distinto de cero ante cualquier error. Nunca muestra valores de plan cuyo nombre de campo tenga forma de credencial.

### Estado local, informes y registros

La evidencia operativa pertenece únicamente al host que la generó, bajo una ruta local configurada como `~/Library/Logs/AgentFabric` y `~/Library/Application Support/AgentFabric`; estas son categorías protegidas y nunca candidatas a recurso compartido. Las ejecuciones de prueba usan un directorio temporal. Los registros se crean con permisos exclusivos del propietario donde sea compatible y se rechazan las rutas bajo SMB, la raíz del espacio de trabajo o un destino de montaje.

Un evento JSON Lines contiene `record_version`, marca de tiempo UTC `timestamp`, `event_type`, `host_role`, `operation_id`, `area_id` cuando corresponde, `outcome`, `diagnostic_codes` y un objeto `details` saneado. `details` puede contener alias de host, duraciones, recuentos de bytes, categorías de salida y hashes SHA-256 de identificadores opacos; no puede contener líneas de comandos, volcados de entorno, stderr sin procesar, contenidos del espacio de trabajo, credenciales, rutas privadas de categorías protegidas ni registros de tiempo de ejecución. La salida orientada a personas resume los mismos campos.

### Registro de medición

`fabric-measure` realiza únicamente sondeos de conectividad y carga de trabajo representativa; no cambia ajustes SMB. Escribe un documento JSON validado por ejecución en una ruta de registro local:

```json
{
  "record_version": 1,
  "recorded_at": "2025-01-01T00:00:00Z",
  "plan_fingerprint": "sha256:<digest>",
  "host_role": "macbook|mac-mini",
  "environment": { "network_label": "operator-supplied-nonsecret-label" },
  "probes": {
    "reachability": { "attempts": 20, "successes": 20 },
    "latency_ms": { "p50": 2.1, "p95": 4.0, "max": 5.2 },
    "throughput_mib_s": { "direction": "read|write", "samples": [123.4] },
    "workspace_smb": { "fixture": "representative-tree-v1", "operations": [{ "name": "git-status", "duration_ms": 0, "outcome": "pass" }] }
  },
  "smb_configuration": "unmodified",
  "review": { "status": "pending", "reviewed_at": null, "decision": null }
}
```

El fixture se genera con datos no sensibles fuera del espacio de trabajo real. Mide recorrido de metadatos, creación/lectura de archivos pequeños, lectura/escritura acotada de un archivo grande y estado Git sobre el fixture. Las mediciones son comparables únicamente cuando coinciden la versión de registro, versión de fixture, roles de host y etiqueta de red. Una decisión de ajuste se bloquea salvo que registros revisados cubran conectividad, latencia, rendimiento en ambas direcciones y todas las operaciones del fixture, con una decisión explícita del revisor. El manual pide a los revisores evaluar la latencia p95, regresión de rendimiento, operaciones fallidas y errores de compatibilidad antes de autorizar por separado ajustes de firma, cifrado o rendimiento.

## Protocolo de bloqueo SSH

### Comandos y transporte

La MacBook es la única autoridad de bloqueo. Cualquiera de los hosts puede iniciar trabajo seleccionado, pero un escritor llama al ayudante MacBook mediante un alias SSH configurado, por ejemplo `ssh -o BatchMode=yes -- agent-fabric-macbook fabric-lock acquire`; el JSON de solicitud y la capacidad de liberación fluyen por entrada estándar, nunca como argumentos de línea de comandos. El comando SSH es únicamente texto ilustrativo del protocolo en este recorte; la futura cuenta SSH y la autorización de comandos forzados requieren una puerta separada.

Las solicitudes contienen `protocol_version`, `operation_id` (UUID), `area_id`, `writer_label`, `initiator_role` y una descripción acotada de la operación prevista. El ayudante deriva el nombre de bloqueo como `sha256(area_id)` y nunca interpola datos del usuario en una ruta de shell. Las respuestas son JSON con un código de resultado estable: `ACQUIRED`, `CONTENDED`, `UNREACHABLE`, `INVALID_REQUEST`, `NOT_OWNER`, `RELEASED`, `INSPECTION_REQUIRED` o `RECOVERY_QUARANTINED`.

La raíz de bloqueo de producción tiene propiedad y permisos restrictivos planificados que permiten únicamente a la futura identidad aprobada de servicio de bloqueo administrar el estado de bloqueo. Establecer esa propiedad es un paso de configuración activa aplazado. Este diseño no implica shell remoto genérico, raíz de bloqueo compartida escribible ni autenticación por contraseña.

### Adquisición, liberación y fencing atómicos

1. El iniciador valida su plan y declara un área más el escritor previsto antes de una escritura del espacio de trabajo.
2. El ayudante remoto crea atómicamente `<lock-root>/<area-hash>.lock` usando `mkdir`. El éxito es la única ruta `ACQUIRED`; un directorio existente es `CONTENDED`, incluso cuando los metadatos están incompletos.
3. Después de la creación, el ayudante escribe metadatos en un archivo temporal privado y lo renombra atómicamente a `metadata.json`. Los metadatos incluyen versión del protocolo, ID de área, ID de operación, etiqueta del escritor, rol del iniciador, marcas de tiempo de creación/heartbeat, una época de fencing generada monótonamente y `capability_sha256`; las capacidades sin procesar nunca se almacenan.
4. El ayudante devuelve una capacidad aleatoria de liberación una vez, por stdout de SSH. El llamador la conserva en un archivo efímero local exclusivo del propietario, no en configuración ni en un argumento. Cada wrapper que escribe en el espacio de trabajo debe verificar la propiedad/época actual del bloqueo antes de comenzar y en puntos de comprobación acotados de la operación; debe detenerse al perder autoridad.
5. La liberación lee `{operation_id, capability}` desde stdin, valida el hash y época de la capacidad, renombra atómicamente el directorio de bloqueo a un nombre de cuarentena `released/` en el mismo volumen y luego elimina esa cuarentena. El renombrado impide que un contendiente vea un bloqueo parcialmente eliminado. Se escribe un registro terminal local antes de reconocer la liberación.

`mkdir` proporciona exclusión mutua atómica en el sistema de archivos local de la MacBook. El cliente nunca implementa su propio bloqueo ni trata un bloqueo SMB como autoritativo. Si SSH falla, falla el análisis de respuesta, faltan metadatos o no puede revalidarse la propiedad, el resultado es falla y la escritura no debe comenzar o debe detenerse en su próximo punto de comprobación. El comportamiento de colisión es denegación inmediata (`CONTENDED`); ningún bucle automático de espera o reintento puede convertir la contención en escrituras simultáneas.

### Inspección y recuperación obsoleta

No existe eliminación obsoleta automática basada en tiempo. Un heartbeat anterior al umbral documentado es únicamente una señal de sospecha. Un operador debe ejecutar una inspección que informe metadatos saneados y determine todo lo siguiente: la operación alcanzó un estado terminal conocido o se confirmó que su proceso escritor se detuvo, el host iniciador es nuevamente alcanzable (o fue aislado explícitamente), no hay escritura del espacio de trabajo activa y el área está inactiva.

Solo después de esos hallazgos y de una confirmación separada del operador `recover` puede renombrar atómicamente el directorio de bloqueo específico a una cuarentena `recovered/` en el mismo volumen, escribir un registro de recuperación y eliminarlo. Si falta algún hallazgo, la recuperación falla de forma cerrada. La época del bloqueo recuperado se registra permanentemente; un escritor antiguo reanudado falla su punto de comprobación y no debe escribir. Para herramientas que no puedan realizar puntos de comprobación, la recuperación está prohibida hasta que ese proceso termine y se verifique manualmente que el espacio de trabajo está inactivo. La recuperación nunca limpia un área diferente, nunca elimina datos del espacio de trabajo y nunca se ejecuta automáticamente.

## Estructura de manuales y puertas de autorización

Cada manual comienza con **Propósito**, **No objetivos**, **Entradas**, **Preflight seguro**, **Evidencia que conservar**, **Acciones aplazadas**, **Condiciones de detención por falla** y **Pasos futuros autorizados**.

- **MacBook:** validar la raíz exacta del recurso compartido; inventariar estado local protegido; verificar que la raíz de bloqueo planificada es local y está fuera de SMB; capturar estado previo al cambio de compartición, cuenta, SSH, firewall y sistema de archivos como evidencia local saneada; enumerar el futuro nombre de recurso dedicado, política de acceso, propiedad y requisitos previos de identidad. Crear un recurso/cuenta/ACL/servicio/regla de firewall es `DEFERRED`.
- **Mac mini:** validar conectividad SSH en modo batch, nombre de identidad y destino de montaje seguro; capturar localmente el estado previo de montaje/cuenta/red; indicar que no se crea montaje, automontaje, identidad ni credencial. Explica la configuración independiente de clones Git locales en lugar de sincronización de habilidades SMB.
- **Orquestación:** proporcionar el flujo declarar/adquirir/punto de comprobación/operar/registrar/liberar, estados terminales (`succeeded`, `failed`, `cancelled`), manejo de contención, regla de detención por autoridad inalcanzable y el procedimiento de recuperación inspeccionada anterior. La MacBook sigue siendo orquestador principal incluso cuando la mini inicia trabajo seleccionado.
- **Validación y recuperación:** ejecutar comprobaciones de entrada segura; afirmar que no se expone ningún comando de aplicación; probar transporte de habilidades solo por Git; ejercitar adquisición, contención, liberación exclusiva del propietario, liberación normal y recuperación obsoleta protegida en estado de prueba; exigir registros de medición antes del ajuste; enumerar futuros puntos de verificación de autorización para política de recurso, permisos de identidad, autorización SSH, ajustes SMB revisados y comandos de reversión específicos por host.

## Límites de reversión

Este recorte se revierte únicamente eliminando o revisando artefactos de repositorio y evidencia de prueba local. No tiene configuración activa de host que deshacer.

Un manual de despliegue posterior debe exigir un registro de estado previo al cambio capturado antes de cualquier cambio. Su reversión específica por host puede eliminar únicamente configuración de recurso SMB creada por la infraestructura, configuración de montaje/automontaje de cliente, la identidad dedicada y sus reglas de acceso de infraestructura, y artefactos de bloqueo de infraestructura confirmados como inactivos. Debe restaurar los valores previos registrados cuando corresponda. Nunca debe eliminar contenido de `/Users/leo/projects`, repositorios de habilidades compartidas, cuentas no relacionadas, recursos compartidos no relacionados, habilidades locales del host, datos de Keychain ni configuración de host no relacionada. Un registro previo al cambio faltante, escritor activo/desconocido o propiedad ambigua detiene la reversión y escala para revisión humana.

## Estrategia de pruebas y mapeo de aceptación

Las pruebas se ejecutan sin MacBook, Mac mini, credenciales, acceso de red, `sudo` ni montaje SMB activo.

| Capa | Cobertura |
|---|---|
| Esquema/unidad | Campos requeridos, campos desconocidos, campos con forma de credencial, marcadores de posición, habilidades solo por Git, todas las categorías de ruta protegida, igualdad canónica de raíz de recurso compartido, rechazo de raíz de montaje y bloqueo, recorrido/superposición de áreas. |
| CLI/subproceso | Banner predeterminado de ejecución en seco, rechazo de `--apply`, ninguna invocación de binario privilegiado, redacción de campos sensibles, rechazo de destino de registro local, diagnósticos estables y códigos de salida. |
| Medición | Esquema de registro, salida solo local, ninguna invocación de ajuste, registros faltantes/con revisión pendiente bloquean preparación de ajuste. |
| Máquina de estados de bloqueo | Carrera de adquisición atómica (exactamente un ganador), contención, solicitud malformada, discrepancia de capacidad, liberación exclusiva del propietario, creación de metadatos interrumpida, transporte inalcanzable, cuarentena de liberación y ninguna adquisición simultánea durante transiciones. |
| Recuperación | Un heartbeat antiguo por sí solo no puede limpiar un bloqueo; cada hallazgo de inspección requerido es obligatorio; solo se pone en cuarentena el área solicitada; falla el punto de comprobación de época antigua; escritor sin puntos de comprobación bloquea la recuperación. |
| Manual/contrato | Los marcadores aplazados cubren todas las acciones privilegiadas; no hay ejemplos de credenciales; no hay flujo de habilidades SMB; están presentes MacBook/mini/cuatro fases operativas y prohibiciones de reversión. |

Un transporte SSH local falso y una raíz de estado temporal hacen deterministas las pruebas de bloqueo; las pruebas de concurrencia usan una barrera y varios procesos hijos. Las pruebas de propiedades generan rutas hostiles y cadenas de área. CI trata como falla cualquier prueba que invoque un binario que cambie configuración o produzca archivos fuera de su directorio temporal.

## Configuración activa aplazada

Lo siguiente requiere cambios separados medidos y autorizados y explícitamente no son tareas de implementación para este recorte: cuenta y grupos dedicados; claves SSH, comandos forzados o autorización; creación de recurso SMB, ACL y cambios de servicio; montaje o automontaje de cliente; cambios de firewall; aprovisionamiento/propiedad de raíz de bloqueo; firma, cifrado y ajustes de rendimiento de SMB; y medición de producción contra hosts reales. Esos cambios no pueden comenzar hasta que el plan valide, se revisen las mediciones, se aprueben las decisiones de acceso/identidad/SSH, se capture el estado previo al cambio y se aprueben los comandos de reversión específicos por host.

## Secuencia de implementación

1. Agregar primero esquema, validador seguro, fixtures y pruebas para límites negativos.
2. Agregar CLI de ejecución en seco y escritor de registros locales saneados; luego probar el rechazo de `--apply`.
3. Agregar validación de registros de medición y ejecutor de fixture que no configura.
4. Agregar la máquina de estados de bloqueo, transporte falso, pruebas de carrera/recuperación y manual de protocolo.
5. Agregar manuales MacBook, Mac mini y de validación/recuperación con comprobaciones de acciones aplazadas.

Detenerse y solicitar una decisión de entrega si una unidad de trabajo de implementación supera el presupuesto de revisión de 400 líneas modificadas; no encadenar ni hacer una excepción de tamaño silenciosamente.
