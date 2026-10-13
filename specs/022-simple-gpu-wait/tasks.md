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

## Amendment: configurable memory availability (2026-10-12)

- [x] T013 [US3] Record FR-007–010 in spec.md and implementation/documentation scope in plan.md.
- [x] T014 [US3] Add failing inventory boundary and settings/wiring regressions in tests/test_gpu_resources.py and tests/test_execution_controls.py.
- [x] T015 [US3] Implement validated controls and memory inventory in src/clearml_yolo/core/execution.py and adapters/runtime/gpu_resources.py (T014).
- [x] T016 [US3] Wire Hydra/direct/supervisor/worker settings and per-owner FIFO admission in src/clearml_yolo/entrypoints/hydra and adapters/runtime/gpu_queue.py (T015).
- [x] T017 [US3] Verify per-project limits, reservations, contraction and bypass behavior in tests/test_gpu_queue.py and affected runtime/configuration tests (T016).

### Documentation update and validation

- [x] T018 Update README.md, docs/project-contracts.md, contracts/execution.md, quickstart.md and specs/013-gpu-experiment-queue/contracts/queue-state.md (T016).
- [x] T019 Validate Markdown/links/exported YAML and run affected tests, lint, typing and import checks; record verification-memory-limit.md (T017–T018).
- [x] T020 Obtain fresh independent read-only review of integrated changes and resolve findings (T019).
- [x] T021 Follow docs/development.md commit/release checks, preserve local source overrides and publish only authorized Git commits/tags (T020).

Parallel work: read-only configuration/queue investigation alongside parent tests and
implementation. Review follows integrated verification; release follows review.
Analysis: FR-007/008 map to T014–015, FR-009/010 to T016–017, documentation to T018–019.
All four requirements are covered; no unresolved ambiguity or constitution conflict.

## Amendment: force and readable admission (2026-10-12)

- [x] T022 Record FR-011–015, parallel ownership, architecture and acceptance checks.
- [x] T023 [P] Add failing force/routing/replay tests and implement policy/core/Hydra/launcher changes (FR-011/012; T022).
- [x] T024 [P] Add failing hidden telemetry/index tests and extend immutable inventory (FR-015; T022).
- [x] T025 Implement immutable queue diagnostics and direct/queued readable decisions with regression tests (FR-013/014/015; T024).
- [x] T026 Verify five-of-eight, FIFO/reservation release, combined blockers, throttling, force bypass, generated YAML and sweeps; run GPU/launcher, architecture, Ruff, mypy and full applicable checks (T023–T025).
- [x] T027 Run controlled native CPU/GPU acceptance; record physical multi-GPU limitations and clean task-owned resources (T026).

### Documentation update and acceptance

- [x] T028 Update README, current GPU/queue contracts, quickstart and diagnostic guidance; validate Markdown/links/examples (T023–T025).
- [x] T029 Inspect integrated diff, obtain fresh independent review, record evidence and reconcile/validate architecture acceptance (T026–T028).
- [ ] T030 Complete applicable commit/release checks, preserving unrelated edits and exact local source overrides (T029).

Follow-ups (not implementation tasks): forced-kill orphan recovery; permission-denied
process inspection. Both require their own reproduction and lifecycle design.

T027 execution evidence: CPU/single-GPU and forced sequential sweep completed;
fresh ClearML status/policy/artifact readback is still unverified because of the
documented SDK naming-query failure after initial harness lookup/cleanup trouble.
T030 remains gated on that publication acceptance gap; no release can claim it passed.
See [verification-force.md](verification-force.md).

T029 implementation/architecture acceptance: final fresh review returned `ship`;
record validation and code/documentation checks passed. This does not close the
separate T027 publication readback or T030 release gates.

On 2026-10-13, the user separately authorized “commit and push work”. Source
commit/push proceeds under the normal commit checks, preserving unrelated edits.
T027 and T030 remain open for the documented live readback and release gates;
source delivery creates no version tag. See the dated source-delivery amendment
in [verification-force.md](verification-force.md).

Source delivery completed: `be587ec` passed all normal commit hooks on an
unchanged-source retry and was pushed to `origin/master`. Unrelated edits and
local source overrides were preserved. No release tag was created or pushed;
T027 and T030 remain open for their stated acceptance gaps.

Release verification resume, 2026-10-13: T027 is complete. Six fresh native
invocations passed exact-task status, effective-policy and downloaded-artifact
readback, including CPU/GPU train→predict and checkpoint reload. The maintained
SDK thread-reporting setting enabled startup without application or service changes.
Scoped cleanup returned zero projects/tasks. Historical failed attempts above remain
recorded; physical multi-GPU/DDP and MPS are unverified. T030 remains open until the
checked version commit, final installed distributions and explicit Git-tag push.
