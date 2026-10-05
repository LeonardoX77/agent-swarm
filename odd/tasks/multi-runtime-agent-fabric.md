# Soporte multiagente de Agent Fabric

## Objetivo

Permitir que cada solicitud remota elija explícitamente qué CLI local ejecutará el host destino: Pi + Gentle Pi, OpenCode o Claude Code.

## Decisiones vigentes

- Agent Fabric sigue siendo una capa de transporte y ejecución restringida; no es un agente ni elige agentes automáticamente.
- La solicitud declara `runtime` con uno de estos valores: `pi`, `opencode` o `claude`.
- Cada host mantiene una allowlist local `allowed_runtimes`; inicialmente ambos habilitan los tres CLI.
- Los comandos se construyen desde una tabla cerrada, sin shell ni flags aportados por la solicitud.
- Cada CLI usa exclusivamente la identidad, configuración, credenciales, sesiones y permisos locales del usuario destino.
- El preflight verifica los binarios habilitados, pero no autentica ni modifica las cuentas de los proveedores.
- La salida, timeout, mapping de workspace, usuario esperado, entorno mínimo y registro de actividad conservan los límites existentes.

## Tareas

- [x] Extender el contrato y la configuración con selección y allowlist de runtime.
- [x] Implementar ejecución cerrada para Pi, OpenCode y Claude Code.
- [x] Extender preflight, ejemplos y pruebas de seguridad para los tres CLI.
- [x] Actualizar arquitectura, instalación, operación, validación y rollback.
- [x] Ejecutar validación completa e independiente.

## Verificación

- Runner: `python3 -m unittest discover -s automation/agent-fabric/test`.
- Ninguna prueba invoca agentes reales, abre conexiones SSH ni aplica configuración del host.
- Deben comprobarse argv exactos, denegación de runtimes desconocidos/no autorizados y ausencia de shell.
