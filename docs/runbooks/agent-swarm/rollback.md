# Controlled Agent Swarm rollback

Remove only artifacts created by a current Agent Swarm onboarding, on the local host and with its owner's authorization. This guide does not authorize remote access, unreviewed SSH changes, or deletion of shared data.

## Before rollback

1. Coordinate the stop of new tasks and retain the last sanitized result for every open UUID.
2. Identify the specific onboarding in the registry, `swarm-setup` state, and artifacts it created. If you cannot establish an artifact's origin, do not remove it.
3. Confirm that no Herdr task is in progress. Recover an ambiguous task before deciding whether to close it.
4. Obtain human authorization before removing Remote Login, keys, aliases, mounts, or Keychain items.

## Permitted scope

| Onboarding resource | Permitted local rollback |
| --- | --- |
| Local registry (`config/hosts.json`, unversioned) | Remove or correct only the approved entry; first make a copy and verify it contains no unrelated changes. |
| Dedicated SSH key and alias | Remove only the keypair and `Host swarm-<target>` block created for that direction. Never delete a reused key. |
| `authorized_keys` | Remove only the line added for the dedicated key, retaining other entries and backups. |
| Persistent SMB mount | Use `swarm-smb-mount unmount --remove-persistent` with registered-share values; it removes only that mount and LaunchAgent. |
| Skill and bootstrap | Remove only the copy and bootstrap block created for the new host, after confirming they serve no other channel. |
| Local updates | Remove only the LaunchAgent and files created by `swarm-update` for that installation. |
| Remote Login | Remove account authorization only if onboarding added it and no other approved use exists. |

## Recommended order

1. Stop new submissions and recover or close only own tasks with a verifiable result.
2. Remove dedicated aliases and keys from each origin and their associated destination lines, one direction at a time.
3. Unmount the share on spokes that no longer need it and remove only their persistent configuration.
4. Remove the skill, bootstrap, and local updates if they belong exclusively to that onboarding.
5. Update the local registry (including a prior copy) and assess Remote Login last.

## Never remove

- Workspaces, repositories, catalog content, or `/Volumes/<share.name>`.
- The complete Keychain, `HOME`, sessions, caches, general logs, or other credentials.
- Other SMB shares, macOS users, SSH aliases, keys, `authorized_keys` entries, or SSH configuration that cannot be attributed to onboarding.
- Herdr tabs, panes, or sessions not belonging to the UUID being recovered or closed.

If a resource is shared, predates onboarding, or has an uncertain origin, leave it intact and escalate the decision to the administrator.
