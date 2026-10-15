# Bug Verification: Input and evaluation identity correctness

- **Slug**: input-evaluation-correctness
- **Tested**: 2026-10-15
- **Assessment**: [assessment.md](assessment.md)
- **Fix**: [fix.md](fix.md)
- **Result**: passed — integrated verification and fresh independent review accepted

## Summary

The reproduced cache substitution, unresolved execution paths, missing literal labels
and unsupported comparison modes are corrected. Focused scientific evaluation preserves
perfect AP50 and exact threshold boundaries for all requested identity strings. Native
execution, actual ClearML downloads, packaging and final independent review are owned
by the parent integration workflow and are not claimed by this report.

## Checks Performed

| Check | Command / action | Result | Notes |
| --- | --- | --- | --- |
| Baseline reproduction | Offline Python probe documented in assessment | reproduced | Distinct sources reused cache; NA became missing; prediction paths remained relative; stem comparison accepted. |
| Red regressions | `uv run --frozen --no-sync pytest tests/test_input_correctness.py -q` before runtime edits | 7 failed, 1 passed | Three behavioral failures plus four missing new interface failures. |
| Final dedicated regressions | `uv run --frozen --no-sync pytest tests/test_input_correctness.py -q` | 23 passed | Includes perfect AP, unknown-name rejection, explicit/legacy/malformed provenance, BOM caches and immutable-image cache-hit semantics. |
| Workflow regression suite | Command below | 248 passed | Prior to final BOM-only adjustment; affected BOM paths separately checked afterward. |
| Dataset/publication follow-up | Command below | 123 passed | Executed after BOM adjustment, including existing strict lexical validation and raw detector exports. |
| Type checking | Command below | passed | 187 source/test files at that checkpoint; no errors. |
| Lint | `uv run --frozen --no-sync ruff check src/clearml_yolo` plus all nine changed test files | passed | No rules disabled. |
| Import contracts | `uv run --frozen --no-sync lint-imports` | passed | 43 kept, 0 broken. |
| Architecture plan | `python3 <module-architecture-planning>/scripts/validate_architecture.py --record .specify/bugs/input-evaluation-correctness/architecture.json --phase plan --repo-root .` | passed | Run before implementation; final reconciliation adds inspected Hydra/storage paths. |
| Native/GPU/publication download, distribution and final review | Parent workflow | pending here | Mocked inference/publication tests do not establish these outcomes. |

Workflow regression command:

```text
uv run --frozen --no-sync pytest tests/test_input_correctness.py tests/test_dataset_cache.py tests/test_predict.py tests/test_metrics.py tests/test_pipeline.py tests/test_comparison_reinfer.py tests/test_comparison_scoring.py tests/test_comparison_identity_cache.py tests/test_comparison_assemble.py tests/test_clearml_results.py tests/test_result_lifecycle.py tests/test_invalid_prediction_workflows.py tests/test_quality_properties.py -q
```

Dataset/publication follow-up:

```text
uv run --frozen --no-sync pytest tests/test_dataset.py tests/test_dataset_records.py tests/test_publication_data.py tests/test_detector_publication.py tests/test_detector_integration.py tests/test_publication_commands.py -q
```

Type checking:

```text
uv run --frozen --no-sync mypy src/clearml_yolo tests/test_input_correctness.py tests/test_metrics.py tests/test_dataset_cache.py tests/test_predict.py tests/test_comparison_identity_cache.py tests/test_comparison_reinfer.py tests/test_clearml_results.py tests/test_comparison_assemble.py tests/test_quality_properties.py
```

## Output and Limitations

Workflow suite: `248 passed, 28 warnings in 115.39s`; dataset/publication follow-up:
`123 passed, 4 warnings in 7.55s`. Warnings concerned existing hydra-zen Pydantic
deprecations and missing CJK glyphs in dependency-generated plots. They are not evidence
of numerical or identity loss. All task-owned temporary probe files were automatically
removed; tests managed their own temporary resources.

## Architecture and Diff Reconciliation

The inspected runtime diff modifies existing storage, core evaluation, application ports/
contracts/workflows, evaluation/YOLO/ClearML adapters and composition/Hydra validation.
No new runtime module, dependency revision or import exception was introduced. All effects
remain adapter-owned. Tests and new bug evidence are task-owned; architecture-checker,
documentation/checker changes, the original local dependency overrides and untracked
grid-search draft belong to other workstreams or pre-existing work and are excluded here.
The linked architecture record remains pending final independent review and parent
acceptance; a structural plan pass does not establish that acceptance.

## Recommendation

Use these focused results in parent integration acceptance. Preserve existing five-GPU
and multi-user/multi-host NFS gaps; this subtask neither executes nor closes those gates.

## Final subtask checks

After the last regression addition, `uv run --frozen --no-sync mypy
tests/test_input_correctness.py` passed (1 source file). The project documentation checker
on this bug's three Markdown artifacts checked 3 files with 0 issues; `git diff --check`
on the owned runtime/test paths was clean. Runtime and tests are frozen for parent
native, packaging, routine-suite and independent-review acceptance.

## Integration follow-up: geometry fixtures (2026-10-15)

Systematic debugging reproduced the full-suite failures with
`uv run --frozen --no-sync pytest tests/test_prediction_geometry.py -q`:
`3 failed, 45 passed in 4.16s`. The failures were incompatible fixture membership and
an obsolete error-message expectation, not a runtime identity defect.

After correcting the fixtures and adding invalid-geometry/unknown-image admission
regressions, the following command passed: `87 passed in 21.70s`.

```text
uv run --frozen --no-sync pytest tests/test_prediction_geometry.py tests/test_input_correctness.py tests/test_invalid_prediction_workflows.py -q
```

`uv run --frozen --no-sync ruff check tests/test_prediction_geometry.py
tests/test_input_correctness.py --output-format concise` passed, and `git diff --check`
was clean for the changed test. The architecture plan validator passed after appending
`tests/test_prediction_geometry.py` to the existing record's scope. No runtime source
changed. Parent owns the full-suite rerun and fresh integrated review.

The follow-up type check, `uv run --frozen --no-sync mypy
tests/test_prediction_geometry.py tests/test_input_correctness.py`, passed with no issues
in 2 source files. The documentation checker validated both appended bug reports with
0 issues.

## Parent integrated acceptance

The final [verification](../../../docs/evidence/2026-10-15-correctness-cleanup/verification.md)
and [fresh independent review](../../../docs/evidence/2026-10-15-correctness-cleanup/review.md)
close this report's earlier pending integration status. Runtime source matches native
and installed-package acceptance; all review findings were corrected and independently
accepted. The architecture record is reconciled with the complete task-owned diff.
External five-GPU/NFS and documented static-analysis limits remain open. Release
delivery is recorded separately after commit/tag checks.
