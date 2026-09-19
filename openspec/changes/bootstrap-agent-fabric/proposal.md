# Inicialización de la infraestructura de agentes

Crear automatización revisable y manuales operativos para una infraestructura de agentes de dos Mac sin cambiar la configuración privilegiada activa. La MacBook se preparará como servidor principal de espacio de trabajo y host de orquestación; la Mac mini se preparará como nodo de ejecución normal. Los entregables hacen repetible un despliegue posterior autorizado, manteniendo claramente separados el contenido del espacio de trabajo, las identidades y el estado sensible local de cada host.

## Intención

Establecer una base operacionalmente segura para trabajo compartido de agentes entre una MacBook y una Mac mini. Este primer recorte produce guías parametrizadas de preparación, validación, recuperación y reversión; no cambios activos de SMB, cuentas, servicios, firewall o privilegios.

## Alcance

### Incluido

- Plantillas de automatización y manuales operativos para las cuatro fases operativas requeridas:
  1. Preparación del servidor MacBook.
  2. Preparación del cliente Mac mini.
  3. Reglas de orquestación bidireccional.
  4. Validación, recuperación y reversión.
- Un diseño de recurso compartido SMB dedicado al espacio de trabajo únicamente para `/Users/leo/projects` en la MacBook.
- Configuración parametrizada para una nueva identidad dedicada de ejecución remota con mínimos privilegios, incluidos los datos de entrada, permisos previstos, pasos de verificación y aplazamiento explícito de la creación de la cuenta.
- Procedimientos de medición de red y SMB de referencia que se recopilarán antes de elegir la firma, el cifrado o los ajustes de rendimiento de SMB.
- Guía de orquestación basada en SSH que permite que cualquiera de los hosts inicie trabajo remoto seleccionado, manteniendo a la MacBook como host principal de orquestación.
- Procedimientos de bloqueo autoritativo local de la MacBook para un escritor por área declarada del espacio de trabajo, alcanzados mediante SSH.
- Un flujo de trabajo de repositorio Git versionado para habilidades compartidas, con clones locales independientes en ambos hosts y un límite explícito para habilidades locales del host.
- Comprobaciones de seguridad que distinguen artefactos de ejecución en seco/planificación de comandos que requerirán futura autorización privilegiada.

### Explícitamente excluido

- Aplicar configuración privilegiada activa en cualquiera de las Mac.
- Crear la identidad dedicada de ejecución remota, credenciales SSH, recurso compartido SMB, daemon, agente de lanzamiento, regla de firewall o configuración de servicio privilegiado.
- Compartir `/Users/leo`, cualquier directorio HOME, dotfiles, datos de Keychain, credenciales, secretos, cachés, sesiones, registros o configuración de tiempo de ejecución.
- Seleccionar o imponer ajustes de firma, cifrado o rendimiento de SMB antes de revisar las mediciones de referencia.
- Sincronizar habilidades mediante SMB.
- Reemplazar la MacBook como host autoritativo de bloqueos o permitir varios escritores simultáneos dentro de una misma área declarada del espacio de trabajo.

## Modelo operativo objetivo

| Área | Decisión para este recorte |
|---|---|
| Servidor principal de espacio de trabajo | La MacBook sirve el recurso SMB dedicado al espacio de trabajo únicamente para `/Users/leo/projects`. |
| Host principal de orquestación | La MacBook es primaria; cualquiera de los hosts puede orquestar trabajo remoto SSH seleccionado. |
| Nodo de ejecución normal | Mac mini. |
| Identidad remota | Se parametriza una identidad diferenciada con mínimos privilegios, pero no se crea. |
| Límite de contenido compartido | SMB transporta únicamente contenido aprobado del espacio de trabajo. |
| Estado sensible y de tiempo de ejecución | Cada host conserva HOME, Keychain, credenciales, secretos, cachés, sesiones, registros y configuración de tiempo de ejecución en disco local. |
| Habilidades compartidas | Un repositorio Git versionado, clonado localmente en ambos hosts. |
| Habilidades locales del host | Permanecen locales y no se sincronizan. |
| Concurrencia | Un escritor por área declarada del espacio de trabajo; los bloqueos locales de la MacBook son autoritativos y se acceden mediante SSH. |

## Entregables propuestos

### 1. Manual y automatización de preparación del servidor MacBook

Proporcionar una lista de verificación orientada al operador y automatización parametrizada que no aplica cambios y que:

- verifica la ruta canónica `/Users/leo/projects` y rechaza raíces de recurso compartido más amplias;
- registra el futuro nombre dedicado del recurso SMB, la ruta aprobada, la política de acceso prevista y los requisitos previos de propiedad;
- identifica cada comando que requeriría privilegios posteriormente y lo etiqueta como aplazado;
- define el directorio de bloqueos en el volumen local de la MacBook, las convenciones de adquisición/liberación de bloqueos, la inspección de bloqueos obsoletos y las expectativas de acceso SSH;
- inventaría rutas exclusivamente locales que nunca deben ingresar al recurso compartido; y
- captura el estado previo al cambio del host necesario para validar o revertir con seguridad un despliegue futuro.

### 2. Manual y automatización de preparación del cliente Mac mini

Proporcionar procedimientos parametrizados que no aplican cambios y que:

- validan la conectividad de red y los requisitos previos de SSH hacia la MacBook;
- definen el destino previsto de montaje SMB dedicado y exigen que permanezca fuera de HOME, ubicaciones de secretos, caché, sesiones, registros y configuración de tiempo de ejecución;
- describen cómo el trabajo de ejecución identifica su área declarada del espacio de trabajo y adquiere/libera el bloqueo autoritativo de la MacBook mediante SSH;
- especifican que la futura identidad de ejecución se proporciona como parámetro y que no se crea; y
- capturan el estado y los requisitos previos del host local antes de cualquier cambio futuro de montaje o cuenta.

### 3. Reglas de orquestación bidireccional

Documentar un protocolo pequeño y explícito para el trabajo iniciado desde cualquiera de los hosts:

1. Declarar el área del espacio de trabajo y el escritor previsto antes de cambiar contenido del espacio de trabajo.
2. Alcanzar la MacBook mediante SSH y adquirir su bloqueo autoritativo para esa área.
3. Ejecutar la operación remota o local seleccionada usando los parámetros de identidad dedicada de ejecución cuando corresponda.
4. Liberar el bloqueo únicamente después de que la operación del espacio de trabajo alcance un estado terminal definido.
5. Registrar el contexto de fallas localmente sin colocar credenciales, registros sensibles ni estado de tiempo de ejecución en SMB.

El manual definirá el manejo de colisiones, el comportamiento ante host de bloqueos inalcanzable, la recuperación de bloqueos abandonados/obsoletos y la regla de que una falla de bloqueo impide las escrituras en lugar de habilitar una escritura simultánea de mejor esfuerzo.

### 4. Manual de medición de referencia, validación, recuperación y reversión

Proporcionar un plan de medición previo a la decisión que cubra conectividad de red, latencia, rendimiento, comportamiento de SMB bajo actividad representativa del espacio de trabajo y los criterios de impacto usados posteriormente para elegir la firma, el cifrado y los ajustes de rendimiento. Los resultados deben registrarse antes de seleccionar configuración.

Las secciones de validación y recuperación incluirán:

- validación en seco de todos los valores de parámetros y límites de ruta;
- comprobaciones de que no se proponga ningún HOME ni categoría protegida de estado local para exposición SMB;
- comprobaciones de que Git, en lugar de SMB, sea el transporte de habilidades compartidas;
- comprobaciones del protocolo de bloqueo para adquisición exitosa, contención, liberación y recuperación de bloqueos obsoletos;
- puntos de verificación de despliegue futuro; y
- pasos de reversión que restauren el estado previo al cambio capturado y eliminen únicamente la configuración creada por un despliegue posterior autorizado.

## Áreas afectadas

| Área | Tipo de cambio esperado | Impacto |
|---|---|---|
| `openspec/changes/bootstrap-agent-fabric/` | Propuesta y posteriores artefactos de planificación | Documenta el modelo operativo aprobado y los límites de implementación. |
| Operaciones de MacBook | Entrada para futuro manual/automatización | Define una ruta de preparación acotada de recurso compartido de espacio de trabajo y bloqueo autoritativo sin aplicarla. |
| Operaciones de Mac mini | Entrada para futuro manual/automatización | Define la preparación de cliente y nodo de ejecución sin montarlo ni configurarlo. |
| Orquestación SSH | Entrada para futuro manual/automatización | Establece las reglas de iniciación bidireccional y bloqueo autoritativo de la MacBook. |
| Distribución de habilidades | Entrada para futuro manual/automatización | Establece clones Git como único mecanismo de habilidades compartidas. |

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Una exportación SMB amplia o accidental expone estado privado del host. | Fijar la raíz prevista como `/Users/leo/projects`, rechazar raíces HOME y dotfiles, y validar el límite antes de cualquier futuro paso de aplicación. |
| Una identidad futura tiene privilegios excesivos. | Parametrizar una identidad dedicada, documentar los requisitos de mínimos privilegios y aplazar la creación/autorización a un recorte posterior aprobado. |
| El ajuste prematuro de seguridad o rendimiento de SMB perjudica compatibilidad o rendimiento. | Recopilar y revisar mediciones de referencia antes de seleccionar ajustes de firma, cifrado o rendimiento. |
| Las escrituras simultáneas corrompen el estado del espacio de trabajo. | Exigir bloqueos autoritativos locales de la MacBook alcanzados por SSH y fallar de forma cerrada cuando no puedan adquirirse. |
| SMB se convierte en un canal involuntario de sincronización de habilidades o secretos. | Usar un repositorio Git versionado para las habilidades compartidas y preservar explícitamente de forma local las habilidades locales del host y todo estado sensible/de tiempo de ejecución. |
| Los comandos del manual se confunden con autorización para cambiar sistemas activos. | Marcar como aplazada toda acción privilegiada o de aplicación y proporcionar comportamiento solo de ejecución en seco/preflight en este recorte. |

## Reversión

Este recorte no tiene configuración activa que revertir. Su reversión es la eliminación o revisión de los artefactos de automatización y manuales antes de cualquier despliegue privilegiado.

Para un futuro despliegue autorizado, el manual debe capturar primero el estado previo al cambio y luego proporcionar pasos de reversión específicos por host únicamente para la configuración que creó: deshabilitar/eliminar el recurso SMB dedicado, eliminar la configuración de montaje de cliente asociada, revocar/eliminar la identidad dedicada de ejecución y las reglas de acceso si se crearon, y limpiar únicamente artefactos de bloqueo propios de la infraestructura tras confirmar que no hay escritor activo. Nunca debe eliminar datos del espacio de trabajo ni alterar configuración de host no relacionada como atajo de reversión.

## Criterios de éxito

- [ ] Los entregables cubren preparación del servidor MacBook, preparación del cliente Mac mini, orquestación bidireccional y validación/recuperación/reversión.
- [ ] Toda guía SMB expone únicamente `/Users/leo/projects` mediante un recurso dedicado al espacio de trabajo y rechaza HOME, dotfiles y categorías protegidas de estado local.
- [ ] La identidad de ejecución remota está completamente parametrizada y claramente no se crea en este recorte.
- [ ] Los manuales exigen mediciones de red/SMB de referencia antes de cualquier decisión sobre firma, cifrado o rendimiento de SMB.
- [ ] El protocolo de orquestación permite trabajo seleccionado iniciado mediante SSH desde cualquiera de los hosts, preservando la MacBook como orquestador principal y autoridad de bloqueo.
- [ ] Cada escritura del espacio de trabajo está vinculada a un área declarada y a un bloqueo autoritativo local de la MacBook alcanzado mediante SSH.
- [ ] Las habilidades compartidas se distribuyen únicamente mediante un repositorio Git versionado con clones locales en ambos hosts; las habilidades locales del host permanecen locales.
- [ ] Ningún artefacto de este recorte aplica configuración privilegiada activa ni indica a los operadores hacerlo sin una futura puerta explícita de autorización.

## Puertas de aprobación para trabajo posterior

Antes de que la implementación pueda aplicar cambios activos, los revisores deben aprobar por separado la decisión medida de seguridad/rendimiento de SMB, la identidad exacta con mínimos privilegios y sus permisos, la política de acceso del recurso dedicado, los detalles de autorización SSH y los comandos de reversión específicos por host. Esas aprobaciones quedan intencionalmente fuera del primer recorte de esta propuesta.
