# Compatibility validation

Prepare approved external dependency copies as described in
[development](../../docs/development.md#external-dependencies). Preserve optional
extras already installed in the development environment.

```bash
uv lock --check
uv build
uv run --frozen --no-sync pytest
uv run --frozen --no-sync lint-imports
uv run --frozen --no-sync python -c 'from clearml_yolo.adapters.runtime.process_tree import require_process_supervision; require_process_supervision()'
```

Repeat the routine suite using a separate environment created with Python 3.13
and the frozen lockfile. Install the built wheel in separate 3.12 and 3.13 test
environments; verify wheel metadata, package origin, `cy --help`, `cy-queue --help`,
`cy-init-config --help` and the supervision probe from outside the checkout.
Use task-owned temporary roots. These checks do not claim GPU or ClearML execution.
