# Orquestación y actividad

## Propósito
Permitir trabajo seleccionado desde ambos hosts con MacBook como orquestador principal y con actividad local visible para cada repositorio.

## No objetivos
No se habilita shell remoto general ni se configura SSH. `fabric-activity` no autoriza, bloquea ni serializa escritores concurrentes.

## Entradas
Área declarada, agente, repositorio, host e ID de operación; el alias SSH no contiene secretos.

## Preflight seguro
Valide el plan y, cuando corresponda, alcance MacBook con `ssh -o BatchMode=yes -- agent-fabric-macbook`. Antes o después de trabajar, use `fabric-activity` para registrar actividad local saneada. El registro nunca determina si un escritor puede continuar.

## Evidencia que conservar
Conserve localmente la última actividad saneada de agente, repositorio y host, junto con el resultado terminal `succeeded`, `failed` o `cancelled`; no guarde credenciales ni contenido del espacio de trabajo.

## Acciones aplazadas
DEFERRED: cuenta SSH, comando forzado y permisos requieren autorización futura.

## Condiciones de detención por falla
Detenga el preflight si faltan metadatos requeridos, el plan falla o el alcance SSH autorizado no está disponible. La actividad concurrente no detiene ni concede permiso a escritores.

## Pasos futuros autorizados
Revise el último registro local saneado para observabilidad y coordinación humana. No use SSH ni el registro de actividad para imponer exclusión entre escritores.
