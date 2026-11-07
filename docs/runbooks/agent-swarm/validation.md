# Validating the Agent Swarm channel

Validate the active channel before delegating a task. These checks do not replace `swarm-setup` human pauses or turn an SSH connection into authorization to modify a host.

## Checklist

- [ ] **Registry.** Review `config/hosts.json`: the destination exists; its SSH alias, catalog, checkout, and PATH match the host to use; and the SMB share is approved.
- [ ] **Local identity.** From the origin, run `automation/agent-swarm/bin/swarm-delegate self`. It must identify the host by its registered hostname prefix; an unknown host stops.
- [ ] **Destination.** Run `automation/agent-swarm/bin/swarm-delegate list` and select a name from that output. Do not replace it with an alias, IP, or informal label.
- [ ] **SSH, catalog, and project.** Run `automation/agent-swarm/bin/swarm-delegate preflight <target> --project <catalog-relative-project>`. JSON must include `"status": "ready"`. `project_unavailable` means that target lacks the requested project; do not submit or create paths as a shortcut. If a shared-mode spoke returns `catalog_missing`, resolve its SMB mount; for local mode, provision its configured local catalog and checkout instead.
- [ ] **Fingerprint and restrictions.** Confirm the alias uses `StrictHostKeyChecking yes`, a dedicated key, and an authorized entry with `no-agent-forwarding,no-port-forwarding,no-X11-forwarding`. These restrictions are not a sandbox and must not be relaxed for diagnosis.
- [ ] **Runtimes.** Confirm Pi, gentle-pi, and Herdr are available at the destination and that Pi has logged in from the GUI when needed. Do not automate login or copy credentials.
- [ ] **Catalog mode.** For shared mode, confirm the registered SMB share is mounted and exposes only the approved catalog. For local mode, confirm the configured catalog and checkout exist on that target; SMB must not be installed, copied, or mounted. Authentication is in Keychain only for shared macOS SMB.
- [ ] **Harmless task.** After human review, submit a read-only envelope with a new UUID, relative project, and `mode: executor`. Recover with the same UUID and close only after verifying it finished.
- [ ] **Evidence.** Retain only sanitized JSON output, phase, and diagnostics. Ensure they contain no passwords, tokens, private keys, complete prompts, or unnecessary project content.

## Acceptance criterion

The channel is ready when the origin identifies itself in the registry, preflight returns `ready`, the required catalog is available, SSH fingerprints and restrictions have been reviewed, and a harmless task can be recovered and closed without resending its envelope.

A failure does not authorize remote changes. Record the diagnostic, determine the responsible host, and return to the relevant `swarm-setup` phase or runbook with a person present.

## Boundaries

- There is no distributed exactly-once guarantee. If SSH fails or state is ambiguous, use `recover <target> <UUID>`; do not create another UUID for the same work.
- A task can modify a shared project. Coordinate the work window and review changes; there are no automatic locks.
- Historical results are in [Test evidence](test-evidence.md); they are observations with limits, not acceptance of the current deployment.
