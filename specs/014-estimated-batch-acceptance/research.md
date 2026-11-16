# Research decisions

- **Decision**: Use explicit recipe-bearing probes, retaining the existing synthetic
  capacity search. **Reason**: the old profile rejected custom augmentation and the
  worker reconstructed defaults, invalidating FP32/JSON/Mosaic equivalence.
  **Rejected**: standard editable-table lookup for acceptance or profile hashing alone.
- **Decision**: Execute the selected custom pipeline on synthetic RGB/box inputs while
  GPU training is resident, retaining a conservative target population and native
  deterministic finalization. **Reason**: actual augmentation must not be skipped;
  random filtering cannot justify a smaller target-memory envelope.
- **Decision**: Add an optional generic reserve, default zero. **Reason**: the campaign's
  8 GiB reservation is execution policy, not a new global estimator restriction.
- **Decision**: Fresh per-case measurement, explicit raw/chosen batches, no fallback.
  **Reason**: frozen recipes and current resource state must match the ensuing run.

- **Decision**: Fixed-recipe acceptance captures batch/epoch requirements in the owned
  native trainer class, including its serialized form. **Reason**: the pinned YOLO
  loop retries first-epoch OOM with halved batches and may repeat NaN epochs; acceptance
  must fail before those retries. Ordinary training is unchanged; its documented
  no-retry discrepancy is tracked separately by the coordinator as ticket 94.
- **Decision**: Apply an optional Torch allocator cap with a 256 MiB cushion, but treat
  whole-device monitoring as authoritative. **Reason**: external and non-Torch native
  allocations cannot be bounded by the allocator cap. A breach leaves incomplete
  evidence and stops owned processes; this is not a hard reservation guarantee.
- **Decision**: Require custom capacity pipelines to preserve measured shape and carry
  their source hash independently from source-file location. Include augmentation
  implementation and Albumentations version in compatibility identity. Native DEIM
  normalization comes from the pinned configuration; RF-DETR normalization and native
  Torchvision/YOLO finalization remain in their adapter boundaries.

- **Decision**: Offer an explicit reusable acceptance home whose descendants contain
  per-case artifacts. **Reason**: fresh homes otherwise repeat CY-managed DEIM source
  and backbone preparation despite shared native caches. The product catalogue still
  executes against its verified cache. Per-case temporary roots and cleared inherited
  arenas preserve cleanup ownership; shared assets/receipts remain campaign-owned.

- **Decision**: Supervise each acceptance case through `IndependentWorkerPool`, with
  estimation workers nested inside it. **Reason**: the distinct case owner marker
  remains inherited when native probes install their worker markers, so detached
  descendants remain attributable during cancellation. Process-group-only cleanup
  is insufficient. The existing case boundary passed real escalation/reaping tests
  while preserving an unrelated sibling; no product supervisor policy was changed.
