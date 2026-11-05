# SMB mounting between machines

`swarm-smb-mount` queries, mounts, and unmounts **one specific SMB share** from another Mac. It uses credentials stored in the macOS Keychain: it does not accept, store, or display passwords. During onboarding, `swarm-setup` takes `share.host`, `share.name`, and `share.user` from `config/hosts.json`; do not copy values from another machine.

## Initial preparation

In the graphical session of the Mac that will mount the share:

1. Read `share.host`, `share.name`, and `share.user` in `config/hosts.json`. Confirm the share publishes only the approved catalog, not a larger disk or directory.
2. In Finder select **Go > Connect to Server** and use `smb://<share.user>@<share.host>/<share.name>`, replacing all three placeholders with those values.
3. Authenticate there and select **“Remember this password in my keychain.”** Never send the password to the agent or include it in commands, files, or logs.
4. Confirm the catalog appears at `/Volumes/<share.name>`. To test a new script mount, unmount the share in Finder first.

## Use

Replace placeholders with `config/hosts.json` values before running from the repository:

```bash
automation/agent-swarm/bin/swarm-smb-mount status --host <share.host> --share <share.name> --user <share.user>
automation/agent-swarm/bin/swarm-smb-mount mount --host <share.host> --share <share.name> --user <share.user>
automation/agent-swarm/bin/swarm-smb-mount unmount --host <share.host> --share <share.name> --user <share.user>
```

Output is JSON. `mount` is idempotent: when exactly `//<share.user>@<share.host>/<share.name>` already exists, it reports the existing mount point. `unmount` acts only on that exact origin; it does not unmount other SMB shares. If macOS selects `/Volumes/<share.name>-1` instead, output includes `unexpected_mount_point`: inspect what occupies the original point before acting.

## Persistent mount

`swarm-setup` installs persistent mounting when onboarding a `spoke`. To install it manually, add `--persistent` to the first mount:

```bash
automation/agent-swarm/bin/swarm-smb-mount mount \
  --host <share.host> --share <share.name> --user <share.user> --persistent
```

This installs a user LaunchAgent that tries to mount at login and every 300 seconds. It stores no password; it uses the graphical-session Keychain. To work before the share is mounted, the script is copied to `~/.local/agent-swarm/bin/swarm-smb-mount`.

Artifacts:

- LaunchAgent: `~/Library/LaunchAgents/com.mac-agent-swarm.smb.<share-identifier>.plist` (check its real name on the host).
- Local copy: `~/.local/agent-swarm/bin/swarm-smb-mount`.
- Logs: `~/Library/Logs/mac-agent-swarm/`.

To remove the mount and LaunchAgent without deleting the local copy or logs:

```bash
automation/agent-swarm/bin/swarm-smb-mount unmount \
  --host <share.host> --share <share.name> --user <share.user> --remove-persistent
```

## SSH operation

`osascript` needs a macOS graphical session: a mount started only through SSH normally cannot display interaction. With `--persistent`, the script installs and uses the LaunchAgent in the graphical session, activates it, and waits for the result; output reports `"via": "launchagent"`.

If onboarding stops at `mount`, connect first in Finder and save the password in Keychain; resume **the same `swarm-setup` command**. If the initial SCP copy reports that the destination directory is missing, use a `swarm-setup` version that creates the remote parent before copying; do not manually relocate files outside the intended directory.
