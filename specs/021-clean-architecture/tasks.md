# Tasks: Clean architecture and Pandera

## Phase 1 — Foundation
- [X] T001 Record approved specification, migration map, analysis and constitution amendment; establish baseline (FR-001–FR-009).
- [X] T002 Relocate modules/imports/runtime targets using the complete map without compatibility shims (FR-001, FR-007).

## Phase 2 — Independent implementation
- [X] T003 [P] Add core Pandera validation schemas and behavioral tests; integrate storage parsing without changing invalid-row policy (FR-003, FR-004).
- [X] T004 [P] Separate evaluation models/computation/rendering, typed upstream conversion and pure comparison code (FR-003, FR-006).
- [X] T005 [P] Introduce typed workflow ports/contracts and explicit injection; separate Hydra conversion and composition (FR-002, FR-005).
- [X] T006 Extract identity persistence, pure redaction, runtime/storage/SDK boundaries, inert initializers and publisher factory (FR-003, FR-006–FR-008).

## Phase 3 — Integration
- [X] T007 Integrate relocated entrypoints, native callbacks/worker/probe/plugin targets and remove helper cycles (FR-005, FR-007, FR-008).
- [X] T008 Enforce exhaustive layers, SDK owners, transitive isolation and negative architecture tests (FR-001–FR-003).
- [X] T009 Run affected and full pytest, Ruff, mypy, lint-imports; fix task-caused failures without weakening checks (SC-001, SC-002).

## Phase 4 — Documentation
- [X] T010 Update architecture/migration guidance, README, contract index, current code links and constitution; validate Markdown/links/examples (FR-009, SC-004; depends T003–T008).

## Phase 5 — Acceptance and release
- [X] T011 Build/install wheel and sdist, exercise command helps and regenerated configs (SC-004).
- [X] T012 Verify real CPU/GPU/ClearML/FiftyOne/comparison/upload failure contracts and owned-resource cleanup; record dated evidence (SC-003).
- [X] T013 Obtain fresh independent final review, converge against spec/plan/tasks, satisfy hooks and complete authorized release commits/tag pushes (FR-009).

## Execution ledger
2026-10-08: approved conversational plan materialized. Isolated worktree created; baseline tests running. Existing local uv.sources preserved. No workflow extension hooks configured.

2026-10-08: Baseline on 72334f4: 1279 passed, 30 skipped. New package-existence check failed four cases before relocation and passes afterward. Pandera 0.34.1 added; existing locked dependency versions unchanged. Module migration complete; behavioral extraction remains in progress.

2026-10-08: Extracted scientific validation, typed ports/contracts, computation/rendering, identity persistence and redaction. Entrypoints bind per-invocation dependencies while workers transport unbound targets. Parent verification found and fixed standalone calibration ownership handling and completed test migration; regression and acceptance gates remain open.

2026-10-08: The integrated regression rerun passed 1,373 tests (30 skipped).
Parent final architecture/injection/comparison checks passed 164 tests. All 27 import
contracts, Ruff and strict mypy passed. Wheel and sdist installations passed all ten
command helps and configuration regeneration. Native CPU/GPU and standalone workflows
passed publication checks; live comparison reuse exposed a pre-existing cache identity
bug, so acceptance remains open until the repaired original path and cleanup pass.

2026-10-08: Full regression reached 1,387 passed, 30 skipped. Cache acceptance exposed
both SDK timestamp sensitivity and CSV confidence precision loss; content-based keys
and round-trip parsing have red/green regressions. Parent affected verification passed
85 tests. Independent full-change and subsequent precision-correction reviewers both
returned ship. Original native resources were cleaned up with zero remaining owned
inventory; fresh native numeric equivalence is being verified under a new tag. Maintained
documentation, 19 Markdown files and 137 local links/anchors passed validation.

2026-10-08: Fresh native cache replay passed exact confidence bits, frozen-threshold
rows, source relationships, workbook cells and published confusion/PR data. Inference
cache CSV/metadata bytes and timestamps were unchanged; provenance sidecars retained
identical bytes. Both native tags are closed with raw API, queue and process cleanup
proof. See verification.md. Final stable hooks and release remain under T009/T013.

2026-10-08: Stable all-files hooks passed with 1,390 tests passed, 30 skipped and
52 warnings. Source commit 493f039 and release commit 6f50507 passed all required
commit/recovery hooks. Version 0.20.0 wheel and sdist installation checks passed.
Master and annotated tag v0.20.0 were pushed. The documented release recovery path
handled local-only dependency resolution with no dependency changes. Buildable intent
across FR-001–FR-009, SC-001–SC-004 and all three user stories is satisfied; no new
convergence tasks remain. Physical multi-GPU execution remains explicitly unverified.
