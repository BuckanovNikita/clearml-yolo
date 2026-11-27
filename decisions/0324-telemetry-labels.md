# ADR-0324 · Render readable identifiers consistently across output surfaces

Encoded identifiers and colliding model labels make it hard to follow the same experiment in terminal output, scalar series and comparison tables.

**Decision.** The presentation layer renders recognized opaque IDs and hashes as names or semantic labels for people. A series registry assigns stable display labels for the life of an invocation. The terminal mirror and console worker use streaming conversion so identifiers split across read chunks can be rendered consistently.

**Consequences.** Scientific record identities and raw captured bytes remain available. Human-readable aliases can gain a distinguishing suffix when two raw labels render alike. Numeric columns retain their data types in reported tables.

[Presentation rules](../src/clearml_yolo/core/presentation.py) · [ClearML adapters](../src/clearml_yolo/adapters/clearml/report.py) · [Readable output cases](../tests/test_readable_output.py) · [Table alias cases](../tests/test_clearml_report.py) · [Telemetry reference](../DOCS.md#diagnostics) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/8ca7d6bc37a0a28ba2c53eeb73c0b9d51ab58a99)
