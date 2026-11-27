# ADR-0003 · Compose one executable configuration for each experiment command

Experiment commands need reproducible settings that users can inspect or override. Each command selects a packaged Hydra document and hydra-zen schemas. The user can supply a configuration directory and command-line overrides. The selected detector family determines which parameter groups are active. Required inputs remain visible as `???` in a configuration export. The launch keeps the working directory for relative inputs.

A user can inspect the resulting job with `--cfg job`. Unknown wrapper keys fail, and extra capabilities such as the workflow dependency bundle cannot be injected as overrides. [Configuration guide](../docs/configuration/README.md) · [Schema and defaults registration](../src/clearml_yolo/entrypoints/hydra/configs.py) · [Composition and precedence tests](../tests/test_release_config.py) · [Dependency injection tests](../tests/test_entrypoint_composition.py)
