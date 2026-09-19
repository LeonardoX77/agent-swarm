```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:4e873f61b07bce194350af0b1f2c6f91e0c6e77b6830b37564e16fa8c5d9f190
verdict: fail
blockers: 5
critical_findings: 5
requirements: 2/8
scenarios: 4/18
test_command: python3 -m unittest discover -s automation/agent-fabric/test
test_exit_code: 0
test_output_hash: sha256:e1737181a75c129a5c03d3fdb54b396e85b16f825f1300be1323a8fd951268d1
build_command: "No disponible: el repositorio no declara sistema de compilación"
build_exit_code: 127
build_output_hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

# Verificación independiente: inicialización de la infraestructura de agentes

**Estado: FALLÓ.** La suite existente pasa, pero la implementación no satisface cinco controles críticos del contrato de seguridad. No está lista para una autorización posterior ni para declararse conforme a la especificación.

## Alcance y artefactos revisados

Se revisaron la propuesta y especificación en español, `design.md`, las seis tareas completadas y `apply-progress.md`, además de los 24 archivos de automatización, pruebas y manuales declarados. No existe `openspec/config.yaml`; por ello no se configuró una comprobación de compilación ni se activó una política estricta de TDD desde configuración.

La superficie funcional inspeccionada (`automation/agent-fabric/**` y `docs/runbooks/agent-fabric/**`) coincide con las superficies de las tareas. El estado nativo autoriza toda la raíz del repositorio. Como todos los elementos aparecen sin seguimiento en Git, no es posible atribuir los elementos ajenos `.gitignore`, `.pi/` y `.specstory/` a esta aplicación; no se modificaron.

La carga de implementación medida es 450 líneas en automatización y manuales, sobre el presupuesto de 400. `apply-progress.md` registra explícitamente `size:exception`, aunque contradice `tasks.md`, que conserva `ask-on-risk` y estrategia de cadena `pending`; no hubo PR ni límite de PR verificable. Esto es una advertencia de carga, no una excepción que reduzca los bloqueos de seguridad.

## Cobertura de especificación

| Requisito | Estado | Evidencia |
|---|---|---|
| Preparación MacBook | Parcial | `fabric-preflight` valida el plan y muestra `mode: dry-run`, pero el rechazo de destino de registro genera traceback y el contrato no es uniforme. |
| Preparación Mac mini | Parcial | Manual en español y validación de destino, pero no hay comprobación real de conectividad SSH por la CLI. |
| Rutas protegidas y secretos | Parcial | Hay filtros léxicos; faltan resolución canónica/ambigüedad de enlaces y el registro inseguro filtra una ruta protegida en traceback. |
| Orquestación y bloqueo autoritativo | Falló | `fabric-lock` escribe en cualquier `--state-root`; recuperación acepta afirmaciones no verificadas sin inspección ni confirmación separada. |
| Habilidades solo por Git | Completo | El validador exige `transport == "git"`; los manuales exigen clones locales y preservan habilidades locales. |
| Medición antes de ajuste SMB | Falló | La medición es sintética de ceros y la puerta acepta registros incompatibles. |
| Validación y puertas futuras | Parcial | Existen manuales y pruebas, pero los bloqueos y medición críticos no cumplen. |
| Recuperación y reversión | Completo | Los manuales limitan este recorte a artefactos y prohíben borrar espacio de trabajo o configuración no relacionada. |

Se consideran completos 2/8 requisitos y 4/18 escenarios: los dos escenarios de distribución de habilidades y los dos de reversión. Los demás solo tienen cobertura parcial o quedan bloqueados por los hallazgos críticos.

## Tareas y progreso

No quedan marcadores de implementación sin completar: `tasks.md` no contiene líneas `- [ ]`. Las seis tareas están marcadas `[x]`. `apply-progress.md` incluye una tabla `TDD Cycle Evidence` con archivo, RED, GREEN, triangulación y refactorización para las seis tareas.

La tabla no sustituye la evidencia independiente: las pruebas actuales son estrechas. Por ejemplo, la puerta de medición se prueba con dos registros aprobados, pero no prueba huella, etiqueta de red, operaciones completas ni rendimiento bidireccional; recuperación no prueba cada hallazgo ausente, otra área, confirmación humana o escritor sin punto de comprobación.

## Comandos y resultados reales

### Suite completa

Comando: `python3 -m unittest discover -s automation/agent-fabric/test`

Salida exacta:

```
...................
----------------------------------------------------------------------
Ran 19 tests in 0.469s

OK
```

Resultado: salida 0; hash `sha256:e1737181a75c129a5c03d3fdb54b396e85b16f825f1300be1323a8fd951268d1`.

### Comprobaciones de seguridad dirigidas

Se ejecutaron, sin configuración macOS activa y usando estado temporal para la prueba de recuperación:

```
$ python3 automation/agent-fabric/bin/fabric-preflight --apply
APPLY_NOT_IMPLEMENTED
[exit=2]

$ python3 automation/agent-fabric/bin/fabric-measure --apply
APPLY_NOT_IMPLEMENTED
[exit=2]

$ python3 automation/agent-fabric/bin/fabric-lock --apply
usage: fabric-lock [-h] --state-root STATE_ROOT
                   {acquire,release,check,inspect,recover}
fabric-lock: error: the following arguments are required: action, --state-root
[exit=2]

$ python3 automation/agent-fabric/bin/fabric-preflight --config <plan-válido-temporal>
mode: dry-run
preflight: valid
[exit=0]

$ gate mismatched approved records
True

$ recovery without inspection/confirmation
RECOVERY_QUARANTINED
```

El escaneo estático de los binarios y bibliotecas no encontró invocaciones activas de `sudo`, `dscl`, `sharing`, `launchctl`, `mount`, `defaults`, `pfctl` o `systemsetup`; la única coincidencia fue el identificador `future_mount_target`. Por tanto, no se observó una acción viva de configuración macOS durante esta verificación. Esto no compensa que `fabric-lock` pueda crear directorios de estado fuera de pruebas cuando se le suministra una ruta.

## Hallazgos críticos y bloqueadores

1. **CRÍTICO — `fabric-lock` no es solo de prueba ni rechaza `--apply` con el contrato requerido.** `automation/agent-fabric/bin/fabric-lock` exige cualquier `--state-root` y construye `LockStore`, que crea directorios y bloqueos en esa ruta. Su `--apply` termina por error de argumentos, no por `APPLY_NOT_IMPLEMENTED`. Contradice el diseño: estado de bloqueo únicamente temporal para pruebas y rechazo uniforme de modo de aplicación.
2. **CRÍTICO — Recuperación de bloqueo no es inspeccionada ni confirmada.** `LockStore.recover()` acepta cuatro booleanos proporcionados por el llamador y recupera inmediatamente; no consume resultado de `inspect`, no exige confirmación separada del operador, no valida alcance del escritor ni preserva una época retirada de forma permanente. La comprobación dirigida devolvió `RECOVERY_QUARANTINED` sin inspección previa.
3. **CRÍTICO — La puerta de medición permite ajuste con evidencia incompatible e incompleta.** `build_measurement()` fabrica métricas cero; `adjustment_ready()` solo comprueba dos roles y `approved`. Aceptó huellas y etiquetas de red distintas, no exige direcciones de rendimiento opuestas ni todas las operaciones representativas. No cumple la puerta de medición antes de firma, cifrado o rendimiento SMB.
4. **CRÍTICO — El manejo de registros inseguros filtra una ruta protegida y no devuelve diagnóstico seguro.** `fabric-preflight --record /Users/leo/projects/verification-record.jsonl` lanzó traceback de `ValueError`, incluyendo la ruta protegida, en lugar de un diagnóstico estructurado y saneado. Esto viola los límites de registros y de error establecidos por diseño.
5. **CRÍTICO — La validación de rutas no implementa la canonización y rechazo de enlaces ambiguos requeridos.** `validate_plan.py` usa comprobaciones léxicas con `PurePosixPath`; no resuelve ancestros mediante `realpath`, no detecta enlaces simbólicos ambiguos y no garantiza que las rutas reales permanezcan bajo los límites aprobados.

## TDD y calidad de aserciones

No se encontró activación explícita de TDD estricto: `openspec/config.yaml` no existe y el progreso solo aporta la tabla de ciclos. La evidencia de ciclos está presente, pero las aserciones no demuestran el contrato completo. No se detectaron tautologías o bucles fantasma; sí se detectó cobertura de seguridad insuficiente: pruebas de humo de manuales por presencia de texto, una prueba de recuperación que no recorre hallazgos individuales y una prueba de medición que valida una condición demasiado débil. La conformidad TDD estricta no puede afirmarse.

## Estado estructurado y acción

Estado nativo consumido: cambio `bootstrap-agent-fabric`, estado `ready`, almacén `openspec`, `actionContext.mode: repo-local`, raíz de trabajo autorizada `/Users/leo/projects/leo/mac-agent-fabric`, y `nextRecommended: archive`. La verificación es opcional y no modifica esa recomendación; los cinco hallazgos permanecen riesgos reales en el informe. No hubo bloqueo nativo previo ni se otorgó autoridad de edición.

## Bloqueadores exactos

- Corregir el límite de estado y rechazo uniforme de aplicación de `fabric-lock`.
- Exigir inspección verificable y confirmación manual separada antes de recuperación.
- Implementar medición real/no configuradora y compatibilidad completa antes de que la puerta permita ajuste.
- Emitir errores estructurados saneados para destinos de registro inseguros.
- Implementar resolución canónica de rutas y rechazo ante enlaces ambiguos.
