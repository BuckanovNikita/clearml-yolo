# Implementation Plan: Custom augmentation and universal mosaic

**Date**: 2026-10-23 | **Specification**: [spec.md](spec.md)

## Technical context and architecture

Use Python >=3.12.13,<3.14, existing uv/Ruff/strict mypy/pytest/import-linter tooling,
and the approved Spec Kit workflow. The only initial unrelated modification is the
local tool.uv.sources section. Preserve it exactly and never change approved external
source revisions. [architecture.json](architecture.json) records affected boundaries.

- Core owns validated transform selectors and immutable JSON snapshot. Hydra owns
  visible native disable policy. It imports no SDK and performs no file/network/process effects.
- adapters/augmentation owns file validation, Albumentations construction, RGB/xyxy
  raw samples, donor sampling, label metadata and returned empty-target samples.
- Backend adapters own raw reads and final conversion into native model inputs.
  Integrations thread explicit typed configuration into owned YOLO/DDP trainers and
  non-YOLO runners; no process-global monkeypatch or upstream source edit is permitted.
- Hydra composition owns default/custom profiles and root model/profile specialization.
  Custom specializations write actual disabled values only for the selected backend.
  File resolution occurs before queue serialization and after remote replay overrides;
  canonical configuration carries the immutable snapshot. Application functions remain
  SDK-free and receive capabilities through dependency composition.
- Severstal test tooling owns authenticated input preparation, RLE conversion, split
  manifests and native acceptance runs. Raw data and machine paths remain untracked.

## Shared interfaces and ownership

Core module `core/transforms.py` exposes TransformConfig(mode, pipeline_file, snapshot),
TransformSnapshot(pipeline, sha256, source), and pipeline_digest. Native-disabled
parameter mappings live at the Hydra composition boundary.
Snapshot pipeline is a JSON-compatible mapping; hash validation detects inconsistent
replay. Native mode prohibits a pipeline selector/snapshot. Custom mode requires a
file or an already frozen snapshot; file loading belongs to the outer adapter.

`adapters/augmentation/pipeline.py` exposes DetectionSample(image, boxes, labels,
instance_ids, iscrowd), TrainingPipeline(snapshot, seed), and
`apply(sample, *, index, size, load_sample, seed)` returning DetectionSample.
The callable load_sample(index) returns a fresh raw sample; size is training population
size, not image shape. Arrays are RGB uint8, absolute xyxy float32, and integer label,
identity/crowd vectors. The adapter preserves label alignment and reconstructs the
requested bbox format internally. A returned sample may have zero boxes.

The shared owner may refine exact signatures before dependent backend implementation;
record changes here and notify all owners before integration. Parent owns Hydra,
composition, YOLO, dependencies, import contracts, native integration and documentation.
Shared worker owns core/transforms and adapters/augmentation with dedicated tests.
Backend worker owns DEIM/RF-DETR/Faster R-CNN integration and their focused tests.
Dataset worker owns scripts/severstal.py and dedicated preparation/native test helpers.
Workers preserve others' changes and do not delegate. Fresh review follows integration.

## Sequence and verification

1. Specify/plan/tasks/analyze and validate architecture planning record.
2. Upgrade dependencies and check existing native configuration/training boundaries.
3. Implement shared contract and test-first pipeline; independent dataset work may run
   concurrently. Backend bridges depend on the agreed shared interface.
4. Integrate visible Hydra policies, snapshots, YOLO/DDP and other backends.
5. Run focused and complete tests, Ruff, mypy, Vulture, lint-imports, architecture tests,
   dependency-floor checks, generated config checks and documentation validation.
6. Execute 45 isolated native Severstal smoke scenarios and download publication evidence.
   Authentication failures and unavailable native outcomes remain acceptance gaps.
7. Reconcile diff/architecture/checks, obtain fresh independent review, update portable
   usage source, validate architecture acceptance, then follow native commit/tag/push.

## Documentation

Update README.md in Russian, docs/multi-model-backends.md, current/project contracts,
baseline affected capability guidance, and add an augmentation guide/examples.
Update corp-skills/skills/clearml-yolo source usage/evaluation references and validate
that package under its maintenance contract. Preserve historical evidence and installed
workflow assets. The independent [full training task](full-training-task.md) stays pending.


## Native acceptance refinement, 2026-10-24

The harness accepts repeatable `--severstal-backbone MODEL=PATH` selectors for
DEIM/Faster R-CNN so gated/offline native assets can be supplied consistently across
all three variants. This extends test configuration only: existing backend asset
validation and pretrained initialization remain authoritative. The test fixture owns
local-file validation; the scenario composer forwards the selected explicit input.
