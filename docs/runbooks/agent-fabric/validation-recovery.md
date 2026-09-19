# Validación, medición y recuperación

## Propósito
Confirmar preparación no aplicable y definir límites de recuperación y reversión.

## No objetivos
Este recorte no tiene configuración activa que revertir.

## Entradas
Plan validado, registros locales saneados de actividad y registros locales de medición.

## Preflight seguro
Ejecute preflight seco; use `fabric-activity` para comprobar que la actividad local saneada registra agente, repositorio y host sin autorizar ni bloquear escritores. Las habilidades compartidas usan solo Git; SMB no transporta habilidades.

## Evidencia que conservar
Conserve registros locales saneados de conectividad, latencia, rendimiento y operaciones representativas. La configuración SMB permanece sin modificación.

## Acciones aplazadas
DEFERRED: no se selecciona firma, cifrado ni rendimiento SMB hasta revisar registros comparables aprobados de ambos hosts.

## Condiciones de detención por falla
Evidencia de medición ausente, pendiente o incompatible, ruta protegida o transporte distinto de Git impiden avanzar hacia una configuración activa. La actividad concurrente no es una condición para autorizar ni detener escritores.

## Pasos futuros autorizados
Una reversión futura requiere estado previo y solo puede eliminar configuración creada por la infraestructura. No se debe eliminar contenido del espacio de trabajo, habilidades locales, Keychain, cuentas ni configuración no relacionada.
