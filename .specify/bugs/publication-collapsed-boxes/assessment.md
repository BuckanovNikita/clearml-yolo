# Bug Assessment: Publication rejects collapsed native prediction boxes

- **Slug**: publication-collapsed-boxes (automatically selected)
- **Created**: 2026-10-02
- **Source**: pasted text
- **Verdict**: valid
- **Severity**: medium

## Report

`fiftyone_adapter.py:252` calls `read_predictions`, which raises
`ValueError: Invalid publication box at CSV data row 225`.

## Symptom

Enabled publication can fail after successful inference because a native prediction
has zero width or height after clipping to the image boundary.

## Reproduction

Calling `read_predictions` on an existing local native prediction CSV with identity
aliases reproduces the same exception at data row 764. That row has finite,
ordered coordinates with equal top and bottom values. The original reported row 225
has not been provided; its precise invalid condition remains unconfirmed.
An automated fixture will reproduce the same validation failure at index 225.

## Suspected Code Paths

- `src/clearml_yolo/publishing/data.py:_box`: requires strictly positive box area for
  both ground truth and raw predictions.
- `src/clearml_yolo/publishing/data.py:read_predictions`: uses this shared validator.
- `src/clearml_yolo/inference.py:_detection_rows`: exports native coordinates unchanged.
- `src/clearml_yolo/publishing/fiftyone_adapter.py:publish`: parses before database writes.

## Root Cause Hypothesis

High confidence for the reproduced failure: Ultralytics scales and clips boxes to
image boundaries, which can collapse their extent. Publication incorrectly applies
ground-truth positive-area validation to these raw predictions. The reported row's
cause remains unconfirmed without its CSV. Publication must retain raw coordinates
and row indices rather than dropping detections or changing evaluation input.

## Proposed Remediation

**Preferred**: Allow finite, ordered zero-area boxes when reading predictions only.
Continue rejecting reversed or non-finite coordinates, invalid confidence, and
zero-area ground truth. Preserve all raw rows, coordinates, confidence and indices.

**Files likely to change**:

- `src/clearml_yolo/publishing/data.py`
- `tests/test_publication_data.py`
- `tests/test_fiftyone_publisher.py`
- `specs/006-fiftyone-integration/contracts/publisher.md`
- `specs/006-fiftyone-integration/spec.md`
- `specs/006-fiftyone-integration/quickstart.md`

**Tests to add or update**:

- Prediction fixtures with zero width, zero height and both at CSV index 225.
- Invalid prediction coordinates and confidence remain rejected.
- Ground-truth zero-area boxes remain rejected.
- Opt-in real FiftyOne persistence retains collapsed prediction coordinates and index.

## Risks & Considerations

- Zero-area predictions are retained for fidelity; they may not be visible as rectangles.
- Do not filter or alter inference/evaluation data or external dependencies.
- Preserve unrelated working-tree edits and existing database resources.

## Documentation Update

Clarify raw prediction geometry in the publisher contract, active feature specification
and quickstart. Validate changed Markdown, local links, and documented test commands.
No configuration, entrypoint, or artifact inventory changes are required.

## Open Questions

- The original CSV and row 225 are unavailable so far. Confirmation of that specific
  observation remains separate from the reproduced collapsed-box bug.
