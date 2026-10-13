# Implementation Plan: Static analysis policy audit

**Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

## Summary

Inventory the installed Ruff catalog and actual suppression sites, tighten compatible
checks, and add a whole-project Vulture gate with an explicit confidence policy.
Keep audit claims grounded in current code and reproducible probes.

## Technical Context

Python 3.12, uv, Ruff, strict mypy, pytest and local system-language pre-commit hooks.
Development-only Vulture addition; retain every existing locked dependency node.
No runtime data model or external API change. Scan src/, tests/ and scripts/ together.

## Constitution Check

Pass before and after design: strict checking remains enabled, suppressions stay
specific, dynamic SDK boundaries stay explicit, and protected dependencies remain
unchanged. Framework setup fixtures must keep their effect when unused parameters
are removed. Preserve concurrent staged files and avoid unrelated lint churn.

## Workstreams and dependencies

1. Read-only delegate audits explicit Ruff/mypy suppressions while the parent probes
   Vulture and records intent. A second read-only delegate audits omitted rule families.
2. Parent owns pyproject.toml, uv.lock, hook changes, minimal source/test corrections,
   the policy report, development guide and this feature's artifacts. Integrate audits
   before finalizing policy; no agents share write ownership.
3. Parent verifies the combined change, then a fresh read-only reviewer checks the
   final diff. Fixes require re-verification and fresh review.

## Verification

Run Ruff, mypy, Vulture, import-linter and affected regression tests. Verify the hook
and a temporary dead-code negative control. Review lock metadata for preservation
of all existing dependency nodes, especially digital-metrics and report-generator.
Run applicable hooks without changelog side effects on unrelated staged work.

## Documentation scope

Maintain docs/static-analysis.md and docs/development.md. Record rule audit inventory,
commands, counts and limitations in this feature's dated evidence. Application contracts,
README usage and GPU/end-to-end guidance need no change because runtime behavior and
user configuration remain unchanged. Validate Markdown, local links and changed examples.

## Structure

Existing src/, tests/ and scripts/ stay in place. No new runtime subsystem, schema,
public contract or speculative abstraction is introduced.

## Approved follow-up — 2026-10-13

Continue the accepted audit with explicit preview opt-ins, meaningful keyword-only
verification expectations, available SciPy/tqdm stubs, and executable tooling boundaries.
Recover only task-owned uncommitted changes into the isolated implementation branch.
Preserve all existing dependency nodes and external source revisions.

### Architecture and parallel work

The [architecture record](architecture.json) maps existing runtime layers to the
import-linter and architecture tests. The only new boundary test guards release-tool
imports and development-only lint/stub dependencies, including injected violations.
No new runtime module or wrapper object is needed. Explicit encodings clarify existing
UTF-8/ASCII file contracts; scientific calculations and external APIs stay unchanged.

After plan validation, one bounded agent owns reported encoding fixes, comparison
local renames, keyword-only ClearML expectations and focused regression coverage.
A second owns SciPy/tqdm type fixes after the parent installs the exact stubs.
The parent owns configuration, dependency locking, tooling boundary tests and docs.
These streams converge before full verification and a fresh independent read-only
review. Commit, master integration and the established Git-tag release follow acceptance.

### Concrete settings and acceptance

Enable lint preview with explicit-preview-rules; explicitly select ASYNC119, B901,
B909, PT029, PLE1141, PLE4703, RUF045, RUF054, RUF066, RUF071, RUF074, RUF052 and
PLW1514. Keep formatter preview unchanged and constrain Ruff to >=0.16.1,<0.17.
Keep ANN401, PLC0415, PLR0913, PLR0917 and TRY003 justified project exceptions.
Pin scipy-stubs==1.18.0.1 and types-tqdm==4.70.0.20260906; remove their missing-import
overrides. Keep Vulture at 80% and refresh its advisory 60% inventory without bulk deletion.

Run Ruff, strict mypy, Vulture, import contracts, architecture tests, affected tests,
full pytest and all pre-commit hooks. Exercise Unicode file handling, SDK verification
and comparison/significance/progress paths. Verify negative controls for Vulture,
stub API misuse and prohibited tooling dependencies. Validate Markdown, local links,
rule inventory and architecture acceptance; record actual results and exclusions.
