# ADR-0012 · Defer runtime initialization until a capability is invoked

CLI discovery, schema inspection and imports used by other programs should not start an experiment. The package root stays inert and heavy model SDKs load at their execution boundaries. Importing a console module does not launch its main function. Native setup and task ownership have explicit invocation lifetimes.

Fresh-interpreter tests observe imports and effects. These tests address module startup. A call that actually launches a command has its own filesystem and process contracts. [Architecture](../DOCS.md#architecture-and-data-flow) · [Package root](../src/clearml_yolo/__init__.py) · [Console import tests](../tests/test_runtime_entrypoints.py) · [Fresh-process checks](../tests/test_architecture.py)
