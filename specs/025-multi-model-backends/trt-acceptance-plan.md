# Prepared TensorRT production acceptance

**Prepared 2026-10-11; not executed.** Heavy execution is already authorized after
2026-10-11 22:00 UTC (2026-10-12 01:00 Moscow). The parent coordinates the actual start;
the scratch driver's release flag is a scheduling guard, not a new user approval. This plan preserves the
[export contract](contracts/export.md), [quickstart](quickstart.md#faster-r-cnn-export-acceptance)
and [deployment API](../../docs/tensorrt-deployment.md). It does not replace the parent
verification ledger or establish passing gates.

## Order and prerequisites

1. Stage the official labeled corpus and immutable source manifest after release.
2. Supply descriptor-bound, task-head-trained checkpoints for ResNet-50, DINOv2-Small and
   DINOv3-Small. Prove their rectangular batch-four gates before expanding to ResNet-101,
   ConvNeXt-Tiny and Swin-Tiny.
3. For each preset, generate one CPU FP32 ONNX graph, then build and verify separate FP32
   and FP16 engines through public `cy-export` operations.
4. Run each engine in a fresh minimal environment with the installed project wheel and
   no Torch/ClearML. Use the shared GPU admission lifecycle for that child too.
5. Review numerical diagnostics, quality, corpus edge cases, profile transitions,
   incompatible artifact/runtime rejection and publication/download evidence separately.

The prepared command generator defaults to printing command arrays. Its `--execute`
option additionally requires the explicit release flag and the UTC time boundary. It runs
sequentially, retains command/log/exit-code evidence and stops on the first failed stage.
Do not bypass a failed quality gate by replacing a trained checkpoint with random heads,
changing the corpus after seeing results or dropping an advertised preset/shape.

## Fixed labeled corpus

Quality acceptance requires accessible source images with verified annotations. Packaged
example photographs without annotations and synthetic adapter images establish smoke
behavior only. Inspect input availability and retain environment-specific findings outside
the repository.

After release, stage a sufficiently rich fixed labeled corpus and its original annotations
in a private task workspace. Choose the source and bounded cohort before inspecting model
outcomes, with coverage of the declared class mapping, scene types, object sizes and aspect
ratios. Record per-class image/object counts, missing classes and the selection rule; do not
impose an image-count cap that prevents the required coverage. Preserve lexical class
labels, original dimensions and category mapping; do not derive ground truth from model
predictions. Freeze source/version, archive/annotation hashes, per-image hashes, split
membership and the converted CSV.

Keep training, validation and test populations disjoint. Audit content hashes and source
groups, including derived copies, rather than relying on distinct filenames. Fit each
native task head only on training images. Select its recipe, hyperparameters, stopping
point and checkpoint using validation, then freeze the checkpoint, preprocessing,
inference policy and evaluator before evaluating the held-out test cohort. A pretrained
backbone with random detector heads is not a meaningful reference.

Require positive native mAP and actual labeled-object detections on the frozen test cohort,
including meaningful native quality at the extreme strip canvases. If that reference
fails, record the quality gate as unmet. Never use held-out test results to decide whether
to continue training, retrain, tune thresholds or change test membership. Further model development
uses training and validation; a subsequent acceptance experiment needs a separately
declared, untouched test cohort after selection is complete.

COCO8 remains useful for smoke checks. Its small partitions, especially when their class
coverage differs, are insufficient acceptance-quality evidence. Positive aggregate mAP
on a few represented classes does not establish recall or label correctness for absent
classes. Record the actual eligible class population and keep smoke findings separate
from the labeled quality gate.

Preserve genuinely empty annotation records and inventory empty/crowded coverage. If
supplemental stress inputs are needed, define their selection and any deterministic
image/box transforms before testing. Use verified background controls and keep mosaics
and their source images in the same held-out partition, with exact provenance. Do not
label an unannotated photograph as empty or count synthetic controls as an official
dataset benchmark. Report the public-image quality denominator and supplemental stress
cohort separately; neither stress results nor test results select the training recipe.

If no inference call yields zero detections under the chosen quality policy, add a separate
`model.predict.conf=1.0` graph/engine edge run and compare against the corresponding native
policy. The normal quality verifier intentionally rejects an all-zero native baseline;
that edge run tests counts/padding/NMS-empty behavior rather than mAP acceptance.

## Public application commands

Use the [quickstart commands](quickstart.md#faster-r-cnn-export-acceptance) with a dedicated
ClearML project and explicit run tags. A prepared manifest binds one checkpoint per preset,
the ground-truth CSV and the RGB archive. Resolve every path before execution.

The scratch handoff includes an unexecuted command generator and manifest example, with
execution gated by the scheduled start and parent coordination flag. These helpers are
private task evidence, not distributed project commands. Use the tracked quickstart's public
`cy-export` examples for project tooling. Repeat for the remaining presets only after the
initial ResNet/DINO gate passes. The complete matrix contains six ONNX
operations, twelve engine builds and twelve quality verifications. Every operation uses
its own output directory and task name. Build/verify request an explicit GPU with normal
queue admission; ONNX requests CPU and FP32.

The expected artifact paths are:

| Stage | Artifact and metadata | Additional evidence |
| --- | --- | --- |
| ONNX | `<preset>/onnx/model.onnx` and `model.onnx.json` | Source descriptor and graph hash |
| Build | `<preset>/<precision>/build/model.engine` and `model.engine.json` | Structured `export_result` runtime/plugin/profile binding |
| Verify | `<preset>/<precision>/verify/verification.json` | `corpus.json`, quality, matching and memory records |

Build evidence is the structured `export_result` together with `model.engine.json`;
the application does not produce a separate build-report file.

Retain failing reports. After successful application operations, independently download
published artifacts into a new directory and compare hashes before fresh-environment use.
Do not infer publication/download outcomes from local files or mocked tests.

## Fresh standalone environment

Build the project wheel locally. Install it with `--no-deps` into a separate Python 3.12
environment alongside NumPy, Pydantic 2, matching TensorRT 10.13.0 and compatible libcudart.
The [deployment guide](../../docs/tensorrt-deployment.md#standalone-environment-and-library-api)
contains dependency and API details. Do not inherit a native environment through `.pth`
files, system site-packages or `PYTHONPATH`.

The prepared RGB packer reads the frozen CSV after release and creates an NPZ plus source
and archive hashes. The standalone script checks that Torch, Torchvision, timm and ClearML
are unavailable, runs with `python -I`, validates outputs through the public runner and
writes fixed outputs/counts/restored coordinates for later numerical inspection.

The prepared scripts are staged outside the repository in the task's acceptance workspace.
Their commands and machine-specific readiness notes remain in the private handoff. They are
not installed project entry points. The tracked deployment guide defines the public runner
and preprocessing API used by the standalone driver.

Run its parent admission wrapper using the regular project environment. That wrapper
registers an exact visible GPU candidate in the shared queue, waits for admission, masks
the child to the admitted UUID, holds `claim_worker` until the child exits and closes the
ticket in `finally`. The minimal child receives visible `device=0`. Never launch a direct
CUDA child beside an already admitted task or bypass occupancy checks.

For every engine, the standalone schedule includes all four endpoint canvases at batches
1–4, both interior canvases at batches 1–4, and exact repeated full/strip/full transitions
on one execution context. It checks batch five, a cross-profile canvas, below-minimum
height and non-stride dimensions are rejected. Each original corpus image remains in the
scientific denominator once; final-batch repeats are recorded as padding only.
It also attempts mismatched engine hashes, TensorRT/CUDA runtime versions, plugin declarations
and profile metadata and requires construction to fail. Those checks establish metadata
binding; they do not prove execution compatibility on a different GPU or CUDA installation.

## Interpreting the current verifier

The application verifier currently exercises 16 endpoint and six interior batch/canvas
cases, evaluates actual COCO bbox metrics and records one-to-one class-aware matches at
IoU 0.99. It checks preprocessing and unsupported shape rejection. The normal workflow
loads the native model and engine in the same Torch process; that does not establish the
fresh standalone gate.

Its aggregate `passed` concerns quality, preprocessing and rejection checks. Unmatched
detection counts and score/box drift remain numerical diagnostics rather than universal
raw-output acceptance thresholds. Inspect those diagnostics and NMS/filtering changes
explicitly before claiming numerical parity. Raw pre-NMS tensors are currently not exposed;
final detections cannot prove raw parity. Corpus validation does not itself require empty
or crowded members, and the application case schedule does not replace exact repeated-shape
standalone replay. These are separate acceptance obligations, not inferred passing results.

Require absolute mAP50–95 loss at most 0.001 FP32 and 0.005 FP16, positive native quality,
meaningful foreground detections, finite outputs, valid labels/counts and original-coordinate
restoration. Preserve per-class recall, evaluator implementation/version/source identity,
corpus hashes and checkpoint identity. Neither a close-box smoke comparison nor native
mAP zero can establish the quality gate.

Record native Torch allocator peaks separately from TensorRT required context memory and
successful I/O allocation request sizes. Neither TensorRT field is total GPU memory or a
process-wide peak. Record cold/warm latency scope and input/output transfer inclusion.

## Evidence required before acceptance

- A valid staged public labeled quality corpus, immutable provenance/split manifests,
  class/scene coverage inventory and evidence of disjoint training, validation and test.
- Six descriptor-bound checkpoints with meaningful trained detector heads and recorded
  validation-selected recipes/checkpoint hashes, frozen before held-out test evaluation.
- Final-source full-backbone ONNX/native matrices and both-precision TensorRT matrices have
  not run. Export-only DINOv3 and Swin shape corrections still need actual graph proof.
- A fresh installed Torch-free environment and independent artifact-download reload have
  not run. The earlier scratch environment shares a native environment and is insufficient.
- Empty/crowded, zero-detection, repeated-shape and incompatible runtime/artifact gates need
  explicit execution records, beyond the application's quality report.
- CUDA 11.8 target acceptance requires a separate compatible deployment GPU/runtime.
  Newer-CUDA local execution cannot establish that gate or serialized-engine portability.

The earlier pretrained ResNet-50 FP32 scratch result remains bounded architectural evidence
for its tested graph and input preparation. Preserve it without promoting it to final
production acceptance. The parent owns the final ledger, review and release decision.
