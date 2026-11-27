# ADR-0110 · Evaluate identifiable predictions at validation-calibrated thresholds

`cy-predict` produces detections tied to a checkpoint and a set of images. `cy-metrics` consumes saved predictions, fits confidence thresholds on validation images and scores the requested splits. `cy-val` connects both workflows in one experiment. Their shared data contracts let the same detections support both operating-point counts and confidence-ranked precision–recall analysis.

## Prediction from a selected checkpoint

For each requested split, `cy-predict` runs inference on its unique ground truth images. Grouping by split keeps the batch composition for a test image independent of the other splits requested. A local path must identify an existing file. A task ID selects a checkpoint from that task, a `clearml://` selector identifies an Output Model, and a bare YOLO model name can reach the native backend. CY checks supplied hashes and keeps trusted identity from ClearML or a bound local sidecar. A local model with unknown provenance needs a `model_label`. A checkpoint that changes during inference fails the provenance check. [Prediction workflow](../src/clearml_yolo/application/use_cases/predict.py)

CY records the group's input manifest, the scoring size and the requested and effective native settings so a reviewer can trace image membership, batching and native size normalization. YOLO reports aggregate progress in place of per-image console output. The native `conf` cutoff already determines which detections are available for later calibration. Every requested image must return a result, including images with zero detections. The CLI's default output is `predict.csv` in the run directory. The command guide lists FiftyOne errors under exit 1, while the optional publisher catches backend setup and publication failures, logs a warning and continues. [Command guide](../docs/commands/cy-predict.md) · [SIP-346](https://linear.app/sip-ds-team/issue/SIP-346)

<details>
<summary>Sources and verification</summary>

- Predict the selected ground truth images with one checkpoint — [Command output routing](../src/clearml_yolo/entrypoints/hydra/common.py) · [Optional publication handling](../src/clearml_yolo/application/use_cases/publication.py) · [Workflow cases](../tests/test_predict.py) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/prediction-and-validation.md#inputs)
- Resolve prediction weights and identify their source — [Model repository](../src/clearml_yolo/adapters/clearml/models.py) · [Checkpoint identity sidecars](../src/clearml_yolo/adapters/storage/identity.py) · [Selector and identity cases](../tests/test_model_identity_sources.py)
- Capture requested and effective inference settings — [YOLO scoring size and inference settings](../src/clearml_yolo/adapters/yolo/inference.py) · [YOLO prediction settings](../docs/configuration/ultralytics-predict.md) · [Other backend settings](../docs/configuration/model.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/prediction-and-validation.md#native-settings-and-quiet-output)

</details>

## Prediction table and provenance

Each detection supplies an image name, class, confidence and four box corners in original image pixels. Empty output retains the headers. Raw consumers can request `name`, `stem` or `path`. Evaluation joins predictions to ground truth by canonical, unique basenames and rejects unknown image names. Recorded `stem` or `path` mode is ineligible even if its strings happen to look like canonical names. [Prediction format](../docs/formats/predictions.md)

The sibling `.provenance.json` binds the CSV bytes to the naming mode and available checkpoint/model identity. Replacing the CSV invalidates its bound digest. Historical CSVs can lack a sidecar. In that case the evaluator checks canonical ground truth membership and requires another source for model labeling. Model identity travels with the evaluation outputs. [Identity flow cases](../tests/test_identity_flows.py)

<details>
<summary>Sources and verification</summary>

- Represent detections in original pixels with explicit image naming — [Prediction data contract](../src/clearml_yolo/application/contracts.py) · [Prediction assembly](../src/clearml_yolo/application/use_cases/predict.py) · [Identity and membership validation](../src/clearml_yolo/core/evaluation/policy.py) · [Inference cases](../tests/test_inference.py) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/prediction-and-validation.md#prediction-table)
- Bind predictions to their bytes, checkpoint and naming mode — [Sidecar writer and reader](../src/clearml_yolo/adapters/clearml/results.py) · [Evaluation consumer](../src/clearml_yolo/application/use_cases/metrics.py) · [Noncanonical provenance cases](../tests/test_metrics.py) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/prediction-and-validation.md#provenance-sidecar)

</details>

## Checkpoint validation and threshold calibration

`cy-val` resolves ground truth once, predicts the union of `val` and the requested splits into `predictions.csv`, then runs metrics on the requested splits under `metrics/`. Both stages share the experiment task and disable optional FiftyOne publication. An operator who already has predictions can enter the same scoring workflow directly through `cy-metrics`. [Validation orchestration](../src/clearml_yolo/application/use_cases/val.py)

Scoring validates image membership, requires `val` and rejects logical image overlap between validation and test. It matches the validation population, including background images, and selects either a threshold per class or one global threshold repeated across classes. It writes `metrics_best_confidences_val.csv` with 17 significant digits and freezes that mapping for all requested splits. Scoring only the test split still requires ground truth images assigned to `val`. The detector may return zero detections for those images. The comparison workflow can reuse the frozen thresholds on its own split. [Metrics workflow](../src/clearml_yolo/application/use_cases/metrics.py)

<details>
<summary>Sources and verification</summary>

- Validate a checkpoint in one experiment task — [Workflow composition cases](../tests/test_workflow_quality.py) · [Publication behavior](../tests/test_publication_commands.py) · [Validation command](../docs/commands/cy-val.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/prediction-and-validation.md#validation-cy-val)
- Evaluate saved predictions at frozen thresholds — [Split evaluation](../src/clearml_yolo/application/evaluation.py) · [Metrics workflow cases](../tests/test_metrics.py) · [Metrics command](../docs/commands/cy-metrics.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/evaluation-metrics.md#order-of-work)
- Fit confidence thresholds only on validation images — [Split policy](../src/clearml_yolo/core/evaluation/policy.py) · [Threshold optimization](../src/clearml_yolo/adapters/evaluation/scoring.py) · [Evaluation settings](../docs/configuration/evaluation.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/evaluation-metrics.md#thresholds)

</details>

## Matching, operating points and average precision

CY delegates calibration, matching and numerical evaluation to digital-metrics through its evaluation adapters. Fixed-threshold scoring uses prepared predictions, after geometry checks and any configured confidence filtering or NMS. Optional preprocessing can also deduplicate ground truth. The chosen IoU, matching strategy and frozen thresholds determine TP, FP, FN and confusion counts. A prediction-only class can contribute false positives while its recall remains unavailable.

AP and precision–recall curves instead use geometry-valid predictions from before optional prediction preprocessing. CY follows the library's confidence ordering and the chosen AP integration method, then checks reconstructed per-class AP50 against the library result. A mismatch fails evaluation. The adapter copies results into CY records so dashboards and reports can render the same scientific values. [Scoring adapter](../src/clearml_yolo/adapters/evaluation/scoring.py) · [Precision–recall reconstruction](../src/clearml_yolo/adapters/evaluation/pr_curves.py)

<details>
<summary>Sources and verification</summary>

- Score detections at fixed operating thresholds — [Split policy](../src/clearml_yolo/application/use_cases/metrics.py) · [Invalid geometry tests](../tests/test_invalid_prediction_workflows.py) · [Prediction-only classes](../tests/test_metrics.py) · [Matching and preprocessing options](../docs/configuration/evaluation.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/evaluation-metrics.md#two-prediction-populations)
- Compute AP and precision–recall curves over the confidence ranking — [Arithmetic and unavailable-recall cases](../tests/test_pr_curves.py)
- Use digital-metrics behind CY evaluation adapters — [Paired statistics bridge](../src/clearml_yolo/adapters/evaluation/comparison.py) · [Separation and value preservation](../tests/test_evaluation_separation.py) · [Shared comparison cases](../tests/test_shared_comparison.py) · [Evaluation reference](../DOCS.md#evaluation-and-metrics) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/evaluation-metrics.md#shared-library)

</details>

## Audit rows and published results

CY assigns source row and object identifiers before preprocessing and carries them into match relationships. Audit rows distinguish TP, FP, FN, background, filtered, excluded and unevaluated inputs with applicable reasons. Duplicate or unknown source identities fail validation. This preserves an explanation for a row even when it disappears from the scored population. [Row assembly](../src/clearml_yolo/core/evaluation/result_rows.py)

Each concrete split produces full and DTRK dashboards, a confusion matrix, confidence-interval plots, evaluation JSON and a summary workbook. Sibling CSVs preserve thresholds, methodology and row-level evidence beyond Excel's display limits. Available model identity and training-population counts accompany the output. Unavailable metrics remain unavailable. A missing required diagnostic or a computation failure fails standalone metrics. Optional visualization can warn and continue. [Metrics command](../docs/commands/cy-metrics.md)

<details>
<summary>Sources and verification</summary>

- Retain a row-level explanation for each evaluation outcome — [Source-to-prepared evaluation](../src/clearml_yolo/adapters/evaluation/scoring.py) · [Payload and relationship tests](../tests/test_evaluation_payload.py) · [Result format](../docs/formats/workbooks.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/evaluation-metrics.md#result-rows)
- Publish split dashboards, audit tables and diagnostics — [Diagnostics rendering](../src/clearml_yolo/adapters/reporting/evaluation.py) · [Workbook and sibling CSV writer](../src/clearml_yolo/adapters/reporting/evaluation_workbook.py) · [Output and large-table tests](../tests/test_metrics.py) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/evaluation-metrics.md#outputs-per-split)

</details>
