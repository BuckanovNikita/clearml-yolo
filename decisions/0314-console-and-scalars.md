# ADR-0314 · Journal native output before publishing it to ClearML

Native libraries and child processes can write directly to file descriptors. A network stall on a logging call could otherwise delay computation.

**Decision.** Hydra commands redirect stdout and stderr to append-only files in the invocation arena. A separate mirror renders human-readable output; scalar records append atomically as individual JSON lines. An attach-only publisher tails these journals and acknowledges flushed byte offsets to the task owner.

**Consequences.** The terminal view can render names differently from the retained raw bytes. A blocked publisher leaves the journals available and the final barrier reports uncertain delivery. CY does not automatically retransmit an uncertain stream. Raw native output can contain anything emitted by the native process.

[Capture and scalar journal](../src/clearml_yolo/adapters/observability/capture.py) · [Publication barrier](../src/clearml_yolo/adapters/clearml/console.py) · [Publisher protocol](../src/clearml_yolo/adapters/clearml/console_worker.py) · [Capture and stalled publisher cases](../tests/test_console_capture.py) · [Published telemetry](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/063b670e3ecb0ee9dca9acaffa83244f40eb76e2)
