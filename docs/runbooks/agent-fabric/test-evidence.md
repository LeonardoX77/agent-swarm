# Evidencia histórica de pruebas de Agent Fabric

> **Estado:** registro histórico, no protocolo de producción ni aceptación de un despliegue. La comprobación vigente está en [validación](validation.md).

## Cómo interpretar la evidencia

- **PASS** confirma únicamente la observación descrita en el entorno y momento anotados.
- **FAIL**, **BLOCKED**, **SKIP** e **INCONCLUSIVE** no deben reinterpretarse como una capacidad disponible.
- Los nombres de tabs, panes, PIDs, nonces y rutas temporales son identificadores históricos, no valores reutilizables.
- Las observaciones no sustituyen el registro actual, una huella verificada, login de Pi, un montaje SMB ni una aceptación del canal.

## Observaciones útiles de Herdr + Pi

| Área | Observación histórica | Límite |
| --- | --- | --- |
| Sesión propia | Una tab y un agente Pi propios pudieron responder un nonce y limpiarse sin cerrar recursos preexistentes. | No demuestra aislamiento completo ni garantía de producción. |
| Resultado JSONL | El adaptador encontró el mensaje exacto de usuario y una respuesta final descendiente en el JSONL de la sesión propia. | Los snapshots de pantalla no correlacionan por sí mismos un turno. |
| Ledger | Persistir intención antes de crear, iniciar, enviar y cerrar permitió conservar estados ambiguos para recuperación. | No aporta exactly-once distribuido ni autoriza reenvío automático. |
| Envelope | El contrato correcto contiene seis campos y `mode: executor`; entradas extra o modos no admitidos se rechazan. | La validación no sustituye el control humano del alcance. |
| Cierre | Un cierre verificado conserva el resultado y confirma `tab_not_found` para la tab propia. | No autoriza cerrar tabs, agentes o sesiones ajenos. |
| Límites JSONL | Se observó una línea de sistema cercana a 99 KiB; el lector admite hasta 1 MiB por línea y 8 MiB por archivo. | Son límites del adaptador, no una promesa sobre futuros formatos de Pi. |

## Comunicación y recuperación

Las pruebas históricas mostraron que una desconexión controlada del cliente SSH o un timeout de espera no prueban la cancelación del trabajo remoto. La recuperación segura conserva el UUID y consulta el estado; no crea un segundo trabajo ni reenvía un prompt ante ambigüedad.

También se observó que Herdr puede emitir errores tipados por stdout o stderr, y que `herdr agent prompt` rechaza `--timeout` sin `--wait`. El adaptador envía el prompt sin esas opciones y analiza ambos canales de error.

## Límites que permanecen abiertos

1. Probar fallas generales de red y servidor con recuperación sin reenvío ciego.
2. Verificar en cada despliegue el catálogo SMB limitado, aliases, huellas y ambas direcciones SSH.
3. Mantener login y credenciales de Pi locales al host; una observación de GUI no demuestra autenticación no interactiva distinta.
4. Coordinar escritores humanos: el canal no implementa locks ni resolución de conflictos.
5. Evaluar cualquier cambio de runtime o protocolo como trabajo nuevo, con evidencia nueva.

## Evidencia local disponible

Las pruebas deterministas del adaptador se ejecutan con fixtures y no abren una GUI viva ni configuran hosts:

```sh
python3 -m unittest automation/agent-fabric/test/test_herdr_task.py
python3 -m unittest discover -s automation/agent-fabric/test
```

Antes de operar, siga [validación](validation.md), [Canal SSH](ssh-channel.md) y [Montaje SMB](smb-mount.md). Para el contrato de tareas, consulte [Tareas Herdr + Pi](herdr-tasks.md).
