# Preparación segura de MacBook

## Propósito
Preparar evidencia para el futuro servidor de espacio de trabajo sin cambiar el host.

## No objetivos
No se crea recurso SMB, cuenta, credencial, ACL, servicio ni firewall.

## Entradas
Plan validado; la única raíz propuesta es `/Users/leo/projects`; nombre futuro dedicado, política y propiedad previstos.

## Preflight seguro
Ejecute `fabric-preflight` en modo seco. Verifique que `/Users/Shared/agent-fabric/locks` sea local y no se exporte. Inventarie HOME, dotfiles, Keychain, secretos, cachés, sesiones, registros y runtime como locales.

## Evidencia que conservar
Guarde localmente el estado previo de compartición, cuenta, SSH, firewall y sistema de archivos, saneado y sin credenciales.

## Acciones aplazadas
DEFERRED: crear SMB, cuenta, permisos, servicio o regla de firewall requiere autorización futura.

## Condiciones de detención por falla
Detenga si la raíz no coincide byte por byte, aparece estado protegido o falla el plan.

## Pasos futuros autorizados
Solo tras autorización separada para acceso, identidad, SSH y reversión específica por host.
