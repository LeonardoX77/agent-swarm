# Historical Agent Swarm test evidence

> **Status:** historical record, not a production protocol or deployment acceptance. Current checks are in [validation](validation.md).

## Interpreting the evidence

- **PASS** confirms only the observation described at the recorded time and environment.
- **FAIL**, **BLOCKED**, **SKIP**, and **INCONCLUSIVE** must not be reinterpreted as an available capability.
- Tab names, panes, PIDs, nonces, and temporary paths are historical identifiers, not reusable values.
- Observations do not replace the current registry, a verified fingerprint, Pi login, an SMB mount, or channel acceptance.

## Linux/WSL evidence

Real observations reported by the test owner on this host: Ubuntu 24.04, kernel 6.18 WSL2, and `systemd --user` running. The scope of each test is distinguished below; a real delegation to WSL does not validate two-machine bidirectional acceptance.

| Area | Observed result | Scope |
| --- | --- | --- |
| `swarm-update` | **PASS**: install/run/status/uninstall through real systemd user services; the test schedule was removed afterward. | Validates the service lifecycle, not every component update. |
| `swarm-smb-mount` | **PASS**: status, mount `--persistent`, status, read, write, unmount, and `--remove-persistent`, without sudo in the tool. The timer remounted after unmounting. | Temporary loopback Samba share, with cifs-utils and Samba installed; `127.0.0.1:1445` because Windows occupied 445. The test used the `fstab-line` output with `port=1445` added; privileged preparation was outside the tool. |
| Safe SMB rejection | **PASS**: a mount without an fstab entry failed with `fstab_entry_required`. | Does not demonstrate compatibility with every SMB server. |
| Host identification | **PASS**: prefix `5CG6031YZW` matched exactly in lowercase, uppercase, and FQDN forms; unrelated names did not match. | Tests case-insensitive comparison, not delegation. |

### Real SSH setup and delegation to this WSL

Evidence reported by the owner of the real run (not repeated by simulated tests):

- **Partial PASS, phases 1–9:** `swarm-setup add-host` over real SSH to this WSL with `--ssh-port 2222 --origin-ssh-port 2222` completed fingerprint verification, the human `authorized_keys` step, installation of Herdr 0.9.5 through `--install-missing`, a real CIFS mount through the setup mount phase against a temporary loopback Samba share, a registry entry with catalog `/mnt/agent-projects`, skill copying, and the systemd update timer. Two more human steps were needed: start the Herdr server and make `pi` visible. A later change added probe diagnostics, start instructions, and discovery of `$HOME/.pi/agent/bin` alongside `$HOME/.local/bin` in setup and swarm-update.
- **Expected FAIL, phase 10:** acceptance failed with `SELF_TARGET` because origin and destination were the same host. Bidirectional acceptance is **not** validated by this single-host loopback.
- **PASS, separate real delegation:** `swarm-delegate submit/recover/close` from the hub to the Linux node returned the exact nonce and closed only its own tab. Before the official Herdr Pi integration was installed, submit returned `unknown` and the prompt was never delivered (documented adapter behavior, not successful delivery).
- **SSH finding:** Windows OpenSSH occupied TCP 22 on every local address of the host; this is why `--ssh-port` and `--origin-ssh-port` were added, without changing their default of 22.
- **Ownership prerequisite:** `herdr integration install pi` installs `~/.pi/agent/extensions/herdr-agent-state.ts`; `herdr integration status` verifies it. Without this integration, Herdr does not provide `agent_session` of kind `path`, source `herdr:pi`, needed to prove ownership before sending the prompt. Setup now probes it as `herdr-pi-integration`, and `--install-missing` can install it on both platforms; dry-run only reports it.
- **Headless startup:** `herdr tab list` returned `server_not_running`. Herdr 0.9.5 rejected a zero-sized terminal with `cannot attach without a usable terminal: terminal reported a zero-sized grid`. Start it with `herdr` in a normal terminal and detach, or with a pty with non-zero rows and columns; the server survives the client exiting. There is no `herdr server start`: that version offers only `server stop` and `server reload-config`.

**Not validated:** bidirectional acceptance between two real machines; native execution of the new code on macOS (only simulated tests and differential comparison with `origin/main`); a Linux node reached over a real network from a macOS hub; servers whose minimum SMB dialect is 3.1.1 (the fstab line uses `vers=3.0`).

## Useful Herdr + Pi observations

| Area | Historical observation | Limit |
| --- | --- | --- |
| Own session | A dedicated tab and Pi agent responded to a nonce and were cleaned up without closing pre-existing resources. | Does not prove complete isolation or production guarantees. |
| Pi startup | **Reproduced on the real WSL node:** at `21:53:53.068` `tab.create` spawned pane 3; `agent.start` errored at `.080`, returned `ok` at `.183`, and Pi was registered only at `.622`. The ledger remained `unknown` at `start_intent` and no prompt was sent. The adapter now polls `herdr agent get <pane_id>` every roughly 0.5 seconds, using a bounded start deadline, before declaring `unknown`; it records `started` and sends the prompt only after strict ownership identity is confirmed. | This protects the observed registration race without retrying `agent start` or blindly resending a prompt. Validate the bounded behavior against future Herdr/Pi runtime versions. |
| JSONL result | The adapter found the exact user message and a descendant final response in its own session JSONL. | Screen snapshots alone do not correlate a turn. |
| Ledger | Persisting intent before create, start, submit, and close retained ambiguous states for recovery. | It provides neither distributed exactly-once nor automatic resend authorization. |
| Envelope | The valid contract has six fields and `mode: executor`; extra fields or unsupported modes are rejected. | Validation does not replace human scope control. |
| Close | A verified close preserves the result and confirms `tab_not_found` for its own tab. | It does not authorize closing others' tabs, agents, or sessions. |
| JSONL limits | A system line near 99 KiB was observed; the reader accepts up to 1 MiB per line and 8 MiB per file. | These are adapter limits, not a promise about future Pi formats. |

## Communication and recovery

Historical tests showed that a controlled SSH-client disconnect or wait timeout does not prove cancellation of remote work. Safe recovery retains the UUID and queries status; it neither creates a second job nor resends a prompt when state is ambiguous.

Herdr can emit typed errors on stdout or stderr, and `herdr agent prompt` rejects `--timeout` without `--wait`. The adapter sends the prompt without those options and parses both error channels.

## Open boundaries

1. Test general network and server failures with recovery without blind resend.
2. Verify at every deployment the restricted SMB catalog, aliases, fingerprints, and both SSH directions.
3. Keep Pi login and credentials local to the host; a GUI observation does not prove separate noninteractive authentication.
4. Coordinate human writers: the channel implements neither locks nor conflict resolution.
5. Revalidate the reproduced `herdr agent start`/Pi registration race when deploying a new Herdr or Pi runtime; the adapter now waits for strict identity through bounded `agent get` polling, never retries `agent start`, and never sends a prompt before ownership is confirmed.
6. Treat every runtime or protocol change as new work requiring new evidence.

## Available local evidence

Adapter deterministic tests use fixtures and do not open a live GUI or configure hosts:

```sh
python3 -m unittest automation/agent-swarm/test/test_herdr_task.py
python3 -m unittest discover -s automation/agent-swarm/test
```

Before operating, follow [validation](validation.md), [SSH channel](ssh-channel.md), and [SMB mount](smb-mount.md). For the task contract, see [Herdr + Pi tasks](herdr-tasks.md).
