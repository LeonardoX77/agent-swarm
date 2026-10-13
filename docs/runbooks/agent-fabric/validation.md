# Validación de Agent Fabric v1

Validá en orden y detenete ante la primera falla. Las comprobaciones de **solo lectura** no configuran hosts; los despachos de aceptación ejecutan el prompt inocuo y requieren un gate humano previo.

> Para resultados anteriores, límites conocidos y pruebas que no equivalen a aceptación, consultá el [informe histórico de evidencia](test-evidence.md). No sustituye este checklist ni demuestra un despliegue actual.

## Checklist ordenado

- [ ] **Solo lectura — identidad local.** En cada host, con la cuenta existente `leo` en su propio host, ejecutá:

  ```sh
  python3 automation/agent-fabric/bin/fabric-host-preflight --config config/macbook/host.json
  ```

  En la Mac mini reemplazá la configuración por `config/mac-mini/host.json`. Debe devolver `"status": "succeeded"`. Este preflight verifica usuario, presencia de binarios y raíces ya existentes; no comprueba autenticación ni configuración interna de los CLI, y tampoco crea mounts, claves o directorios.

- [ ] **Solo lectura — runtimes locales.** Confirmá manualmente en cada cuenta que Pi + Gentle Pi, OpenCode y Claude Code están instalados y que la autenticación/configuración local de cada uno funciona con la política habitual de esa cuenta. Esta comprobación es independiente del preflight; no copies `HOME`, sesiones, cachés, Keychain ni credenciales entre hosts, ni automatices login.

- [ ] **Solo lectura — SMB.** En la MacBook confirmá que el share existente es `agent-projects` y expone sólo `/Users/leo/projects`. En la Mac mini confirmá que `/Volumes/agent-projects` ya está montado y que `leo` de la Mac mini puede leer y escribir un archivo de prueba acordado por una persona dentro del workspace compartido. Esta prueba de lectura/escritura cambia ese archivo: usá una ruta temporal aprobada y eliminá sólo ese archivo de prueba con la persona presente. Nunca pongas la autenticación SMB en archivos o comandos; macOS la solicita interactivamente y la conserva en el Keychain local.

- [ ] **Solo lectura — endpoint y huella.** Elegí un endpoint por alias: LAN cuando ambos hosts están en la misma red confiable; Tailscale cuando están fuera de esa LAN o cuando es el camino administrado. No alternes sin actualizar y revisar la configuración local del alias. Confirmá que `StrictHostKeyChecking yes` está presente y que la huella del host fue verificada por un canal confiable antes de aceptar una clave nueva.

- [ ] **Solo lectura — SSH restringido.** Revisá localmente cada plantilla de alias y la línea dedicada de `authorized_keys`: el comando forzado debe usar `restrict,command="…fabric-runner --config …"`, sin PTY ni forwarding. Verificá que ambos aliases usen `leo` en su host destino: el de MacBook apunta a `agent-fabric-mac-mini` y el de Mac mini a `agent-fabric-macbook`. El mismo nombre no comparte HOME ni credenciales. No pruebes con shell interactivo, forwarding ni comandos remotos arbitrarios.

- [ ] **Solo lectura — red y SMB de base.** Registrá latencia, resolución de nombre y disponibilidad del mount antes del despacho. Compará con una ejecución local previa si existe. Una degradación de LAN, Tailscale o SMB es una razón para detener la aceptación, no para cambiar la red durante esta lista.

- [ ] **Cambio activo con gate humano — Pi.** Una persona revisa el JSON inocuo de [task-request.example.json](../../../automation/agent-fabric/examples/task-request.example.json), le asigna un UUID nuevo, confirma `"runtime": "pi"` y el allowlist del destino, y confirma el despacho en cada sentido: **MacBook → Mac mini** y **Mac mini → MacBook**, con los comandos de [operation.md](operation.md). Debe devolver `succeeded`, un resultado acotado y actividad saneada en el destino.

- [ ] **Cambio activo con gate humano — OpenCode.** Repetí en cada sentido con UUID nuevo y `"runtime": "opencode"`, usando un prompt sólo de lectura de los ejemplos seguros de [operation.md](operation.md#runtimes-y-ejemplos-seguros). Confirmá que el destino lo permite en `allowed_runtimes`, que devuelve un resultado acotado y que no se usó `--auto`.

- [ ] **Cambio activo con gate humano — Claude Code.** Repetí en cada sentido con UUID nuevo y `"runtime": "claude"`, usando un prompt sólo de lectura. Confirmá que el destino lo permite en `allowed_runtimes`, que el argv contiene `--permission-prompts none` y que una operación que requiera un prompt sin respuesta falla cerrado. Las políticas locales siguen gobernando.

- [ ] **Solo lectura — secretos y logs.** Inspeccioná los resultados y `fabric-activity` local para confirmar que no contienen prompt completo, JSON completo, tokens, credenciales, variables de entorno, contenido del workspace ni stderr crudo. Confirmá también que no se registró una contraseña SMB ni material de Keychain.

## Criterio de aceptación

La v1 queda aceptada sólo si ambos preflights pasan, el mount SMB ya existente permite el acceso acordado, las huellas y restricciones SSH son correctas y los despachos inocuos de Pi, OpenCode y Claude Code en ambos sentidos devuelven resultados saneados. Una falla no autoriza cambios de host: anotá el diagnóstico y pedí una nueva decisión humana para la corrección local.

## Límites de seguridad

- No se configura nada desde esta guía; cualquier alta o corrección privilegiada ocurre interactivamente en el host local y con autorización explícita.
- No se usa `sudo` remoto, shell SSH general ni reenvío de puertos. El comando forzado restringe el transporte, no sandboxea a los runtimes.
- No se habilita un reenvío de puertos en el router.
- Un preflight exitoso no elimina el riesgo de dos escritores concurrentes; coordiná los cambios humanos antes de una tarea que escriba.
- Cada request selecciona explícitamente `pi`, `opencode` o `claude`; el allowlist `allowed_runtimes` es local e independiente en cada host. No hay flags ni shell controlados por la solicitud.
