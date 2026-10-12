# Feature Specification: Multi-model detection backends

**Feature Branch**: `025-multi-model-backends`

**Created**: 2026-10-11

**Status**: Complete; verified and released as Git tag `v0.24.0`

**Input**: The user requested DEIM, RF-DETR and Faster R-CNN with modern backbones,
approved the complete multi-model plan revalidated against v0.23.0, and instructed
"Implement the plan."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Train and evaluate multiple detector families (Priority: P1)

A detection researcher selects a model preset, trains or fine-tunes it using the existing
CSV dataset input, and uses the existing prediction, validation, metrics and report commands.
The same experiment owns its tracking records and one downloadable best checkpoint.

**Why this priority**: New model families are useful only when they participate in the
complete reproducible training and evaluation workflow.

**Independent Test**: For every advertised preset, complete short native training, reload
the saved and freshly downloaded best checkpoint, predict, validate and inspect published
artifacts without substituting mocks for execution.

**Acceptance Scenarios**:

1. **Given** valid CSV ground truth including empty images and separate train/validation/test
   splits, **When** a supported preset is trained, **Then** its classes, splits, geometry and
   original image bytes remain intact and the selected best checkpoint reloads successfully.
2. **Given** an existing YOLO command or editable configuration, **When** it is used unchanged,
   **Then** the existing setting precedence, outputs and evaluation behavior are preserved.
3. **Given** a completed training invocation, **When** its best model is downloaded in a fresh
   process, **Then** backend, preset, vocabulary, preprocessing and checkpoint identity permit
   prediction without guessing from a filename or mutable model metadata.
4. **Given** a native callback, upload, flush or interruption failure, **When** completion is
   attempted, **Then** the command and owned task fail and retain local diagnostics.

### User Story 2 - Compare checkpoints across model families (Priority: P1)

A researcher compares a candidate and baseline from different detector families on the
current dataset using the existing calibrated evaluation and reporting workflow.

**Why this priority**: Adding architectures must preserve valid model selection and the
meaning of comparison results.

**Independent Test**: Compare each new backend against YOLO and another new backend,
checking current image membership, exact threshold maps, checkpoint lineage and reports.

**Acceptance Scenarios**:

1. **Given** candidate and baseline checkpoints from different families, **When** comparison
   runs, **Then** each checkpoint selects its own backend while both infer the same current
   images on one shared device under the same requested inference and evaluation policy.
2. **Given** validation-calibrated thresholds, **When** test comparison runs, **Then** the
   candidate thresholds remain frozen and baseline thresholds are loaded without test calibration.
3. **Given** different family preprocessing or an unsupported requested setting, **When**
   comparison is prepared, **Then** effective preprocessing is recorded and unsupported
   settings fail explicitly instead of being silently ignored.

### User Story 3 - Preserve scheduled and isolated execution (Priority: P1)

A researcher runs individual jobs and mixed-model sweeps using the released queue and
automatic GPU controls while keeping credentials, library configuration and temporary
resources isolated to the owning invocation.

**Why this priority**: New model SDKs must not bypass v0.23.0 resource ownership or alter
the behavior of existing concurrent runs.

**Independent Test**: Exercise each backend in all four queue/autogpu combinations,
including CPU bypass, exact devices, replay, cancellation and mixed-model sweeps.

**Acceptance Scenarios**:

1. **Given** a waiting queued job, **When** configuration and demand are resolved, **Then**
   no model SDK, CUDA context or ClearML task is created before admission.
2. **Given** exact devices or automatic allocation, **When** a supervised child starts,
   **Then** requested identities remain recorded separately from child-local effective devices.
3. **Given** training descendants or pending uploads, **When** execution changes phases or
   ends, **Then** owned processes finish or are reaped before reservation contraction and scratch cleanup.
4. **Given** a mixed-family Hydra sweep, **When** the queue is enabled or disabled, **Then**
   its released concurrency policy, result order, callbacks and failure behavior are preserved.
5. **Given** a request to generate one model command configuration, **When** local export
   runs, **Then** only its selected wrapper and required groups are written with overwrite
   and symlink protections and without creating a task or importing model runtimes.

### User Story 4 - Export Faster R-CNN for standalone deployment (Priority: P1)

A deployment engineer exports any supported Faster R-CNN checkpoint, builds FP32 and
FP16 TensorRT engines, and verifies inference independently of the training framework.

**Why this priority**: Dynamic standalone Faster R-CNN deployment is an explicitly approved
acceptance requirement, including the modern backbones.

**Independent Test**: For each Faster R-CNN preset, run serialized engines without Torch
at all required sizes, batches and profile transitions, then compare with the same native
checkpoint and preprocessing on a fixed labeled corpus with meaningful detections.

**Acceptance Scenarios**:

1. **Given** a supported Faster R-CNN checkpoint, **When** export succeeds, **Then** the
   output contains the graph, engine, class/preprocessing metadata, profiles and verification
   evidence with source-checkpoint lineage and no duplicate trained-model registration.
2. **Given** batch sizes one through four and either supported spatial profile, **When** a
   serialized engine executes, **Then** variable detection counts, image geometry and class
   mapping remain correct through shape/profile changes, including empty and crowded scenes.
3. **Given** an out-of-profile shape or unsupported operator, **When** export or inference
   runs, **Then** it fails clearly; falling back to Torch does not count as deployment support.
4. **Given** only local execution evidence, **When** a deployment report is produced,
   **Then** it distinguishes local verification from documented, untested CUDA 11.8 compatibility.

### Edge Cases

- Empty images, all-empty predictions, non-square images, source filename collisions,
  Unicode/numeric class labels, and classes absent from one comparison checkpoint.
- Missing optional dependencies, unavailable pretrained weights, inconsistent checkpoint
  descriptors, malformed metadata, and incompatible upstream source revisions.
- CPU inference, busy GPUs, exact-device order, remapped child devices, cancellation,
  failed native workers, replay changes and interrupted artifact publication.
- Profile boundaries and interior shapes, DINO patch alignment, valid-image sizes smaller
  than the batch canvas, filtering/NMS ties and precision-related nonfinite outputs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Support DEIMv2 S/M/L/X; RF-DETR Nano/Small/Medium/Large; and Faster R-CNN
  ResNet-50-FPN, ResNet-101-FPN, ConvNeXt-Tiny, Swin-Tiny, DINOv2-Small and DINOv3-Small.
- **FR-002**: Every preset must support native training/fine-tuning, checkpoint reload,
  prediction, validation, canonical metrics/reports and verified ClearML publication.
- **FR-003**: Existing YOLO commands, native configuration precedence and evaluation
  algorithms must remain compatible; optional SDKs load only when selected for execution.
- **FR-004**: CSV remains the public ground-truth input. Backend dataset preparation must
  be deterministic, preserve empty images, splits, vocabulary and original coordinates,
  leave source images unchanged, and include output format/class mapping in cache identity.
- **FR-005**: Checkpoints must retain backend, preset, class mapping, preprocessing,
  dependency/source revision and checkpoint identity through local loading and downloads.
- **FR-006**: Training owns one ClearML task and one selected best Output Model. Workers
  must not create tasks or publish independently; upload/flush completion is mandatory.
- **FR-007**: Candidate and baseline backend resolution is independent. Comparison retains
  current-image membership, shared requested settings, one shared inference device,
  validation-only calibration, frozen thresholds, canonical CSVs and reporting algorithms.
- **FR-008**: All four released queue/autogpu modes, exact-device selection, child remapping,
  replay restrictions, scheduling provenance and mixed-family sweeps must be preserved.
- **FR-009**: Generic invocation isolation must cover every backend through final uploads.
  Training descendants must be reaped before GPU memory cleanup/reservation contraction;
  bounded FiftyOne publication and ownership rules remain in force.
- **FR-010**: Local configuration generation must support model selection and the export
  command while preserving selected-command output, lazy imports and filesystem protections.
- **FR-011**: `cy-export` must support Faster R-CNN graph export, engine build and
  verification, using existing bootstrap, scheduling, replay, tracking and output ownership.
  CPU-only graph export bypasses GPU discovery; GPU build/verification reserves one GPU.
- **FR-012**: Every Faster R-CNN preset must produce standalone FP32 and FP16 engines
  with dynamic batches 1–4 and the profiles below, including proposals, ROI processing
  and NMS. A runtime fallback to the training framework does not satisfy this requirement.
- **FR-013**: Native and exported inference must share normalization, aspect-preserving
  resizing, padding, valid-image sizes and coordinate restoration. DINO alignment and
  positional/rotary embedding conversion must preserve their numerical semantics.
- **FR-014**: Export verification must bind checkpoint, preprocessing, corpus and evaluator
  identities; report available intermediate/raw output differences separately from
  class-aware one-to-one detection agreement and aggregate quality changes.
- **FR-015**: TensorRT 10.13.0 is the CUDA 11.8 deployment compatibility target. Engines
  must be rebuilt for target hardware/runtime; newer-CUDA local success is not proof of
  CUDA 11.8 target execution or binary portability.
- **FR-016**: Documentation must describe new presets, configuration, runtime behavior,
  export profiles, dependency versions/plugins, deployment rebuilding and limitations;
  changed Markdown, links and examples must pass validation before completion.

**Required export profiles** (width × height; batch min/opt/max = 1/2/4):

| Profile | Minimum | Optimum | Maximum |
| --- | --- | --- | --- |
| Full frames | 960×608 | 960×608 | 960×736 |
| Strips | 1536×128 | 1920×256 | 1920×256 |

### Key Entities *(include if feature involves data)*

- **Model preset**: Named backend/model combination with native recipe and supported capabilities.
- **Checkpoint descriptor**: Durable backend, vocabulary, preprocessing and source identity
  associated with one checkpoint.
- **Prepared dataset**: Immutable-source derived training records, split membership,
  class mapping and cache identity.
- **Execution phase**: Enabled operation, requested/effective device and ownership requirements.
- **Export bundle**: Source checkpoint, graph, engine, profile/plugin metadata and evidence.
- **Verification record**: Exact inputs, environment, checks, results and unverified limitations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 14 advertised presets complete actual short training, best-checkpoint
  reload, prediction, validation and fresh model/artifact download checks.
- **SC-002**: Each new backend completes comparisons against YOLO and another new backend
  with identical current-image membership and unchanged threshold/evaluation policy.
- **SC-003**: Each new backend passes all four scheduling modes, CPU telemetry bypass,
  replay/device provenance, cancellation/cleanup and mixed-family sweep acceptance.
- **SC-004**: All six Faster R-CNN presets execute FP32 and FP16 engines without Torch
  at the four listed profile endpoint sizes, batches 1–4, interior sizes and repeated
  profile changes; out-of-profile requests are rejected.
- **SC-005**: On the identical fixed labeled acceptance corpus, absolute mAP50–95 loss
  versus the native checkpoint is at most 0.001 for FP32 and 0.005 for FP16. The corpus
  has meaningful reference detections; empty or all-zero evidence alone cannot pass.
- **SC-006**: Verification reports contain finite-output, class-mapping, coordinate,
  per-class recall, latency and memory evidence, with deployment/runtime limitations
  explicit and quality gates distinguished from raw numerical parity claims.
- **SC-007**: Required repository checks, documentation/example validation, parent
  integration and fresh independent review pass before the authorized tag-only release.

## Assumptions

- This approved feature narrowly supersedes constitution Principle III's requirement
  to delegate all model execution to Ultralytics: each selected native backend now owns
  its model execution. Existing YOLO configuration compatibility and all typing,
  architecture, tracking, scheduling, privacy and verification principles remain in force.
  The installed constitution and Spec Kit tooling are not edited by this feature.
- The published v0.23.0 baseline governs scheduling and isolation. The implementation
  worktree also contains inherited follow-up commit `2114714`; it must be preserved.
- DEIM means DEIMv2 in this release. Original DEIM, segmentation, INT8 and additional
  backbone sizes are deferred. Training uses a supported modern stack; CUDA 11.8 is a
  deployment compatibility target, not a training environment constraint.
- RF-DETR 1.11.2 and DEIMv2 revision `1d2ca42171570c713e78fc6a766ec5104b7f4724` are
  the approved upstream integration targets; native compatibility is an early gate.
- Pretrained backbone weights are used with dataset-specific Faster R-CNN detection heads.
  Missing access to a required pretrained asset is reported as an unmet gate, not hidden
  by silently accepting random initialization.
- Preserve approved `digital-metrics` and local dependency overrides. Publication is Git
  version tags only: no GitHub Release objects, release assets or registry uploads.

## Torch compatibility amendment — 2026-10-12

The user approves minimum requirements `torch>=2.13.0` and `torchvision>=0.28.0`,
with the lockfile updated to Torch 2.14.1 / Torchvision 0.29.1 and only required
transitive dependency changes. Preserve the approved local dependency revisions and
source overrides. Upstream [Torchvision 0.29.1 release notes](https://github.com/pytorch/vision/releases/tag/v0.29.1)
document the compatible pair and relaxed Torch dependency. Native operators, CPU DDP,
detector execution and applicable GPU/export acceptance must verify the updated pair.
Runtime storage follows the [file ownership amendment](../024-runtime-isolation/spec.md#file-ownership-amendment--2026-10-12).
