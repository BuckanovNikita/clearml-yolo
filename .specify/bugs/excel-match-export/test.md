# Bug Verification: Excel match-table export

- **Slug**: excel-match-export (assessment/fix context)
- **Tested**: 2026-10-01
- **Assessment**: [Assessment](assessment.md)
- **Fix**: [Fix report](fix.md)
- **Result**: partial — requested export behavior verified locally; production exception and live uploads unavailable; unrelated whole-suite failures remain.

## Summary

The reproduced prediction-match serializer failure no longer occurs: arbitrary
control-character diagnostics round-trip through CSV. A table with 1,048,577 rows
also round-trips with its first/last indices and complete row count. Only metrics
remain in evaluation/comparison Excel sheets; metadata/evidence sidecars retain
headers and publication through the strict deduplicating table adapter.

## Checks performed

| Check | Command/action | Result | Notes |
|---|---|---|---|
| Pre-fix regression | metrics/workbook focused tests | expected failure | 9 failed, 21 passed; IllegalCharacterError at reported prediction_matches.to_excel call |
| Excel row limitation | synthetic DataFrame.to_excel | reproduced | 1,048,577 rows rejected as larger than Excel limit |
| Affected tests | `uv run --locked --no-sync pytest tests/test_metrics.py -q --tb=short` | pass | 16 passed, including oversized CSV and illegal-character cases |
| Comparison regression | `uv run --locked --no-sync pytest tests/test_comparison_workbook.py tests/test_comparison_assemble.py -q --tb=short` | pass | 54 passed |
| Whole-suite snapshot | `uv run --locked --no-sync pytest -q --tb=short` | partial | 692 passed, 8 skipped, 4 failed; run preceded addition of the oversized CSV test |
| Ruff | `uv run --locked --no-sync ruff check .` | pass | Latest run; earlier unrelated filesystem-test PT012 was resolved by concurrent work |
| Mypy | `uv run --locked --no-sync mypy .` | pass | Latest run, 96 source files; transient unrelated native_dataset error was resolved by concurrent work |
| Import contracts | `uv run --locked --no-sync lint-imports` | pass | 9 kept, 0 broken |
| Patch whitespace | `git diff --check` | pass | Whole working tree at validation time |
| Markdown and local links | CommonMark parser with tables, balanced-fence check, local link-target existence | pass | Reviewed changed documentation and workflow artifacts |
| Independent review | fresh read-only export_review agent | ship | No scoped findings; parent inspected combined diff |
| Production run/ClearML downloads | unavailable production input and no integration invocation | not-run | No native training, GPU or real upload claims |
| Pre-commit | no commit requested | not-run | Mutating release/changelog hooks are outside scope |

The four whole-suite failures are all parametrizations of
`tests/test_publication_commands.py::test_remote_clone_does_not_replay_previous_owner_output_route`:
`False-train`, `False-pipeline`, `True-train`, `True-pipeline`. They fail while
monkeypatching absent `clearml_yolo.tasks.train.RUNS_ROOT`, before invoking the
export path. Concurrent filesystem work removed that import; this task preserved
those changes rather than repairing unrelated code/tests. Eight skipped tests are
not passing acceptance evidence. Four upstream Hydra/Pydantic deprecation warnings
were emitted by the whole suite.

## Documentation update and validation

Updated and inspected:

- [README](../../../README.md) export and artifact passages.
- [Publication inventory](../../../specs/008-dataset-clearml-tracking/contracts/publication.md).
- [Active spec](../../../specs/008-dataset-clearml-tracking/spec.md).
- [Quickstart](../../../specs/008-dataset-clearml-tracking/quickstart.md).
- [Contract index](../../../docs/current-contracts.md).
- [Export migration](https://github.com/BuckanovNikita/clearml-yolo/blob/96aa7508d9e16364722d9126f37748ce074d2134/docs/migration-evaluation-csv.md).
- [Integration skill](../../../.agents/skills/running-end-to-end-tests/SKILL.md).

Documentation describes exact workbook sheets, CSV filenames, full-precision
thresholds, deduplication aliases and migration from removed sheets. The parent
parsed nine Markdown files before this report, confirmed balanced fences and 61
local link targets, then included this report in final validation. No command,
configuration, machine endpoint or environment execution example changed;
existing global environment guidance did not need amendments. Completed histories
and installed Spec Kit files were preserved. The required documentation stage is
complete after the final Markdown/link check.

## Residual risks and recommendation

The original exception type/data were not supplied; the synthetic IllegalCharacterError
reproduction is not proof of that exact production cause. Re-run the user's original
invocation to confirm its particular failure. ClearML publication assertions use
mocked adapters; real upload/download, native training and GPU behavior were not run.
CSV consumers must migrate from removed Excel sheets as documented. The requested
export change is ready for use, with whole-suite blockers listed above. No commit or
push was performed; unrelated changes and shared resources remain intact.
