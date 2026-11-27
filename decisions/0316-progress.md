# ADR-0316 · Expose invocation progress to local observers

A terminal, a captured log and a queue client consume progress differently. A queue-specific dependency would bind direct runs to an optional consumer.

**Decision.** Progress helpers adapt the display to terminal availability. Setting `CY_PROGRESS_FILE` selects a workspace-local JSON object. Writers merge fields such as `progress`, `iteration` and `task_url` and replace the file atomically. The terminal image-progress counter enforces the expected image population.

**Consequences.** An observer can read a complete JSON snapshot as a workflow moves from task creation into training or prediction. The file is optional. A replacement protects readers from partial writes; it does not provide a multiwriter transaction across independent invocations.

[Progress reporting](../src/clearml_yolo/adapters/observability/progress.py) · [JSON update](../src/clearml_yolo/adapters/observability/capture.py) · [Partial batches and local observers](../tests/test_console_capture.py) · [Environment setting](../docs/installation.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/d96263c2444f6d69bd5e862a7acd1c0f01f6061f)
