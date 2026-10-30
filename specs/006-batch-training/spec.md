# Feature Specification: Batch estimation and native distributed training

**Created**: 2026-10-26

**Status**: Implementation in progress

**Input**: Implement the supplied batch estimation, multi-GPU training, FCOS and
self-contained configuration export plan. Baseline: [stage zero](../000-baseline/spec.md).

## User Scenarios & Testing

### User Story 1 — Measure and reuse training capacity (Priority: P1)

An operator measures per-GPU training capacity for supported pretrained models once
per resolution, training profile and distinct GPU type/capacity, then receives measured
or explicitly extrapolated recommendations for selected allocations. `batch=null`
opts training into a compatible recommendation.

**Independent test**: bounded synthetic trials produce versioned results; training
selects only a compatible successful result after inspecting its dataset and devices.

1. Given a hardware group needing measurement, estimation probes the first idle
   selected GPU, using five warm-up optimizer updates and ten measured updates,
   then independently repeats the winner on one GPU. Identical GPUs share evidence;
   other selected GPUs may remain busy.
2. Given an existing compatible case, rerunning reuses it unless `--refresh` is present.
3. Given no compatible exact-allocation measurement, lookup derives N times the
   smallest compatible single-GPU capacity across all target hardware groups. Missing,
   failed, stale or incompatible required sources stop null-batch training with
   actionable instructions; explicit numeric batches retain existing behavior.
4. Given a queue submission containing null, only its executing worker resolves it.
5. Given requested output counts, reporting derives the first N selected allocations
   without distributed probes or confirmation. Extrapolated totals may exceed the
   per-GPU ceiling and never claim measured multi-GPU maxima.
6. Given discovery-time nonfinite computation after a fully successful under-budget
   candidate, repeat that last good batch once in a fresh process. Only a full
   successful repeat yields usable `numerically_limited`; preserve the failed
   numerical trial and diagnostic without claiming a memory upper bound or maximum.
   First-candidate numerical failure, every failed confirmation and other failures
   retain no recommendation.

### User Story 2 — Train native detectors across GPUs (Priority: P1)

Users train DEIMv2, RF-DETR, Faster R-CNN and FCOS with a global microbatch divisible
by the selected world size. Accumulation remains a separate effective-batch multiplier.

**Independent test**: distributed ranks shard training, synchronize optimization/EMA,
evaluate each validation example once, and leave one checkpoint and publication owner.

1. Given multiple GPUs, one worker per GPU executes outside the invocation owner.
2. Given a rank OOM/crash, timeout or cancellation, owned peers terminate within a
   bounded interval and a later trial succeeds without leaked processes.
3. Given training completion, inference and queue handoff retain the first GPU.

### User Story 3 — Use all six FCOS backbones (Priority: P1)

FCOS offers ResNet-50/101 FPN, ConvNeXt-Tiny, Swin-Tiny, DINOv2-Small and DINOv3-Small
at default resolution 800, with pretrained backbones and newly initialized heads.

**Independent test**: each preset supports finite loss/backward, checkpoint round trips,
prediction, validation, comparison, augmentation, publication and estimation.

1. Foreground class zero survives training, prediction and checkpoint recovery.
2. FCOS uses P3–P7 and compatible anchors; existing Faster R-CNN behavior is preserved.
3. Deployment export remains restricted to its existing Faster R-CNN scope.

### User Story 4 — Export complete editable configurations (Priority: P1)

Fresh exports include the selected command base and the transitive application,
model and augmentation YAML dependencies. Existing local files keep precedence.

**Independent test**: fresh trees compose with packaged application defaults disabled
and schema warnings treated as errors; legacy trees and invalid values remain tested.

1. Public YAML names and registered schema names do not collide.
2. Interpolation, CLI overrides, multiruns, collision protection and `--force` survive.
3. Existing generated trees work without automatic rewriting.

### Edge Cases

Heterogeneous GPU capacities, visibility remapping, external workload contamination,
confirmed CUDA OOM versus runtime errors, nonfinite losses, missing assets, interrupted
writes, stale versions, unsupported custom recipes, dense real datasets, search ceilings,
failed winner repetition, and orphaned distributed workers must fail or report explicitly.

## Requirements

- **FR-001**: `cy-batch-estimate` defaults to 150 classes, 300 objects per image, 90%
  memory per GPU, per-GPU search ceiling 1024, five warm-up and ten measured steps.
  Extrapolated global batches may exceed the search ceiling.
- **FR-002**: Model/device/count filters, refresh, memory budget, search ceiling and
  trial timeout are explicit options. Default coverage includes the intended 44 YOLO
  pretrained variants, all existing native presets and six FCOS presets. `--devices`
  selects hardware; `--gpu-counts` filters output over the first N selected GPUs.
  Search runs once per model/resolution/profile and distinct GPU name/total-memory
  group, using its first idle selected representative only when measurement is needed.
- **FR-003**: Exponential growth and binary refinement measure real forward, loss,
  backward, optimizer, EMA and bounded validation in fresh supervised processes.
  Every trial uses exactly one GPU. Probe maximum effective native resolution and
  both YOLO auto-optimizer paths; never launch distributed probes or confirmation.
- **FR-004**: Save atomic versioned JSON under `CY_HOME/.config/clearml-yolo/`, retaining
  successful/failed cases, global/per-GPU batches, diagnostics and provenance.
  Preserve stored trial evidence and legacy records; derive extrapolations only at
  lookup/report time, without manufacturing measured cases or trials. Read schema 1;
  normal saves write schema 2 and require upgraded readers. Read-only access never
  rewrites files. Pending snapshots remain failed with null batches and a diagnostic
  that confirmation is pending, whether the search is active or interrupted.
- **FR-005**: Compatibility covers architecture, nominal/effective resolution, hardware
  types/capacities, dependencies, precision, compilation, optimizer, accumulation,
  EMA and augmentation. Real class count and maximum object density fit synthetic bounds.
  Prefer a compatible exact ordered allocation/count measurement; otherwise require
  compatible single-GPU measurements for every target type/capacity and use
  `global_batch = N × min(per_gpu_capacities)`. Identical hardware shares one source.
  Never extrapolate across unmeasured hardware; global batch remains divisible by N.
  Exact lookup and extrapolation retain source diagnostics and status precedence:
  `numerically_limited`, then `ceiling_limited`, then `validated`.
- **FR-006**: Null selects an estimate only during training, after dataset/device
  resolution; requested null remains in replay and chosen provenance is separate.
  A typed recommendation records measured/extrapolated origin, target allocation,
  source estimate keys, global/per-GPU batches, source boundary/ceiling/numerical
  status and retained diagnostics.
  Explicit batches and worker-side queue resolution are preserved. Normal training
  failure behavior remains: no automatic OOM retry or hidden batch reduction.
- **FR-007**: Native distributed training has global microbatch semantics, supervised
  rank lifetime, owner-only publication and correct synchronization/sharding.
- **FR-008**: FCOS is a distinct backend with six backbones and zero-based labels;
  shared Torchvision machinery preserves Faster R-CNN's label offset and public behavior.
- **FR-009**: Fresh configuration exports are self-contained and warning-free with
  explicit schemas; legacy configuration and ordinary validation remain compatible.
- **FR-010**: Core/application policy is pure; adapters own GPU discovery, SDKs, processes
  and storage behind explicit interfaces. Executable boundaries include negative tests.
- **FR-011**: Documentation, canonical verification, applicable mutation, paired latest
  CY/queue checks, native acceptance and fresh independent review precede release.
- **FR-012**: Recover discovery-time nonfinite computation only by one fresh repeat
  of the last fully successful under-budget candidate. Every required native
  optimizer path, update, validation and memory check remains mandatory. A full
  successful repeat yields `numerically_limited`, retaining failed trial and
  diagnostic without establishing a capacity maximum or numerical memory bound.
  Numerical failure before any success and every failed confirmation remain failed;
  other failures abort. This does not fix the underlying native numerical cause.

### Key Entities

Training profile, GPU identity, synthetic workload, trial request/result, estimate case,
saved catalogue, resolved recommendation, selected-batch provenance and distributed
training request/result.

## Success Criteria

- **SC-001**: Real single-GPU searches and automated extrapolation checks replace the
  exhaustive estimator multi-GPU matrix. Checks cover identical/mixed hardware,
  missing/stale/failed sources, ceilings, refresh, provenance, assigned queue allocations
  and divisibility, and prove every trial launches one GPU regardless of output counts.
  Failures, ceiling-limited and numerically limited measurements remain visible;
  derived recommendations are explicitly extrapolated and never masquerade as measured multi-GPU maxima.
- **SC-002**: Incompatible estimates never silently influence training.
- **SC-003**: Real multi-GPU evidence exists for every supported training backend before
  distributed acceptance; unavailable hardware is an explicit acceptance gap.
- **SC-004**: All six FCOS presets preserve class zero and pass native round trips.
- **SC-005**: Fresh and legacy configuration tests pass with schema warnings as errors.

## Assumptions

The supplied plan authorizes implementation and the established Git-only release after
acceptance. Existing numeric defaults and approved dependency revisions remain fixed.
No deployment, package publication or unrelated workload intervention is authorized.
Saved values are recommendations for the recorded workload, not arbitrary-dataset guarantees.

## Single-GPU amendment

The 2026-10-27 simplification supersedes the original estimator count-matrix search
and acceptance requirement. Separate real multi-GPU training correctness gates remain
in SC-003. Earlier dated verification records retain their historical meaning.
