# Tasks: Simple GPU waiting

## Specification and design

- [x] T001 Capture the requested removal, compatibility boundaries and edge cases in spec.md.
- [x] T002 Inspect current queue, GPU inventory, Hydra execution and installed native device mapping.
- [x] T003 Define implementation and mandatory documentation scope in plan.md.
- [x] T004 Analyze requirements/plan/tasks: all FR-001–006 covered; explicit user instruction
  supersedes historical queue governance; no unresolved requirement decisions.

## Implementation

- [x] T005 [P] Add failing tests and stateless GPU wait; cover CPU bypass, busy-to-free,
  impossible demand, visibility, telemetry failure, interruption and own-process reuse.
- [x] T006 Replace supervisor dispatch with direct invocation and standard Hydra launcher;
  retain requested/effective configuration and native memory cleanup (depends on T005 API).
- [x] T007 Remove queue/worker/plugin implementation and obsolete queue tests; update
  packaging and architecture contracts/target checks (depends on T006).
- [x] T008 Verify same-process execution, direct error propagation, CPU bypass and
  sequential multirun with Hydra job environment/chdir behavior (depends on T006).

## Documentation update and validation

- [x] T009 [P] Update maintained GPU/CLI/filesystem/architecture/verification guidance and
  README; annotate superseded feature 013 contracts (depends on final implementation).
- [x] T010 Run affected/full checks, generated YAML and command helps, native CPU/GPU
  execution and distribution checks; record outcomes and limitations (depends on T005–T009).
- [x] T011 Validate changed Markdown/local links/examples and inspect full combined diff;
  obtain fresh independent review (depends on T010).
- [x] T012 Follow applicable release workflow only after release gates pass; publish Git
  tags only and restore local source overrides (depends on T011).
  Cancelled by the user's explicit no-commit instruction. The implementation commit
  already existed locally; no release commit, tag or push completed during that attempt.
  Partial release metadata and staging were removed on resume, preserving local dependency overrides.
  The subsequent explicit “commit and push” request reauthorized completion of this task.
  Release commit `0b3479d` passed commit and recovery checks; `master` and annotated
  tag `v0.21.0` were pushed. Exact local dependency overrides were restored unstaged.

Implementation, verification, documentation and Git-tag publication are complete.
See [verification.md](verification.md).
