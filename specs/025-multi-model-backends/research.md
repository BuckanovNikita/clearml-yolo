# Research: Multi-model detection backends

**Date**: 2026-10-11

This document records design decisions and inspected sources. Native training and export
probes are separate execution gates; no successful runtime result is inferred from a
package version, documentation statement or completed planning artifact.

## Existing architecture and released behavior

**Decision**: Extend the current `ModelRunner`, dataset/repository ports and composition
boundary, retaining existing use cases and scientific evaluation.

**Rationale**: The inspected application already routes training, prediction and comparison
through injected ports. Scheduler/bootstrap paths sit outside model execution. Current
contracts explicitly preserve all four queue/autogpu modes, child supervision, replay,
isolation through uploads and bounded FiftyOne workers.

**Alternatives considered**: Separate family-specific applications would duplicate ownership
and evaluation policy; eager SDK registration would violate admission/configuration behavior.

**Evidence**: [Ports](../../src/clearml_yolo/application/ports.py),
[composition](../../src/clearml_yolo/entrypoints/composition.py),
[current contract index](../../docs/current-contracts.md),
[runtime isolation](../../docs/runtime-isolation.md).

## Native backend selection

**Decision**: Default `model=ultralytics`; new presets use nested typed `model.train` and
`model.predict` settings. Keep legacy YOLO groups authoritative. Compare roles resolve
their own checkpoint descriptors; raw external checkpoints can specify backend/preset.

**Rationale**: A common selection boundary is needed, while native setting vocabularies and
supported recipes differ. Explicit group ownership avoids accidental YOLO argument leakage.

**Alternatives considered**: One untyped universal native mapping would hide unsupported
settings; removing existing groups would break the accepted compatibility requirement.

## RF-DETR

**Decision**: Integrate RF-DETR 1.11.2 using its native training/prediction APIs for
Nano/Small/Medium/Large; freeze its dependency stack after actual compatibility probes.

**Rationale**: The approved release exists on PyPI and official documentation provides
the native custom-dataset training workflow. Pinning a released API avoids tracking main.

**Alternatives considered**: Copying the trainer or wrapping only inference would fail
native training and owner publication requirements.

**Sources**: [Release package](https://pypi.org/project/rfdetr/1.11.2/),
[official training guide](https://rfdetr.roboflow.com/learn/train/).

**Execution gate**: Import, train briefly, reload and predict using the chosen Python/Torch
stack; inspect callbacks, selected best checkpoint, class mapping and effective recipe.

## DEIMv2

**Decision**: Use official S/M/L/X recipes at revision
`1d2ca42171570c713e78fc6a766ec5104b7f4724`, loading verified external source privately.

**Rationale**: Upstream documents these presets, COCO custom-data preparation, separate
backbone assets and native training recipes. Its documented environment does not establish
compatibility with this project's selected modern stack; that requires a probe.

**Alternatives considered**: Original DEIM is deferred by approved scope; a main-branch
checkout is insufficient provenance; putting an unqualified `engine` on global import
paths risks collisions with unrelated libraries.

**Source**: [Official DEIMv2 repository](https://github.com/Intellindust-AI-Lab/DEIMv2).
The commit-specific browser fetch failed; source-checkout verification remains mandatory
before import. This is not evidence that the approved revision is unavailable.

**Execution gate**: Verify exact checkout and assets, import privately, train/reload/predict
and confirm native data category remapping is disabled for the project's class vocabulary.

## Faster R-CNN and modern features

**Decision**: Use Torchvision detection heads with ResNet-50/101 FPN, ConvNeXt-Tiny,
Swin-Tiny and explicit DINOv2/DINOv3-Small pyramids. Use Torchvision/timm pretrained backbones
with task-specific heads; train all six through one project-owned typed native adapter.

**Rationale**: Torchvision exposes Faster R-CNN construction and documented detection
interfaces. Hierarchical features and patch-token backbones require explicit adapters;
an architecture name alone does not prove feature shapes or exportability.

**Alternatives considered**: Advertising arbitrary timm names would imply unverified
training/export capabilities; one ResNet-only preset would omit approved modern backbones.

**Source**: [Torchvision Faster R-CNN documentation](https://docs.pytorch.org/vision/stable/models/faster_rcnn.html).

**Execution gate**: ResNet and DINO dynamic export first, then every advertised preset's
native and standalone acceptance. Do not silently replace unavailable pretrained weights.

## Dataset and checkpoint provenance

**Decision**: Preserve CSV as input, generate deterministic backend-native records, and
bind a versioned descriptor to the checkpoint hash. Preserve mapping and preprocessing
through the best Output Model and downloaded local checkpoint.

**Rationale**: Current caches assume an immutable source contract; current comparisons
already hash checkpoints/settings/current membership. New family/class transformations
must enter those identities so incompatible caches cannot be reused.

**Alternatives considered**: Mutable remote display metadata is not an authoritative class
vocabulary; inferring architecture from filenames is ambiguous; adding raw checkpoint
artifact duplicates would violate the one-best-model publication contract.

## TensorRT compatibility and parity

**Decision**: TensorRT 10.13.0 is the deployment target, with ONNX opset 17 as the starting
operator contract. Keep native and exported preprocessing identical and build standalone
FP32/FP16 engines with both approved dynamic profiles.

**Rationale**: NVIDIA's 10.13.0 release notes list CUDA 11.8 and newer CUDA 12.x versions.
That compatibility statement does not prove any detector graph, particular GPU or binary
portability. Use the appropriate local build, rebuild for the deployment runtime and label
unexecuted CUDA 11.8 acceptance explicitly.

**Alternatives considered**: Fixed-batch tracing, host-side proposal/ROI/NMS fallback or
changing DINO interpolation to satisfy a parser would violate accepted behavior.

**Source**: [NVIDIA TensorRT 10.13.0 release notes](https://docs.nvidia.com/deeplearning/tensorrt/10.x.x/getting-started/release-notes-10/10.13.0.html).

**Execution gate**: Actual graph parsing/build/execution for dynamic batch four and
rectangular ResNet/DINO inputs precedes expansion. Collect preprocessing/raw diagnostics
where available and class-aware final detections. Frozen labeled-corpus quality gates are
0.001/0.005 absolute mAP50–95 loss for FP32/FP16; quality alone is not numerical parity.

## Workflow and release

**Decision**: Use Spec Kit with explicit feature-directory environment selection, direct
resolved templates and read-only prerequisite discovery. Do not edit installed tooling.

**Rationale**: `setup-plan.sh` and `setup-tasks.sh` persist `.specify/feature.json` through
`get_feature_paths`; direct template resolution avoids modifying that protected state.
The inspected extension registry contains `hooks: {}`.

**Alternatives considered**: Patching installed workflow helpers or rewriting constitution
history is unnecessary. The spec documents the narrow explicitly approved policy change.

After required checks, documentation and independent review, follow the existing local
release hooks and Git-tag-only publication policy. No GitHub Release object is created.
