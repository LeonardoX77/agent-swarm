# Reversión controlada de Agent Fabric v1

Revertí sólo recursos que la instalación de Fabric haya creado y sólo en el host local. La reversión requiere presencia humana para cada cambio de sistema o credencial.

## Contención por runtime

Antes de retirar infraestructura, podés reducir el alcance de ejecución sin afectar el otro host: editá localmente `allowed_runtimes` en la configuración del host y conservá sólo los runtimes que la persona autorice. Por ejemplo, un host puede permitir sólo `pi` mientras el otro conserva `opencode` y `claude`. Cada request sigue declarando `runtime`, y el runner rechaza localmente los valores fuera de su allowlist. No copies configuración, credenciales ni sesiones entre hosts, no agregues flags a la solicitud y no uses el comando SSH forzado como si sandboxeara a los agentes.

## Antes de revertir

1. Confirmá que no hay un despacho activo y avisá a la otra persona: no hay locks que lo impidan.
2. Conservá el último resultado saneado y los eventos locales relevantes para diagnóstico.
3. Identificá cada recurso como creado por Fabric. Si no podés demostrarlo, no lo elimines.
4. Desmontar, quitar miembros de acceso o editar claves cambia el host: pedí la autorización humana específica antes de cada paso.

## Alcance permitido

| Recurso creado por Fabric | Reversión local permitida |
|---|---|
| Runtime y configuración de Fabric bajo `~/.local/agent-fabric` | Usá el revertidor del runtime sólo si existe su manifest; elimina únicamente archivos registrados por ese helper. |
| Línea dedicada en `authorized_keys` | Quitá sólo la línea `restrict,command="…fabric-runner --config …"` asociada a la clave de Fabric. |
| Claves SSH dedicadas y aliases | Quitá las dos claves privadas dedicadas, sus públicas correspondientes y sólo los bloques `Host agent-fabric-macbook` o `Host agent-fabric-mac-mini` creados para Fabric. |
| Mac mini | Desmontá `/Volumes/agent-projects` y quitá sólo el login item o mount persistente creado para Fabric. |
| MacBook | Quitá sólo el share SMB `agent-projects` creado para `/Users/leo/projects`. |
| Remote Login | Quitá a `leo` de la membresía de Remote Login en el host correspondiente sólo si la instalación de Fabric agregó esa membresía y no tiene otro uso autorizado. |

## Runtime

Con autorización humana, el siguiente comando cambia sólo el runtime que fue instalado por el helper y cuyo manifest puede validar:

```sh
python3 automation/agent-fabric/bin/fabric-install-runtime --revert
```

Si informa que no existe manifest o que es inválido, detenete. No borres manualmente árboles amplios para forzar la reversión.

## Orden recomendado

1. Detené nuevos despachos con coordinación humana y guardá evidencia saneada.
2. Si necesitás contención gradual, reducí `allowed_runtimes` de forma independiente en cada host antes de retirar el transporte.
3. Quitá la línea restringida de `authorized_keys` en cada destino, verificando que corresponde a la clave dedicada correcta.
4. Quitá los aliases y claves dedicadas de cada originador.
5. Revertí el runtime con el helper y verificá que no eliminó archivos ajenos.
6. En la Mac mini, desmontá el mount y quitá sólo su login item o configuración persistente de Fabric.
7. En la MacBook, quitá sólo el share `agent-projects` de Fabric.
8. Evaluá la membresía de Remote Login al final y retirala únicamente cuando fue creada para Fabric.

## Nunca elimines

- Workspaces, repositorios ni contenido de `/Users/leo/projects` o `/Volumes/agent-projects`.
- El Keychain completo, credenciales no relacionadas, HOME, sesiones, cachés o logs generales.
- Otros shares SMB, usuarios macOS, aliases SSH, líneas de `authorized_keys` o configuración de SSH ajenos a Fabric.
- Membresías de Remote Login existentes antes de Fabric o requeridas por otro servicio.

Si un recurso es compartido, previo a Fabric o de procedencia incierta, dejalo intacto y escalá la decisión a la persona administradora. Esta guía no autoriza cambios remotos ni privilegios delegados.
