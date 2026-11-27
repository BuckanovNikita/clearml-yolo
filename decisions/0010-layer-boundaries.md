# ADR-0010 · Keep scientific logic inside explicit import boundaries

CY combines several heavyweight SDKs with scientific code that must also run in isolation. Core owns records and algorithms. Application composes use cases and declares effect ports. Adapters implement those ports. Entrypoints assemble and invoke the workflow. The import contracts enumerate which adapter can touch each SDK and which cross-adapter edges are permitted.

Developers can check a new import against the exhaustive contract. Runtime effect ownership also requires inspection of the code that actually opens a file, creates a task or starts a process. [Architecture](../DOCS.md#architecture-and-data-flow) · [Import rules](../.importlinter) · [Application ports](../src/clearml_yolo/application/ports.py) · [Import behavior tests](../tests/test_architecture.py)
