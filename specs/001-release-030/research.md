# Research decisions — 2026-09-19

## Native configuration and execution

Decision: sparse Hydra mappings and ordinary dictionary overlay; default comparison is removed.
Rationale: presence preserves explicit defaults; native parameter validation remains upstream.
Alternative rejected: maintain a second full default schema, which loses provenance and drifts.
Evidence: the pre-0.3.0 configs.py `_overlaid` treated equal values as absent; installed Ultralytics
configuration is authoritative. Keep dataset/table adapters, delegate model runtime settings.

## Tracking

Decision: explicit invocation owner, nested reuse, synchronous required artifacts and manifest.
Rationale: ClearML 2.1.10 `upload_artifact` defaults asynchronous and returns a success boolean;
`flush(wait_for_uploads=True)` alone cannot establish artifact success. Explicit failure handling
is needed because SDK shutdown classifies interrupts as stopped. Native ClearML callbacks must
be disabled in parent and DDP workers without altering user settings.
Alternative rejected: rely on atexit or native callbacks; these hide upload failures and duplicate work.
Installed evidence: clearml/task.py upload_artifact, flush and shutdown handlers;
ultralytics/utils/callbacks/clearml.py and utils/dist.py worker construction.

## Frozen evaluation and reports

Decision: a fixed-threshold adapter around installed digital-metrics scoring, preserving full
metrics/dashboard schema; the same current-test evaluation supplies statistical and workbook data.
Rationale: Evaluation's public calibration API does not accept an arbitrary frozen threshold map;
public match_boxes/slice_by_conf primitives preserve match semantics and empty-image membership.
Missing required thresholds must fail instead of slice_by_conf's zero fallback.
Alternative rejected: fetch historical dashboard workbooks or independently recalibrate test.
Evidence: tasks/metrics.py, comparison/scoring.py, installed digital_metrics evaluation/scoring;
report_generator DevReportBuilder and BusinessReportBuilder consume dashboard readers.

## Compatibility and release evidence

Decision: retain Python/toolchain constraints; remove only dependencies exclusively serving deleted
features. Keep statistical implementations and their regression tests. Verify real CPU/single-GPU
runs in an isolated integration environment and label real multi-GPU unverified.
Alternative rejected: claim mocked tests establish live artifact or GPU behavior.
