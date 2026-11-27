# ADR-0317 · Keep GPU scheduling in cy-queue

Direct CY workflows accept a native device selection. Concurrent admission and GPU reservation involve a separate package with a different ownership lifetime.

**Decision.** CY rejects legacy queue/autogpu settings and the cy-queue Hydra launcher. Its supported [sweep](0007-sequential-sweeps.md) uses Hydra's sequential launcher. The separate cy-queue package depends on CY and calls its admission validators; the shared one-argument validation interface is a compatibility boundary.

**Consequences.** A user who wants scheduling submits through cy-queue. A direct job can still exchange [progress](0316-progress.md) with an external observer. CY-side rejection tests cover CLI behavior. Cross-package compatibility requires the paired check against both proposed versions.

[Admission and wrapper validation](../src/clearml_yolo/entrypoints/hydra/validation.py) · [Legacy control cases](../tests/test_execution_controls.py) · [Direct execution scenarios](../tests/test_direct_execution.py) · [Queue guide](../docs/queue.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/ad6a8ec81901801c7bb434beed67405da81551ab)
