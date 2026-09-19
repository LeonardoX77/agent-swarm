# Tareas de implementación: inicialización de la infraestructura de agentes

## Pronóstico de carga de revisión

| Campo | Valor |
|-------|-------|
| Líneas modificadas estimadas | 1,250–1,650 |
| Riesgo de presupuesto de 400 líneas | Alto |
| PR encadenados recomendados | Sí |
| División sugerida | PR 1 contrato y preflight → PR 2 registros y medición → PR 3 protocolo de bloqueo → PR 4 manuales y comprobaciones de seguridad |
| Estrategia de entrega | ask-on-risk |
| Estrategia de cadena | pending |

Decisión necesaria antes de aplicar: Sí
PR encadenados recomendados: Sí
Estrategia de cadena: pending
Riesgo de presupuesto de 400 líneas: Alto

## Decisión de runtime

El repositorio actualmente no tiene convención de implementación. Usar **Python 3 solo con la biblioteca estándar** (`argparse`, `json`, `pathlib`, `subprocess`, `hashlib`, `tempfile`, `unittest`) para este kit que no aplica cambios. No agregar gestores de paquetes, instaladores, daemons ni dependencias de host.

## Unidades de trabajo

### 1. Contrato de plan y validador de fallo cerrado (PR 1)

- [x] Implementar y verificar el comportamiento. <!-- sdd-owner: implementation -->

**Inicio / superficie de edición permitida:** Agregar únicamente `automation/agent-fabric/schema/fabric-plan.schema.json`, `automation/agent-fabric/lib/validate_plan.py`, `automation/agent-fabric/examples/fabric-plan.example.json`, `automation/agent-fabric/test/test_validate_plan.py` y `automation/agent-fabric/test/fixtures/plan-*.json`.

**Trabajo:** Escribir pruebas RED y luego implementar esquema y validación semántica para versión de esquema, rechazo de campos desconocidos, claves con forma de credencial en cada profundidad, identidad de ejecución no marcadora de posición, raíz de recurso compartido exacta canónica, raíces seguras de montaje y bloqueo, habilidades solo por Git, URL Git seguras, clasificación de rutas protegidas y áreas declaradas del espacio de trabajo únicas y sin superposición. Usar diagnósticos estructurados deterministas y redactar valores con forma de credencial.

**Evidencia:** `python3 -m unittest automation.agent-fabric.test.test_validate_plan` pasa; los fixtures demuestran cada categoría de ruta prohibida, recorrido/superposición, rechazo de habilidades SMB y la distinción válida de ejemplo solo con marcadores de posición.

**Límite de reversión:** Revertir este commit de unidad de trabajo; crea únicamente artefactos de contrato/prueba de repositorio y ningún estado de host.

**Commit:** `feat(agent-fabric): validate fail-closed fabric plans`

### 2. CLI de preflight en seco y registros locales saneados de eventos (PR 1)

- [x] Implementar y verificar el comportamiento. <!-- sdd-owner: implementation -->

**Inicio / superficie de edición permitida:** Agregar únicamente `automation/agent-fabric/bin/fabric-preflight`, `automation/agent-fabric/lib/records.py`, `automation/agent-fabric/test/test_preflight_cli.py`, `automation/agent-fabric/test/test_records.py` y `automation/agent-fabric/test/fixtures/record-*.json`; modificar archivos de la unidad de trabajo 1 únicamente cuando sea necesario para exponer su API pública de validador.

**Trabajo:** Escribir pruebas RED de subproceso y registro, luego implementar un preflight predeterminado de ejecución en seco que acepte `--config` y `--record` local opcional. Rechazar `--apply` con `APPLY_NOT_IMPLEMENTED` distinto de cero; emitir diagnósticos estructurados seguros y registros JSON Lines con permisos exclusivos del propietario donde sea compatible. Rechazar destinos de registro en la raíz del recurso compartido, destino de montaje o categorías protegidas, y asegurar que no se registre línea de comandos, volcado de entorno, stderr sin procesar, ruta protegida ni valor de credencial.

**Evidencia:** Las pruebas unitarias y de subproceso prueban el banner de ejecución en seco, comportamiento de rechazo, rechazo de destino de registro, códigos de salida deterministas, redacción y ausencia de invocaciones privilegiadas/que cambian configuración; ejecutar `python3 -m unittest discover -s automation/agent-fabric/test -p 'test_preflight_cli.py'` y `test_records.py`.

**Límite de reversión:** Revertir este commit; puede permanecer únicamente evidencia temporal de pruebas local, y las pruebas la eliminan.

**Commit:** `feat(agent-fabric): add dry-run preflight and safe local records`

### 3. Artefactos de medición de referencia que no configuran (PR 2)

- [x] Implementar y verificar el comportamiento. <!-- sdd-owner: implementation -->

**Inicio / superficie de edición permitida:** Agregar únicamente `automation/agent-fabric/bin/fabric-measure`, `automation/agent-fabric/lib/measurements.py`, `automation/agent-fabric/test/test_measurements.py`, `automation/agent-fabric/test/test_measure_cli.py` y `automation/agent-fabric/test/fixtures/measurement-*.json`; modificar `automation/agent-fabric/lib/records.py` únicamente para serialización segura compartida.

**Trabajo:** Escribir pruebas RED y luego implementar sondeos de conectividad, latencia, rendimiento direccional y carga de trabajo de árbol representativo generado que no configuran. Producir un registro de medición JSON local validado que contenga huella, versión, rol, etiqueta de red no secreta, versión de fixture y estado de revisión pendiente. Bloquear la preparación de ajuste salvo que registros revisados compatibles cubran todos los sondeos requeridos; nunca invocar ajuste SMB ni escribir fuera del destino de registro local explícito.

**Evidencia:** Las pruebas validan forma/saneamiento de registro, operaciones de fixture, salida solo local, declaración SMB no modificada, comprobaciones de comparabilidad y rechazo de evidencia de medición ausente o con revisión pendiente. Ejecutar `python3 -m unittest discover -s automation/agent-fabric/test -p 'test_measure*.py'`.

**Límite de reversión:** Revertir este commit y eliminar registros de medición locales generados explícitamente; no se cambia configuración ni datos reales del espacio de trabajo.

**Commit:** `feat(agent-fabric): capture non-configuring measurement evidence`

### 4. Máquina de estados de bloqueo local atómica y comprobaciones de protocolo (PR 3)

- [x] Implementar y verificar el comportamiento. <!-- sdd-owner: implementation -->

**Inicio / superficie de edición permitida:** Agregar únicamente `automation/agent-fabric/bin/fabric-lock`, `automation/agent-fabric/lib/lock.py`, `automation/agent-fabric/test/test_lock.py`, `automation/agent-fabric/test/test_lock_race.py`, `automation/agent-fabric/test/test_lock_recovery.py` y `automation/agent-fabric/test/fixtures/lock-*.json`.

**Trabajo:** Escribir pruebas RED, luego implementar solicitudes y respuestas JSON stdin/stdout para la máquina de estados local de la MacBook. Usar nombres de área hasheados, `mkdir` atómico, metadatos temporales privados seguidos de renombrado atómico, devolución única de capacidad solo con hash almacenado, fencing de época, cuarentena de liberación en el mismo volumen y `--state-root` restringido a uso de prueba. Implementar resultados de falla cerrada para solicitud malformada, contención, propiedad, metadatos interrumpidos y transporte inalcanzable sin interpolación de shell ni transporte de secretos por línea de comandos.

**Evidencia:** Las pruebas deterministas de raíz temporal incluyen una carrera de adquisición multiproceso impulsada por barrera con exactamente un ganador; probar adquisición, contención, solicitudes malformadas, discrepancia de capacidad, liberación exclusiva del propietario, ninguna adquisición durante transiciones de cuarentena y falla de punto de comprobación de época antigua. Ejecutar `python3 -m unittest discover -s automation/agent-fabric/test -p 'test_lock*.py'`.

**Límite de reversión:** Revertir este commit; las pruebas eliminan raíces temporales y la invocación de producción no se conecta a configuración ni estado persistente del host.

**Commit:** `feat(agent-fabric): implement fenced local lock protocol`

### 5. Inspección de bloqueo protegida y recuperación manual (PR 3)

- [x] Implementar y verificar el comportamiento. <!-- sdd-owner: implementation -->

**Inicio / superficie de edición permitida:** Modificar únicamente `automation/agent-fabric/lib/lock.py`, `automation/agent-fabric/bin/fabric-lock`, `automation/agent-fabric/test/test_lock_recovery.py` y `automation/agent-fabric/test/fixtures/lock-recovery-*.json`.

**Trabajo:** Escribir pruebas RED de recuperación, luego agregar inspección saneada y recuperación confirmada explícitamente. Exigir cada hallazgo—estado terminal conocido o escritor detenido, conectividad/aislamiento del iniciador, ninguna escritura activa y área inactiva—antes de que un área específicamente nombrada se mueva atómicamente a cuarentena de recuperación en el mismo volumen. Registrar la época retirada, prohibir eliminación automática/solo por tiempo y recuperación de escritores sin puntos de comprobación, y devolver códigos de falla estables cuando la evidencia sea incompleta.

**Evidencia:** Las pruebas prueban que un heartbeat antiguo por sí solo no puede recuperar un bloqueo, que cada hallazgo faltante falla de forma cerrada, que un área diferente no se toca, que la recuperación no es automática y que un escritor antiguo reanudado no puede pasar su comprobación de época. Ejecutar `python3 -m unittest automation/agent-fabric/test/test_lock_recovery.py`.

**Límite de reversión:** Revertir este commit; la recuperación sigue siendo solo de estado de prueba y nunca elimina contenido del espacio de trabajo.

**Commit:** `feat(agent-fabric): require inspected lock recovery`

### 6. Manuales operativos y contrato de seguridad documental (PR 4)

- [x] Implementar y verificar el comportamiento. <!-- sdd-owner: implementation -->

**Inicio / superficie de edición permitida:** Agregar únicamente `docs/runbooks/agent-fabric/macbook.md`, `docs/runbooks/agent-fabric/mac-mini.md`, `docs/runbooks/agent-fabric/orchestration.md`, `docs/runbooks/agent-fabric/validation-recovery.md`, `automation/agent-fabric/test/test_runbook_safety.py` y `automation/agent-fabric/test/fixtures/runbook-required-content.json`.

**Trabajo:** Escribir pruebas de contrato documental, luego redactar cuatro manuales fáciles de escanear, cada uno comenzando con Propósito, No objetivos, Entradas, Preflight seguro, Evidencia que conservar, Acciones aplazadas, Condiciones de detención por falla y Pasos futuros autorizados. Cubrir límite SMB exacto, clones Git de habilidades independientes, habilidades locales del host, identidad solo por parámetro, evidencia local, bloqueo SSH ilustrativo en modo batch, estados terminales, reglas de detención por contención/inalcanzable, recuperación manual obsoleta, criterios de revisión de medición, reversión del recorte actual y límites de reversión futuros específicos por host. Etiquetar como `DEFERRED` todas las acciones de aplicación/privilegiadas; no proporcionar instrucciones ejecutables de configuración activa.

**Evidencia:** Las pruebas documentales verifican las cuatro fases, marcadores aplazados requeridos, exclusiones de estado protegido y ejemplos de credenciales, transporte de habilidades solo por Git, ningún flujo `--apply`, todas las comprobaciones de ciclo de vida de bloqueos, puerta de medición antes del ajuste y prohibiciones de reversión. Ejecutar `python3 -m unittest automation/agent-fabric/test/test_runbook_safety.py` y la suite completa `python3 -m unittest discover -s automation/agent-fabric/test`.

**Límite de reversión:** Revertir este commit; cambia únicamente documentación del repositorio y sus comprobaciones estáticas de seguridad.

**Commit:** `docs(agent-fabric): add safe operator preparation runbooks`

## Verificación de integración

Después de cada unidad de trabajo, ejecutar su evidencia de prueba enfocada indicada. Antes de proponer un recorte de entrega, ejecutar `python3 -m unittest discover -s automation/agent-fabric/test` desde la raíz del repositorio e inspeccionar el diff para cualquier ruta fuera de la superficie de edición permitida de la unidad. No crear, modificar ni probar contra configuración macOS activa, identidades, credenciales, recursos compartidos, montajes, firewall, servicios ni raíces de bloqueo de producción.

## Puerta de entrega

El pronóstico supera el presupuesto de 400 líneas. Bajo `ask-on-risk`, pausar antes de implementación/entrega para obtener una decisión explícita sobre la división propuesta de PR encadenados; no elegir implícitamente una estrategia de cadena ni una excepción de tamaño.
