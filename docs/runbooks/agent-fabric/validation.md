# Validación de Agent Fabric v1

Validá en orden y detenete ante la primera falla. Las comprobaciones de **solo lectura** no configuran hosts; los despachos de aceptación ejecutan el prompt inocuo y requieren un gate humano previo.

## Checklist ordenado

- [ ] **Solo lectura — identidad local.** En cada host, con la cuenta correcta (`leo` en MacBook y `jarvis` en Mac mini), ejecutá:

  ```sh
  python3 automation/agent-fabric/bin/fabric-host-preflight --config config/macbook/host.json
  ```

  En la Mac mini reemplazá la configuración por `config/mac-mini/host.json`. Debe devolver `"status": "succeeded"`. Este preflight verifica usuario, binarios y raíces ya existentes; no crea mounts, claves ni directorios.

- [ ] **Solo lectura — Pi y Gentle Pi locales.** Confirmá en cada cuenta que Pi está instalado y que su autenticación local ya funciona con la política habitual de esa cuenta. No copies `HOME`, sesiones, cachés, Keychain ni credenciales entre hosts.

- [ ] **Solo lectura — SMB.** En la MacBook confirmá que el share existente es `agent-projects` y expone sólo `/Users/leo/projects`. En la Mac mini confirmá que `/Volumes/agent-projects` ya está montado y que `jarvis` puede leer y escribir un archivo de prueba acordado por una persona dentro del workspace compartido. Esta prueba de lectura/escritura cambia ese archivo: usá una ruta temporal aprobada y eliminá sólo ese archivo de prueba con la persona presente. Nunca pongas la autenticación SMB en archivos o comandos; macOS la solicita interactivamente y la conserva en el Keychain local.

- [ ] **Solo lectura — endpoint y huella.** Elegí un endpoint por alias: LAN cuando ambos hosts están en la misma red confiable; Tailscale cuando están fuera de esa LAN o cuando es el camino administrado. No alternes sin actualizar y revisar la configuración local del alias. Confirmá que `StrictHostKeyChecking yes` está presente y que la huella del host fue verificada por un canal confiable antes de aceptar una clave nueva.

- [ ] **Solo lectura — SSH restringido.** Revisá localmente cada plantilla de alias y la línea dedicada de `authorized_keys`: el comando forzado debe usar `restrict,command="…fabric-runner --config …"`, sin PTY ni forwarding. Verificá que el alias de MacBook apunte a `agent-fabric-mac-mini` como `jarvis` y el de Mac mini a `agent-fabric-macbook` como `leo`. No pruebes con shell interactivo, forwarding ni comandos remotos arbitrarios.

- [ ] **Solo lectura — red y SMB de base.** Registrá latencia, resolución de nombre y disponibilidad del mount antes del despacho. Compará con una ejecución local previa si existe. Una degradación de LAN, Tailscale o SMB es una razón para detener la aceptación, no para cambiar la red durante esta lista.

- [ ] **Cambio activo con gate humano — MacBook → Mac mini.** Una persona revisa el JSON inocuo de [task-request.example.json](../../../automation/agent-fabric/examples/task-request.example.json), le asigna un UUID nuevo y confirma el despacho. Ejecutalo desde la MacBook con el comando de [operation.md](operation.md#macbook--mac-mini). Debe devolver `succeeded`, un resultado acotado y actividad saneada en la Mac mini.

- [ ] **Cambio activo con gate humano — Mac mini → MacBook.** Una persona revisa una copia con UUID nuevo e `initiator` igual a `mac-mini`, y confirma el despacho. Ejecutalo desde la Mac mini con el comando de [operation.md](operation.md#mac-mini--macbook). Debe devolver `succeeded`, un resultado acotado y actividad saneada en la MacBook.

- [ ] **Solo lectura — secretos y logs.** Inspeccioná los resultados y `fabric-activity` local para confirmar que no contienen prompt completo, JSON completo, tokens, credenciales, variables de entorno, contenido del workspace ni stderr crudo. Confirmá también que no se registró una contraseña SMB ni material de Keychain.

## Criterio de aceptación

La v1 queda aceptada sólo si ambos preflights pasan, el mount SMB ya existente permite el acceso acordado, las huellas y restricciones SSH son correctas y los dos despachos inocuos devuelven resultados saneados. Una falla no autoriza cambios de host: anotá el diagnóstico y pedí una nueva decisión humana para la corrección local.

## Límites de seguridad

- No se configura nada desde esta guía; cualquier alta o corrección privilegiada ocurre interactivamente en el host local y con autorización explícita.
- No se usa `sudo` remoto, shell SSH general ni reenvío de puertos.
- No se habilita un reenvío de puertos en el router.
- Un preflight exitoso no elimina el riesgo de dos escritores concurrentes; coordiná los cambios humanos antes de una tarea que escriba.
