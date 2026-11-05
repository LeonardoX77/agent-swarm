# SMB mounting between machines

`swarm-smb-mount` queries, mounts, and unmounts **one specific SMB share** on macOS and Linux/WSL. macOS uses Keychain; Linux uses CIFS with a user-mountable fstab entry. The tool does not accept, store, or display passwords, and never uses sudo. During onboarding, `swarm-setup` takes `share.host`, `share.name`, and `share.user` from `config/hosts.json`; do not copy values from another machine.

## Initial preparation (macOS)

In the graphical session of the Mac that will mount the share:

1. Read `share.host`, `share.name`, and `share.user` in `config/hosts.json`. Confirm the share publishes only the approved catalog, not a larger disk or directory.
2. In Finder select **Go > Connect to Server** and use `smb://<share.user>@<share.host>/<share.name>`, replacing all three placeholders with those values.
3. Authenticate there and select **“Remember this password in my keychain.”** Never send the password to the agent or include it in commands, files, or logs.
4. Confirm the catalog appears at `/Volumes/<share.name>`. To test a new script mount, unmount the share in Finder first.

## Linux/WSL: preparation

Install `cifs-utils` and make `findmnt`, `mount`, and `umount` available through system administration. From the account that will mount the catalog, generate the instructions (replace H, S, and U with `share.host`, `share.name`, and `share.user`):

```sh
automation/agent-swarm/bin/swarm-smb-mount fstab-line --host H --share S --user U
```

The JSON includes `fstab_line`, `credentials_file`, `credentials_mode`, and `credentials_template`. A person must:

1. As root, create `/mnt/<share>` and add the exact line to `/etc/fstab`. It includes `cifs`, the absolute credentials path, local uid/gid, and `vers=3.0,noauto,user,_netdev`; do not invent it or copy it from another account.
2. Personally create `~/.config/agent-swarm/smb-credentials` with mode `0600`, using the `username=...` / `password=...` template. Do not give the password to the agent or include it in commands or shared logs. The tool never creates or reads that file directly: the system CIFS mount uses it.
3. Run `mount` as a normal user with the options in the next section. Without a user-mountable fstab entry, a new mount fails safely with `fstab_entry_required`.

The Linux catalog is at `/mnt/<share>`; macOS retains `/Volumes/<share>`. A Linux hub must publish its catalog manually through its own SMB server (for example, Samba); setup does not configure that server. In WSL, Windows can occupy TCP 445 on loopback: a local test needs another port (the recorded test used `port=1445` in fstab). This CLI has no port option. Servers that require SMB 3.1.1 have not been validated; the generated line uses `vers=3.0`.

## Use

Replace placeholders with `config/hosts.json` values before running from the repository:

```bash
automation/agent-swarm/bin/swarm-smb-mount status --host <share.host> --share <share.name> --user <share.user>
automation/agent-swarm/bin/swarm-smb-mount mount --host <share.host> --share <share.name> --user <share.user>
automation/agent-swarm/bin/swarm-smb-mount unmount --host <share.host> --share <share.name> --user <share.user>
```

Output is JSON. `mount` is idempotent: it reports the already-mounted point. macOS identifies the origin `//<share.user>@<share.host>/<share.name>`; Linux identifies the CIFS mount by host and share, not user. `unmount` uses that same identification. It does not unmount shares from another host or with another name. If macOS selects `/Volumes/<share.name>-1` instead of the expected point, output includes `unexpected_mount_point`: inspect what occupies the original point before acting.

## Persistent mount

`swarm-setup` installs persistent mounting when onboarding a `spoke`. To install it manually, add `--persistent` to the first mount:

```bash
automation/agent-swarm/bin/swarm-smb-mount mount \
  --host <share.host> --share <share.name> --user <share.user> --persistent
```

The script is copied to `~/.local/agent-swarm/bin/swarm-smb-mount` so it works without depending on the catalog being mounted.

| Platform | Persistence every 300 s | Artifacts and logs |
| --- | --- | --- |
| macOS | LaunchAgent at login; uses Keychain | `~/Library/LaunchAgents/com.mac-agent-swarm.smb.<share-identifier>.plist`; logs in `~/Library/Logs/mac-agent-swarm/` |
| Linux/WSL | `systemd --user` timer | `.service` and `.timer` in `~/.config/systemd/user/`, prefixed `com.mac-agent-swarm.smb.`; logs in `~/.local/state/agent-swarm/logs/<label>.out.log` and `.err.log`; if HOME contains spaces or other characters systemd cannot express in those directives, the service uses the journal (`journalctl --user -u <label>.service`) |

On Linux, if `systemctl --user` is unavailable or cannot enable the timer, mounting returns a warning and `persistent: false`; this does not mean persistence was installed. In WSL, enable `[boot]` / `systemd=true` in `/etc/wsl.conf`. Timers run only while the user has a session unless `loginctl enable-linger $USER` is enabled.

To remove the mount and its LaunchAgent or timer, without deleting the local copy or logs (or fstab or Linux credentials):

```bash
automation/agent-swarm/bin/swarm-smb-mount unmount \
  --host <share.host> --share <share.name> --user <share.user> --remove-persistent
```

## SSH operation (macOS)

Linux uses the same fstab entry over SSH; it needs neither Finder nor a graphical session.

`osascript` needs a macOS graphical session: a mount started only through SSH normally cannot display interaction. With `--persistent`, the script installs and uses the LaunchAgent in the graphical session, activates it, and waits for the result; output reports `"via": "launchagent"`.

If onboarding stops at `mount`, connect first in Finder and save the password in Keychain; resume **the same `swarm-setup` command**. If the initial SCP copy reports that the destination directory is missing, use a `swarm-setup` version that creates the remote parent before copying; do not manually relocate files outside the intended directory.
