# Recovery compatibility verification — 2026-10-05

Scope: the approved recovery-only amendment in [task-recovery.md](contracts/task-recovery.md).
Current publication, inference settings, automatic baseline lookup, report formats and dependency
pins remain unchanged. No commits or dependency updates were performed. The existing local
`pyproject.toml` source overrides were preserved.

## Implementation and regression evidence

- Threshold recovery accepts ordered current/historical mappings, encoded JSON, Series,
  DataFrames, CSV (including ClearML's gzip DataFrame serialization) and dashboard XLSX.
  Tests cover leading-zero names, precision, single-value columns in either order, invalid
  classes/values, all adjacent source priorities and failures without fallback.
- Checkpoint recovery covers metadata, URL-decoded filename, last registered output, ordered
  checkpoint artifacts, ambiguity and selected-only download/validation failures.
- A new regression first reproduced mismatched checkpoint/provenance when registered models
  changed between reads. `resolve_task_model` now provides one selection to comparison.
- Mixed current/legacy and both-legacy tests exercise both roles, explicit threshold overrides,
  `test`/`val`, paired current-image membership (including empty images), unchanged frozen
  thresholds, truthful source links and agreement between dashboards/statistics.

## Checks executed

All commands used the existing environment with `uv run --locked --no-sync`.

| Check | Observed result |
| --- | --- |
| `pytest` | 1,002 passed, 9 skipped; four upstream hydra-zen/Pydantic deprecation warnings |
| `pytest -q tests/test_clearml_models.py tests/test_comparison_recovery.py` | 93 passed after final recovery additions |
| `pytest -q tests/test_comparison_recovery.py tests/test_comparison_assemble.py` | 57 passed, including both models legacy |
| Independent combined recovery/comparison test run | 149 passed |
| `ruff check .` | Passed |
| `mypy .` | Passed, 112 source files |
| `lint-imports` | All 9 contracts kept |
| `git diff --check` | Passed |

The full suite collected before ten final recovery cases and four both-legacy comparison
cases were added; the final focused runs include them and the reversed single-value-column
correction. Nine skipped tests are
opt-in FiftyOne persistence tests, outside this recovery change. Shared consumers (prediction,
validation and pipeline) are included in the full regression suite.

Documentation review covered README, contract summary/index, affected 001/008/010 contracts
and appended 012 specification/design/task artifacts. Twenty-one changed Markdown files parsed
and 121 local links resolved in the final parent check. The existing comparison CLI
composed successfully with `--cfg job`, explicit baseline/candidate task IDs, `split=val`
and a `001` class threshold override, preserving its string key and stored precision.

## Native verification

Two isolated CPU comparisons completed against a real ClearML stand through the application
`compare` function, its invocation owner and fully resolved native prediction group:

| Baseline | Candidate | Current split | Outcome |
| --- | --- | --- | --- |
| Legacy checkpoint artifact and uploaded dashboard DataFrame | Metadata-best Output Model and validation CSV | `test` | Completed |
| Metadata-best Output Model and validation CSV | Legacy checkpoint artifact and uploaded dashboard DataFrame | `holdout` | Completed |

Each split had two generated current images, one annotated and one empty. Both model input
manifests contained exactly that split's current images. Real native inference and scoring
ran for both roles. Runtime observation recorded unchanged scoring input/output thresholds:
legacy `0.3141592653589793`, current `0.2718281828459045`; no calibration calls occurred.

Both checkpoints were force-downloaded, matched their fixture SHA-256 hashes and loaded in
Ultralytics. The legacy DataFrame was actually stored as `dashboard_full_val.csv.gz`, and
recovery preserved its threshold exactly. Provenance identified the legacy `best.pt` artifact
without a model link and the current selected Output Model. All published comparison artifacts
were force-downloaded and hashed; workbook inspection retained only the `Сравнение` sheet.
Identical empty prediction tables used the existing canonical-table deduplication behavior.

Limitations: these were task-owned random-weight detection checkpoints using the installed
architecture, producing zero detections and an excluded class. This proves recovery, native
execution, frozen thresholds, paired membership and publication, not useful model quality or
statistical significance. No training, GPU execution, CLI launcher or separate native report
acceptance was attempted.
Historical architecture compatibility with the installed Ultralytics remains outside the
guarantee of artifact recovery. Initial fixture attempts required SDK lifecycle and full-group
configuration corrections; no application/dependency changes were made for those failures.
Machine-specific scripts, logs, task IDs and downloaded evidence are archived with the global
ClearML environment skill. Tagged cleanup deleted the owned project and its tasks/models/artifacts;
the final listing showed zero projects/tasks for the tag, and the owned run directory was removed.

## Independent review

Fresh independent read-only review returned **ship** for the code/docs, with no blocking
findings, after the combined 149-test run and diff checks. Final native-evidence review also
returned **ship**, independently checking all ten archived comparison-artifact hashes and
three source-artifact hashes, workbook sheets, exact frozen thresholds, both completed CPU
runs and cleanup evidence. No blocking findings remain.
