# Implementation Plan: Multi-model detection backends

**Branch**: `025-multi-model-backends` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: Approved feature specification in this directory.

## Summary

Extend the current ports/composition architecture with lazy native DEIMv2, RF-DETR and
Faster R-CNN adapters. Preserve YOLO configuration and the v0.23.0 supervisor, FIFO queue,
replay, invocation isolation, evaluation and publication contracts. Add deterministic
backend dataset preparation, durable checkpoint descriptors, cross-family comparison,
selected model configuration export and standalone dynamic Faster R-CNN TensorRT export.

Prove native upstream compatibility and dynamic ResNet/DINO engine feasibility before
expanding presets. The specification is approved; neither this plan nor a created adapter
counts as runtime acceptance.

## Technical Context

**Language/Version**: Existing Python 3.12, runtime annotations, strict mypy and Ruff.

**Primary Dependencies**: Existing Hydra/hydra-zen, Pydantic, Pandera, ClearML and native
Ultralytics; optional RF-DETR 1.11.2, verified DEIMv2 source at the approved revision,
Torchvision/timm, ONNX and TensorRT 10.13.0. Lock only a stack proven by early probes.

**Storage**: Existing local dataset caches and invocation directories, canonical CSVs,
checkpoint descriptors and ClearML Output Models/artifacts; no new service/database.

**Testing**: pytest, Ruff, mypy, import-linter, installed-command/configuration checks,
repository hooks, real native training/download tests and standalone engine validation.

**Target Platform**: Existing supported execution platform; GPU acceptance on NVIDIA.
CUDA 11.8 deployment compatibility is documented separately from the local newer-CUDA
TensorRT validation environment. No target deployment is authorized.

**Project Type**: Python package with composable Hydra CLIs and native backend adapters.

**Performance Goals**: Record latency/memory; no invented throughput target. Export quality
loss limits are 0.001 FP32 and 0.005 FP16 mAP50–95 against the identical native checkpoint.

**Constraints**: No eager SDK/CUDA initialization, upstream monkeypatching, data mutation,
new scheduling service, digital-metrics revision change or weakened architecture checks.

**Scale/Scope**: Four DEIMv2, four RF-DETR and six Faster R-CNN presets; all 14 complete
the native workflow, all six Faster R-CNN presets complete standalone export acceptance.

## Constitution Check

| Principle | Design compliance and evidence gate |
| --- | --- |
| Typed explicit Python | Pydantic request/descriptor/profile records; SDK opacity stays at adapters; configured lint/type checks remain mandatory. |
| Enforced boundaries | Core and application own records/ports; composition selects adapters; package/configuration imports stay SDK-free; exhaustive import contracts are extended. |
| Configuration/run ownership | Existing one-task publication, source ownership, strict setting validation and requested/effective separation remain. New family groups do not reinterpret YOLO overrides. |
| Evidence-based verification | Mocked tests cover contracts; only actual native and fresh-download runs satisfy model acceptance; engine quality is distinct from raw parity. |
| Safe collaboration | Explicit adapter file ownership, parent integration and fresh independent review; task-owned cleanup and preserved pre-existing changes. |

The user-approved scope explicitly supersedes only Principle III's Ultralytics-exclusive
model delegation and groups for non-YOLO backends. The rest remains mandatory. This
exception is recorded in [spec.md](spec.md); the constitution and installed workflow
tooling remain unchanged. Pre-design and post-design review find no additional deliberate
exceptions. Native compatibility and dynamic export remain execution gates, not assumed facts.

## Project Structure

### Documentation (this feature)

```text
specs/025-multi-model-backends/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── backend.md
│   └── export.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/clearml_yolo/
├── core/                         # Pure model/execution records
├── application/                  # Shared contracts, ports and use cases
├── adapters/
│   ├── deim/                     # DEIMv2 loader, training and inference
│   ├── rfdetr/                   # RF-DETR native adapter
│   ├── fasterrcnn/               # Backbones, native training and inference
│   ├── export/                   # ONNX, TensorRT build and standalone execution
│   ├── storage/                  # Dataset preparation, checkpoint descriptor I/O
│   ├── runtime/                  # Existing admission and isolation
│   ├── clearml/                  # Existing owner publications/model resolution
│   └── yolo/                     # Existing YOLO behavior retained
└── entrypoints/                  # Composition, Hydra/config export and cy-export
tests/                            # Contract, adapter, architecture and native checks
```

**Structure Decision**: Keep one package and its current dependency direction. Model SDKs
belong to separate adapter packages selected by composition. Scheduler/configuration paths
consume lightweight phase descriptors rather than importing native libraries. No service
or generic plugin installation framework is added.

## Implementation Design

### Model configuration and execution

- Register `model=ultralytics` as the default and explicit presets such as
  `model=rfdetr/small` and `model=fasterrcnn/resnet50_fpn`. New-family groups own `backend`,
  `preset`, optional `source_dir`, and typed `train`/`predict` settings. For YOLO, the
  existing top-level `ultralytics`/`ultralytics_predict` mappings remain authoritative.
- Generalize phase demand, device-setting paths, exact selection, child remapping, replay
  admission and provenance together. Train/predict/export phases retain the released four
  execution modes; both controls false preserves native settings and bypasses discovery.
- Keep generic bootstrap/isolation around every invocation through task closure. Backend
  initialization occurs only after admission. Owned training descendants must be reaped
  before GPU cleanup and reservation contraction. Preserve bounded FiftyOne workers.
- Extend `cy-init-config --command ... --model PRESET` with one selected wrapper and only
  required groups, including `cy-export`, retaining atomic preflight and symlink refusal.

### Native adapters, data and publications

- RF-DETR uses the approved released native training APIs. DEIMv2 is loaded from a verified
  external checkout under a private namespace without global import-path mutation. Preserve
  effective native recipes; reject unsupported settings rather than ignoring them.
- Faster R-CNN uses Torchvision detection components, hierarchical FPN adapters and an
  explicit DINO feature pyramid, pretrained backbones and dataset-specific heads.
- Extend dataset preparation to deterministic COCO and typed detection records. Reuse the
  existing CSV validation and immutable-source policy; include format and vocabulary in
  cache identity. Background/internal category numbering never leaks into public labels.
- Persist descriptor/checkpoint binding through local copies and ClearML downloads. Legacy
  project checkpoints without a new descriptor remain YOLO; explicit backend/preset
  overrides support raw external checkpoints. A conflicting descriptor fails.
- Reuse one owner task, callback/error propagation and one verified best Output Model.
  Native worker telemetry returns to the owner. Export artifacts retain checkpoint lineage
  without registering another trained model.

### Comparison and export

- Resolve candidate and baseline descriptors independently, then use the same current
  image set, shared requested inference policy and one shared inference device. Record
  family-effective preprocessing and preserve calibration, exact thresholds and reports.
- Build `cy-export` around the existing command lifecycle. CPU-only graph creation has no
  GPU demand; engine build and GPU verification reserve one GPU. Follow the exact profile
  and evidence rules in [export.md](contracts/export.md).
- Export tensor-based dynamic operations through proposal generation, ROI processing and
  NMS. Preserve DINO interpolation and lower rotary operations explicitly. Begin with opset
  17; unsupported operators are resolved through verified decompositions or versioned
  plugins, never a hidden Torch fallback.

## Workstreams and Dependencies

1. Parent establishes repository/environment evidence and shared interfaces while separate
   bounded investigators prove native upstream compatibility and dynamic ResNet/DINO export.
   Probe results must resolve critical failures before broad preset implementation.
2. Parent owns shared contracts, model config/registry, composition, scheduling, dataset and
   checkpoint integration. Freeze these interfaces before assigning independent adapters.
3. Delegate DEIMv2, RF-DETR and Faster R-CNN/export adapter/test ownership independently;
   no bounded agent delegates further. Parent continues comparison and owner publication.
4. Serialize real GPU acceptance on shared hardware. Inspect combined changes, execute full
   checks, then obtain fresh independent read-only review and resolve findings.
5. Complete documentation and validation before the authorized release workflow. Release
   commits/tags follow existing hooks and explicit task staging; no GitHub Release objects.

## Verification and Documentation Scope

Run every requirement in [quickstart.md](quickstart.md), including all 14 native presets,
six FP32/FP16 export presets, four execution modes and mixed-family comparisons. Freeze
corpus/checkpoint/evaluator identity for quality checks. Record per-class recall and raw
differences where observable; aggregate quality success alone is not numerical equivalence.

Update `docs/project-contracts.md`, `docs/current-contracts.md`, `docs/runtime-isolation.md`,
affected maintained native-configuration/GPU/publication/recovery contracts, generated
examples, `README.md`, `.agents/skills/running-end-to-end-tests/` and a new English
`docs/multi-model-backends.md`/`docs/tensorrt-deployment.md`. Preserve dated history and mark
superseded intent with links. Validate Markdown, local links and executable examples.
Machine-specific setup/results belong to global environment evidence, not tracked guidance.

## Complexity Tracking

| Authorized exception | Why needed | Simpler alternative rejected because |
| --- | --- | --- |
| Native execution extends beyond Ultralytics | Explicit approved DEIMv2/RF-DETR/Faster R-CNN scope | Translating every model into a YOLO runtime would replace native training recipes and fail the requested families. |
| Separate standalone export runtime | Explicit no-Torch deployment requirement | Reusing native inference as a fallback would not verify standalone TensorRT execution. |

## Torch compatibility implementation — 2026-10-12

Dependency agent exclusively edits pyproject.toml and uv.lock in parallel with feature
024 runtime/storage implementation. Preserve exact local sources and approved upstream
revisions. Upgrade only Torch/Torchvision and required transitive dependencies, inspect
semantic lock changes, then coordinate environment sync before parent verification.
Parent integrates both workstreams, runs native operators/CPU DDP/detector/GPU/export
checks and records current evidence. Documentation and fresh independent review precede
release. Historical acceptance remains dated evidence of the former pair.
