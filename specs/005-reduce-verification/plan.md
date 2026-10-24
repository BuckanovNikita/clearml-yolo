# Implementation Plan: Reduce code and verify each release once

**Branch**: `master` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

## Summary

Implement the supplied approved plan with three independent streams after the architecture gate: runtime/asset/composition cleanup, receipt/release tooling, and architecture enforcement consolidation. Parent owns dependency/mutation configuration, documentation, integration, final verification, review and release. Preserve current behavior except removal of `adapters.runtime.supervision`.

## Technical Context

Python >=3.12.13,<3.14; uv/uv_build; strict mypy and Ruff; pytest includes ordinary architecture and native CPU-DDP cases. Add direct safetensors dependency and locked mutmut 3.8.x development dependency without unrelated dependency upgrades. Keep the approved editable external trees and lock entries unchanged. Tooling receipts/logs live in Git-private storage and use no application runtime imports. Final verification uses `uv run --frozen --no-sync python scripts/verify.py`, with `--docs` independently and `--force` when fresh checks are required.

Mutation scope is `core.datasets.validate_training_box`, `core.evaluation.policy`, and `core.export_quality`. Copy required sources/fixtures explicitly and select existing offline dataset/evaluation/export tests; exclude native training, GPU, publication and release machinery. Mutmut supports function/module selection and incremental reruns. Assess results, not exit status alone; all survivors require stronger tests or reviewed equivalence evidence.

## Constitution Check

Before and after design: retain typed ports, pure domain policy and adapter-owned effects; no DI framework or dependency monkeypatches. No future annotations, installed workflow changes, upstream revision updates, release distributions, deployments or packages. Preserve other work and task-owned process cleanup. Required verification, documentation and independent review remain acceptance gates. Existing workflow text requiring separate architecture pytest runs will be reconciled with the canonical complete suite (same assertions, one invocation).

## Project Structure

- `src/clearml_yolo/adapters/runtime/supervision.py`: delete obsolete API; migrate tests to active process_tree and queue callers.
- `entrypoints/composition.py`: direct module imports, same typed factories and class binding semantics.
- `adapters/assets/resolver.py`: safe_open format validation and existing ValueError fallback boundary.
- `adapters/storage/{identity,dedup}.py`, `adapters/clearml/native.py`, `adapters/export/metadata.py`: file_digest without dropping tracing or post-read identity checks.
- `tests/architecture_helpers.py`, `tests/test_architecture.py`, `.importlinter`: consolidate supported rules; retain effects, dynamic resolution, allowlists and inert/target checks; graphlib cycles.
- `scripts/verify.py`, `scripts/local_release.py`, hook configuration and tooling/lifecycle tests: exact input receipts, atomic success, index/release checks.
- `pyproject.toml`, `uv.lock`, Ruff/Git exclusions and mutation tests/evidence: bounded offline mutation acceptance.

## Architecture

See [architecture.json](architecture.json) for affected modules, interfaces, dependency/effect ownership and executable acceptance. Runtime adapters own signals/files/SDKs; composition builds typed ports; verification owns subprocesses, fingerprints and private receipts. Import-linter owns supported static rules and augmented dynamic graph evaluation; AST checks retain only unique rules. Actual configured negative cases prove the retained rejection paths.

Release reuse is a narrow exception: exact source parent, expected release paths, parsed root-version-only metadata changes and generated changelog hash are checked before receipt mapping. Existing ownership, concurrency and conflicting-tag checks remain. An index/worktree mismatch prevents reusing evidence for another file view. Docs receipts have separate inputs, so dated prose evidence does not invalidate application checks.

## Execution and acceptance

Agents own disjoint scopes and cannot delegate further. Parent changes configuration and records; runtime and verification streams wait for validated planning, then proceed concurrently with architecture. Integrate all streams and inspect their checks. Remove/preserve exact local uv overrides before final canonical verification and keep absent through review, contributor commit and generated release. Restore exactly and unstaged on success or failure.

Fresh independent read-only review follows parent integration/verification and covers Python behavior, receipt trust, architecture coverage and mutation equivalence. Reconcile the complete diff, including new/deleted files, with this record and tasks; validate architecture acceptance. Then use existing Conventional Commit/post-commit/tag workflow on master and push only intended branch/tag. No new approval is needed within the supplied scope.

## Documentation scope

Update development/agent workflow/static-analysis/import boundaries, API migration, model assets, contract index and baseline verification sections. Inspect README and module diagrams. Portable corp-skills usage sources contain no removed Python API or contributor check commands; record an inspected no-change reason if final diff remains internal. Keep actual counts/timings and logs in dated evidence here. Run docs validation including untracked Markdown.
