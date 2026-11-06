# Scoped campaign improvements fix

- Slug: `campaign-scoped-improvements` (from the bounded assessment).
- Applied: 2026-11-05.
- Assessment: [assessment.md](assessment.md).
- Status: applied; final integrated acceptance remains pending.

## Changes

| File | Result |
| --- | --- |
| `adapters/observability/capture.py` | Nonfinite scalar errors identify title, series, iteration and value before any journal write |
| `adapters/torchvision/training.py` | Nonfinite loss errors retain the exception type and identify batch, target image IDs and component losses before backward/update |
| `core/evaluation/result_rows.py` | Convert columns once to records, retaining sparse all-text null inference and canonical lineage/export semantics |
| `tests/test_campaign_numerics.py` | Real nonfinite scalar and Torch CPU forward regressions pin context and unchanged failure safety |
| `tests/test_result_export.py` | Extension metadata, geometry exclusions, threshold flags and sparse numeric audit/CSV boxing regressions |
| `tests/test_native_backend_ddp_harness.py` | Stub accelerator discovery only; retain real CPU AdamW, EMA, serialization and digest evidence |
| `docs/multi-model-backends.md` | Explain contextual failures and preserve scientific settings during diagnosis |

The six tracked source/test/doc files match the preserved scoped campaign bytes
exactly, and the new diagnostic test was copied unchanged. `git apply --check`
and application passed against the current master plus DINOv3 port. No dependency revisions, SDK ownership or project import edges changed;
the pure row helper adds only the standard-library `Hashable` type import. DINOv3 files, `.importlinter`, environment,
root package metadata and original worktrees were excluded from write ownership.

## Verification

The [dated test report](test.md) records four failing baseline diagnostics, then
251 passing focused diagnostics/export/CPU observer/architecture checks. Parent
verification still owns 50,000-row exact parity/profile, final canonical and
documentation checks, prospective CY/queue compatibility, fresh integrated
review and architecture acceptance. This scoped port does not repair the
original numerical computations or close SIGILL/full campaign recovery.

## Deviations and follow-up

The original full campaign recovery assessment is preserved in its source
worktree and retained history. This task creates a bounded derived ledger because
the user selected diagnostic/export/fixture improvements without full recovery.
The original 20-case matrix and its scientific settings remain untouched and
unresolved; no historical timing or source check is promoted to native recovery.
No intermediate commit, release, installation or private automation update was
performed by this bounded implementation. The parent owns the final integrated
workflow and companion portable usage update.
