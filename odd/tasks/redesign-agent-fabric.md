# Rediseño mínimo de Agent Fabric

## Objetivo

Construir una guía completa y entregables ejecutables para que el agente Pi + Gentle Pi de cada Mac configure su propio host y pueda delegar tareas al agente local del otro host.

## Decisiones vigentes

- MacBook: usuario `leo`, workspace local `/Users/leo/projects`, share SMB `agent-projects`.
- Mac mini: cuenta existente `leo`; mount `/Volumes/agent-projects`. El mismo nombre que en la MacBook no comparte HOME, credenciales ni estado local.
- SSH bidireccional por LAN y Tailscale mediante aliases `agent-fabric-macbook` y `agent-fabric-mac-mini`.
- Cada solicitud remota ejecuta el Pi + Gentle Pi instalado y autenticado localmente en el host destino.
- Los pasos privilegiados usan `sudo` interactivo y se ejecutan localmente; nunca se delega la contraseña.
- Sin locks. `fabric-activity` registra actividad local saneada sin controlar concurrencia.
- Skills compartidas por Git con clones locales; HOME, credenciales, Keychain, sesiones, cachés y configuración permanecen locales.
- Los planes SDD/OpenSpec y ODD anteriores que ya no representen esta solución se eliminan después de transferir la información útil.

## Tareas

- [x] Diseñar la arquitectura mínima y el contrato de solicitud remota.
- [x] Crear los entregables comunes de preflight, configuración, dispatch y runner.
- [x] Crear la guía y configuración local del MacBook.
- [x] Crear la guía y configuración local del Mac mini.
- [x] Crear la guía de operación bidireccional, validación y reversión.
- [x] Eliminar documentación y automatización obsoletas.
- [x] Ejecutar validación completa e independiente.

## Verificación

- Runner de pruebas: `python3 -m unittest discover -s automation/agent-fabric/test`.
- Ninguna prueba o guía debe aplicar cambios reales durante la validación automática.
- Los scripts de configuración deben disponer de `--plan` y aplicar sólo sobre el host local tras confirmación explícita.
