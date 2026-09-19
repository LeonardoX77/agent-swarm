# Preparación segura de Mac mini

## Propósito
Comprobar el futuro nodo de ejecución sin montar ni configurar nada.

## No objetivos
No se crea identidad, credencial, montaje ni automontaje.

## Entradas
Alias SSH existente, identidad de ejecución suministrada como parámetro y destino futuro fuera de HOME y estado protegido.

## Preflight seguro
Compruebe SSH batch mediante `ssh -o BatchMode=yes -- agent-fabric-macbook`; una falla detiene el trabajo. El destino propuesto es `/Volumes/agent-workspaces`.

## Evidencia que conservar
Registre localmente estado previo de red, montaje y cuenta sin secretos ni stderr.

## Acciones aplazadas
DEFERRED: identidad, autorización SSH, montaje SMB y configuración de montaje.

## Condiciones de detención por falla
Detenga ante destino en HOME, Keychain, credenciales, caché, sesiones, registros o runtime.

## Pasos futuros autorizados
Use clones Git independientes para habilidades compartidas; las habilidades locales permanecen locales. No se crea ninguna configuración en este recorte.
