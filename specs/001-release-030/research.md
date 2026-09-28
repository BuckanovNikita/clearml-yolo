# Research decisions — 2026-09-19

## Native configuration and execution

Historical decision: sparse Hydra mappings and ordinary dictionary overlay; default comparison
was removed for 0.3.0.
Historical rationale: presence preserved explicit defaults; native parameter validation remained
upstream. The alternative of maintaining a second full default schema was rejected because it
would lose provenance and drift. The pre-0.3.0 `configs.py` `_overlaid` treated equal values as
absent; installed Ultralytics configuration was authoritative.

The [native configuration feature](../003-ultralytics-config-groups/spec.md) superseded this
design with a full shared group sourced from the installed defaults and sparse explicit
prediction overrides. Presence still preserves explicit null/default overrides. Raw/non-null
`cfg` and nested stage-native mappings now fail with migration guidance.

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
