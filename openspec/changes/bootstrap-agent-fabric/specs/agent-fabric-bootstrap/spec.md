# Especificación de inicialización de la infraestructura de agentes

## Propósito

Definir artefactos de preparación revisables que no aplican cambios para una infraestructura de agentes de dos Mac. Este recorte DEBE preparar trabajo posterior autorizado sin cambiar configuración privilegiada activa, crear identidades o credenciales, ni exponer estado protegido local del host.

## Requisitos

### Requisito: Artefactos de preparación del servidor MacBook

Los entregables DEBEN proporcionar un manual de preparación del servidor MacBook y automatización parametrizada que operen únicamente como comprobaciones de ejecución en seco o preflight. DEBEN designar `/Users/leo/projects` como la única raíz propuesta de recurso compartido SMB del espacio de trabajo; registrar un futuro nombre de recurso dedicado, política de acceso prevista, requisitos previos de propiedad, ubicación de bloqueo local de la MacBook y estado del host previo al cambio capturado; y etiquetar como aplazado, pendiente de una puerta de autorización posterior, cada comando que aplicaría configuración o requeriría privilegios. La automatización DEBE rechazar cualquier raíz propuesta de recurso compartido que no sea `/Users/leo/projects`, incluidos `/Users/leo`, cualquier directorio HOME y cualquier raíz de dotfiles.

#### Escenario: La preparación del servidor acepta la raíz canónica del espacio de trabajo

- DADO QUE la raíz propuesta del recurso compartido es `/Users/leo/projects`
- CUANDO se ejecuta el preflight de preparación del servidor
- ENTONCES DEBE informar que la raíz es elegible para un futuro recurso dedicado del espacio de trabajo sin crear ni cambiar ese recurso

#### Escenario: La preparación del servidor rechaza raíces inseguras de recurso compartido

- DADO QUE la raíz propuesta del recurso compartido es un directorio HOME, una raíz de dotfiles, una ruta protegida de estado local o cualquier ruta distinta de `/Users/leo/projects`
- CUANDO se ejecuta el preflight de preparación del servidor
- ENTONCES DEBE fallar antes de cualquier acción de aplicación e identificar la categoría de ruta rechazada

#### Escenario: Las acciones privilegiadas del servidor permanecen aplazadas

- DADO QUE un artefacto de preparación del servidor describe un cambio de SMB, cuenta, servicio, firewall o privilegio
- CUANDO un operador sigue o ejecuta el artefacto en este recorte
- ENTONCES el artefacto DEBE etiquetar la acción como aplazada y NO DEBE aplicar el cambio

### Requisito: Artefactos de preparación del cliente Mac mini

Los entregables DEBEN proporcionar un manual de preparación del cliente Mac mini y automatización parametrizada que operen únicamente como comprobaciones de ejecución en seco o preflight. DEBEN validar la conectividad de red de la MacBook y los requisitos previos de SSH, registrar el estado del cliente previo al cambio, aceptar una futura identidad de ejecución únicamente como parámetro de entrada y definir un futuro destino de montaje SMB fuera de directorios HOME y categorías protegidas de estado local. NO DEBEN crear una identidad, credenciales, un montaje ni configuración de montaje.

#### Escenario: La preparación del cliente valida entradas seguras sin configurar el cliente

- DADO QUE existen requisitos previos de SSH alcanzables en la MacBook, un parámetro de identidad de ejecución suministrado y un destino de montaje fuera de categorías de ruta inseguras
- CUANDO se ejecuta el preflight de preparación del cliente
- ENTONCES DEBE informar los requisitos previos validados y NO DEBE crear identidad, credencial, montaje ni configuración

#### Escenario: La preparación del cliente rechaza un destino de montaje inseguro

- DADO QUE el destino de montaje propuesto está dentro de un directorio HOME o de una ubicación de secreto, caché, sesión, registro o configuración de tiempo de ejecución
- CUANDO se ejecuta el preflight de preparación del cliente
- ENTONCES DEBE fallar e identificar la categoría prohibida antes de cualquier acción de aplicación

### Requisito: Exclusión de rutas protegidas y secretos

Todos los artefactos de preparación, validación, recuperación y reversión DEBEN preservar los límites locales del host para directorios HOME, dotfiles, datos de Keychain, credenciales, secretos, cachés, sesiones, registros y configuración de tiempo de ejecución. DEBEN rechazar propuestas para exponer, montar en, sincronizar, registrar en SMB o usar como raíz de espacio de trabajo cualquier categoría protegida. El contexto de falla DEBE registrarse localmente sin credenciales, registros sensibles ni estado de tiempo de ejecución.

#### Escenario: La validación de límites bloquea estado protegido

- DADO QUE una ruta de entrada o contenido SMB solicitado pertenece a una categoría protegida de estado local
- CUANDO cualquier artefacto valida su límite de ruta o contenido
- ENTONCES DEBE rechazar esa entrada y NO DEBE proponer exposición SMB ni sincronización

#### Escenario: El informe de fallas preserva el estado sensible

- DADO QUE falla una operación de orquestación o validación
- CUANDO se registra el contexto de falla
- ENTONCES el registro DEBE permanecer local y DEBE excluir credenciales, registros sensibles y estado de tiempo de ejecución

### Requisito: Orquestación bidireccional y bloqueo autoritativo

El manual DEBE definir un protocolo en el que MacBook o Mac mini PUEDAN iniciar trabajo remoto SSH seleccionado, mientras que la MacBook DEBERÁ permanecer como host principal de orquestación y único host autoritativo de bloqueos. Antes de una escritura del espacio de trabajo, el iniciador DEBE declarar un área del espacio de trabajo y el escritor previsto, adquirir el bloqueo local correspondiente de la MacBook mediante SSH y liberarlo únicamente después de un estado terminal definido. El protocolo DEBE imponer un escritor por área declarada del espacio de trabajo, fallar de forma cerrada ante contención de bloqueo o autoridad de bloqueo inalcanzable, y definir inspección y recuperación de bloqueos abandonados u obsoletos sin permitir escrituras simultáneas.

#### Escenario: Un escritor declarado completa una operación bloqueada

- DADO QUE un iniciador declara un área del espacio de trabajo y el escritor previsto, y alcanza la MacBook mediante SSH
- CUANDO adquiere el bloqueo autoritativo y la operación del espacio de trabajo alcanza un estado terminal
- ENTONCES DEBE liberar ese bloqueo y registrar el resultado terminal

#### Escenario: La contención de bloqueo impide un escritor simultáneo

- DADO QUE se mantiene un bloqueo autoritativo para un área declarada del espacio de trabajo
- CUANDO otro escritor solicita esa área
- ENTONCES el protocolo DEBE denegar o esperar según su manejo documentado de colisiones y NO DEBE permitir una escritura simultánea

#### Escenario: La autoridad de bloqueo no está disponible o está obsoleta

- DADO QUE el host de bloqueos MacBook es inalcanzable o un bloqueo parece abandonado
- CUANDO un iniciador intenta una escritura o un operador inicia la recuperación de bloqueo obsoleto
- ENTONCES una adquisición fallida DEBE impedir la escritura, y la recuperación DEBE requerir inspección documentada antes de limpiar únicamente el bloqueo obsoleto aplicable

### Requisito: Límite de distribución de habilidades

Los artefactos DEBEN designar un repositorio Git versionado con clones locales independientes en ambos hosts como el único transporte de habilidades compartidas. DEBEN indicar que SMB NO DEBE sincronizar habilidades y que las habilidades locales del host DEBEN permanecer locales.

#### Escenario: Las habilidades compartidas usan Git en lugar de SMB

- DADO QUE un operador valida el plan de distribución de habilidades
- CUANDO el plan identifica el transporte de habilidades compartidas
- ENTONCES DEBE identificar el repositorio Git versionado y los clones locales independientes por host, y DEBE rechazar SMB como transporte de habilidades

#### Escenario: Las habilidades locales del host permanecen aisladas

- DADO QUE cualquiera de los hosts contiene habilidades locales del host
- CUANDO se prepara o valida la distribución de habilidades
- ENTONCES los artefactos DEBEN preservar esas habilidades localmente y NO DEBEN incluirlas en el alcance de sincronización

### Requisito: Medición antes del ajuste de SMB

El manual DEBE exigir mediciones de referencia registradas de conectividad de red, latencia, rendimiento y comportamiento SMB de espacio de trabajo representativo antes de seleccionar ajustes de firma, cifrado o rendimiento. DEBE definir criterios de impacto para revisar dichas mediciones y DEBE aplazar la selección de configuración hasta que se revisen las mediciones.

#### Escenario: Las mediciones preceden una decisión de ajuste

- DADO QUE no existen mediciones de referencia registradas y revisadas
- CUANDO un operador solicita una decisión sobre firma, cifrado o rendimiento de SMB
- ENTONCES el manual DEBE bloquear la decisión y exigir el registro de medición de referencia

#### Escenario: La medición de referencia se captura sin cambios de configuración

- DADO QUE se ejecuta el plan de medición
- CUANDO se recopilan conectividad, latencia, rendimiento y comportamiento SMB representativo
- ENTONCES los resultados DEBEN registrarse para revisión y NO DEBEN aplicar configuración ni ajuste SMB

### Requisito: Validación y puntos de verificación de despliegue futuro

El manual de validación DEBE verificar valores de parámetros de ejecución en seco, límites de ruta, acciones privilegiadas aplazadas, distribución de habilidades solo por Git, adquisición, contención, liberación y recuperación de bloqueo obsoleto. DEBE definir puntos de verificación de despliegue futuro para política de acceso al recurso autorizada por separado, permisos de identidad de ejecución, autorización SSH, ajustes SMB medidos y comandos de reversión específicos por host. Una validación fallida DEBE impedir la progresión a un paso futuro de aplicación.

#### Escenario: La validación tiene éxito para el recorte que no aplica cambios

- DADO QUE todos los parámetros son seguros, todas las acciones de aplicación están aplazadas, Git es el transporte de habilidades y las comprobaciones del protocolo de bloqueo pasan
- CUANDO se ejecuta el manual de validación
- ENTONCES DEBE informar preparación para autorización posterior sin aplicar configuración activa

#### Escenario: La validación detecta preparación insegura o incompleta

- DADO QUE se detecta una ruta protegida, acción de aplicación, transporte de habilidades distinto de Git o comprobación de bloqueo fallida
- CUANDO se ejecuta el manual de validación
- ENTONCES DEBE fallar, informar la condición incumplida y NO DEBE autorizar un paso de aplicación

### Requisito: Límites de recuperación y reversión

El manual de recuperación y reversión DEBE indicar que este recorte no tiene configuración activa que revertir. Para un despliegue posterior autorizado, DEBE exigir el estado previo al cambio capturado y la reversión específica por host únicamente de recurso compartido creado por la infraestructura, configuración de montaje de cliente, identidad de ejecución y reglas de acceso, y artefactos de bloqueo de la infraestructura confirmados como inactivos. DEBE prohibir la eliminación de datos del espacio de trabajo y la alteración de configuración de host no relacionada como atajos de reversión.

#### Escenario: La reversión del recorte actual cambia únicamente artefactos

- DADO QUE no se produjo ningún despliegue activo autorizado
- CUANDO un operador revierte este recorte
- ENTONCES el manual DEBE limitar la reversión a eliminación o revisión de los artefactos de preparación

#### Escenario: La reversión futura preserva estado no relacionado y datos del espacio de trabajo

- DADO QUE un despliegue posterior autorizado creó configuración de infraestructura y capturó estado previo al cambio
- CUANDO se realiza su reversión
- ENTONCES DEBE restaurar únicamente la configuración creada por la infraestructura documentada y NO DEBE eliminar datos del espacio de trabajo ni modificar configuración de host no relacionada
