# Automatic host updates

`swarm-update` checks and updates the channel's local components without `sudo`: Herdr, `mosh`, `moshi-hook`, `gentle-ai`, Pi, and Pi extensions on macOS and Linux/WSL. It uses launchd on macOS and a systemd user timer on Linux; `mosh` and `gentle-ai` are skipped on Linux because they depend on Homebrew or the system package manager. It is a self-contained Python CLI copied during installation to `~/.local/agent-swarm/bin/swarm-update`; it installs no dependencies.

## Installation and schedule

Install the agent from the repository checkout:

```bash
automation/agent-swarm/bin/swarm-update install
```

The default schedule is once daily at 04:30. Change it during installation, for example:

```bash
automation/agent-swarm/bin/swarm-update install --hour 3 --minute 15 --components herdr,mosh,moshi-hook,gentle-ai,pi,pi-extensions
```

| Platform | Schedule and requirements |
| --- | --- |
| macOS | LaunchAgent `com.mac-agent-swarm.update`; launchd runs a scheduled job missed while the Mac was asleep after it wakes. |
| Linux/WSL | `~/.config/systemd/user/agent-swarm-update.service` and `agent-swarm-update.timer`, with `OnCalendar` and `Persistent=true`. Requires `systemctl --user`; installation fails when it is unavailable. |

The command rejects root and never uses `sudo`. In WSL, enable systemd with `[boot]` / `systemd=true` in `/etc/wsl.conf`. User timers run only while the user has a session unless `loginctl enable-linger $USER` is enabled.

A node configured before the `auto-update` phase existed (for example, the Mac mini on October 27) has no LaunchAgent, configuration, or registry. Run `swarm-update install` from that node's checkout (on a spoke, the catalog mount is sufficient). If the node has an older configuration without `gentle-ai`, run `install` again to add it to `components`.

## Operation

```bash
swarm-update check             # read-only; does not run brew update
swarm-update check --refresh   # macOS: also refreshes Homebrew metadata; Linux: no additional effect
swarm-update run               # updates if at least 20 hours have elapsed
swarm-update run --force       # skips that wait
swarm-update status
swarm-update uninstall         # removes the LaunchAgent or systemd user units
```

Normal output is an English, one-line-per-component summary. `--verbose` adds the PATH used and each command, exit code, and truncated output; `--json` emits the automation report. Failure of one component does not prevent trying the others, but makes `run` exit with code 1. `check` does not alter installed software, though Homebrew may refresh its local API cache.

`~/.config/agent-swarm/update.json` contains `enabled`, hour, minute, components, and the agent PATH. To disable updates without removing the configuration, set only `"enabled"` to `false`; to remove the schedule, use `swarm-update uninstall` (which preserves configuration, the local copy, and logs). Runs are logged to `~/Library/Logs/mac-agent-swarm/swarm-update.log` on macOS or `~/.local/state/agent-swarm/logs/swarm-update.log` on Linux. The last result is `~/.local/state/agent-swarm/update/last-run.json`.

## Per-component behavior

| Component | macOS | Linux/WSL |
| --- | --- | --- |
| Herdr | Homebrew | `herdr update` when installed; does not install an absent Herdr |
| mosh / mosh-server | Homebrew | Skipped: managed by the system package manager |
| `gentle-ai` | Homebrew | Skipped: Linux does not run Homebrew |
| moshi-hook | Homebrew formula when available; otherwise standalone updater | Standalone updater: `moshi-hook update` |
| Pi | `pi update --self` | Same |
| Pi extensions | `pi update --extensions` | Same |

The moshi-hook standalone updater restarts only its own service when its CLI announces that operation. Linux does not run Homebrew. For Herdr, Pi, and standalone updaters, `check` detects installation; it does not guarantee a newer version exists: the updater checks when `run` executes.

A Herdr update **never restarts the Herdr server**: doing so would close active tabs. After updating its binary, the report states (`server restart pending`, in output and the log; there is no other notification) that restart is pending. Restart Herdr manually, only when appropriate for active tabs, following the host-specific procedure (on macOS, for example, the Homebrew service or `dev.herdr.server`).
