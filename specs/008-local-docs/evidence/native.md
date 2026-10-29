# Representative native execution — 2026-10-29

## Scope and setup

Two fresh complete pipeline invocations verified the feature's configuration declarations
against native execution, actual ClearML publication and downloaded outputs. These are
random-weight, one-epoch execution checks on the tutorial dataset, not model-quality evidence.
The parent owns canonical checks, paired CY/queue verification and release acceptance.

The `running-end-to-end-tests` and `clearml-yolo-environment` workflows supplied the
execution, ownership and cleanup rules. A fresh minted tag, project and `CY_HOME` isolated
all outputs. The environment helper authenticated the shared test stand and returned GO.
GPU capacity was rechecked before native GPU execution; existing workloads were preserved.
Previously validated native asset caches were copied into the owned workspace to avoid
unrelated downloads from feature 007's automatic preparation. No earlier execution result
was reused as acceptance evidence.

The quickstart generator produced 12 non-square images: four disjoint images per train,
val and test split, including one empty image per split. Source CSV SHA-256:
`c13a4e1755db8421bcfb33bcb6d23d7b11c45f964146f395a077f2e66b213b18`.
Source CSV bytes remained unchanged after both pipelines.

## Executed commands

These commands use portable placeholders for the owned workspace and minted tag. Exact
invocations, environment preflight logs, task/model IDs, code hashes, generated YAML,
downloaded files and verification scripts are retained in private environment evidence.
ClearML credentials were consumed from the environment helper and were not printed.

```bash
uv run --frozen --no-sync cy-init-config "$WORKSPACE/yolo-config"
uv run --frozen --no-sync cy-init-config "$WORKSPACE/fasterrcnn-config" \
  --model fasterrcnn/resnet50_fpn

uv run --frozen --no-sync cy --config-dir "$WORKSPACE/yolo-config" --config-name cy \
  "ground_truth=$WORKSPACE/data/ground_truth.csv" "run_dir=$WORKSPACE/yolo-cpu" \
  ultralytics.model=yolo11n.yaml ultralytics.pretrained=false ultralytics.device=cpu \
  ultralytics.epochs=1 ultralytics.imgsz=128 ultralytics.batch=2 ultralytics.workers=0 \
  ultralytics.compile=false ultralytics.amp=false ultralytics.plots=true \
  ultralytics_predict.device=cpu ultralytics_predict.batch=2 ultralytics_predict.imgsz=128 \
  fiftyone.enabled=false compare.bootstrap_iterations=32 \
  "clearml.project_name=$TAG clearml-yolo" "clearml.tags=[$TAG]" \
  clearml.task_name=docs008-yolo-cpu

uv run --frozen --no-sync cy --config-dir "$WORKSPACE/fasterrcnn-config" --config-name cy \
  "ground_truth=$WORKSPACE/data/ground_truth.csv" "run_dir=$WORKSPACE/fasterrcnn-gpu" \
  model.train.pretrained=false model.train.device=0 model.train.epochs=1 \
  model.train.imgsz=128 model.train.batch=2 model.train.workers=0 model.train.amp=false \
  model.predict.device=0 model.predict.batch=2 model.predict.imgsz=128 \
  model.predict.max_det=20 fiftyone.enabled=false compare.bootstrap_iterations=32 \
  "clearml.project_name=$TAG clearml-yolo" "clearml.tags=[$TAG]" \
  clearml.task_name=docs008-fasterrcnn-gpu
```

Both commands exited zero. The completed CPU task was tagged `prod` through the SDK
before launching the GPU candidate, so the second invocation exercised automatic
baseline discovery, mixed-family current-test reinference, comparison and reports.

## Verified outcomes

| Observation | YOLO CPU | Faster R-CNN GPU |
| --- | --- | --- |
| Fresh owner task status | completed | completed |
| Native training | one epoch, CPU | one epoch, single CUDA device |
| Evaluated splits | train, val, test | train, val, test |
| Published GT rows | 12 | 12 |
| Published combined prediction/result rows | 256 | 83 |
| Required artifacts force-downloaded | 11 | 17 |
| Trained best Output Models | exactly one | exactly one |
| Downloaded checkpoint reload and inference | passed on CPU | passed on CPU |
| Paired comparison/report behavior | absent baseline retained candidate outputs | baseline and candidate outputs, paired XLSX and both final reports |

Best checkpoint SHA-256 values:

- YOLO: `cd158a170efdcb6c7baa647ec89fc41a568709196c9cb6a4955c4b7948932f78`.
- Faster R-CNN: `26d604d4119aaf9a24a3b0339ee283fe8ba50b23eae76bc7d1ca8700ab2e1020`.

Fresh SDK reads verified exactly two completed owner tasks. Every registered artifact
and each sole output model was force-downloaded, checked for nonempty contents and hashed.
Downloaded checkpoint bytes match the native producer's best checkpoint. The native
checkpoint descriptor preserves the backend and `square` class vocabulary. Canonical
`run` configuration, native parameters and reported training/evaluation scalars were read
back independently. No duplicate checkpoint/configuration artifact was present.

Downloaded GT and combined result rows preserve all 12 image names, including empty images.
Both comparison contexts contain the same four current test images. Published JSON match
relationships parse correctly. Every populated prediction threshold flag equals the strict
comparison `confidence < confidence_threshold`.

Exact validation thresholds were `square=0.012323923408985138` for YOLO and
`square=0.49024108052253723` for Faster R-CNN. Published CSV thresholds, frozen local values
and output-model metadata agree; model metadata identifies calibration split `val` and
the actual checkpoint hash. Test scoring and baseline comparison retain those frozen
thresholds. Fresh baseline readback after comparison remained unchanged.

All full/DTRK dashboard downloads open as Excel workbooks. The paired workbook contains
the `Сравнение` sheet. Downloaded comparison, developer-report and business-report bytes
match their local producer files. Generated YAML, local manifests, evaluation JSON,
thresholds and provenance records were captured before cleanup. The copied Ultralytics
settings file remained byte-identical to its original.

## Limitations and cleanup

Synthetic metrics and bootstrap warnings do not establish scientific accuracy or statistical
power. The candidate emitted a native Torch `SubprocPool unclean exit` warning after report
publication; its command exited zero, its task completed, all downloads/hash checks passed
and no owned native/compiler process remained. The warning's underlying cause was not
investigated as part of this documentation feature. An unrelated parent verification process
observed afterward was preserved.

These checks do not establish all-preset training, physical multi-GPU execution, queue
scheduling, Agent replay, TensorRT/ONNX deployment quality, live chart interaction or
FiftyOne publication. FiftyOne was explicitly disabled. Separate configuration/browser
and repository tests cover their declared scopes; they are not substituted for native proof.

The required cleanup helper exited zero after capture: it removed the owned project and
tasks, proved zero projects/tasks remained under the exact minted tag, and removed the
owned runtime directory. Only private, detached evidence remains; shared caches, workloads
and services were preserved.
