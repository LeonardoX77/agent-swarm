# Transporte de retorno: Mac mini → MacBook

Este procedimiento permite que un agente del Mac mini invoque el adaptador Herdr que se ejecuta en el MacBook. No incluye material de claves.

> La clave dedicada no tiene frase de paso para que un agente pueda usarla sin atención humana. Las restricciones de `authorized_keys` reducen reenvíos, pero **siguen permitiendo una shell**: no constituyen un sandbox.

## 1. Requisito en el MacBook

Active **Remote Login** en el MacBook y compruebe que la cuenta `leo` puede recibir SSH.

## 2. Crear la clave dedicada en el mini

En el Mac mini, cree la clave sólo si aún no existe; no sobrescriba una clave existente:

```bash
if [ -e ~/.ssh/agent_fabric_macbook ] || [ -e ~/.ssh/agent_fabric_macbook.pub ]; then
  echo 'La clave ya existe; no se modifica.' >&2
else
  ssh-keygen -t ed25519 -f ~/.ssh/agent_fabric_macbook -N '' -C agent-fabric-mini-to-macbook
fi
```

## 3. Verificar la huella del host antes de confiar

Primero, lea la huella directamente en el MacBook:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

En el mini, compare esa huella con el resultado de:

```bash
ssh-keyscan -t ed25519 MacBookLeo.local | ssh-keygen -lf -
```

Sólo si ambas huellas coinciden, añada la clave escaneada a `~/.ssh/known_hosts`. No desactive nunca `StrictHostKeyChecking`.

## 4. Autorizar la clave pública en el MacBook

En el MacBook, haga una copia de seguridad de `~/.ssh/authorized_keys`. Después añada la clave pública del mini, en una sola línea, precedida exactamente por:

```text
no-agent-forwarding,no-port-forwarding,no-X11-forwarding
```

Conserve el resto de la línea como la clave pública original. Verifique permisos y que la copia de seguridad permite volver atrás.

## 5. Crear el alias SSH en el mini

Añada este bloque a `~/.ssh/config` en el mini:

```sshconfig
Host agent-fabric-macbook
  HostName MacBookLeo.local
  User leo
  IdentityFile ~/.ssh/agent_fabric_macbook
  IdentitiesOnly yes
  BatchMode yes
  StrictHostKeyChecking yes
  ConnectTimeout 15
  ServerAliveInterval 15
  ServerAliveCountMax 4
  ForwardAgent no
```

## 6. Verificar conectividad

Desde el mini:

```bash
ssh agent-fabric-macbook hostname
```

La configuración se realizó y verificó en vivo: el canal mini → MacBook devolvió el nonce exacto en la tarea del adaptador `03423bd5`.

## 7. Invocar el adaptador

Un agente del mini envía el sobre JSON por entrada estándar y después usa `recover` y `close` para la misma tarea:

```bash
ssh agent-fabric-macbook 'PATH=/opt/homebrew/bin:/usr/bin:/bin /usr/bin/python3 /Users/leo/projects/leo/mac-agent-fabric/automation/agent-fabric/bin/fabric-herdr-task submit' < envelope.json
```

No cree un identificador de tarea nuevo para recuperar una ejecución ambigua: use `recover` y, al finalizar, `close` con el mismo identificador.

## 8. Reversión

En el MacBook, elimine la línea añadida a `authorized_keys` o restaure su copia de seguridad. En el mini, elimine el bloque `Host agent-fabric-macbook` de `~/.ssh/config` y borre el par `~/.ssh/agent_fabric_macbook` y `~/.ssh/agent_fabric_macbook.pub`.
