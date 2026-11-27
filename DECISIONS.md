# Architecture decision register

| When you change… | Read the decision | Command entry points |
| --- | --- | --- |
| Training data, detector families, weights, GPU capacity or model export | [Build and deploy a detector](#adr-0200--build-and-deploy-a-detector-from-a-reproducible-training-population) | [`cy-ground-truth`](#ground-truth-and-dataset-preparation), [`cy-download-weights`](#model-assets-and-initialization), [`cy-batch-estimate`](#gpu-capacity-and-training-batch), [`cy-train`](#native-training-and-checkpoint-handoff), [`cy-export`](#faster-r-cnn-export-and-serving) |
| Prediction identity, thresholds, evaluation populations, paired comparisons or reports | [Evaluate and compare models](#adr-0110--evaluate-checkpoints-and-compare-models-on-the-same-data) | [`cy-predict`](#predict-and-calibrate), [`cy-val`](#predict-and-calibrate), [`cy-metrics`](#predict-and-calibrate), [`cy-compare`](#compare-paired-checkpoints), [`cy-report`](#report-eligible-populations-and-preserve-workbook-identity) |
| Command composition, task ownership, publication, runtime or release | [Operate experiments and releases](#adr-0001--own-experiment-execution-publication-and-release) | [`cy`](#configure-and-run-a-pipeline), [`cy-init-config`](#configure-and-run-a-pipeline), [`cy-dedup`](#own-files-workers-and-diagnostics) |

To inspect a contract, expand the evidence for its section. Test links identify the exercised scenario. A claim about a live GPU, upload, Agent or paired checkout needs dated evidence from that environment.

## ADR-0200 · Build and deploy a detector from a reproducible training population

A detector run starts with an identified population, an ordered vocabulary, and a choice of weights and preprocessing. CY carries these inputs into the native trainer and binds them to the selected checkpoint. Export carries that identity into the deployment artifact so its predictions can be checked against the trained model.

### Ground truth and dataset preparation

`cy-ground-truth` converts YOLO annotations to pixel corners and preserves background images as rows with empty class and coordinates. Conversion rejects a declared class named exactly `background`, even when unused, and rejects class names interpreted differently by the supported YAML readers. When test images are absent, a seeded fraction of validation images supplies the test split.

An experiment resolves its local CSV or finalized ClearML Dataset once. Remote datasets must contain root `dataset.csv`. A stage-specific Pandera schema validates without modifying cells and reports original row labels where available. Identifiers retain their lexical spelling. During preparation, duplicate valid annotations and duplicate background rows fail. Each invalid box is dropped and counted, including repeated invalid rows. The image may remain as background.

YOLO uses NDJSON or flat YOLO data. Other families use COCO. A locked prepared copy is keyed by CSV bytes, ordered resolved image references, format and preparation version. Replacing image bytes at an unchanged path can leave a cache hit.

<details>
<summary>Implementation and evidence</summary>

**History**  [SIP-275](https://linear.app/sip-ds-team/issue/SIP-275) · [SIP-218](https://linear.app/sip-ds-team/issue/SIP-218) · [Commit 493f039](https://github.com/BuckanovNikita/clearml-yolo/commit/493f0399fc10c2f99ac072335115f754176baa14) · [SIP-219](https://linear.app/sip-ds-team/issue/SIP-219)

**Implementation**  [Conversion workflow](src/clearml_yolo/application/use_cases/ground_truth.py) · [Ground truth sources](src/clearml_yolo/application/ground_truth.py) · [YOLO reader and split selection](src/clearml_yolo/adapters/yolo/ground_truth.py) · [ClearML dataset adapter](src/clearml_yolo/adapters/clearml/datasets.py) · [Dataframe schemas](src/clearml_yolo/core/validation/schemas.py) · [Detection CSV reader](src/clearml_yolo/adapters/storage/file_io.py) · [Preparation validation](src/clearml_yolo/adapters/storage/dataset_records.py) · [Native format writers](src/clearml_yolo/adapters/storage/dataset_export.py) · [Cache implementation](src/clearml_yolo/adapters/storage/dataset_cache.py)

**Tests**  [Conversion, YAML compatibility and split tests](tests/test_ground_truth.py) · [Source resolution tests](tests/test_ground_truth_sources.py) · [Duplicate-row cases](tests/test_dataset_records.py) · [Validation and non-mutation cases](tests/test_dataframe_validation.py) · [Export contract cases](tests/test_dataset_export.py) · [COCO layout cases](tests/test_coco_dataset.py) · [Reuse and locking tests](tests/test_dataset_cache.py)

</details>

### Model assets and initialization

`cy-download-weights` verifies archive and member sizes and digests against the pinned release. Selected-model resolution respects explicit paths, then uses caches and configured upstream routes. Portable selectors remain in the run configuration. Resolved bytes and source revisions supply provenance. DEIMv2 requires its verified source tree. Large presets can use the original Meta backbone or convert a pinned Hugging Face snapshot. Weight releases carry upstream notices, separate restricted DEIMv2 assets and bind timm-backed assets to their producing version. DINOv3 access and use remain subject to its upstream terms.

<details>
<summary>Implementation and evidence</summary>

**Implementation**  [Execution copy](src/clearml_yolo/adapters/assets/execution.py) · [Asset resolver](src/clearml_yolo/adapters/assets/resolver.py) · [Settings update and verification](src/clearml_yolo/adapters/yolo/assets.py) · [CLI outcome](src/clearml_yolo/entrypoints/download_weights.py) · [Catalogue and receipts](src/clearml_yolo/adapters/assets/preparation.py) · [Bundle restore](src/clearml_yolo/adapters/assets/bundles.py) · [Archive packager](scripts/package_weights.py) · [DINOv3 access handling](src/clearml_yolo/adapters/deim/assets.py) · [Upstream source admission](src/clearml_yolo/adapters/deim/source.py) · [Managed tree resolution](src/clearml_yolo/adapters/assets/sources.py) · [Backbone conversion and validation](src/clearml_yolo/adapters/deim/hf_weights.py)

**Tests**  [Resolution, integrity and recovery cases](tests/test_model_assets.py) · [File loading cases](tests/test_model_assets_loading.py) · [Persistence and failure cases](tests/test_yolo_weights_settings.py) · [Integrity and release-only cases](tests/test_weight_bundles.py) · [Preparation receipt cases](tests/test_weight_preparation.py) · [Unauthorized backbone access cases](tests/test_dinov3_hf_weights.py) · [DEIM asset cases](tests/test_deim_assets.py)

**History**  [Native-cache integration history](https://github.com/BuckanovNikita/clearml-yolo/commit/9266772328422e3f6131144a3b1008327e1d83af) · [Cache directory decision](https://github.com/BuckanovNikita/clearml-yolo/commit/597985fa39476b262bc05daa66ee3fb3e468724a) · [SIP-327](https://linear.app/sip-ds-team/issue/SIP-327) · [Detector integration history](https://github.com/BuckanovNikita/clearml-yolo/commit/43f9e7dc85672bbb25f29e6abcb27344201ac443) · [Official DINOv3 acquisition history](https://github.com/BuckanovNikita/clearml-yolo/commit/c16dbb19d0b59df30c173696406a5f76ec1ac768)

</details>

### GPU capacity and training batch

`cy-batch-estimate` probes a selected CUDA hardware profile with bounded trials and confirms the usable batch. `--force` permits background activity only when no competing compute process is attributable. Missing whole-device telemetry or a known foreign compute PID prevents measurement. The estimator records capacity, ceiling, numerical limit, no capacity or failure. `--list` inspects saved coverage without a GPU.

With `batch=null`, training reads the editable batch table. It uses an exact match or the largest eligible lower-or-equal memory capacity, respecting confirmed no-capacity results. The smallest selected per-device value times GPU count gives the global batch. CPU, MPS, custom YOLO and non-square inputs need an explicit batch.

<details>
<summary>Implementation and evidence</summary>

**Implementation**  [Command and scheduling](src/clearml_yolo/entrypoints/batch_estimate.py) · [Measurement workflow](src/clearml_yolo/application/use_cases/batch_estimate.py) · [Trial search](src/clearml_yolo/core/batch_estimation.py) · [GPU telemetry and admission](src/clearml_yolo/adapters/runtime/gpu_inventory.py) · [Evidence store](src/clearml_yolo/adapters/storage/batch_estimates.py) · [Table storage](src/clearml_yolo/adapters/storage/batch_sizes.py) · [Entry and selection contracts](src/clearml_yolo/core/batch_sizes.py) · [Opt-in lookup and provenance](src/clearml_yolo/adapters/integrations/batch_resolution.py)

**Tests**  [Search bounds](tests/test_batch_search_strategy.py) · [Workflow and failure cases](tests/test_batch_estimate_workflow.py) · [Telemetry and process cases](tests/test_gpu_inventory.py) · [Admission and forced reporting](tests/test_batch_estimate_cli.py) · [Legacy and corrupt store cases](tests/test_batch_estimate_store.py) · [GPU-free listing cases](tests/test_batch_estimate_list.py) · [Batch table editing and metadata cases](tests/test_batch_sizes.py) · [Lookup cases](tests/test_batch_lookup.py) · [Training integration cases](tests/test_batch_resolution.py)

**History**  [Small-batch search and table history](https://github.com/BuckanovNikita/clearml-yolo/commit/0d1889dd1c9198a8827b90754c7eae0b2b9925fe) · [Forced-measurement decision](https://github.com/BuckanovNikita/clearml-yolo/commit/c16dbb19d0b59df30c173696406a5f76ec1ac768) · [Missing-model listing history](https://github.com/BuckanovNikita/clearml-yolo/commit/a89e4869b0ee801c28ac31f9d99573d9485ac4e3)

</details>

### Native training and checkpoint handoff

`cy-train` requires populated training and validation splits and starts fresh optimizer and scheduler state. Explicit non-YOLO detector weights initialize the run. With no full checkpoint, supported families load explicitly supplied backbone weights even with `pretrained=false`. The model guide describes that case as training from scratch. [SIP-344](https://linear.app/sip-ds-team/issue/SIP-344)

| Family | Native execution and best checkpoint |
| --- | --- |
| Ultralytics YOLO | Stage-specific native settings and detector outputs in original coordinates. Training selects `weights/best.pt`. |
| DEIMv2 | Square training sizes divisible by 32, supervised NCCL for distributed runs. Prefer `best_stg2.pth`, then `best_stg1.pth`. |
| RF-DETR | Square sizes divisible by 32, full-detector initialization, Lightning DDP and `checkpoint_best_total.pth`. |
| Faster R-CNN | Padded aspect-preserving canvas and an internal background class. Select `best.pth` by validation mAP50–95. |
| FCOS | Shared Torchvision training recipe and canvas, zero-based foreground labels and a P3–P7 head. Select `best.pth` by validation mAP50–95. |

Custom training augmentation freezes an Albumentations snapshot and digest for workers and replay. Mosaic donors come from the training population. The owner publishes rank results. A rank failure terminates its peers. Training propagates numerical and resource failures without changing the requested settings.

Non-YOLO checkpoints embed the detector descriptor. The reference directs users to keep both sidecars with the checkpoint. The reader can recover an embedded descriptor without its companion, checks a supplied companion against the bytes, and may require an explicit label when identity is missing. [SIP-345](https://linear.app/sip-ds-team/issue/SIP-345)

<details>
<summary>Implementation and evidence</summary>

**Implementation**  [Training workflow](src/clearml_yolo/application/use_cases/train.py) · [Selected initialization inputs](src/clearml_yolo/adapters/assets/execution.py) · [Backbone load](src/clearml_yolo/adapters/torchvision/backbone.py) · [Full checkpoint load](src/clearml_yolo/adapters/torchvision/training.py) · [Ultralytics recovery policy](src/clearml_yolo/adapters/integrations/native_trainer.py) · [Native training](src/clearml_yolo/adapters/integrations/training.py) · [Prediction conversion](src/clearml_yolo/adapters/yolo/inference.py) · [Native solver and prediction](src/clearml_yolo/adapters/deim/backend.py) · [Source validation](src/clearml_yolo/adapters/deim/source.py) · [RF-DETR training and prediction](src/clearml_yolo/adapters/rfdetr/backend.py) · [Registry asset mapping](src/clearml_yolo/adapters/rfdetr/assets.py) · [Faster R-CNN model](src/clearml_yolo/adapters/fasterrcnn/model.py) · [Canvas transform](src/clearml_yolo/adapters/torchvision/transform.py) · [FCOS model](src/clearml_yolo/adapters/fcos/model.py) · [FCOS integration](src/clearml_yolo/adapters/fcos/backend.py) · [Classification and projections](src/clearml_yolo/adapters/yolo/config.py) · [Evaluation](src/clearml_yolo/adapters/torchvision/evaluation.py) · [Albumentations pipeline](src/clearml_yolo/adapters/augmentation/pipeline.py) · [Detector bridges](src/clearml_yolo/adapters/augmentation/torch_data.py) · [Snapshot resolution](src/clearml_yolo/adapters/augmentation/configuration.py) · [Canonical digest and validation](src/clearml_yolo/core/transforms.py) · [Supervised rank group](src/clearml_yolo/adapters/integrations/distributed_training.py) · [Native callback relay](src/clearml_yolo/adapters/integrations/native_ddp.py) · [Descriptor writer and reader](src/clearml_yolo/adapters/storage/checkpoint.py) · [Identity companion](src/clearml_yolo/adapters/storage/identity.py)

**Tests**  [CSV training boundary](tests/test_train.py) · [Training finalization cases](tests/test_training_success_finalization.py) · [Local weights and registry cases](tests/test_model_assets_loading.py) · [OOM and configured batch cases](tests/test_yolo_oom.py) · [Native training outcomes](tests/test_native_training_outcomes.py) · [DEIMv2 contract cases](tests/test_deim_backend.py) · [RF-DETR contract cases](tests/test_rfdetr_backend.py) · [Faster R-CNN contract cases](tests/test_fasterrcnn_backend.py) · [FCOS head and label cases](tests/test_fcos_backend.py) · [Installed template and changed-default cases](tests/test_native_config.py) · [Detector augmentation cases](tests/test_detector_augmentation.py) · [YOLO augmentation cases](tests/test_yolo_augmentation.py) · [Snapshot and serialization cases](tests/test_augmentation.py) · [Distributed configuration](tests/test_distributed_configuration.py) · [CPU callback relay cases](tests/test_native_ddp_cpu.py) · [Native relay cases](tests/test_native_ddp.py) · [Copy, tampering and compatibility cases](tests/test_checkpoint_descriptor.py)

**History**  [Detector integration history](https://github.com/BuckanovNikita/clearml-yolo/commit/43f9e7dc85672bbb25f29e6abcb27344201ac443) · [SIP-325](https://linear.app/sip-ds-team/issue/SIP-325) · [Custom augmentation history](https://github.com/BuckanovNikita/clearml-yolo/commit/3b95fbaae4bc2440e239e7b01a3c47755475ac8f)

</details>

### Faster R-CNN export and serving

Each `cy-export` invocation exports ONNX, builds a TensorRT engine, or verifies it. The CPU FP32 opset-17 graph fixes confidence, NMS IoU and detection limits. Build binds engine precision, supported shapes and plugin requirements to the artifact. The reference calls the sidecars immutable. A successful repeated export or build can replace the output sidecar at the same path. Consumers validate input metadata. [SIP-353](https://linear.app/sip-ds-team/issue/SIP-353)

Verification compares native and engine predictions on the same labeled corpus. It needs native detections and positive reference mAP. Maximum mAP50–95 loss is 0.001 for FP32 and 0.005 for FP16. All-zero exported mAP, AP50, recall and per-class recall fail regardless of tolerance.

`TensorRTRunner(engine_path, metadata, *, device=0)` accepts a serialized engine path and matching `ExportMetadata`. It checks the digest, runtime, plugin, tensor signatures and profiles. The caller serializes inference calls. Each call owns its allocations and CUDA stream.

<details>
<summary>Implementation and evidence</summary>

**Implementation**  [Export workflow](src/clearml_yolo/application/use_cases/export.py) · [Operation admission](src/clearml_yolo/core/export_requests.py) · [ONNX graph export](src/clearml_yolo/adapters/export/onnx.py) · [Graph and metadata assembly](src/clearml_yolo/adapters/integrations/export_operations.py) · [Metadata schema](src/clearml_yolo/core/export.py) · [Sidecar writer](src/clearml_yolo/adapters/export/metadata.py) · [Engine builder and plugin lowering](src/clearml_yolo/adapters/export/build.py) · [FP16 graph policy](src/clearml_yolo/adapters/export/precision.py) · [Runner checks](src/clearml_yolo/adapters/export/runtime.py) · [Verification cases](src/clearml_yolo/adapters/export/verification.py) · [Quality gate](src/clearml_yolo/core/export_quality.py) · [Evaluator](src/clearml_yolo/adapters/export/quality.py) · [NumPy preprocessing](src/clearml_yolo/adapters/export/preprocessing.py)

**Tests**  [Inputs and publication ordering](tests/test_export_workflow.py) · [Early artifact publication](tests/test_early_export_publication.py) · [Graph output and shape contracts](tests/test_detector_export.py) · [CPU export admission](tests/test_export.py) · [Explicit precision cases](tests/test_export_precision.py) · [Quality boundary cases](tests/test_export_quality.py)

</details>

## ADR-0110 · Evaluate checkpoints and compare models on the same data

CY binds detections to a checkpoint and an image population, fits operating thresholds on validation data and records which objects contributed to each result. A comparison can then pair two checkpoints on the same split. Reports and FiftyOne reuse that evidence so a reader can follow a difference in a workbook back to the models, images and labels that produced it.

### Predict and calibrate

`cy-predict` resolves local weights, a ClearML task or an Output Model and infers each split separately. A local checkpoint with unknown provenance needs a `model_label`. Each requested image must yield a result, including images with zero detections. The CSV records original-pixel boxes. Its sidecar binds the file digest, naming mode and available model identity. Evaluation joins on unique canonical basenames and rejects recorded `stem` or `path` modes. Historical CSVs without a sidecar require canonical image membership and another source for the model label.

`cy-val` predicts validation and requested images and runs metrics in one task. `cy-metrics` starts from saved predictions. Both fit per-class or global confidence thresholds using `val`, including background images, and freeze them for scoring. Test-only scoring still requires validation ground truth. Validation detections may be empty. Overlap between validation and test images fails. The native inference cutoff limits which detections remain available for calibration.

Fixed-threshold counts use prepared predictions after optional filtering and NMS. AP and precision–recall use confidence-ranked, geometry-valid predictions before optional preprocessing. CY uses digital-metrics and checks reconstructed per-class AP50 against its result. Row identities survive preprocessing so the audit can explain matches, exclusions and false positives from prediction-only classes. Split dashboards, confusion matrices, plots, workbook and CSV diagnostics preserve unavailable values as NA.

<details>
<summary>Implementation and evidence</summary>

**Implementation**  [Prediction workflow](src/clearml_yolo/application/use_cases/predict.py) · [Command output routing](src/clearml_yolo/entrypoints/hydra/common.py) · [Optional publication handling](src/clearml_yolo/application/use_cases/publication.py) · [Model repository](src/clearml_yolo/adapters/clearml/models.py) · [Checkpoint identity sidecars](src/clearml_yolo/adapters/storage/identity.py) · [YOLO scoring size and inference settings](src/clearml_yolo/adapters/yolo/inference.py) · [Prediction data contract](src/clearml_yolo/application/contracts.py) · [Identity and membership validation](src/clearml_yolo/core/evaluation/policy.py) · [Sidecar writer and reader](src/clearml_yolo/adapters/clearml/results.py) · [Evaluation consumer](src/clearml_yolo/application/use_cases/metrics.py) · [Validation orchestration](src/clearml_yolo/application/use_cases/val.py) · [Split evaluation](src/clearml_yolo/application/evaluation.py) · [Threshold optimization](src/clearml_yolo/adapters/evaluation/scoring.py) · [Precision–recall reconstruction](src/clearml_yolo/adapters/evaluation/pr_curves.py) · [Paired statistics bridge](src/clearml_yolo/adapters/evaluation/comparison.py) · [Row assembly](src/clearml_yolo/core/evaluation/result_rows.py) · [Diagnostics rendering](src/clearml_yolo/adapters/reporting/evaluation.py) · [Workbook and sibling CSV writer](src/clearml_yolo/adapters/reporting/evaluation_workbook.py)

**History**  [SIP-346](https://linear.app/sip-ds-team/issue/SIP-346)

**Tests**  [Workflow cases](tests/test_predict.py) · [Selector and identity cases](tests/test_model_identity_sources.py) · [Identity flow cases](tests/test_identity_flows.py) · [Inference cases](tests/test_inference.py) · [Noncanonical provenance cases](tests/test_metrics.py) · [Workflow composition cases](tests/test_workflow_quality.py) · [Publication behavior](tests/test_publication_commands.py) · [Invalid geometry tests](tests/test_invalid_prediction_workflows.py) · [Arithmetic and unavailable-recall cases](tests/test_pr_curves.py) · [Separation and value preservation](tests/test_evaluation_separation.py) · [Shared comparison cases](tests/test_shared_comparison.py) · [Payload and relationship tests](tests/test_evaluation_payload.py)

</details>

### Compare paired checkpoints

`cy-compare` resolves each model and frozen threshold map. An absent automatic baseline permits candidate-only diagnostics and skips the paired report. A missing explicit baseline fails. The evaluation guide says comparison ignores `evaluation.backend`, while preflight rejects every non-null value. The technical reference describes a `best` tag for model recovery. CY first checks `clearml_yolo_checkpoint_role=best` metadata, then best-checkpoint filenames, and finally registration order with a warning. [Backend discrepancy](https://linear.app/sip-ds-team/issue/SIP-347) · [Model recovery discrepancy](https://linear.app/sip-ds-team/issue/SIP-352)

Both models infer the same split with shared requested settings. Cached predictions require compatible checkpoint, inference settings, image membership and available provenance. The split fingerprint assumes media at each path is immutable. For shared eligible classes, CY reports candidate-minus-baseline differences. An image-level paired bootstrap supplies the precision test and recall interval. Exact paired McNemar supplies the recall p-value. Benjamini–Hochberg correction covers class-level precision and recall hypotheses together within each split. The pooled result sits outside that correction family.

<details>
<summary>Implementation and evidence</summary>

**Implementation**  [Model recovery](src/clearml_yolo/adapters/clearml/models.py) · [Comparison workflow](src/clearml_yolo/application/use_cases/compare.py) · [Command preflight](src/clearml_yolo/entrypoints/hydra/validation.py) · [Candidate workbook writer](src/clearml_yolo/adapters/reporting/evaluation_workbook.py) · [Archive writer](src/clearml_yolo/adapters/storage/native_archive.py) · [Native inference reuse](src/clearml_yolo/adapters/yolo/reinfer.py) · [Statistical assembly](src/clearml_yolo/core/comparison/assemble.py) · [Numerical tests](src/clearml_yolo/adapters/evaluation/comparison.py) · [Workbook format](src/clearml_yolo/adapters/reporting/comparison_workbook.py) · [Manifest consumer](src/clearml_yolo/application/use_cases/report.py)

**Tests**  [Comparison workflow cases](tests/test_comparison_reinfer.py) · [Recovery cases](tests/test_comparison_recovery.py) · [Explicit and automatic absence cases](tests/test_comparison_assemble.py) · [Cache identity cases](tests/test_comparison_identity_cache.py) · [Containment cases](tests/test_project_output_containment.py) · [Statistical cases](tests/test_comparison_significance.py) · [Pooled and per-class display](tests/test_comparison_workbook.py) · [Manifest and missing-path cases](tests/test_report.py)

**History**  [SIP-211](https://linear.app/sip-ds-team/issue/SIP-211)

</details>

### Report eligible populations and preserve workbook identity

`cy-report` uses the comparison manifest to find both models' dashboards. Eligibility uses each checkpoint's own training population. Counts below the configured minimum exclude a class. Unknown counts stay unavailable, produce warnings and remain outside aggregates. Each model aggregate uses its own eligible classes. Paired differences require shared classes and available operands.

The developer workbook shows metric availability. The business workbook uses fixed columns, computed values and summed example counts. Both show readable identities. Hidden metadata preserves the original workbook and a fingerprint for detecting later edits. Reversible display aliases leave scientific class keys intact.

<details>
<summary>Implementation and evidence</summary>

**Implementation**  [Report workflow](src/clearml_yolo/application/use_cases/report.py) · [Training-count recovery](src/clearml_yolo/adapters/clearml/population.py) · [Paired rendering](src/clearml_yolo/adapters/reporting/reports.py) · [Original annotation counting](src/clearml_yolo/adapters/storage/population.py) · [Training count contract](src/clearml_yolo/core/report_counts.py) · [Partition and issue annotations](src/clearml_yolo/adapters/reporting/count_issues.py) · [OOXML integration](src/clearml_yolo/adapters/reporting/workbook_identity.py) · [Readable label allocation](src/clearml_yolo/core/presentation.py) · [Dashboard and plot display](src/clearml_yolo/adapters/reporting/evaluation.py)

**Tests**  [Input and output cases](tests/test_report.py) · [Count provenance tests](tests/test_training_count_provenance.py) · [Dataset counts workbook cases](tests/test_population_count_workbooks.py) · [Count issue cases](tests/test_report_count_issues.py) · [One-sided availability cases](tests/test_report_class_availability.py) · [Real business workbook cases](tests/test_report_business_layout.py) · [Identity round-trip cases](tests/test_workbook_identity.py) · [Class label round-trip cases](tests/test_comparison_workbook.py)

**History**  [SIP-242](https://linear.app/sip-ds-team/issue/SIP-242)

</details>

### Inspect matches in FiftyOne

Optional publication adds run-specific overlays to a dataset keyed by ground truth, using a bounded worker and a dataset lock. A local receipt identifies the dataset and fields. The prediction guide lists FiftyOne errors under exit 1. CY warns and continues on ordinary backend or publication failures. Cancellation propagates. [Exit-status discrepancy](https://linear.app/sip-ds-team/issue/SIP-346)

A native FiftyOne evaluation links stored labels to the object pairs CY scored for each split. The explicitly installed App extension can select those samples and labels from a result. Filtered views can show subset operating-point evidence. AP and precision–recall curves belong to the full split on which they were calculated.

<details>
<summary>Implementation and evidence</summary>

**Implementation**  [Workflow policy](src/clearml_yolo/application/use_cases/publication.py) · [Worker supervision](src/clearml_yolo/adapters/fiftyone/bounded.py) · [Dataset publication](src/clearml_yolo/adapters/fiftyone/publisher.py) · [Native evaluation mapping](src/clearml_yolo/adapters/fiftyone/evaluation.py) · [Installer and panel](src/clearml_yolo/adapters/fiftyone/panel.py) · [Extension manifest](src/clearml_yolo/adapters/fiftyone/plugin/fiftyone.yml)

**Tests**  [Database integration scenarios](tests/integration/fiftyone/test_fiftyone_publisher.py) · [Result tests](tests/test_fiftyone_evaluation_results.py) · [Native database scenarios](tests/integration/fiftyone/test_fiftyone_native_evaluations.py) · [Panel behavior](tests/test_fiftyone_panel.py) · [Live view scenarios](tests/integration/fiftyone/test_fiftyone_panel_views.py)

**History**  [Commit 63fd899](https://github.com/BuckanovNikita/clearml-yolo/commit/63fd89940303402af3fcd957dcd3cfabb5eea795) · [Commit 60ab70b](https://github.com/BuckanovNikita/clearml-yolo/commit/60ab70bf90fffab7747f0f53ab2e0e67ac08b764)

</details>

## ADR-0001 · Own experiment execution, publication and release

An experiment has one owner from configuration through process cleanup and ClearML finalization. Stages contribute results to that owner. Operators can trace a failure to a stage, a local diagnostic or a delivery acknowledgement. Maintainers verify and release the code through a separate lifecycle tied to its source revision.

### Configure and run a pipeline

`cy` runs training, prediction, metrics, comparison and reporting within one task. Standalone experiment commands use the same stage implementations and own their own tasks. The entrypoint injects storage, tracking and runtime adapters through typed application ports. Core computes scientific results without I/O. Importing a package leaves SDK initialization to the invocation.

Hydra composes packaged defaults, user YAML and command-line overrides. Use `--help` to see selectable groups and `--cfg job` to inspect effective settings. `cy-init-config` and `dump_config_tree` export editable defaults for a command and model. Export checks all destinations before writing. The command preflight checks composed values and write routes before task creation and rechecks restored Agent settings. File contents and certain use-case settings are checked later. A direct sweep validates every member's destinations first, then runs members sequentially under a shared launch tag. [Remaining preflight checks](https://linear.app/sip-ds-team/issue/SIP-276)

A successful training stage must produce a nonempty checkpoint. If a downstream stage fails, the pipeline can retain that checkpoint, skip dependent stages and finish with warnings. Interrupted runs, runs that skipped training, and standalone commands retain their failure status. With training and comparison skipped, reporting can reuse an existing comparison manifest. If it is absent, the outcome records a skipped report. [Pipeline outcome cases](tests/test_pipeline_outcomes.py)

<details>
<summary>Implementation and evidence</summary>

**Implementation**  [Pipeline use case](src/clearml_yolo/application/use_cases/pipeline.py) · [Outcome record](src/clearml_yolo/core/pipeline_outcome.py) · [Schema and defaults registration](src/clearml_yolo/entrypoints/hydra/configs.py) · [Exporter](src/clearml_yolo/entrypoints/hydra/config_tree.py) · [Validators](src/clearml_yolo/entrypoints/hydra/validation.py) · [Sweep expansion](src/clearml_yolo/entrypoints/hydra/sweeps.py) · [Resolver](src/clearml_yolo/entrypoints/hydra/config_resolution.py) · [Publication call site](src/clearml_yolo/adapters/clearml/session.py) · [Composition root](src/clearml_yolo/entrypoints/composition.py) · [Import rules](.importlinter) · [Application ports](src/clearml_yolo/application/ports.py) · [Package root](src/clearml_yolo/__init__.py)

**History**  [SIP-212](https://linear.app/sip-ds-team/issue/SIP-212) · [SIP-208](https://linear.app/sip-ds-team/issue/SIP-208) · [SIP-205](https://linear.app/sip-ds-team/issue/SIP-205)

**Tests**  [Composition and precedence tests](tests/test_release_config.py) · [Dependency injection tests](tests/test_entrypoint_composition.py) · [Help composition cases](tests/test_hydra_help_composition.py) · [Export and fresh-process tests](tests/test_config_tree.py) · [Preflight tests](tests/test_command_preflight.py) · [Launch cases](tests/test_hydra_sweep_configuration.py) · [Grouping tests](tests/test_multirun_tags.py) · [Resolution cases](tests/test_config_resolution.py) · [Configuration publication tests](tests/test_configuration_publication.py) · [Import behavior tests](tests/test_architecture.py) · [Console import tests](tests/test_runtime_entrypoints.py)

</details>

### Own files, workers and diagnostics

Project writes resolve under the frozen `CY_HOME`. A task identity determines the default run directory. An explicit `run_dir` wins over `run_id`. Reusing the directory preserves existing results. Invocation scratch survives success, failure and cancellation for diagnosis. `cy-dedup` verifies matching image names, sizes, digests and bytes before replacing a duplicate with a same-filesystem reflink. A dry run can inspect an external directory.

The Linux supervisor identifies each descendant by PID and start time before signalling it. Cancellation escalates within a deadline and checks for quiescence. cy-queue owns concurrent admission and device reservation. Direct commands reject queue controls. Workers and ranks leave task creation and uploads to the invocation owner. The local console journal retains native output, a separate publisher forwards console and scalar records, and the progress file exposes complete snapshots to observers. Trace mode adds watchdog diagnostics. Structured redaction protects published settings and remote failure status. A native process controls what it prints to the raw journal.

<details>
<summary>Implementation and evidence</summary>

**Implementation**  [Workspace bootstrap](src/clearml_yolo/adapters/runtime/bootstrap.py) · [Composed destination validation](src/clearml_yolo/entrypoints/hydra/validation.py) · [Run identities and latest link](src/clearml_yolo/adapters/storage/run_identity.py) · [Launch check](src/clearml_yolo/adapters/runtime/git_workspace.py) · [Command integration](src/clearml_yolo/entrypoints/hydra/common.py) · [Command entry](src/clearml_yolo/entrypoints/dedup.py) · [Comparison and replacement](src/clearml_yolo/adapters/storage/dedup.py) · [Ownership and signal rules](src/clearml_yolo/adapters/runtime/process_tree.py) · [Execution boundary](src/clearml_yolo/adapters/runtime/execution_lifecycle.py) · [Capture and scalar journal](src/clearml_yolo/adapters/observability/capture.py) · [Publication barrier](src/clearml_yolo/adapters/clearml/console.py) · [Publisher protocol](src/clearml_yolo/adapters/clearml/console_worker.py) · [Presentation rules](src/clearml_yolo/core/presentation.py) · [ClearML adapters](src/clearml_yolo/adapters/clearml/report.py) · [Operation and watchdog rules](src/clearml_yolo/adapters/observability/tracing.py) · [Progress reporting](src/clearml_yolo/adapters/observability/progress.py)

**Tests**  [Native route containment](tests/test_native_output_containment.py) · [Routing and displacement cases](tests/test_run_identity.py) · [Retention and subprocess scenarios](tests/test_runtime_bootstrap.py) · [Probe and warning cases](tests/test_git_workspace.py) · [Filesystem scenarios](tests/test_dedup.py) · [Orphan and replacement scenarios](tests/test_subreaper_process_tree.py) · [Host capabilities](tests/test_process_capabilities.py) · [Legacy control cases](tests/test_execution_controls.py) · [Direct execution scenarios](tests/test_direct_execution.py) · [Capture and stalled publisher cases](tests/test_console_capture.py) · [Readable output cases](tests/test_readable_output.py) · [Table alias cases](tests/test_clearml_report.py) · [Lifecycle and watchdog tests](tests/test_tracing.py)

**History**  [Commit 28b74f7](https://github.com/BuckanovNikita/clearml-yolo/commit/28b74f72054889c4b0706fecb8983c0ed6196235) · [Commit 7ef1c10](https://github.com/BuckanovNikita/clearml-yolo/commit/7ef1c10ab4d633d4b9535aef24167bdb5c5247da) · [Commit d9d6fcd](https://github.com/BuckanovNikita/clearml-yolo/commit/d9d6fcdf2d1f2a8ea986cf72e6dc2aa70d483497) · [Commit e1fe64e](https://github.com/BuckanovNikita/clearml-yolo/commit/e1fe64ea7a053bb39daf4d8f477f63e4a6a8a236) · [Commit ad6a8ec](https://github.com/BuckanovNikita/clearml-yolo/commit/ad6a8ec81901801c7bb434beed67405da81551ab) · [Commit 063b670](https://github.com/BuckanovNikita/clearml-yolo/commit/063b670e3ecb0ee9dca9acaffa83244f40eb76e2) · [Commit 8ca7d6b](https://github.com/BuckanovNikita/clearml-yolo/commit/8ca7d6bc37a0a28ba2c53eeb73c0b9d51ab58a99) · [Commit d96263c](https://github.com/BuckanovNikita/clearml-yolo/commit/d96263c2444f6d69bd5e862a7acd1c0f01f6061f)

</details>

### Replay inputs and confirm results in ClearML

Each experiment creates a fresh task and records its effective configuration, readable names and available source checkout identity. The owner aggregates row-level results from the declared stages and publishes tables, plots and scalars with model identity. It also binds validation-calibrated thresholds to its own verified Output Model by checkpoint digest and reads the metadata back.

The technical contract identifies `run` as the only replay and cache input. Agent replay reads one snapshot, revalidates it and can apply eligible native YOLO `General` parameters. Ground truth conversion and reporting can also consume Agent-supplied configuration attachments. Training disables remote replacement of its prepared dataset file. The controller's cache callback strips routing differences and retains other hash material, including asset provenance when present. [Replay discrepancy](https://linear.app/sip-ds-team/issue/SIP-354) · [Cache discrepancy](https://linear.app/sip-ds-team/issue/SIP-350)

The delivery contract requires remote readback for every upload. For ordinary artifacts the implementation checks SDK acknowledgement, the artifact manifest and the final flush. For Output Models it downloads the checkpoint and verifies its SHA-256. An uncertain delivery is never retried automatically. The reference gives each finalization step a separate timeout. The successful finalization path shares one alarm across steps, with separate recovery deadlines. Unconfirmed closure prevents another owner in the same process. [Artifact discrepancy](https://linear.app/sip-ds-team/issue/SIP-348) · [Finalization discrepancy](https://linear.app/sip-ds-team/issue/SIP-349)

<details>
<summary>Implementation and evidence</summary>

**Implementation**  [Owner and worker guard](src/clearml_yolo/adapters/clearml/session.py) · [Collision queries and recheck](src/clearml_yolo/adapters/clearml/naming.py) · [Source lookup and readback](src/clearml_yolo/adapters/clearml/script.py) · [Structured redaction](src/clearml_yolo/core/redaction.py) · [Direct command integration](src/clearml_yolo/entrypoints/hydra/common.py) · [Ground-truth consumer](src/clearml_yolo/application/use_cases/ground_truth.py) · [Report consumer](src/clearml_yolo/application/use_cases/report.py) · [Training policy](src/clearml_yolo/application/use_cases/train.py) · [Controller projection and invariants](src/clearml_yolo/adapters/clearml/cache.py) · [Result assembly](src/clearml_yolo/adapters/clearml/results.py) · [ClearML reporting adapter](src/clearml_yolo/adapters/clearml/report.py) · [YOLO verification](src/clearml_yolo/adapters/clearml/native.py) · [Detector publication](src/clearml_yolo/adapters/clearml/detectors.py) · [Pipeline calibration call](src/clearml_yolo/application/use_cases/pipeline.py) · [Deadline mechanism](src/clearml_yolo/adapters/clearml/deadline.py)

**Tests**  [Ownership and failure cases](tests/test_clearml_session.py) · [Collision and retry cases](tests/test_clearml_naming.py) · [Checkout metadata cases](tests/test_clearml_script.py) · [Configuration publication cases](tests/test_configuration_publication.py) · [Agent scenarios](tests/test_agent_replay.py) · [Attachment replay scenarios](tests/test_config_upload_commands.py) · [Cache identity tests](tests/test_clearml_cache.py) · [Multi-producer and identity cases](tests/test_clearml_results.py) · [Table and headline cases](tests/test_clearml_report.py) · [YOLO boundary tests](tests/test_clearml_native.py) · [Detector boundary tests](tests/test_detector_publication.py) · [Trained pipeline failure cases](tests/test_training_success_finalization.py)

**History**  [Commit 589dc4a](https://github.com/BuckanovNikita/clearml-yolo/commit/589dc4a563e8a767a3cf9b675df66820b0a3c83b) · [Commit 5d89443](https://github.com/BuckanovNikita/clearml-yolo/commit/5d89443b8e1a8e63d21b3c318b2cab0242c4e418) · [Commit fd395d3](https://github.com/BuckanovNikita/clearml-yolo/commit/fd395d34bff7f3128047e5d0c302f2c3f0720b78) · [Commit 2e4b5f2](https://github.com/BuckanovNikita/clearml-yolo/commit/2e4b5f2fa3c3e9dc90920af75fe3edb8e346bcd0) · [Configuration source decision](https://github.com/BuckanovNikita/clearml-yolo/commit/6aefaa354e2f20ef05e3d62b7901399548045133) · [Commit a6a78e8](https://github.com/BuckanovNikita/clearml-yolo/commit/a6a78e895cb84a2fc960d4b3f91e8327f2ea3e89) · [Commit d247a2e](https://github.com/BuckanovNikita/clearml-yolo/commit/d247a2e6f6d179a255ea6caaa5017ac477be8f4c)

</details>

### Verify the environment and accept a change

Select checks against the branch's merge-base diff. Whole-tree checks cover hygiene, locks, formatting, imports, typing and dependencies. Routed verification uses staged, working or committed inputs. Prose takes the static route. Product changes select affected unit tests. Coverage requires the full branch-coverage run. Mutation results identify survivors and unreached functions for disposition.

Change acceptance checks a clean committed tip, runs coverage and live integration, and confirms the source stayed unchanged. Integration creates an owned ClearML/FiftyOne environment with session credentials and tagged resources. Unavailable required infrastructure defers acceptance. The Severstal scenario derives boxes from local masks, verifies fixture identities and exercises training, checkpoint reload, inference and publication on the selected GPU. Release acceptance adds native scenarios, FiftyOne and the CY/cy-queue pairing check. Results apply to the versions, devices and services actually exercised.

<details>
<summary>Implementation and evidence</summary>

**Implementation**  [Verification tasks](Taskfile.yml) · [Change selector](scripts/verification.py) · [Hygiene implementation](scripts/hygiene.py) · [Bounded collection](scripts/verification_collection.py) · [Environment fingerprint](scripts/testmon_environment.py) · [Pytest configuration](pyproject.toml) · [Selector and report](scripts/mutation.py) · [Task entry points](Taskfile.ops.yml) · [Corpus builder](scripts/severstal.py) · [Metadata checks](scripts/paired_metadata.py)

**Tests**  [Lifecycle and operating guide](tests/integration/lifecycle.py) · [Live fixtures](tests/integration/conftest.py) · [CPU ClearML scenario](tests/integration/test_cpu_stand_smoke.py) · [FiftyOne service scenarios](tests/integration/fiftyone) · [Native scenario](tests/integration/test_severstal_gpu.py) · [Scenario harness](tests/severstal_harness.py)

</details>

### Install and release reviewed source

Prepare the approved digital-metrics and report-generator revisions before building the worktree's local wheelhouse. The lock identifies package distributions. Verify the source revisions separately. Git installations resolve declared ranges, so test a changed dependency minimum on each supported Python minor as well as in the locked environment. CY needs the digital-metrics evaluation APIs and a requests version that scopes netrc credentials to the host. [Dependency declarations](pyproject.toml) · [Evaluation dependency](https://linear.app/sip-ds-team/issue/SIP-337) · [HTTP dependency](https://linear.app/sip-ds-team/issue/SIP-338)

The Linear issue identifies the change. Its PR records verification and review before human merge. The operating instructions say no CI check runs on PRs. The repository declares an automatic PR review job and a separate mention-triggered assistant workflow. Product verification runs separately. After a merge to master, semantic-release decides whether a new version is due. For a version change, the runner validates the release metadata and annotated tag and pushes both atomically. Model weight archives have their own release. [PR automation discrepancy](https://linear.app/sip-ds-team/issue/SIP-351)

<details>
<summary>Implementation and evidence</summary>

**History**  [SIP-335](https://linear.app/sip-ds-team/issue/SIP-335) · [SIP-234](https://linear.app/sip-ds-team/issue/SIP-234)

**Tests**  [Process capability tests](tests/test_process_capabilities.py)

**Implementation**  [Bootstrap](Taskfile.ops.yml) · [Local configuration validation](scripts/check_local_uv.py) · [Lock](uv.lock) · [Consumer](src/clearml_yolo/entrypoints/hydra/validation.py) · [Review workflow](.github/workflows/claude-code-review.yml) · [Release trigger](.github/workflows/release.yml) · [Event and permission declarations](.github/workflows/claude.yml) · [Release runner](scripts/release.py) · [Lock guard](scripts/release_lock_guard.py)

</details>

## Maintaining the register

Update the affected decision in the PR that changes its behavior. Trace a command to its result or failure, or an internal contract to its owning component. Keep exceptions with the rule they qualify. Add or update the command's same-page link when its entry point changes.

When documentation and implementation disagree, record both accounts beside the rule. Reuse the exact open issue with its current owner and status. Otherwise open a Triage issue in the clearml-yolo project and assign it to the requester. Update the decision in the resolving PR.

Keep an active decision's identifier through a rename. Remove obsolete sections and their navigation entries. When the entire capability is retired, its identifier becomes available for reuse. Git preserves previous wording. Attribute historical reasoning only when its source records it.
