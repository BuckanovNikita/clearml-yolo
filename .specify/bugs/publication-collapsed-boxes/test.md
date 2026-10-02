# Bug Verification: Optional visualization and collapsed predictions

- **Slug**: publication-collapsed-boxes (reused from context)
- **Tested**: 2026-10-02
- **Assessment**: [assessment.md](assessment.md)
- **Fix**: [fix.md](fix.md)
- **Result**: verified

## Summary

The original collapsed-box geometry passes CSV parsing with its coordinates, label,
confidence and index preserved. Visualization errors at the command boundary warn
and allow the invocation lifecycle to complete. This verification covers the parser
and command/lifecycle behavior. The subsequent shared-stand retest below also
establishes real database persistence; a real ClearML/GPU pipeline is not claimed.

## Checks Performed

| Check | Command / Action | Result | Notes |
| --- | --- | --- | --- |
| Original geometry | Parse the supplied row at index 225 | Pass | Exact coordinates, Unicode label, confidence and index retained |
| Original failing path | Re-read a native prediction CSV previously rejected at row 764 | Pass | All 149,819 rows retained, including collapsed boxes |
| Affected regressions | `uv run --locked --no-sync pytest tests/test_publishing.py tests/test_publication_data.py tests/test_publication_commands.py tests/test_pipeline.py tests/test_predict.py tests/test_metrics.py -q --tb=short` | Pass | 109 passed |
| Full regression suite | `uv run --locked --no-sync pytest -q` | Pass | 746 passed, 9 opt-in database tests skipped, 4 existing deprecation warnings |
| Lint | `uv run --locked --no-sync ruff check .` | Pass | No findings |
| Types | `uv run --locked --no-sync mypy .` | Pass | 96 source files checked |
| Imports | `uv run --locked --no-sync lint-imports` | Pass | All 9 contracts kept |
| Patch whitespace | `git diff --check` | Pass | No findings |
| Independent final review | Focused boundary/geometry tests and diff review | Ship | 22 passed, 44 deselected; no blocking findings |
| Real labels | FiftyOne `Detection.validate()` with services disabled | Pass | Zero width, zero height and point geometry retained |
| Real database | Opt-in `test_collapsed_native_predictions_are_persisted` against task-owned isolated configuration | Setup blocked | Database prerequisite unavailable; not a passing persistence check |

## Output Excerpts

Before the geometry fix, regression fixtures raised
`ValueError: Invalid publication box at CSV data row 225`.
Before the boundary fix, eight new visualization failure cases escaped as exceptions.
Both observations were captured before changing the corresponding production logic.

Final suite: `746 passed, 9 skipped, 4 warnings in 127.97s`.
Targeted parser checks: `24 passed`.
Lifecycle regressions confirm required prediction artifact upload and task completion
after both preflight and publication failure, with no failed task status.

## Documentation Update

Reviewed and updated README, contract summaries, publisher contract, active spec,
plan and quickstart. Annotated the superseded strict-failure intent in existing task
and checklist history. Markdown parsing, fence/whitespace structure and local links
are validated after creating this report. Current example commands name existing
tests and preserve documented configuration/defaults. Dated historical evidence
remains unchanged.

## Residual Risks

- The initial real-database prerequisite was unavailable; the subsequent
  authenticated shared-stand retest below resolves that limitation.
- SDK adapters are replaced in lifecycle tests; these do not prove live ClearML uploads.
- Partial visualization state can remain in the backend after a publication failure;
  existing task-scoped retry/recovery applies. No computational results are filtered.
- Receipt/run-link bookkeeping can be incomplete after its own warning; successful
  adapter writes may still exist. Cancellation retains its normal interruption behavior.

## Recommendation

Accept the parser and optional-visualization boundary fix. Database persistence
is now verified by the retest below; do not infer GPU or ClearML-upload acceptance.

## Shared-stand retest — 2026-10-02

After provisioning an authenticated external MongoDB, all nine opt-in
`tests/test_fiftyone_publisher.py` checks passed against a dedicated test database
(`9 passed, 723 third-party deprecation warnings in 5.15s`). This covers real
dataset reuse, recovery, normalization, exact evaluation overlays, concurrency,
and persistence of zero-width, zero-height and point detections.

An additional real publication placed the supplied Unicode-label prediction at
CSV data index 225, using a synthetic 1920×1464 image. The persisted detection
retained its label, confidence, index and normalized zero-height box; the receipt
reported a complete run. Task-owned datasets were removed after verification.
This uses synthetic media because the user's original image was not provided.

The first external-database attempt exposed a configuration issue: a database
path in the URI overrides MongoEngine's explicit database name. Removing that
path and retaining `authSource` restored consistent application/test isolation.
The infrastructure env helper now rejects URIs that select a database path.
Only the nine datasets created by that failed test attempt were removed.

Shared infrastructure and machine setup are documented in global environment
guidance. The application publication contract needed no further changes during
this retest. No native model execution, GPU computation or live ClearML artifact
upload was performed in this follow-up.

## Completion review — 2026-10-02

The final independent audit identified credential-bearing backend exception text
in visualization warnings. Three test-first cases reproduced the exposure in
factory, preflight and publication errors. Warnings now retain safe context and
the exception type while omitting arbitrary backend messages.

Verification of the final application diff in an isolated checkout:

- Normal regression suite: `749 passed, 9 skipped, 4 warnings in 124.97s`.
- Separate authenticated real-FiftyOne suite: `9 passed, 723 upstream deprecation
  warnings in 4.90s`.
- Focused publication/parser/pipeline checks: 69 passed.
- Ruff passed; strict mypy checked 96 files; all nine import contracts passed.
- Changed Markdown structure and local paths: 12 files and 79 links validated.

An extra experiment enabling real-database tests inside the entire ordinary
suite crashed with SIGILL in garbage collection during the existing threaded
FiftyOne concurrency test. The adapter concurrency code and test were unchanged;
the same nine real tests, including concurrency, passed in a fresh process. The
native raiser was not identified, so this is not claimed as a passing combined
run or a resolved native-runtime issue. The normal and separate opt-in checks
follow the documented quickstart; the evidence does not establish a patch regression.

The isolated checkout excludes unrelated local dependency metadata and source
overrides. The original checkout and approved external dependency revisions are
preserved. Feature task history and the original assessment remain unchanged;
the bug remediation, final verification and documentation stages are complete.
