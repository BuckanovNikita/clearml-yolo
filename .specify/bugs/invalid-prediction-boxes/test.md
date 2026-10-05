# Bug Verification: Invalid prediction boxes

- **Slug**: invalid-prediction-boxes (from assessment/fix context)
- **Tested**: 2026-10-05
- **Assessment**: [assessment.md](assessment.md)
- **Fix**: [fix.md](fix.md)
- **Result**: verified

## Summary

The original zero-width reproduction now emits one warning and continues with
empty predictions and a valid calibration result. Mixed valid/invalid inputs and
all-invalid inputs pass through real scoring, dashboards and evaluation payloads.

## Checks Performed

All direct uv checks used `--locked --no-sync` to preserve the dependency environment.

- Targeted geometry, metrics, comparison scoring/assembly and payload tests:
  **134 passed**.
- Finalized workflow regression file: **11 passed** in the parent's run, including
  mixed/all-invalid inputs at 640 and 960, raw CSV/cache preservation, match identity,
  all-invalid FNs and clean-input scoring parity. Confidence-filtered valid boxes
  still contribute to raw mAP.
- Ruff: passed. Mypy: passed for 114 source files. Import contracts: all 9 passed.
- First broad suite: 1060 passed, 9 skipped, 2 failed, 4 warnings. It collected the
  integration file during authoring; both failures were its earlier incorrect
  AP expectation (0.995 vs the dependency's 0.9975) for mixed comparison inputs.
  The finalized integration tests pass; no production scoring change was required.
- A subsequent broad run passed **1063 tests**, skipped 9, with 4 warnings. Its
  pre-commit wrapper reported concurrent tracked-file edits while the numeric-string
  review correction was being applied, so it was not accepted as a clean hook run.
- Review found pandas numeric coercion rejected upstream-valid strings such as
  `1_000`. A failing regression reproduced the issue; conversion now uses upstream
  float semantics, with per-cell fallback only for malformed frames. Post-correction
  geometry/workflow tests passed (48 cases before the final numeric-string matrix
  expansion); the finalized geometry matrix passes 41 cases.
- A second review reproduced invalid confidence escaping validation on a discarded
  geometry row. A failing regression now covers missing/nonnumeric/non-finite and
  out-of-range confidence plus missing/reserved labels on geometry-invalid rows.
  The filter validates these fields through the unchanged upstream validator using
  a separate copy with finite positive substitute geometry.
- Markdown parsing and all 71 local links/anchors passed across five documents.
  `git diff --check` passed. Required commit/release hooks remain completion gates;
  their results are reported with the resulting Git commit/tag.

## Documentation Update

The CLI evaluation safety contract and current-contract summary describe filtering,
warning counts, raw-artifact preservation, prepared match identity, and all-invalid
behavior. README and FiftyOne publication guidance remain accurate; command/config
examples and native execution behavior did not change. Existing dated history and
workflow tooling were preserved.

## Residual Risks

Native prediction/checkpoint loading and ClearML tracking are replaced in workflow
tests. No live GPU, ClearML upload or native inference verification was performed;
real digital-metrics preprocessing, matching, mAP and reporting were exercised.
Nine opt-in integration tests are skipped by the default suite. Four warnings come
from existing hydra-zen Pydantic field deprecation notices.

## Final Independent Acceptance

After both review corrections, the parent passed all **59 geometry and workflow
regressions**, Ruff, mypy (114 source files), and all 9 import contracts. A fresh
read-only reviewer independently passed the same 59 tests and returned **ship**
with no blocking findings. Requested delegate model/effort was GPT-6.1 Sol / medium;
runtime model/effort telemetry was not exposed. Parent inspection confirmed no
changes to digital-metrics source, gitlink, dependency reference or locked revision.

## Final Parent Gate

`uv run --locked --no-sync pre-commit run --all-files` passed on the settled
implementation, including the full pytest suite, Ruff, mypy, import contracts,
changelog generation, format/whitespace and configuration-file checks. Final
Markdown parsing and all 71 local links/anchors across five documents also passed.
The contributor and release commits must run their configured hooks again.
