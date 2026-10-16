# Implementation Plan: Readable shared queue

**Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

Implement the approved three-story feature using pure readable formatting, durable
archive sidecars, and explicitly resolved shared file-store configuration. Preserve
raw identities/bytes and all scheduling and ownership invariants.

## Technical Context

Python >=3.12.13,<3.14; development interpreter 3.12.13. Existing uv/uv_build,
Pydantic, Textual, Loguru, pytest, strict mypy, Ruff, Vulture and import-linter remain
authoritative. File storage retains atomic NFS records and host-local flock coordination.
No dependency resolution or digital-metrics changes. Existing local pyproject source
overrides and the unrelated grid-search document must be preserved.

## Constitution Check

Typed pure core; effects stay in adapters; CLI composition supplies dependencies.
Direct commands do not import queue/UI modules. New helpers need cohesive responsibilities
and exhaustive import classification. Changes intentionally amend CLI/display contracts
at the user's explicit request, not scientific outputs or persisted job states.
Native Spec Kit owns artifacts; installed skills and .specify files remain unchanged.
Use explicit feature-path discovery because helpers that persist feature.json would
violate that last restriction. No Spec Kit stage hooks are registered; Git hooks run
the documented checks and master-only local release workflow.

## Project Structure and Architecture

The [architecture record](architecture.json) describes scope, contracts and acceptance.

- Core: pure human-text/reference policy, unchanged raw model identity, archive view
  metadata. No filesystem, SDK, logging or environment effects.
- Application queue service: reference resolution, owner archive operations and visibility
  after full-history scheduling/replay, through explicit storage/process ports.
- Queue adapters: frozen adapter settings, safe TOML input, host binding, atomic archive sidecars and
  propagation into store transactions, GPU controls, workers and guardians.
- Observability/reporting/ClearML adapters: readable display boundaries retaining original
  captured bytes, scalar values, receipts and machine provenance.
  Opaque class names use distinct display aliases. The existing workbook identity adapter
  owns a reversible presentation envelope through the dependency's public metadata APIs;
  source DataFrames, metrics and original class-key recovery remain exact. No dependency
  source changes or scientific recomputation are permitted.
  Fixed-set tables share one distinct alias map. Scalar registries retain assignments
  within the invocation owner or console publication state across calls and checkpoints;
  no process-global task state is introduced.
- Entrypoints: readable CLI defaults/explicit JSON, job selection, archive filters and TUI.

Add import negative cases for new helpers; reuse inward dependency, SDK ownership,
pure-core/effect and direct-versus-queue contracts. No broad ignores or loosened rules.

## Interfaces and sequencing

See [contracts/interfaces.md](contracts/interfaces.md) and [data-model.md](data-model.md).
First validate architecture. Then bounded agents implement settings, archive/service and
readable reports/console in disjoint files; parent owns CLI/TUI, GPU word labels,
architecture registration, real-user harness and documentation. Storage constructor
changes are coordinated through its archive owner. Parent integrates and runs checks
before a fresh independent final review. Agents do not delegate or commit.

## Acceptance and documentation

Run scoped regressions and then `uv run --frozen --no-sync pytest`, Ruff, mypy, Vulture,
`lint-imports`, architecture tests and `python scripts/check_docs.py --all` through uv.
Run real two-user fixtures, retain readable dated evidence and clean up owned resources.
Run appropriate native/ClearML publication checks through the repository E2E skill.
Validate architecture record in plan and acceptance phases with the installed shared validator.

Update README (Russian), docs/queue.md, filesystem-policy.md, diagnostics.md,
current-contracts.md, affected identity/publication/plot contracts and the canonical
corp-skills clearml-yolo skill/references. Preserve historical evidence. Validate examples,
Markdown, links and skill discovery. Reconcile complete diff and review evidence before
release. Follow docs/development.md commit source-override removal/restoration and Git-only
semantic release, including authorized pushes. Production host setup is excluded.
