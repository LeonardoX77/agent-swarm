# Orquestación y bloqueo

## Propósito
Permitir trabajo seleccionado desde ambos hosts con MacBook como orquestador principal y autoridad única de bloqueo.

## No objetivos
No se habilita shell remoto general ni se configura SSH.

## Entradas
Área declarada, escritor previsto, ID de operación y alias SSH no secreto.

## Preflight seguro
Valide el plan, alcance MacBook con `ssh -o BatchMode=yes -- agent-fabric-macbook`, y adquiera el bloqueo antes de escribir. La capacidad viaja por stdin, nunca por argumentos.

## Evidencia que conservar
Registre localmente resultado terminal `succeeded`, `failed` o `cancelled`, sin credenciales ni contenido del espacio de trabajo.

## Acciones aplazadas
DEFERRED: cuenta SSH, comando forzado, permisos y provisión de raíz de bloqueo.

## Condiciones de detención por falla
Contención, autoridad inalcanzable, metadatos faltantes o pérdida de época detienen la escritura; no hay espera automática.

## Pasos futuros autorizados
Para un bloqueo obsoleto, inspeccione estado terminal o escritor detenido, conectividad/aislamiento, ausencia de escritura y área inactiva; solo entonces confirme recuperación manual. Nunca recupere automáticamente.
