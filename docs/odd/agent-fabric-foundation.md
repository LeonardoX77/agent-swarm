# Fundación ODD para Agent Fabric

## Decisión vigente

**Organic Driven Development (ODD) es el proceso activo para Agent Fabric.** Los artefactos de `openspec/changes/bootstrap-agent-fabric/` son evidencia histórica: documentan decisiones, implementación y una verificación fallida previa, pero no abren fases ni autorizan trabajo OpenSpec/SDD adicional.

Esta fundación conserva un kit de preparación revisable y no aplicable. Su propósito es hacer verificables los límites y las decisiones previas a una futura autorización humana; no modifica la configuración de ningún host.

## Lectura rápida

1. Usá ODD y `odd/tasks/simplify-agent-activity-log.md` como guía operativa de la transición.
2. Tratá OpenSpec como antecedente archivado, incluida su verificación fallida histórica.
3. Compartí sólo el espacio de trabajo aprobado y mantené el estado sensible en cada host.
4. Usá `fabric-activity` sólo para observabilidad local saneada: registra actividad de agente, repositorio y host, sin autorizar ni bloquear escritores concurrentes.
5. Elegí firma, cifrado y rendimiento SMB sólo después de revisar mediciones compatibles.

## Arquitectura retenida

| Área | Decisión retenida |
|---|---|
| Kit de preparación | Automatización y manuales no aplicables: validan y producen evidencia local, sin configurar hosts. |
| Límite SMB | La MacBook es el host principal del espacio de trabajo; el único candidato a recurso SMB dedicado es `/Users/leo/projects`. |
| Estado local | HOME, dotfiles, Keychain, credenciales, secretos, cachés, sesiones, registros y configuración de ejecución permanecen locales a cada host. |
| Habilidades compartidas | Se distribuyen por un repositorio Git versionado, con clones locales independientes en ambos hosts. SMB no sincroniza habilidades. |
| Decisiones SMB | Firma, cifrado y rendimiento se deciden sólo después de medir conectividad, latencia, rendimiento y operaciones representativas de SMB, y revisar evidencia compatible. |
| Actividad de agentes | `fabric-activity` conserva localmente la última actividad saneada de agente, repositorio y host. Es observabilidad; no autoriza, bloquea ni coordina escritores. |

### Límite de la MacBook y Mac mini

La MacBook sigue siendo el host principal de espacio de trabajo y de orquestación. La Mac mini es el nodo de ejecución normal; ambos pueden iniciar trabajo remoto SSH seleccionado cuando exista una autorización futura apropiada.

El recurso compartido, si llegara a autorizarse, transportará únicamente contenido aprobado del espacio de trabajo. Ningún directorio HOME ni estado sensible del host es parte del límite compartido.

### Política de actividad local

`fabric-activity` registra actividad saneada local al host para identificar la última interacción de un agente con un repositorio. El registro excluye credenciales, secretos, contenido sensible y estado de ejecución.

La política es estrictamente observacional:

- no concede autoridad para escribir;
- no bloquea ni serializa escritores concurrentes;
- no usa SSH para imponer exclusión;
- no sustituye la coordinación humana ni la revisión de cambios.

## Qué no se configurará

Este recorte no configura ni autoriza:

- recursos SMB, ACL, servicios, montajes o automontajes;
- cuentas, grupos, identidades de ejecución, credenciales, claves SSH, comandos forzados ni reglas de autorización;
- firewall, privilegios, daemons, agentes de lanzamiento ni cambios de configuración macOS;
- ajustes de firma, cifrado o rendimiento de SMB;
- exposición, sincronización o registro por SMB de habilidades, HOME o estado sensible;
- mecanismos que impongan exclusión o serialización de concurrencia.

Las identidades y los cambios de host futuros requieren una decisión separada, evidencia medida, estado previo al cambio y un plan de reversión específico por host.

## Informe histórico y controles corregidos

El informe archivado de verificación fallida registró cinco brechas de la implementación anterior. Es un antecedente útil, no una descripción del control vigente. La transición ODD ya corrigió los controles de concurrencia anterior, registros, rutas y medición:

| Hallazgo histórico | Control vigente corregido |
|---|---|
| El mecanismo anterior podía crear estado fuera de pruebas y no mantenía el límite no aplicable. | `fabric-activity` sólo registra observabilidad local saneada; no aplica configuración ni decide concurrencia. |
| La recuperación del mecanismo anterior dependía de afirmaciones del llamador. | No existe recuperación operativa: el registro no controla escritores y la coordinación permanece humana. |
| La puerta SMB aceptaba evidencia incompleta o incompatible. | Las decisiones SMB exigen huella, etiqueta de red, rendimiento bidireccional y operaciones representativas completas antes de ajustar. |
| Un destino de registro rechazado podía revelar una ruta protegida. | Los diagnósticos y registros se mantienen estructurados y saneados, sin rutas protegidas ni secretos. |
| La validación de rutas era léxica y ambigua ante enlaces simbólicos. | La validación canónica resuelve ancestros y rechaza ambigüedades de enlaces simbólicos. |

La discrepancia histórica de carga de revisión entre `tasks.md` y `apply-progress.md` sigue siendo evidencia archivada; no modifica estos límites ni los controles corregidos.

## Evidencia archivada

Consultá estos materiales sólo para reconstruir decisiones y riesgos previos:

- `openspec/changes/bootstrap-agent-fabric/proposal.md`: alcance original y límites de seguridad.
- `openspec/changes/bootstrap-agent-fabric/design.md`: diseño técnico y contratos esperados.
- `openspec/changes/bootstrap-agent-fabric/specs/agent-fabric-bootstrap/spec.md`: requisitos y escenarios históricos.
- `openspec/changes/bootstrap-agent-fabric/verify-report.md`: informe histórico de verificación fallida.
- `odd/tasks/simplify-agent-activity-log.md`: decisiones ODD vigentes y tareas de transición.

## Checklist para trabajo posterior

- [ ] El trabajo sigue ODD; no inicia fases SDD/OpenSpec para esta iniciativa.
- [ ] Los cambios respetan el kit no aplicable y el límite SMB del espacio de trabajo.
- [ ] El estado sensible y las habilidades locales permanecen locales al host.
- [ ] Las habilidades compartidas usan Git, no SMB.
- [ ] Toda decisión SMB se apoya en mediciones compatibles y revisadas.
- [ ] La actividad de agentes se implementa sólo como observabilidad local saneada.
- [ ] Los controles de concurrencia anterior, registros, rutas y medición siguen corregidos y comprobados antes de una autorización de configuración activa.
