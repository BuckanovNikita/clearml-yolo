# Data model: Multi-model detection backends

Project-owned records use Pydantic and serializable primitives. Native SDK objects remain
inside adapters. These records extend existing contracts rather than introducing a database.

## Model selection

- `backend`: one of `ultralytics`, `deimv2`, `rfdetr`, `fasterrcnn`.
- `preset`: a registered preset within the selected backend.
- `source_dir`: optional external source directory, required for DEIMv2 execution.
- `train` / `predict`: typed settings owned by that backend, including requested device,
  batch and relevant native recipe controls. YOLO retains authoritative legacy groups.
- Validation: **Unknown backend/preset combinations and unsupported settings fail explicitly.**
  A new-family setting must never be silently accepted as a YOLO argument.

## Class vocabulary and prepared data

- Ordered public class names; deterministic backend category IDs; background offset where
  required; source split membership and original image dimensions/coordinates.
- Prepared paths, output format, source fingerprint, format/version and vocabulary identity
  contribute to cache identity. Canonical CSV source IDs remain recoverable.
- Validation: **Public labels remain exact strings; background is not a public class.**
  Empty images are represented with no instances, not fabricated boxes.
- Dataset lifecycle: validate CSV → prepare deterministic derived records/cache → train or
  predict → retain durable cache and remove only task-owned temporary files.

## Checkpoint descriptor

- Schema version, backend, preset, ordered class mapping, preprocessing contract,
  upstream/dependency revision, selected checkpoint hash and source model/task lineage.
- The descriptor references one checkpoint; local persistence and remote publication must
  preserve this association. The checkpoint remains the vocabulary source of truth.
- Validation: **Descriptor/checkpoint hash or backend/preset disagreement fails before execution.**
  Existing project checkpoints without a descriptor retain YOLO behavior. Explicit model
  reference backend/preset overrides identify raw external checkpoints, not conflicting
  already-described project checkpoints.
- Lifecycle: training selection → descriptor binding → owner publication → fresh download
  → descriptor validation → native backend loading.

## Execution phase and device provenance

- Phase kind: train, predict or export; enabled flag; setting path; requested device;
  CPU/GPU demand derived from native configuration; effective child-local device after admission.
- Preserve admitted GPU identities/order, capacity and released replay policy; phase
  descriptions must be inspectable without importing the corresponding SDK.
- Validation: **No SDK import, CUDA initialization or task creation occurs before admission.**
  CPU-only graph export has zero GPU demand; build and GPU verification each demand one GPU.
- Lifecycle: describe → admit/wait → remap → execute → reap owned descendants → contract
  reservation → flush publications → close task and clean invocation scratch.

## Export request and bundle

- Operation: `onnx`, `build` or `verify`; Faster R-CNN selection; source weights where
  required; output directory; selected precision/device; ONNX or engine input for later phases.
- Profiles contain min/opt/max NCHW shapes and valid-image size contract. Metadata records
  checkpoint/graph/engine hashes, normalization, class mapping, precision, operator/plugin
  versions and build environment sufficient to reproduce or reject an incompatible load.
- Validation: **Batch is an integer from 1 through 4; shapes must fit one complete profile.**
  `onnx` requires weights; `build` requires ONNX and metadata; `verify` requires engine,
  metadata, native weights and labeled ground truth. GPU operations reject CPU devices.
- Lifecycle: validate source → export graph/metadata → build engine/report → standalone
  inference → native comparison/evidence → owner artifact upload/flush.

## Verification record

- Bound checkpoint, graph/engine, preprocessing, dataset membership/labels and evaluator
  identities; environment and precision; tested shapes/batches; available raw comparisons;
  class-aware detection matches; mAP50–95 deltas, per-class recall, timing and memory.
- Validation: **An all-empty or all-zero native reference does not satisfy the quality gate.**
  Reports distinguish passed, failed and unexecuted checks and record local versus target
  deployment evidence separately. Aggregate mAP tolerance is not a raw-output tolerance.
