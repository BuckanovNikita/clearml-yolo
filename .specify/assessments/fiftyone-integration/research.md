# Idea Research: FiftyOne Integration

- **Slug**: fiftyone-integration
- **Created**: 2026-09-29
- **Evidence confidence (overall)**: adequate

## Users & Demand

- Pipeline operators need an inspectable record of prediction and fixed-threshold outcomes while retaining the CSV/dashboard artifacts used today. — [source: user requirements and `src/clearml_yolo/tasks/metrics.py`] (confidence: high)

## Prior Art

- `compute_metrics` already separates raw predictions from prepared prediction frames, calibrates on validation, and evaluates every split using frozen thresholds. — [source: `src/clearml_yolo/tasks/metrics.py`] (confidence: high)
- `comparison.scoring` already calls digital-metrics matching and confidence slicing; it exposes evaluated status frames but does not persist a neutral complete payload. — [source: `src/clearml_yolo/comparison/scoring.py`] (confidence: high)
- Pipeline stages currently share a single ClearML task through `init_task`, while standalone prediction and metrics initialize their invocation task. — [source: `src/clearml_yolo/tasks/pipeline.py`, `tasks/predict.py`, `tasks/metrics.py`] (confidence: high)

## Market & Context

- Users otherwise inspect CSVs and dashboard workbooks without sample-level visual context. — [source: user requirements; ASSUMPTION] (confidence: medium)

## Data & Constraints

- Ground truth contains `image_name`, `split`, `image_path`, and labelled-box fields; empty/background rows must remain representable. — [source: repository metrics and prediction code] (confidence: high)
- The installed package declares direct runtime dependencies in `pyproject.toml`; a FiftyOne dependency therefore belongs in the main install if imported. — [source: constitution and `pyproject.toml`] (confidence: high)
- Existing import contracts forbid ClearML outside adapters and enforce package layers. — [source: `.specify/memory/constitution.md`, `pyproject.toml`] (confidence: high)

## Evidence Against the Idea

- An optional visual-review service can introduce persistent-state conflicts, data reuse errors, and a large transitive dependency. Correctness requires identity, lock, retry, and disabled-mode requirements. — [source: user requirements; ASSUMPTION] (confidence: medium)

## Gaps & Open Questions

- External FiftyOne API/version behavior has not been executed in this assessment; validate through the required real smoke test.

## Sources

- Repository source (host: local repository, policy: not fetched)
