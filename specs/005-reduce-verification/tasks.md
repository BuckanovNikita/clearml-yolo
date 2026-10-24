# Tasks: Reduce code and verify each release once

Input: [plan](plan.md), [specification](spec.md), [architecture](architecture.json).

## Phase 1: Setup

- [x] T001 Inspect current instructions, hooks, dependencies and baseline; record `evidence/baseline.md`.
- [x] T002 Create `spec.md`, research/design/contracts and validate `architecture.json` in plan phase.

## Phase 2: Foundational

- [x] T003 Analyze requirement coverage and agree disjoint stream ownership in `plan.md` before code edits.
- [x] T004 Declare direct safetensors and locked mutmut 3.8.x in `pyproject.toml`/`uv.lock`, preserving approved external metadata.

## Phase 3: US1 — Reduced maintained implementation

Independent checks: focused asset/composition/process tests plus actual import contracts and negative cases.

- [x] T005 [P] [US1] Migrate cancellation scenarios in `tests/test_gpu_cancellation.py` to active process_tree and remove `tests/test_gpu_supervision.py` plus `adapters/runtime/supervision.py`.
- [x] T006 [US1] Simplify `entrypoints/composition.py` module imports with typed ports and retained class-binding behavior; verify `tests/test_execution_lifecycle.py` and composition tests.
- [x] T007 [US1] Replace parser/hash loops in `adapters/assets/resolver.py`, storage identity/dedup, clearml native and export metadata; add malformed/nonempty/cache tests in `tests/test_model_assets_loading.py`.
- [x] T008 [P] [US1] Map duplicated enforcement to `.importlinter` and reduce `tests/architecture_helpers.py`/`tests/test_architecture.py`; preserve unique/dynamic/negative checks and graphlib cycles.

## Phase 4: US2 — One ordinary verification per source release

Independent checks: temporary Git repositories exercise actual hook/release state transitions and invocation counts.

- [x] T009 [P] [US2] Add failure/invalidation/index/environment/dependency and lifecycle tests in `tests/test_verify.py` and `tests/test_local_release.py`.
- [x] T010 [US2] Implement `scripts/verify.py` with exact content/environment fingerprints, private logs, atomic receipts and fresh-check flags.
- [x] T011 [US2] Integrate `.pre-commit-config.yaml` and `scripts/local_release.py` with validated generated-version mapping; retain tag/ownership/concurrency safeguards and `tests/test_tooling_boundaries.py`.

## Phase 5: US3 — Bounded mutation acceptance

Independent checks: selected offline baseline plus explicit result inspection.

- [x] T012 [P] [US3] Configure source/function/test/fixture selection in `pyproject.toml` and exclude generated mutants in `.gitignore`/`ruff.toml`/mypy.
- [x] T013 [US3] Run selected mutations, strengthen assertions for non-equivalent survivors and record all outcomes in `evidence/mutation.md`.

## Phase 6: Documentation update and acceptance

- [x] T014 Update `docs/development.md`, `docs/agent-workflow.md`, architecture/import/migration/assets/queue/static-analysis guidance, contract index and baseline; record portable usage review.
- [x] T015 Integrate all changes; remove/preserve local overrides and run canonical verification plus docs; record timings/check invocations and before/after line totals in `evidence/verification.md`.
- [x] T016 Obtain fresh independent review after verification, resolve findings, reconcile `architecture.json` with actual diff and validate acceptance; record `evidence/review.md`.
- [ ] T017 Complete task-scoped Conventional Commit and automatic Git-tag-only release/push, restore local overrides exactly and record `evidence/release.md`.

## Dependencies and parallel execution

Review follow-up (required before T016/T017 acceptance):

- [x] T018 Correct dependency inventory gaps and host bookkeeping normalization; add regression coverage and disprove/fix mutation survivor 47's assertion gap.
- [x] T019 Refresh the explicit mutation selection and canonical gate, prove actual receipt reuse across separate tool calls, then obtain fresh independent review of the integrated corrections.
- [x] T020 Correct nested fixture/package inventory exclusions found in fresh review; reproduce stale success, verify invalidation and repeat receipt/release regressions before the final gate.
- [x] T021 Include ignored root configuration and fixture inputs; verify invalidation, stage requirements and both index-retry paths before repeating the final gate.
- [x] T022 Replace hard-coded discovery roots with governed-directory traversal, preserve fixture Markdown and ignored external inputs, and verify failure/interruption retry plus independent inventory probes.

T001–T003 gate all implementation. T004 supplies new parser/mutation dependencies and precedes their verification. Runtime T005–T007, architecture T008 and tooling T009–T011 have disjoint ownership and may progress concurrently; parent owns T004/T012–T014. T013 follows mutation configuration; T015 waits for integrated implementation and mutation outcomes. T016 follows final checks; T017 follows accepted review. No bounded agent delegates further.

Implementation strategy: verify each stream with focused checks, integrate once, run the complete canonical suite after override removal, then review and release. Documentation evidence edits remain separate from application receipt identity. No unrelated full-suite repetitions.
