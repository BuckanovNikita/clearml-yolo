# ADR-0416 · Verify advertised dependency floors separately from locked versions

An installation from Git resolves the package's declared ranges. A worktree using the lock can therefore pass with an API that its declared minimum lacks. When a direct dependency floor changes, the project calls for an isolated lowest-direct resolution on each supported Python minor alongside the locked checks.

Test the imports and entry points that actually consume the dependency. For example, the Hydra floor changed when direct configuration validation began depending on an API absent from an earlier permitted release. [Installation contract](../DOCS.md#installation-and-dependencies) · [Declared ranges](../pyproject.toml) · [Consumer](../src/clearml_yolo/entrypoints/hydra/validation.py) · [Hydra decision](https://linear.app/sip-ds-team/issue/SIP-335)
