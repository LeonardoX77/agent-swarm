# Bidirectional SSH channel between registered hosts

This runbook configures **one direction** of the Agent Swarm channel: an origin host connects to a destination host through a `swarm-<target>` alias. Repeat it for the reverse direction. The dedicated key has no passphrase so an agent can use it unattended; `authorized_keys` restrictions reduce forwarding but **still permit a shell** and are not a sandbox.

Use names and values from `config/hosts.json`; do not copy host names, users, or paths from this document.

## Per-direction template

| Placeholder | Required value |
| --- | --- |
| `<origin>` | Name of the host that starts SSH. |
| `<target>` | Registry name of the destination host (`[a-z0-9-]`). |
| `<host>` | Confirmed destination LAN/Tailscale address or name; the first candidate when failover is configured. |
| `<user>` | Authorized account at the destination. |
| `<key>` | `~/.ssh/agent_swarm_<target>` at the origin. |

### 1. Enable access at the destination

**Person — in the destination GUI.** Enable **Remote Login** for account `<user>` and confirm the LAN or Tailscale network.

**STOP:** macOS login, password, firewall, Tailscale, and Sharing approvals require human intervention.

**Verify:** Remote Login lists `<user>` among authorized accounts and the destination has confirmed address `<host>`.

**Resume:** after approval, repeat this local check; do not attempt SSH using a password sent by the agent.

### 2. Create or reuse a key at the origin

**Agent — at `<origin>`, with authorization.** You may reuse a key already working for an alias; otherwise create a dedicated key. Never overwrite an existing key:

```sh
if [ -e ~/.ssh/agent_swarm_<target> ] || [ -e ~/.ssh/agent_swarm_<target>.pub ]; then
  echo 'La clave ya existe; no se modifica.' >&2
else
  ssh-keygen -t ed25519 -f ~/.ssh/agent_swarm_<target> -N '' -C agent-swarm-<origin>-to-<target>
fi
```

**Verify:** both new-key files exist, or the previously working reused key is documented.

### 3. Verify the host fingerprint before trusting it

**Person — in front of `<target>`'s local screen.** Read the fingerprint directly at the destination and communicate it in person or over an already trusted channel:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

**STOP:** do not add to `known_hosts` or accept an SSH connection until this local reading has been compared with the origin scan.

**Agent — at `<origin>`.** Obtain the fingerprint observed from the network:

```sh
ssh-keyscan -t ed25519 <host> | ssh-keygen -lf -
```

**Verify:** key type and fingerprint exactly match the destination's local reading.

**Resume:** only on a match, add the scanned key to `~/.ssh/known_hosts`. On a difference, stop setup, verify `<host>` locally, and repeat both readings. Never disable `StrictHostKeyChecking`.

### 4. Authorize the public key at the destination

**Agent — at `<target>`, after human authorization.** Back up `~/.ssh/authorized_keys` and add the origin's public key without overwriting existing lines. The entry must be one line: the exact prefix followed by the original public key.

```text
no-agent-forwarding,no-port-forwarding,no-X11-forwarding
```

**Verify:** a backup exists, the entry appears once, retains the entire public key, and all other entries remain intact.

### 5. Create the alias at the origin

**Agent — at `<origin>`.** A single candidate keeps the existing alias shape:

```sshconfig
Host swarm-<target>
  HostName <host>
  Port <port> # written only when it is not 22
  User <user>
  IdentityFile ~/.ssh/agent_swarm_<target>
  IdentitiesOnly yes
  BatchMode yes
  StrictHostKeyChecking yes
  ConnectTimeout 15
  ServerAliveInterval 15
  ServerAliveCountMax 4
  ForwardAgent no
```

With two or more ordered candidates, the alias instead has `HostKeyAlias swarm-<target>` and a `ProxyCommand` equivalent to:

```sshconfig
Host swarm-<target>
  HostKeyAlias swarm-<target>
  ProxyCommand /usr/bin/python3 ~/.local/agent-swarm/bin/swarm-ssh-connect --port <port> -- <candidate-1> <candidate-2>
```

The setup copies `swarm-ssh-connect` to `~/.local/agent-swarm/bin/swarm-ssh-connect` **on the side that runs SSH**. It tries candidates in order. Each unreachable candidate costs at most the helper's per-candidate connect timeout.

For a multi-candidate alias, `known_hosts` has one line keyed by `swarm-<target>`, not one line per address. Every reachable candidate must present that human-verified key; one presenting another key fails closed. Unreachable candidates are reported but not trusted separately. If that alias-keyed line already exists with a different key, setup stops until a human verifies and removes the stale line. Apply the same rule in the reverse direction.

When reusing a key, retain its `IdentityFile`; all other controls remain mandatory.

**Verify:** from `<origin>`, run:

```sh
ssh swarm-<target> hostname
```

It must return the destination name without requesting a password or fingerprint confirmation. Repeat steps 1–5 with origin and destination swapped to establish bidirectional communication.

## Optional: interactive zsh shortcut

`aiconnect` is an optional convenience function for opening an interactive SSH terminal on a registered host; Agent Swarm does not need it for delegation. Add the following function to `~/.zshrc` on the origin **after** configuring and verifying SSH aliases. Pass it a name from `swarm-delegate list`; it selects the corresponding SSH alias rather than a raw address:

```zsh
aiconnect() {
  if (( $# != 1 )); then
    printf 'Usage: aiconnect <registered-host>\n' >&2
    return 2
  fi
  local target=$1
  if [[ ! $target =~ '^[a-z0-9-]+$' ]]; then
    printf 'Invalid Agent Swarm target: %s\n' "$target" >&2
    return 2
  fi
  command ssh "swarm-$target"
}
```

If you already have an `aiconnect` function, adapt its routing instead of redefining it. Run `source ~/.zshrc` or open a new terminal, then use `aiconnect <registered-host>`. The function checks only the name's syntax; confirm registration with `swarm-delegate list` before use. This example assumes setup-generated `swarm-<target>` aliases; for custom aliases, use the registry's `ssh_alias` instead. It delegates SSH host verification and connection options to the existing alias; an SSH connection alone does not prove that a particular project is available on that host.

## Use with Agent Swarm

Once both directions respond, confirm registry and catalog with `swarm-delegate preflight <target>`. If a shared-catalog spoke reports `catalog_missing`, configure its SMB mount; a local-only spoke instead needs its pre-provisioned catalog and checkout. For a specific task, check `swarm-delegate preflight <target> --project <catalog-relative-project>` before submitting; `project_unavailable` means that project is not on the target. See [Add a host to the Agent Swarm channel](../../setup/add-host.md) for the complete process and [SMB mounting between machines](smb-mount.md) for persistent mounting.

## Per-direction rollback

**Agent — with authorization.** Remove the `Host swarm-<target>` block from the origin, the added `authorized_keys` entry at the destination (or restore the backup if it contains only this change), and the dedicated `agent_swarm_<target>` key pair at the origin. For a multi-candidate alias, also remove its alias-keyed `known_hosts` line. Remove `~/.local/agent-swarm/bin/swarm-ssh-connect` only when no other alias uses it. Do not remove a reused key or a backup containing unrelated changes.

## Final check

In each direction, verify that `ssh swarm-<target> hostname` works without a password and that the alias matches the host in `config/hosts.json`. From a registered host, `swarm-delegate preflight <target> --project <catalog-relative-project>` must return `"status": "ready"` for the requested project; shared-catalog spokes require SMB mounting, while local-only spokes require a local checkout and project. A successful SSH connection alone does not show that Pi, Herdr, and bidirectional acceptance work: complete the `swarm-setup` phases and inspect their status.
