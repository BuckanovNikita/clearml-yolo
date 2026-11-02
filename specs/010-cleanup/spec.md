# Feature Specification: Simplify maintenance and complete pending delivery

**Created**: 2026-11-01
**Status**: Implemented, independently accepted and delivered; see [release](release.md).
**Baseline**: [Stage zero](../000-baseline/spec.md)

## Intent and boundaries

Maintain less duplicated implementation and test setup, correct demonstrated bugs,
reconcile current specifications, and reduce release verification cost without
changing supported public behavior or weakening ordinary acceptance.

The user selected preservation of public behavior, completion of genuinely pending
work, and optimization of the full verification gate. The initial request stopped at
creating and validating planning artifacts. Later implementation and delivery requests
continued the [plan](plan.md) through the completed [task ledger](tasks.md).
The original planning baseline below predates the refreshed-source amendment at the end.

The root checkout is stale relative to the locally recorded `origin/master` at
`b23952c` (CY 0.44.4). Previously delivered features 007–009 must not be implemented
or released again merely because their old copies appear unfinished here. Reconcile
both existing worktrees before implementation. The genuinely pending DINOv3 amendment
continues its existing 009 ledger; its local archive/native evidence does not establish
hosted-byte verification, final-pin checks, final review, or delivery.

## User scenarios and acceptance

### US1 — Preserve behavior while removing duplication (P1)

Maintainers simplify metrics and native Hub publication without altering numerical
results, model identity, public schemas, cache discovery, or failure handling.

Acceptance: orphan metrics rendering code disappears while the reporting owner stays;
Hub publication preserves safe paths, locks, validated atomic placement, copy fallback,
and original files. Existing public schema metadata and worker-role ownership remain.

### US2 — Receive consistent validation and trustworthy tests (P1)

Users see export-preview errors for known missing operation inputs, consistent with
runtime validation. Maintainers can run release fixtures with local uv overrides.

Acceptance: ONNX/build/verify missing-input reproductions become regression tests;
valid and deferred inputs remain supported. Preview never resolves external inputs.
Temporary release projects include only the selected semantic-release tables and
retain protected-lock and real-hook assertions.

### US3 — Spend less time maintaining and running acceptance (P1)

Maintainers remove proven overlapping cases and avoid rebuilding equivalent setup,
while preserving complete ordinary acceptance and trustworthy receipt reuse.

Acceptance: all import syntax forms and SDK ownership rules retain coverage; every
command/model/profile remains covered. New evidence distinguishes test-body count,
collected cases, setup cost, and full-run duration. Timing improvements are measured,
not inferred from case count or parallelism.

### US4 — Follow consistent contracts and complete pending work (P1)

Users and maintainers find current format, release, command, and weight-preparation
rules without confusing superseded intent with current behavior.

Acceptance: current summaries agree on schema 3 and release-only bulk preparation;
historical evidence and standalone selected-model resolution remain intact. Pending
DINOv3 publication completes its own documented gates before final code delivery.

## Functional requirements

- **FR-001**: Preserve public CLI/API behavior, configuration precedence, JSON-schema
  metadata, serialized data, scientific results, Python compatibility, and dependency pins.
- **FR-002**: Reconcile latest source and existing dirty work safely; complete only
  genuinely pending DINOv3 work through the existing 009 amendment and authorized asset exception.
- **FR-003**: Share pure export input-presence policy between execution and previews,
  preserving validation order, error messages, and exact `is not None` semantics.
  Known missing required inputs fail; unresolved expressions remain deferred without IO.
- **FR-004**: Isolate semantic-release fixture configuration from unrelated TOML tables,
  including local uv overrides, without weakening real-hook or protected-lock checks.
- **FR-005**: Remove the orphan methodology helper and consolidate Hub snapshot
  publication within its existing effect owner; preserve atomicity, validation and recovery.
- **FR-006**: Consolidate the identified overlapping configuration cases and independent
  syntax/SDK matrix dimensions, preserving every unique assertion and prohibited edge.
- **FR-007**: Add duration diagnostics and evaluate reusable isolated setup against a
  current baseline. Retain complete ordinary checks and existing byte-based receipt trust.
- **FR-008**: Reconcile schema-format summaries, bulk-preparation supersession, stale
  release claims, immutable manifest semantics, command inventories and status navigation;
  update affected portable guidance and preserve dated history.
- **FR-009**: Record module/interface/effect ownership before implementation; retain
  executable import contracts and negative cases without widening exemptions.
- **FR-010**: Require integrated canonical, documentation, affected browser/native,
  applicable mutation and latest/proposed/final paired-source checks, followed by fresh
  independent review and architecture acceptance before authorized final delivery.
- **FR-011**: Use bounded Sol workstreams with disjoint ownership and no child delegation;
  parent owns integration, evidence, review and release. Respect the current planning-only stop.

## Success criteria

- **SC-001**: Both reproduced validation/fixture failures pass original-path regressions,
  with runtime/export compatibility and preview isolation retained.
- **SC-002**: Maintained duplicate implementation decreases; safe Hub publication and
  fresh-cache offline native loading pass on the final source after its refactor.
- **SC-003**: The identified 51 redundant collected cases are replaced or removed with
  all unique scenarios mapped to retained checks. Record the actual net count after new
  bug regressions; no reduction is achieved by skipping required behavior.
- **SC-004**: Dated before/after evidence identifies source, environment, workload and
  timings. Reusable fixture setup is adopted only with demonstrated improvement and
  isolation; no unmeasured percentage speedup is claimed.
- **SC-005**: Current normative documents agree with their implementation authority;
  documentation/examples pass validation, and pending DINOv3 delivery has actual hosted
  and final-pin evidence rather than inferred completion.
- **SC-006**: Final checks, independent review, diff reconciliation and architecture
  acceptance are recorded before code delivery; historical hardware exceptions remain
  explicit limitations, never passing results.

## Assumptions and exclusions

No dependency upgrades, public feature removal, new validator framework, installed
workflow changes, history reset, deployment, or routine project distributions are
included. Code delivery remains Git commits and annotated tags only. The existing
weights-release exception applies only to the pending model assets. Existing physical
acceptance gaps and scoped historical delivery exceptions are neither erased nor
closed by CPU/process fixtures. New failures are assessed through the native bug route.

## Implementation authorization and baseline refresh — 2026-11-01

The later user request “/compact then implement a plan” authorizes execution of
this saved plan through verification and its existing release scope. Planning-only
stopping statements above describe the earlier request and no longer limit execution.
Fetched CY origin/master is e82cc49 (0.44.5), including completed DINOv3 tasks
T020–T023 and published weights-2026-10-31. Retain that delivered work; no duplicate
asset publication or intermediate code release is needed. The isolated cleanup
workspace starts at that source; both original dirty worktrees remain untouched.

## Delivered outcome — 2026-11-02

Implementation, corrected companion integration, required documentation, independent
review and Git source delivery are complete. [Release evidence](release.md) and the
completed ledger supersede historical pending checkpoints without deleting them.
Supported public contracts and approved dependency sources remain preserved; all
recorded physical/live-stand evidence limits remain explicit.
