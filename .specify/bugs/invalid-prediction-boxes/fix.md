# Bug Fix: Invalid prediction boxes

- **Slug**: invalid-prediction-boxes (from assessment context)
- **Fixed**: 2026-10-05
- **Assessment**: [assessment.md](assessment.md)
- **Status**: applied

## Summary

Geometry filtering now runs once on each in-memory evaluation input before it
splits into prepared predictions and the raw mAP frame. Original CSVs and the
external digital-metrics source and pin remain unchanged.

## Changes

- `comparison/scoring.py`: shared finite, numeric, positive-extent filter; one
  bounded warning with mutually exclusive reason counts and affected image names.
- `tasks/metrics.py` and `tasks/compare.py`: filter evaluation copies before
  preprocessing. Validation inherits the metrics path.
- `tests/test_prediction_geometry.py`: coordinate variants, enabled preprocessing,
  all-invalid calibration, sample bounds, index preservation and strict GT/schema/
  confidence validation.
- `tests/test_invalid_prediction_workflows.py`: real scoring/reporting through
  metrics, validation and comparison with controlled native prediction output.

## Local Verification

Before the fix, the new mixed-geometry regression failed in upstream validation.
After the fix, the initial 31 coordinate tests passed. Broader checks and final
acceptance are recorded in [test.md](test.md).

## Documentation Update

Updated evaluation safety in `specs/001-release-030/contracts/cli.md` and the
summary in `docs/current-contracts.md`. Reviewed README and FiftyOne publication
contracts: their raw-artifact promises remain true, so no changes are needed.
There are no changed command or configuration examples or machine-specific facts.

## Deviations from Assessment

Review corrected numeric parsing to match upstream float conversion, including
underscore and Unicode-digit strings. A second review confirmed that discarded
rows must retain confidence/label validation: an isolated copy with valid substitute
geometry now runs the existing upstream validator before dropping original rows.
That validation-only copy never enters preprocessing or scoring. Missing required columns remain upstream schema failures; missing coordinate
cells are dropped. Existing prepared-frame indexing and unrelated validation are
retained. Native inference is replaced only in integration tests; no GPU or live
ClearML outcome is claimed.
