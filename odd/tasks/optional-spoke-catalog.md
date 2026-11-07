Objective: Make shared SMB mounting optional for new spoke onboarding; document the generic aiconnect functionality.
Branch: feat/optional-spoke-catalog. Delivery: local merge to main; no PR (user correction). Runner: python3 -W error::SyntaxWarning -m unittest discover -s automation/agent-swarm/test.

## Specs
S1: "spoke sea opcional también en el funcionamiento de Agent Swarm"; "al ser un agente instalado en un server remoto podría verse expuesto a ataques o podría darse el caso de no necesitar acceder a esa carpeta". Check: an explicit non-SMB spoke setup route works without mounting and cannot silently claim a remote-only project exists.
S2: "documentalo y si es necesario implementalo para que sea opcional en el proceso del setup de un nuevo agent swarm". Check: setup/help/docs and tests reflect optional spoke mount; current shared-catalog behavior remains.
S3: "tenias que comentar la funcionalidad, no el atajo al dispositivo en si". Check: generic aiconnect function guidance replaces hardcoded device example in English/Spanish runbooks.

## Tasks
T1 [S1-S2] route delegated + inline security correction; done; commit ebd4d38: local-only catalog, project-aware preflight, bidirectional acceptance, docs. RED observed (10 errors/failures initial; 4 registry failures follow-up), GREEN 213 tests/1 skip.
T2 [S3] route inline; done; commit pending: generic zsh function in English/Spanish, zsh syntax and example tested.
T3 [S1-S3] route inline + independent verifier for high-risk contracts; in_progress; commit pending: full checks passed; verifier blockers corrected and independently rechecked.

## Log
L1: "documentalo y si es necesario implementalo para que sea opcional en el proceso del setup de un nuevo agent swarm"
L2: Earlier user correction verbatim: "el atajo opcional aiconnect wsl-leo << no, tenias que comentar la funcionalidad, no el atajo al dispositivo en si. también el montaje de la carpeta smb de proyectos en el orquestador (spot?) debe ser opcional"
L3: Earlier user clarification verbatim: "spoke sea opcional también en el funcionamiento de Agent Swarm << esto. porque si añadimos un agente remoto, no se si estando en la vpn de tailscale es capaza de montar el directorio compartido del spoke. y aunque se pudiera, al ser un agente instalado en un server remoto podría verse expuesto a ataques o podría darse el caso de no necesitar acceder a esa carpeta , que opinas?"
L4: Exploration: registry demands absolute catalog_root and repo, setup derives both from SMB, acceptance assumes shared relative repo. Proposed explicit local-only spoke with preinstalled local checkout, no implicit access to hub projects. Forecast >400 changed lines; ask-on-risk delivery strategy.
L5: Implemented paired local paths and catalog_mode; mount skipped, explicit project-aware preflight and target-specific acceptance. Tests 213 OK (1 skipped), diff --check OK; generic aiconnect zsh example checked. Independent verifier found local registry containment and four stale doc lines; fixed with RED (4 failures) / GREEN (1 test) and verifier recheck PASS. No live remote onboarding (would mutate remote host).
L6: User initially chose a single oversized PR, then corrected this: "recuerda que no hay PR, soy yo solo en este pryecto y el merge se hace directo a main. dame un resumen de lo hecho". Delivery is local merge to main, no PR. Differential script compared unchanged list/self CLI stdout/stderr/exit against main and passed. Native RDD assess for ebd4d38 was unassessable (package-local-binary-missing); no native review claim. Independent verifier PASS after correction.
