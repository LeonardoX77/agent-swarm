# Simplificar actividad de agentes

## Contexto absorbido de SDD/OpenSpec

Este documento pasa a ser la fuente operativa de verdad bajo ODD. Conserva como antecedentes históricos los artefactos versionados en `openspec/changes/bootstrap-agent-fabric/`, incluida la verificación fallida. No se ejecutarán nuevas fases SDD/OpenSpec para esta iniciativa.

Decisiones vigentes:

- El kit sigue siendo no aplicable: no configura SMB, SSH, cuentas, montajes ni credenciales.
- Se elimina el mecanismo de locks; la concurrencia no se bloquea ni serializa.
- Se agrega un registro local y saneado de actividad para saber qué agente tocó cada repositorio por última vez.
- Los documentos humanos permanecen en español; código, rutas, comandos y claves de datos siguen en inglés.
- La implementación anterior se conserva en el commit `dce3410` como punto de partida y evidencia histórica.

## TDD efectivo

- Modo: estricto para cambios de comportamiento.
- Runner: `python3 -m unittest discover -s automation/agent-fabric/test`.
- Fuente: decisión de trabajo ODD basada en la evidencia de verificación fallida.

## Tareas

- [x] Consolidar los antecedentes SDD en documentación ODD y declarar la sustitución de proceso.
  - Resultado: un documento ODD legible que resume requisitos, riesgos y evidencia sin depender de fases OpenSpec activas.
  - Comprobación: revisión estructural de enlaces, decisiones y límites no aplicables.

- [x] Reemplazar el sistema de locks por un registro local de actividad de agentes.
  - Resultado: eliminar `fabric-lock` y sus pruebas; agregar una CLI `fabric-activity` que registre eventos locales saneados sin controlar la concurrencia.
  - Comprobación: RED, GREEN, REFACTOR; pruebas de CLI, privacidad, destinos locales y ausencia de enforcement.

- [x] Corregir los controles de seguridad no relacionados con locks.
  - Resultado: errores saneados para registros inseguros, validación canónica resistente a symlinks y puerta de mediciones compatibles.
  - Comprobación: pruebas negativas para rutas, symlinks, redacción y registros de medición incompatibles.

- [x] Actualizar manuales, validar el conjunto y cerrar la transición ODD.
  - Resultado: runbooks que describen sólo observabilidad, documentación ODD consolidada y evidencia de pruebas.
  - Comprobación: suite completa, revisión independiente y estado Git limpio salvo archivos locales ignorados.

## Límites de reversión

Cada tarea sólo modifica archivos del repositorio. No hay cambios de host para revertir. La reversión será un commit focalizado que restaure los archivos de la tarea afectada; nunca borrará proyectos, montajes, HOME ni estado local ajeno.
