# ADR-0008 · Resolve file-backed configuration objects in the invocation context

A file can reference values from the command configuration. Before publishing its configuration object, the owner resolves the file's fields in the invocation context and returns only the file's roots. A file root replaces the corresponding context root. Native scalar types survive a whole-value interpolation.

This boundary checks the origin of interpolated values and rejects unsafe or unresolved content before it can enter the published object. The CLI supplies the resolver to the ClearML owner. Resolution errors surface at the caller. [Resolver](../src/clearml_yolo/entrypoints/hydra/config_resolution.py) · [Publication call site](../src/clearml_yolo/adapters/clearml/session.py) · [Resolution cases](../tests/test_config_resolution.py) · [Configuration publication tests](../tests/test_configuration_publication.py)
