# Implementation plan: behavior-preserving cleanup

**Date**: 2026-11-01
**Status**: Implementation and independent acceptance complete; release pending.
The original planning scope below is superseded by the dated authorization at the end.
**Specification**: [spec.md](spec.md)
**Ledger**: [tasks.md](tasks.md)

## Outcome and technical context

Complete genuinely pending DINOv3 work, fix reproduced failures, reduce redundant
tests and maintained implementation, and reconcile contradictory contracts. Preserve
supported commands, configuration, public JSON-schema metadata, scientific values,
dependency sources and Python >=3.12.13,<3.14. Retain uv, uv_build, strict mypy,
Ruff, Vulture, import-linter and complete ordinary pytest acceptance.

The inspected root HEAD is 0037059, while recorded origin/master is
b23952c433f2addbbdc981fbed1fd8073602cd01 (0.44.4). The root is behind 20 commits.
The linked DINOv3 worktree contains the genuinely pending amendment. Planning here
does not authorize copying stale root files over current implementation. Re-fetch
and reconcile both snapshots before implementation; preserve originals and local
dependency overrides. Details and evidence limits are in [research.md](research.md).

## Native workflow and stopping point

Use Spec Kit specify/clarify-if-needed/plan/tasks/analyze before implement, retaining
the native bug assess/fix/test records for the two failures. Existing 009 tasks
remain authoritative for its DINOv3 amendment; link rather than duplicate completion
history. This request creates and verifies planning artifacts only. No application
changes, commits, tags, publication or deployment occur during this planning task.
Do not change installed workflow tooling or the active feature selector. Future
execution selects this directory explicitly using supported prerequisite discovery.

## Implementation decisions

### Baseline and pending weights

Parent creates an isolated latest-source workspace and inventories each dirty file
against its original base and latest source. Record retain/already-delivered/unapplied
dispositions; never infer ownership from untracked status. Prepare an isolated
normally resolved CY/queue environment with approved external revisions.

Finish the existing DINOv3 tasks T020-T023 in their recorded order: documentation and
notices, prepublication checks/current and proposed pairing/review, authorized immutable
snapshot publication and hosted-byte verification, explicit pin update, then eventual
code delivery. Reuse unchanged verified local archives and their existing identity;
a conflicting published tag with different bytes blocks replacement. The first
required canonical run supplies the pre-optimization per-command timing baseline as well as
applicable prepublication evidence. Combine subsequent cleanup into one final code
release; do not manufacture a separate intermediate code release. Benchmark targeted
release/graph setup separately with duration reporting before optimization. Final
canonical per-case diagnostics arrive with the reporting-only tooling change; the
baseline does not depend on that later change.

### Runtime workstream

- Extract export input-presence policy into one pure function in the existing core
  export-request module. The existing method delegates with identical validation
  order, messages and `is not None` presence semantics. Preview invokes the same
  predicate for a known operation, treating unresolved presence as potentially
  present so independently known absences still fail. Unknowns remain visibly
  deferred. Do not resolve expressions, inspect files or execute workflow targets.
- Remove metrics' orphan `_methodology_frame` and its exclusive json import. Keep
  the active reporting implementation and observable outputs.
- Consolidate duplicated Hub blob-to-snapshot publication into a typed internal
  helper receiving source/blob, destination and validator. Preserve locks, native
  symlinks, validated copy fallback, atomic replacement, containment and originals.
- Retain schema metadata and worker-role helpers; their removal would change
  introspection or introduce an unjustified adapter dependency.

### Tests and tooling workstream

- Fix release fixture generation to extract only semantic-release tables and their
  children. Cover later unrelated tables/local uv sources without weakening the
  protected-lock or real-hook assertions.
- Remove eight configuration round-trip and four warning cases subsumed by the
  complete export/self-containment matrix; transfer ClearML/backend/profile assertions.
- Replace the six-syntax by nine-SDK product with six minimal-graph syntax tests and
  nine configured SDK-owner negative integrations. Preserve positive/shadowed alias
  behavior and every ownership rule. This removes 39 redundant cases, for 51 total
  before bug regressions.
- Share immutable import graph/options setup; copy before contract mutation or edge
  injection. Keep fresh-process command isolation and all CPU-DDP scenarios.
- Benchmark one immutable release-repository seed copied to each Unicode/spaced test
  directory. Retain real hooks, independent writable Git state, environment cleanup
  and path correctness. Adopt only with measured improvement and isolation evidence;
  otherwise record the rejected optimization and keep independent setup.
- Add `--durations=25` to canonical pytest reporting without changing selection.
  Retain byte fingerprints, index checks, invalidation and release-recovery trust.

### Contract reconciliation

Correct the maintained schema-2 summary to schema 3, retaining legacy readers.
Explicitly supersede old bulk upstream-fallback promises with the accepted release-only
correction, keeping standalone resolution distinct. Correct stale unreleased claims,
immutable manifest-tag examples, command inventory and current status navigation.
Preserve dated history, hardware limitations and scoped delivery exceptions.

## Architecture and interfaces

[architecture.json](architecture.json) records future runtime scope, interfaces,
dependencies, effects and executable coverage. Core owns pure export policy;
application owns port-based orchestration; Hub owns cache/network/filesystem effects;
entrypoints own preview composition; verification tooling owns subprocesses/private logs.
No new layers, widened peer exceptions or public CLI/wire changes are planned.

Reuse inward, SDK-owner, peer, initializer, dynamic-import and tooling contracts and
their negative cases. Validate the record in plan phase before implementation and
acceptance phase only after actual checks, final diff reconciliation and fresh review.
[planning-architecture.json](planning-architecture.json) separately records the
documentation-only impact of writing this plan; it is not runtime acceptance.

## Orchestration and integration

The parent retains the selected model/effort and owns baseline reconciliation,
shared contracts, DINOv3 stages, workflow records, documentation, integration and release.
After validated interfaces and baseline evidence, dispatch two bounded agents using
sol-orchestration and inherited model/effort:

| Owner | Exclusive writes | Acceptance evidence |
| --- | --- | --- |
| Runtime agent | Export core/preview and regression tests; metrics helper; Hub helper and affected asset tests | Original failure regression, runtime compatibility and cache publication checks |
| Tests/tooling agent | Release fixtures/tests; configuration consolidation; architecture/isolation fixtures; verifier duration reporting | Unique-scenario mapping, fixture isolation, test counts and measured setup costs |
| Parent | Planning/task records, shared docs, asset pin/preparation amendment and integration | Complete diff reconciliation and final gates |

Resolve any newly discovered shared-file overlap before edits. Bounded agents cannot
delegate further. Parent checks returned diffs and results. A fresh reviewer with no
write ownership assesses final integrated changes after parent verification. Missing
or failed gates and unresolved blocking findings remain acceptance gaps.

## Verification, documentation and delivery

Follow [quickstart.md](quickstart.md) for commands. Run focused regressions during
implementation, including tooling-boundary checks whenever architecture helpers or
verification infrastructure change, then one final canonical gate on integrated
source and final pin.
Also run docs, catalog/browser, scoped mutation applicability and normally resolved
current/proposed/final CY-queue checks. After the Hub refactor repeat fresh-cache
restoration and genuine offline DINOv3 loading; earlier native evidence predates it.
Record source/interpreter/dependency/cache conditions, net test count and comparable
timings. No percentage speedup is promised; an existing receipt is not a current baseline.

Update affected README in Russian, current topic contracts, active specifications and
authoritative portable usage sources. Validate Markdown/links, catalog and changed
examples. Preserve original001-009 completed history and old hardware exceptions;
unexecuted physical outcomes never become passes.

After future implementation acceptance, follow normal commit/tag-only code delivery,
exact local uv-source preservation, post-commit recovery and intended-ref pushes.
Verify final source/installed paired versions and remote refs. Reuse canonical evidence
only for unchanged trusted inputs; no hooks are bypassed. Weight assets use only the
existing explicit model-assets exception. No code distributions, registry publication
or deployment are planned.

## Implementation authorization and baseline refresh — 2026-11-01

The later user request “/compact then implement a plan” authorizes execution of
this saved plan through verification and its existing release scope. Planning-only
stopping statements above describe the earlier request and no longer limit execution.
Fetched CY origin/master is e82cc49 (0.44.5), including completed DINOv3 tasks
T020–T023 and published weights-2026-10-31. Retain that delivered work; no duplicate
asset publication or intermediate code release is needed. The isolated cleanup
workspace starts at that source; both original dirty worktrees remain untouched.
