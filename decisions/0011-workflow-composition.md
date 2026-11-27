# ADR-0011 · Inject workflow capabilities once per invocation

The same use case serves a standalone command and a pipeline stage. The composition root constructs the workflow's dependency bundle and binds the selected implementations to the use case. A use case receives its storage, tracking and runtime capabilities through typed ports. Hydra keeps the serialized call separate from these live objects.

A test can exercise stage behavior through the same port contract with offline dependencies. CY can choose the dataset adapter appropriate for a detector family without leaking that choice into a user override. [Composition root](../src/clearml_yolo/entrypoints/composition.py) · [Port definitions](../src/clearml_yolo/application/ports.py) · [Entrypoint tests](../tests/test_entrypoint_composition.py)
