# Pre-implementation consistency analysis

All FR-001–FR-009 map to T001–T013; all SC-001–SC-004 have explicit acceptance tasks. No scope clarification remains after approved full redesign, scientific/Pandera core, clean Python cutover and regenerated YAML. Constitution mismatch is explicitly resolved by T001 targeted amendment, not bypassed. Implementation must preserve current publication/recovery contracts and upstream revisions.

| Shared work | Producer / consumer | Resolution |
|---|---|---|
| T002/T003–T006 | module map / implementation paths | parent completes relocation before parallel source edits |
| T003/T004 | validated frames / evaluation inputs | preserve dataframe columns/index; structured findings |
| T004/T005 | computed/artifact DTOs / workflow ports | communicate interface moves before integration |
| T005/T006/T007 | injected dependencies / composition | parent owns final composition and cross-task imports |
| T008/T003–T007 | final modules / graph rules | final rules follow approved responsibilities, never whitelist violations |
| T010/T001–T009 | docs / implemented interfaces | final dedicated documentation stage |
| T011–T013/T009 | release acceptance / verified code | no success claim or release before required gates |

Each task's outputs match its tests and named scope; no task permits weakening validation or import boundaries.
