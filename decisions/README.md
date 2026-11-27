# Architecture decisions

Start with a command below, or find a feature by topic. Each record describes the decision CY implements, its observable consequences and the sources a reader can use to check it. The [technical reference](../DOCS.md), [user guide](../docs/README.md) and [glossary](../GLOSSARY.md) own detailed contracts, instructions and terminology.

## Commands

| Command | Workflow or tool decision |
| --- | --- |
| `cy` | [Run the detector pipeline as one experiment](0001-pipeline.md) |
| `cy-train` | [Run standalone training from ground truth](0200-training.md) |
| `cy-predict` | [Predict the selected ground truth images with one checkpoint](0110-prediction.md) |
| `cy-val` | [Validate a checkpoint in one experiment task](0120-validation.md) |
| `cy-metrics` | [Evaluate saved predictions at frozen thresholds](0130-metrics.md) |
| `cy-compare` | [Compare candidate and baseline on a common split](0140-comparison.md) |
| `cy-report` | [Render paired developer and business reports from one comparison](0150-report.md) |
| `cy-ground-truth` | [Convert a YOLO dataset into ground truth](0100-ground-truth-conversion.md) |
| `cy-export` | [Run each detector export operation as its own task](0230-export.md) |
| `cy-init-config` | [Export editable YAML for one command and detector selection](0005-config-tree.md) |
| `cy-dedup` | [Reflink identical cached images with cy-dedup](0312-cache-deduplication.md) |
| `cy-download-weights` | [Prepare the maintained weight catalogue from a pinned release](0213-bulk-weights.md) |
| `cy-batch-estimate` | [Measure training batch capacity on one GPU per probe](0220-batch-estimation.md) |

## Invocation and configuration

- [ADR-0001 · Run the detector pipeline as one experiment](0001-pipeline.md)
- [ADR-0002 · Preserve a successful training result across downstream failures](0002-pipeline-outcome.md)
- [ADR-0003 · Compose one executable configuration for each experiment command](0003-hydra-composition.md)
- [ADR-0004 · Show each Hydra command’s selectable options](0004-command-help.md)
- [ADR-0005 · Export editable YAML for one command and detector selection](0005-config-tree.md)
- [ADR-0006 · Validate composed settings before owning a remote task](0006-command-preflight.md)
- [ADR-0007 · Run a direct Hydra sweep sequentially](0007-sequential-sweeps.md)
- [ADR-0008 · Resolve file-backed configuration objects in the invocation context](0008-file-configuration.md)

## Architecture and shared contracts

- [ADR-0010 · Keep scientific logic inside explicit import boundaries](0010-layer-boundaries.md)
- [ADR-0011 · Inject workflow capabilities once per invocation](0011-workflow-composition.md)
- [ADR-0012 · Defer runtime initialization until a capability is invoked](0012-import-effects.md)
- [ADR-0013 · Sanitize structured values at publication boundaries](0013-credential-redaction.md)
- [ADR-0014 · Keep native comparison diagnostics in a local archive](0014-native-output-archive.md)
- [ADR-0015 · Validate tables at the stage that consumes them](0015-dataframe-validation.md)

## Ground truth and datasets

- [ADR-0100 · Convert a YOLO dataset into ground truth](0100-ground-truth-conversion.md)
- [ADR-0101 · Preserve image membership and lexical identity in ground truth](0101-ground-truth-csv.md)
- [ADR-0102 · Resolve a ground truth source once per invocation](0102-ground-truth-source.md)
- [ADR-0103 · Prepare native training datasets from validated records](0103-dataset-preparation.md)
- [ADR-0104 · Share prepared datasets under a locked content key](0104-dataset-cache.md)

## Prediction and validation

- [ADR-0110 · Predict the selected ground truth images with one checkpoint](0110-prediction.md)
- [ADR-0111 · Resolve prediction weights and identify their source](0111-weight-selection.md)
- [ADR-0112 · Represent detections in original pixels with explicit image naming](0112-prediction-csv.md)
- [ADR-0113 · Bind predictions to their bytes, checkpoint and naming mode](0113-prediction-provenance.md)
- [ADR-0114 · Capture requested and effective inference settings](0114-prediction-settings.md)
- [ADR-0120 · Validate a checkpoint in one experiment task](0120-validation.md)

## Evaluation and metrics

- [ADR-0130 · Evaluate saved predictions at frozen thresholds](0130-metrics.md)
- [ADR-0131 · Fit confidence thresholds only on validation images](0131-calibration.md)
- [ADR-0132 · Score detections at fixed operating thresholds](0132-fixed-scoring.md)
- [ADR-0133 · Compute AP and precision–recall curves over the confidence ranking](0133-average-precision.md)
- [ADR-0134 · Retain a row-level explanation for each evaluation outcome](0134-evaluation-lineage.md)
- [ADR-0135 · Publish split dashboards, audit tables and diagnostics](0135-evaluation-outputs.md)
- [ADR-0136 · Use digital-metrics behind CY evaluation adapters](0136-digital-metrics.md)

## Model comparison

- [ADR-0140 · Compare candidate and baseline on a common split](0140-comparison.md)
- [ADR-0141 · Recover checkpoints and frozen thresholds for comparison](0141-model-recovery.md)
- [ADR-0142 · Reuse comparison predictions only for compatible inputs](0142-comparison-inference.md)
- [ADR-0143 · Test paired model differences over shared eligible classes](0143-comparison-statistics.md)
- [ADR-0144 · Bind comparison outputs to named model roles](0144-comparison-manifest.md)
- [ADR-0145 · Retain candidate diagnostics when no automatic baseline exists](0145-candidate-only.md)

## Reports and workbooks

- [ADR-0150 · Render paired developer and business reports from one comparison](0150-report.md)
- [ADR-0151 · Recover class counts from the evaluated checkpoint's training population](0151-population-counts.md)
- [ADR-0152 · Determine report eligibility separately for each model](0152-report-eligibility.md)
- [ADR-0153 · Present a fixed-column business comparison](0153-business-workbook.md)
- [ADR-0154 · Attach readable model identity while retaining original workbook bytes](0154-workbook-identity.md)
- [ADR-0155 · Show metric availability in the developer report](0155-developer-workbook.md)
- [ADR-0156 · Keep report-generator presentation behind the reporting adapter](0156-report-generator.md)
- [ADR-0157 · Show readable class aliases without changing scientific keys](0157-readable-class-labels.md)

## Training and detector families

- [ADR-0200 · Run standalone training from ground truth](0200-training.md)
- [ADR-0201 · Train and predict with Ultralytics YOLO](0201-yolo.md)
- [ADR-0202 · Run DEIMv2 against its pinned upstream source](0202-deimv2.md)
- [ADR-0203 · Use the RF-DETR preset's full detector checkpoint](0203-rfdetr.md)
- [ADR-0204 · Preserve Faster R-CNN geometry on a padded canvas](0204-faster-rcnn.md)
- [ADR-0205 · Use FCOS with a zero-based foreground vocabulary](0205-fcos.md)
- [ADR-0206 · Keep explicit training weights authoritative](0206-training-initialization.md)
- [ADR-0207 · Bind detector identity and class order to checkpoint bytes](0207-checkpoint-descriptor.md)
- [ADR-0208 · Apply custom augmentation only to training samples](0208-training-augmentation.md)
- [ADR-0209 · Keep distributed training under one invocation owner](0209-distributed-training.md)
- [ADR-0210 · Freeze the augmentation pipeline for workers and replay](0210-augmentation-snapshot.md)
- [ADR-0211 · Draw mosaic donors from the current training population](0211-mosaic-augmentation.md)
- [ADR-0212 · Resolve only the selected detector's execution assets](0212-selected-assets.md)
- [ADR-0213 · Prepare the maintained weight catalogue from a pinned release](0213-bulk-weights.md)
- [ADR-0214 · Persist a stable Ultralytics weight-cache directory](0214-yolo-weight-cache.md)
- [ADR-0215 · Require a verified DEIMv2 source revision](0215-deim-source.md)
- [ADR-0216 · Translate official DINOv3 backbones for DEIMv2 large presets](0216-deim-dinov3.md)
- [ADR-0217 · Classify the installed Ultralytics settings by stage](0217-native-yolo-settings.md)
- [ADR-0218 · Share the training recipe across Torchvision detectors](0218-torchvision-training.md)
- [ADR-0219 · Replay Ultralytics DDP callbacks in the owning process](0219-native-ddp-relay.md)

## Batch estimation

- [ADR-0220 · Measure training batch capacity on one GPU per probe](0220-batch-estimation.md)
- [ADR-0221 · Store human-editable per-GPU training batches in YAML](0221-batch-size-table.md)
- [ADR-0222 · Resolve an unspecified training batch from the local table](0222-batch-lookup.md)
- [ADR-0223 · Inspect saved batch coverage without a GPU](0223-batch-coverage.md)
- [ADR-0224 · Keep measurement evidence separate from training inputs](0224-batch-evidence.md)
- [ADR-0225 · Admit batch probes only on observable CUDA devices](0225-batch-probe-admission.md)

## Export and inference

- [ADR-0230 · Run each detector export operation as its own task](0230-export.md)
- [ADR-0231 · Export Faster R-CNN as a standard CPU FP32 ONNX graph](0231-onnx-export.md)
- [ADR-0232 · Compile a TensorRT engine for an explicit GPU and precision](0232-tensorrt-build.md)
- [ADR-0233 · Compare the exported engine against its source checkpoint](0233-export-verification.md)
- [ADR-0234 · Execute a metadata-bound TensorRT engine without Torch](0234-tensorrt-runner.md)
- [ADR-0235 · Bind graph, engine and inference policy with a sidecar](0235-export-metadata.md)
- [ADR-0236 · Bound the engine's input shapes with optimization profiles](0236-optimization-profiles.md)

## Training policy and weight licences

- [ADR-0240 · Keep the requested training run intact on failure](0240-training-execution-policy.md)
- [ADR-0241 · Keep upstream licences attached to pretrained model assets](0241-weight-licences.md)

## ClearML, FiftyOne and runtime

- [ADR-0300 · Share one ClearML task across experiment stages](0300-task-ownership.md)
- [ADR-0301 · Track required ClearML artifacts through finalization](0301-artifact-publication.md)
- [ADR-0302 · Bind a ClearML Output Model to the best checkpoint](0302-output-model-verification.md)
- [ADR-0303 · Attach calibrated thresholds only to the matching owned model](0303-threshold-metadata.md)
- [ADR-0304 · Restore executable settings from the Agent task snapshot](0304-agent-replay.md)
- [ADR-0305 · Project ClearML step identity before controller cache lookup](0305-controller-cache.md)
- [ADR-0306 · Publish run-scoped overlays to a shared FiftyOne dataset](0306-fiftyone-publication.md)
- [ADR-0307 · Import CY matches as native FiftyOne evaluations](0307-fiftyone-evaluation.md)
- [ADR-0308 · Install the FiftyOne evaluation panel explicitly](0308-fiftyone-app.md)
- [ADR-0309 · Resolve project writes beneath the selected workspace](0309-workspace-containment.md)
- [ADR-0310 · Route result directories by task identity or explicit destination](0310-run-routing.md)
- [ADR-0311 · Retain invocation scratch after every exit](0311-runtime-scratch.md)
- [ADR-0312 · Reflink identical cached images with cy-dedup](0312-cache-deduplication.md)
- [ADR-0313 · Supervise native descendants using Linux process identity](0313-process-ownership.md)
- [ADR-0314 · Journal native output before publishing it to ClearML](0314-console-and-scalars.md)
- [ADR-0315 · Trace long-running operations with a bounded watchdog](0315-tracing.md)
- [ADR-0316 · Expose invocation progress to local observers](0316-progress.md)
- [ADR-0317 · Keep GPU scheduling in cy-queue](0317-queue-boundary.md)
- [ADR-0318 · Resolve readable project-local task and model names](0318-display-names.md)
- [ADR-0319 · Publish the package checkout as ClearML execution metadata](0319-script-identity.md)
- [ADR-0320 · Publish one set of result rows per invocation](0320-result-bundle.md)
- [ADR-0321 · Publish scientific results as ClearML plots, tables and scalars](0321-clearml-result-views.md)
- [ADR-0322 · Publish executable settings and a redacted differences view](0322-configuration-publication.md)
- [ADR-0323 · Bound ClearML finalization and quarantine uncertain owners](0323-task-finalization.md)
- [ADR-0324 · Render readable identifiers consistently across output surfaces](0324-telemetry-labels.md)
- [ADR-0325 · Warn when Git cannot identify the launch directory as a working tree](0325-launch-checkout.md)
- [ADR-0326 · Resolve attached configuration files at the point of use](0326-configuration-attachments.md)

## Installation, verification and delivery

- [ADR-0400 · Install the experiment runtime before launching a command](0400-installation.md)
- [ADR-0401 · Build the approved scientific dependencies into a worktree-local wheelhouse](0401-local-dependencies.md)
- [ADR-0402 · Apply the same whole-tree static checks to each change](0402-static-checks.md)
- [ADR-0403 · Route verification by the change set](0403-verification-routing.md)
- [ADR-0404 · Select affected unit tests with testmon](0404-unit-selection.md)
- [ADR-0405 · Measure branch coverage on the full unit suite](0405-coverage.md)
- [ADR-0406 · Report mutation outcomes for changed product functions](0406-mutation.md)
- [ADR-0407 · Give each integration run an owned test environment](0407-live-environment.md)
- [ADR-0408 · Derive a reproducible detection corpus from Severstal masks](0408-severstal-corpus.md)
- [ADR-0409 · Exercise the native detector lifecycle on one GPU](0409-native-validation.md)
- [ADR-0410 · Tie change and release acceptance to identified inputs](0410-acceptance.md)
- [ADR-0411 · Verify CY and cy-queue together before an interface or dependency release](0411-pairing.md)
- [ADR-0412 · Publish a version commit and annotated tag together](0412-code-release.md)
- [ADR-0413 · Package verified weights and licence notices as a separately versioned release](0413-weight-release.md)
- [ADR-0414 · Request automated review on pull request updates](0414-pr-review.md)
- [ADR-0415 · Dispatch repository assistance on explicit Claude mentions](0415-mention-assistance.md)
- [ADR-0416 · Verify advertised dependency floors separately from locked versions](0416-dependency-floors.md)
- [ADR-0417 · Run live service checks with isolated credentials and tagged resources](0417-live-integration.md)
- [ADR-0418 · Track a change from Linear through human merge](0418-change-delivery.md)

## Maintaining the records

Each independently usable feature or independently governed contract has one living ADR. A compound workflow owns its sequencing and links to its component records. A detector family owns its presets unless a preset introduces a separate contract. For integrations, document the decisions that CY controls and identify the sibling that owns the other side.

Add, update or remove the record and its index entry in the PR that changes the feature. Keep its identifier through a rename and update incoming links. Removing a feature removes its record. Its identifier becomes available for reuse. Git history preserves earlier text. Use a commit permalink when citing a particular historical decision.

Trace each feature from its public entry point to a result, status or failure. For internal decisions, trace the owning contract. A test link identifies the scenario the test exercises. A live result requires dated evidence for that environment in an issue or PR. These records describe current behavior. Where there is no source for the original reasoning, its historical rationale is unknown.

When code and documentation disagree, describe both accounts in the affected record. Link the exact open issue if one exists, keeping its owner and status. Otherwise file a Triage issue in the clearml-yolo project and assign it to the requester. Update the ADR in the resolving PR. Before merging an inventory, reconcile it with freshly fetched master.
