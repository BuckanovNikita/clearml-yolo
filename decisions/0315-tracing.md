# ADR-0315 · Trace long-running operations with a bounded watchdog

A blocked SDK call or native operation may produce no log messages while a user is deciding whether the experiment is still active.

**Decision.** `LOGURU_LEVEL=TRACE` enables operation start, completion, failure and interruption events. A process-local watchdog samples active operations and writes heartbeats and bounded, changed stack snapshots through a separate stderr descriptor. Context fields are allow-listed and redacted.

**Consequences.** Sampling intervals do not terminate operations. Watchdog output identifies source locations without inspecting local variables. Tracing is inert at other levels and does not establish task success. Failure and cancellation keep their original meaning.

[Operation and watchdog rules](../src/clearml_yolo/adapters/observability/tracing.py) · [Lifecycle and watchdog tests](../tests/test_tracing.py) · [Environment setting](../docs/installation.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/8ca7d6bc37a0a28ba2c53eeb73c0b9d51ab58a99)
