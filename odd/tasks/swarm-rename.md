# Rename Agent Fabric to Agent Swarm and stop versioning the host registry
Branch: main (owner-directed; no branch policy given) | Delivery strategy: single-pr (inherited; no push authorized this turn) | Test runner: python3 -m unittest discover -s automation/agent-swarm/test (after rename; automation/agent-fabric/test before)
Forecast: >400 changed lines, mostly mechanical renames; one cohesive work unit.

## Specs
S1. User request, verbatim: "config/hosts.json no debería estar versionado. quitalo de git. en su lugar crea config/hosts.example.json". Acceptance: `config/hosts.json` is untracked and ignored but remains on disk; `config/hosts.example.json` is tracked, generic, and valid for the registry loader.
S2. User request, verbatim: "antes de hacer el cambio, hay que reajustar el git remote, elimina el actual y reapunta a https://github.com/LeonardoX77/agent-swarm.git". Acceptance: `origin` points only to that URL; nothing is pushed.
S3. User request, verbatim: "reemplaza la palabra Fabric por Swarm en todo el proyecto, incluido el skill/s de pi/Claude/opencode". Acceptance: no active tracked file, path, identifier, command, skill or doc keeps the word in any case, except removed v1 command names kept in historical records so history is not falsified.
S4. User scope selection: "Repo + skills instaladas en este Mac". Acceptance: after the repository work, update installed Pi/Claude/OpenCode skill and bootstrap copies on this Mac only after naming and authorizing each outside path; no remote Mac is touched.

## Tasks
T1 [S2] Replace remote `origin`; route inline; done (no push); commit n/a.
T2 [S1] Untrack and ignore registry, add valid generic example with test and docs; route inline; done (RED: example missing -> GREEN: registry loads it and the file stays generic); committed together with T3-T4 in one commit.
T3 [S3] Rename paths and replace the word across tracked files; route inline; done (all tracked paths renamed with git mv, content replaced, leftovers limited to removed v1 command names); same commit.
T4 [S3] Verify tests, links, absence of the word, and installed-path references; route inline; done (110 tests OK, five CLIs answer --help, 13 docs/36 links valid, diff check OK); same commit.
T5 [S4] Update installed local skill/bootstrap copies after per-path authorization; route inline; pending (needs the owner's per-path permission); no repo commit.

## Log
L1. config/hosts.json no debería estar versionado. quitalo de git. en su lugar crea config/hosts.example.json
antes de hacer el cambio, hay que reajustar el git remote, elimina el actual y reapunta a https://github.com/LeonardoX77/agent-swarm.git
reemplaza la palabra Fabric por Swarm en todo el proyecto, incluido el skill/s de pi/Claude/opencode
L2. Remote changed first: old origin removed, `origin` now https://github.com/LeonardoX77/agent-swarm.git. Previous history already contains hosts.json on the old remote; untracking does not rewrite history.
L3. Scope answer: "Repo + skills instaladas en este Mac". Runtime identifiers (aliases, paths, markers) are renamed in code; deployed Macs and old aliases are not migrated here. Spoke checkouts share this tree through SMB, so stale skill copies on other Macs will point at removed paths until updated.
L4. Implemented as one cohesive commit because the example registry, its test and the renamed tree overlap in the same files. The ignored local registry stays on disk with its old `fabric-*` SSH aliases and paths, so existing delegation keeps working until the owner migrates aliases. The on-disk checkout directory is still named `mac-agent-fabric`; renaming it is the owner's call and also changes registry `repo` paths on spokes.
