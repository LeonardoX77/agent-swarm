# Automatic host updates

`swarm-update` checks and updates the channel's local components without `sudo`: Herdr, `mosh` (including `mosh-server`), `moshi-hook`, `gentle-ai`, Pi, and Pi extensions. It is a self-contained Python CLI copied during installation to `~/.local/agent-swarm/bin/swarm-update`; it installs no dependencies.

## Installation and schedule

Install the agent from the repository checkout:

```bash
automation/agent-swarm/bin/swarm-update install
```

The default schedule is once daily at 04:30. Change it during installation, for example:

```bash
automation/agent-swarm/bin/swarm-update install --hour 3 --minute 15 --components herdr,mosh,moshi-hook,gentle-ai,pi,pi-extensions
```

Installation creates the `com.mac-agent-swarm.update` LaunchAgent. `launchd` runs a scheduled job missed while the Mac was asleep after it wakes; the machine need not remain on at the scheduled time. Do not run the command as root: it never uses `sudo`.

A node configured before the `auto-update` phase existed (for example, the Mac mini on October 27) has no LaunchAgent, configuration, or registry. Run `swarm-update install` from that node's checkout (on a spoke, the catalog mount is sufficient). If it has an older configuration without `gentle-ai`, run `install` again to add it to `components`.

## Operation

```bash
swarm-update check             # read-only; does not run brew update
swarm-update check --refresh   # also refreshes Homebrew metadata
swarm-update run               # updates if at least 20 hours have elapsed
swarm-update run --force       # skips that wait
swarm-update status
swarm-update uninstall         # removes only the LaunchAgent
```

Normal output is an English, one-line-per-component summary. `--verbose` adds the PATH used and each command, exit code, and truncated output; `--json` emits the automation report. Failure of one component does not prevent trying the others, but makes `run` exit with code 1. `check` does not alter installed software, though Homebrew may refresh its local API cache.

`~/.config/agent-swarm/update.json` contains `enabled`, hour, minute, components, and the agent PATH. To disable updates without removing the configuration, set only `"enabled"` to `false`; to remove the LaunchAgent, use `swarm-update uninstall`. Runs are logged to `~/Library/Logs/mac-agent-swarm/swarm-update.log`; the last result is `~/.local/state/agent-swarm/update/last-run.json`.

## Per-component behavior

Herdr, mosh, and `gentle-ai` update through Homebrew. `moshi-hook` prefers its Homebrew formula when available and otherwise uses its standalone updater; it then restarts only its own service when the CLI announces that operation. Pi uses `pi update --self`, and extensions use `pi update --extensions`.

A Herdr update **never restarts the Herdr server**: doing so would close active tabs. After updating its binary, the report states (`server restart pending`, in output and the log; there is no other notification) that restart is pending. Restart Herdr's LaunchAgent manually, only when appropriate for active tabs, using that host's procedure (for example, the Homebrew service or `dev.herdr.server`).
