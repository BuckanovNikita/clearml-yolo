# Feature Specification: Custom augmentation and universal mosaic

**Created**: 2026-10-23
**Status**: Approved; implementation in progress
**Baseline**: [Current contracts](../000-baseline/spec.md)

## User scenarios and acceptance

### US1 — Portable training augmentation (P1)

Users select `transforms=albumentations transforms.pipeline_file=augmentations.json`
for any registered detector. The standard Albumentations JSON determines training
augmentation. The default profile leaves native augmentation unchanged. The composed
configuration visibly lists disabled native parameters, and conflicting overrides
are disabled and reported. Validation, prediction and export preprocessing is unchanged.

### US2 — Mosaic for every detector (P1)

A first, top-level Albumentations Mosaic works for every backend, with donor count
derived from its grid. Donors come only from raw training samples. Native mosaics and
hidden batch augmentation cannot run again. Boxes, classes, crowd flags and instance
identities stay aligned, including empty images and crops removing every box.

### US3 — Reproducible real-data acceptance (P1)

All 15 registered choices (YOLO26n, four DEIMv2, four RF-DETR and six Faster R-CNN
presets) complete native smoke training/evaluation for default, JSON, and JSON+mosaic
variants on the same frozen Severstal subset. This establishes execution, not accuracy.

## Requirements

- FR-001: Preserve the default native augmentation recipe; custom mode disables all
  optional native augmentation through visible backend-specific Hydra overrides.
- FR-002: Accept one JSON file selector and standard A.save serialization. Validate
  names, parameters, targets and preprocessing conflicts with precise error paths.
- FR-003: Preserve composition probabilities/order, bbox filtering and worker/rank
  reproducibility. Normalize and tensorize exactly once after required final geometry.
- FR-004: Support one first top-level Mosaic, arbitrary valid grids and custom metadata
  keys. Sample distinct other training images when possible, otherwise with replacement;
  only a one-image dataset may use the primary as donor. Never recursively augment donors.
- FR-005: Freeze the pipeline content/hash before queue snapshots/publication. Remote
  replay and DDP cannot depend on the original JSON file or parent-process state.
- FR-006: Integrate all four native training adapters while preserving model selection,
  prediction, export, class conventions and checkpoint contracts.
- FR-007: Upgrade Ultralytics to 8.4.184 and require Albumentations >=2.0.8,<3; preserve
  approved external dependency revisions and unrelated local source overrides.
- FR-008: Convert official Severstal column-major one-based RLE to one half-open box
  per 8-connected component, without size filtering. Preserve four literal class IDs,
  background images and source/component provenance.
- FR-009: Freeze seed-0 multilabel-stratified 80/10/10 splits grouped by decoded-content
  identity; derive a 160/40/40 smoke subset with classes and backgrounds in each split.
- FR-010: Provide opt-in real-data tests for 15 choices x three variants, one epoch,
  batch one, native preset resolution, same per-preset initialization and seed zero.
  Smoke runs use FP32 so AMP loss-scale warm-up cannot consume their few updates.
- FR-011: Validate genuine optimization, finite losses, checkpoint reload, validation,
  held-out predictions and downloaded ClearML evidence; unavailable checks block release.
- FR-012: Update contracts, examples, README and portable usage skill; complete architecture
  acceptance, independent review and Git-only release after applicable checks pass.
- FR-013: Record full-data training as an independent task requiring additional user
  approval after release. Do not launch or submit it during this feature.

## Success criteria

- SC-001: Every preset's default/custom profiles compose and export correctly.
- SC-002: Synthetic geometry/conflict/replay tests and native backend tests pass.
- SC-003: All 45 real Severstal smoke scenarios produce auditable successful evidence.
- SC-004: Documentation, static checks, import contracts and final review pass.

## Decisions and exclusions

No inline alternative to the JSON file. Reject Normalize, tensor conversion, custom
executable transforms, unsupported target requirements and nested/repeated Mosaic.
User geometry is followed by required backend finalization. No minimum smoke mAP.
Official unlabeled test images are excluded from scored evaluation. Full training
waits for a later explicit approval. Dataset download/authentication is a prerequisite,
not permission to replace the requested dataset with synthetic data.

The user's explicit approved feature supersedes the old capability statement that
augmentation JSON is unsupported in constitution section III. This is a capability
extension, not a relaxation of architecture or verification principles. Per project
instructions, installed workflow and .specify files remain unchanged.
