# Historical Agent Swarm test evidence

> **Status:** historical record, not a production protocol or deployment acceptance. Current checks are in [validation](validation.md).

## Interpreting the evidence

- **PASS** confirms only the observation described at the recorded time and environment.
- **FAIL**, **BLOCKED**, **SKIP**, and **INCONCLUSIVE** must not be reinterpreted as an available capability.
- Tab names, panes, PIDs, nonces, and temporary paths are historical identifiers, not reusable values.
- Observations do not replace the current registry, a verified fingerprint, Pi login, an SMB mount, or channel acceptance.

## Useful Herdr + Pi observations

| Area | Historical observation | Limit |
| --- | --- | --- |
| Own session | A dedicated tab and Pi agent responded to a nonce and were cleaned up without closing pre-existing resources. | Does not prove complete isolation or production guarantees. |
| Pi startup | In real acceptance, Herdr returned an idle agent immediately after `agent start`; the adapter kept the ledger at `start_intent` and acceptance became `unknown`. Repeating the same setup passed. | Evidence of a possible startup race, not a confirmed or fixed cause. Add a deterministic delayed-ready-agent test and verify acceptance is not declared failed or blindly resent. |
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
5. Reproduce and cover the possible race between `herdr agent start` and Pi's effective readiness before modifying the adapter; distinguish an idle agent with no received turn from a valid final answer and avoid blind resend.
6. Treat every runtime or protocol change as new work requiring new evidence.

## Available local evidence

Adapter deterministic tests use fixtures and do not open a live GUI or configure hosts:

```sh
python3 -m unittest automation/agent-swarm/test/test_herdr_task.py
python3 -m unittest discover -s automation/agent-swarm/test
```

Before operating, follow [validation](validation.md), [SSH channel](ssh-channel.md), and [SMB mount](smb-mount.md). For the task contract, see [Herdr + Pi tasks](herdr-tasks.md).
