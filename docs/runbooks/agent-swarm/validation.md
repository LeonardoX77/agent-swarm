# Validación del canal Agent Swarm

Valide el canal activo antes de delegar una tarea. Estas comprobaciones no sustituyen las pausas humanas de `swarm-setup` ni convierten una conexión SSH en autorización para modificar un host.

## Checklist

- [ ] **Registro.** Revise `config/hosts.json`: el destino existe, el alias SSH, catálogo, checkout y PATH corresponden al host que se va a usar, y el share SMB está aprobado.
- [ ] **Identidad local.** Desde el origen, ejecute `automation/agent-swarm/bin/swarm-delegate self`. Debe identificar el host por el prefijo de hostname registrado; un host desconocido se detiene.
- [ ] **Destino.** Ejecute `automation/agent-swarm/bin/swarm-delegate list` y seleccione un nombre de esa salida. No sustituya un alias, IP o etiqueta informal por el nombre del registro.
- [ ] **SSH y catálogo.** Ejecute `automation/agent-swarm/bin/swarm-delegate preflight <destino>`. El JSON debe incluir `"status": "ready"` (también devuelve el destino). Si un spoke devuelve `catalog_missing`, resuelva primero su montaje SMB con el procedimiento aprobado; no envíe la tarea ni cree rutas como atajo.
- [ ] **Huella y restricciones.** Confirme que el alias usa `StrictHostKeyChecking yes`, una clave dedicada y la entrada autorizada con `no-agent-forwarding,no-port-forwarding,no-X11-forwarding`. Estas restricciones no son un sandbox y no se deben relajar para diagnosticar.
- [ ] **Runtimes.** Confirme en el destino que Pi, gentle-pi y Herdr están disponibles y que Pi inició sesión desde la GUI cuando fue necesario. No automatice login ni copie credenciales.
- [ ] **SMB.** Cuando el destino es un spoke, compruebe que el share registrado está montado en el punto esperado y que sólo expone el catálogo aprobado. La autenticación vive en Keychain; no la ponga en comandos, archivos ni logs.
- [ ] **Tarea inocua.** Tras revisión humana, envíe un sobre de sólo lectura con UUID nuevo, proyecto relativo y `mode: executor`. Recupere el resultado con el mismo UUID y cierre la tarea sólo después de verificar que finalizó.
- [ ] **Evidencia.** Conserve únicamente salida JSON saneada, fase y diagnóstico. Verifique que no contiene contraseñas, tokens, claves privadas, prompts completos o contenido innecesario del proyecto.

## Criterio de aceptación

El canal queda listo para una tarea cuando el origen se identifica en el registro, el preflight devuelve `ready`, el catálogo requerido está disponible, las huellas y restricciones SSH fueron revisadas, y una tarea inocua puede recuperarse y cerrarse sin reenviar su sobre.

Una falla no autoriza cambios remotos. Anote el diagnóstico, determine el host responsable y vuelva a la fase de `swarm-setup` o al runbook específico con una persona presente.

## Límites

- No hay garantía distribuida de exactamente una vez. Si SSH falla o el estado es ambiguo, use `recover <destino> <UUID>`; no cree otro UUID para el mismo trabajo.
- Una tarea puede modificar un proyecto compartido. Coordine la ventana de trabajo y revise los cambios; no hay locks automáticos.
- Los resultados históricos están en [Evidencia de pruebas](test-evidence.md); son observaciones con límites, no aceptación del despliegue actual.
