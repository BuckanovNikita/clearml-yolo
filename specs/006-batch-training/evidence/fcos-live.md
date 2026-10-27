# FCOS CPU live acceptance — 2026-10-26

## Scope and source

Real `fcos/resnet50_fpn` acceptance ran against the authorized shared ClearML stand,
using a helper-minted project/tag and CPU-only execution. The inspected checkout
was the uncommitted feature working tree based on
`9fd2294ab219c534fcce87b59eea7b56e9d01173`, source version `0.40.0`.
The parent owns broader verification, architecture acceptance and GPU coverage.
This bounded worker changed only this evidence file; it made no application,
dependency, shared-service, commit or release changes. Its documentation-only
architecture impact is none: the record describes executed acceptance of the
existing feature modules and adds no interface, import or effect ownership.

The fixture contained twelve distinct non-square PNG images, four in each of
train/validation/test. Each split contained the exact labels `0`, `NA`, `класс-猫`
and one empty image. Validation/test membership was disjoint. Source bytes remained
unchanged, including the uppercase image extension. The custom pipeline used a
serialized Albumentations `HorizontalFlip(p=1)` with Pascal VOC boxes and
`class_labels`. FiftyOne was explicitly disabled.

## Commands and results

Commands ran from the source checkout with `uv run --frozen --no-sync`,
`CUDA_VISIBLE_DEVICES=''`, `OMP_NUM_THREADS=2`, `MKL_NUM_THREADS=2`, and `CY_HOME`
set to the helper-owned invocation directory. The following uses the actual
helper variables and task-local filenames; credentials were consumed directly
from the helper environment and were never written into evidence.

```bash
uv run --frozen --no-sync cy-init-config "$CY_RUN_DIR/configs" \
  --command cy --model fcos/resnet50_fpn

common=("ground_truth=$CY_RUN_DIR/inputs/truth.csv"
  model.train.device=cpu model.predict.device=cpu model.train.epochs=1
  model.train.batch=2 model.train.imgsz=128 model.train.workers=0
  model.train.amp=false model.predict.batch=2 model.predict.imgsz=128
  model.predict.conf=0.05 model.predict.max_det=20
  "clearml.project_name=$CY_RUN_TAG clearml-yolo" "clearml.tags=[$CY_RUN_TAG]"
  fiftyone.enabled=false compare.bootstrap_iterations=100)

uv run --frozen --no-sync cy --config-dir "$CY_RUN_DIR/configs" --config-name cy \
  "${common[@]}" "run_dir=$CY_RUN_DIR/pipeline-native" \
  clearml.task_name=fcos-native-cpu

# The completed task was marked prod through the SDK inside this owned project.
uv run --frozen --no-sync cy --config-dir "$CY_RUN_DIR/configs" --config-name cy \
  "${common[@]}" "run_dir=$CY_RUN_DIR/pipeline-custom" \
  transforms=albumentations "transforms.pipeline_file=$CY_RUN_DIR/inputs/flip.json" \
  clearml.task_name=fcos-custom-cpu

inference=(model=fcos/resnet50_fpn "ground_truth=$CY_RUN_DIR/inputs/truth.csv"
  model.predict.device=cpu model.predict.batch=2 model.predict.imgsz=128
  model.predict.conf=0.05 model.predict.max_det=20
  "clearml.project_name=$CY_RUN_TAG clearml-yolo" "clearml.tags=[$CY_RUN_TAG]")

uv run --frozen --no-sync cy-predict "${inference[@]}" \
  "weights=$CY_RUN_DIR/downloaded/baseline.pth" 'splits=[test]' \
  "output=$CY_RUN_DIR/standalone-predict/predictions.csv" \
  clearml.task_name=fcos-downloaded-predict fiftyone.enabled=false

uv run --frozen --no-sync cy-val "${inference[@]}" \
  "weights=$CY_RUN_DIR/downloaded/baseline.pth" 'splits=[test]' \
  "output_dir=$CY_RUN_DIR/standalone-val" evaluation.ap_method=continuous \
  clearml.task_name=fcos-downloaded-val

uv run --frozen --no-sync cy-compare "${inference[@]}" \
  "baseline_model.task_id=$BASELINE_TASK_ID" \
  "candidate_model.task_id=$CANDIDATE_TASK_ID" \
  "output_dir=$CY_RUN_DIR/standalone-compare" bootstrap_iterations=100 \
  inference.reuse_existing=false clearml.task_name=fcos-standalone-compare
```

All five execution commands exited 0. An earlier validation invocation mistakenly
selected unsupported `evaluation.ap_method=pycocotools`; it exited 1 with the
expected literal-validation error and one failed task, no artifacts or models.
The corrected `continuous` invocation passed. There were exactly six tasks for
six application invocations, five completed and one failed; nested stages created
no additional tasks. Existing task/model name collisions received shared readable
suffixes. Auxiliary inspection-script mistakes were corrected outside the checkout;
they did not require product changes.

## Verified native and publication evidence

- Both training runs loaded the approved Torchvision ResNet-50 pretrained asset,
  SHA-256 `11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca`.
  Independent construction from that actual asset reproduced its first convolution
  tensor exactly. The native trained tensor changed by a maximum absolute
  `0.00010013580322265625`, confirming optimization after initialization.
- Both runs selected epoch-zero best checkpoints by native `val/map50_95`, with
  finite training losses `3.023613691329956` and `3.009538412094116`. Each registered
  exactly one best Output Model. The native checkpoint SHA-256 was
  `ad3c4f91d43a0ec6a27f3e0d3a0f84d415254b42e35c25d9bae5f3a3ff4484a6`; the custom
  checkpoint SHA-256 was
  `a84878239fd9d5eb8d9f99ef102edd752fcd9fefd32ad7b2fa9205cabec7c0a6`.
- Both remote model downloads matched the actual local checkpoint bytes. Embedded
  descriptors retained FCOS, preset, exact foreground strings, 128×128 letterbox
  preprocessing and dependency versions. Tensor reload succeeded without `module.`
  prefixes. Standalone prediction/validation loaded a force-downloaded copy without
  a descriptor sidecar; its separate training-identity sidecar was preserved.
- Independent SDK readback while the native task was active found console events
  and Native training scalars. Saved `run`, `run_overrides`, `model_assets`, consumed
  dataset configuration and General parameters were read back from the server.
  General recorded global/per-rank batch 2, world size 1 and native selection metric.
  Canonical FCOS inputs passed the replay input/runtime filters. The custom frozen
  augmentation snapshot resolved with its source-file selector absent. This checks
  replay inputs; it does not establish actual ClearML Agent replay execution.
- The first pipeline retained candidate dashboards and a recorded comparison skip
  reason with no baseline. After promotion, custom and standalone comparisons
  reinferred both checkpoints over the same four current test images with matching
  CPU, batch, confidence, resolution and detection-limit settings. Exact baseline
  and candidate validation thresholds remained unchanged.
- Force-download/readback succeeded for all **43 artifacts**: 11 native-pipeline,
  17 custom-pipeline, 2 standalone prediction, 5 standalone validation and
  8 standalone comparison artifacts. The inventories matched the
  [publication contract](../../000-baseline/spec.md#publication-inventory), with
  no extra checkpoint/configuration/diagnostic artifacts. Logs confirmed one
  `gt_csv` and one `predicts_csv` upload per successful invocation.
- Every GT download retained all twelve source rows and unique source row IDs,
  exact strings and empty labels. Combined predictions retained foreground `0`,
  exclusions and separate prediction/baseline/candidate contexts. Downloaded strict
  threshold flags matched `<`; pre/post-match JSON parsed successfully. Standalone
  prediction rows remained `not_evaluated` without invented thresholds. Full/DTRK
  dashboards, paired `Сравнение`, exclusions and developer/business workbooks opened.
- Downloaded full-precision validation threshold CSVs, local frozen values and fresh
  model metadata agreed exactly, including typed per-class values and the actual
  prediction-checkpoint SHA-256. Standalone stages registered no Output Models.

## Limitations and cleanup

This is short synthetic CPU execution evidence for **one FCOS preset**. Native
validation mAP was zero; these fixtures establish neither useful detector accuracy
nor comparative quality. Some early predictions became zero-area boxes after
clipping; the existing evaluation path retained them as excluded rows.

This worker did not exercise other FCOS presets, GPU/DDP, queued execution,
cross-family comparison, actual Agent replay, browser plot interactions, optional
FiftyOne, transport fault injection or ten-second telemetry latency. Those claims
remain outside this record and require their own evidence. No broader release or
feature acceptance is inferred from these results.

Private evidence retains exact commands, exit statuses, logs, force-downloaded
artifacts, configuration/metadata/scalar readback, input hashes, source hashes and
the complete task-owned invocation files before cleanup. Machine-specific paths,
task IDs and stand identity remain in that external bundle, communicated to the
parent worker. The environment cleanup helper then exited 0, deleted the one
owned project and its tasks/models/artifacts, proved **zero matching projects and
tasks**, and removed only its tag-named invocation directory. No shared services
or unrelated workloads were changed.
