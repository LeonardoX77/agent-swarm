# Pi tasks through Herdr

`swarm-herdr-task` runs a Pi task on the host controlled by Herdr. It creates UUID-exclusive resources, keeps a durable ledger, and obtains the response from its own session JSONL. `swarm-delegate` invokes it over SSH from another registered Mac.

## Lifecycle

1. `submit` receives an envelope on stdin and reserves `task_id` in the ledger.
2. It creates a private session with a Pi v3 header, an unfocused Herdr tab, and a Pi agent whose `--session` points to that session.
3. It persists every intent before the remote effect and verifies tab, pane, runtime, name, and session before sending the exact envelope.
4. `recover` reads only its own JSONL: it finds the user message and follows its chain to a final assistant response with `stopReason: "stop"`.
5. `close` closes only its own tab after a verifiable result. The typed absence of that tab confirms closure.

Ledger phases are `reserved`, `create_intent`, `created`, `start_intent`, `started`, `submit_intent`, `submitted`, `result`, `cleanup_intent`, and `closed`; `unknown` and `recover_intent` represent recovery. There is no automatic path back to `submit`.

## Delegation between Macs

`config/hosts.json` is the source of truth. It defines the SSH alias, catalog, checkout, PATH, and GUI cwd per host. From the origin:

```sh
automation/agent-swarm/bin/swarm-delegate list
automation/agent-swarm/bin/swarm-delegate self
automation/agent-swarm/bin/swarm-delegate preflight <target>
automation/agent-swarm/bin/swarm-delegate submit <target> < envelope.json
automation/agent-swarm/bin/swarm-delegate recover <target> <UUID> [--wait SECONDS]
automation/agent-swarm/bin/swarm-delegate close <target> <UUID>
```

`<target>` must be a `list` name. `preflight` checks only SSH and catalog; if a spoke reports `catalog_missing`, mount its share using [SMB mount](smb-mount.md) before submitting work. The remote response is retained unchanged.

SSH exit 255 makes the state unknown from the origin. Recover later or repeat `submit` with the **same** envelope; never create another UUID for the same work. If a Mac is off, do not use the channel; use local alternatives.

## Envelope and quick use

The envelope contains exactly `task_id`, `origin_host`, `project`, `goal`, `acceptance`, and `mode: executor`. `task_id` is a UUID; `project` is relative to the catalog. Replace these placeholders with registry values:

```sh
printf '%s' '{"task_id":"<UUID>","origin_host":"<origin-host>","project":"<relative-project>","goal":"Review the change.","acceptance":"Return findings.","mode":"executor"}' \
 | automation/agent-swarm/bin/swarm-herdr-task submit --project-root <catalog-root>

automation/agent-swarm/bin/swarm-herdr-task recover <UUID>
automation/agent-swarm/bin/swarm-herdr-task close <UUID>
```

`recover` waits and polls every two seconds for 120 seconds by default. `--wait` accepts 0–900; `--wait 0` performs one read. `submit` accepts only bounded stdin; `swarm-herdr-task --registry PATH` permits a validated registry source in tests.

## Security and recovery boundaries

| Area | Contract |
| --- | --- |
| Identity | An unknown host fails unless an explicit, existing, secure catalog is supplied. |
| Execution | Herdr resolves explicitly or through `PATH`; each call uses closed argv, without shell or injected environment. |
| State | Ledger, sessions, and directories are private; an existing session or ambiguous effect becomes `unknown`. |
| Retries | There is no automatic resend or distributed exactly-once guarantee. |
| Close | Active agents, foreign identities, and incomplete results are rejected. |

A valid report, including `pending`, `unknown`, or `timed_out`, exits 0. Invalid input or failure exits 2. The final response includes `task_id`, `status`, `resubmit: false`, and, when available, `resulttext`, `userentry`, and `assistantentry`.

## Local verification

```sh
python3 -m unittest automation/agent-swarm/test/test_herdr_task.py
python3 -m unittest discover -s automation/agent-swarm/test
```

Tests use Herdr fixtures. They neither test a live GUI nor constitute a deployment.
