# Validate multirun grouping

With the documented development environment prepared, run:

```bash
uv run --frozen --no-sync pytest tests/test_multirun_tags.py tests/test_hydra_sweep_configuration.py
uv run --frozen --no-sync pytest tests/test_clearml_session.py tests/test_architecture.py
uv run --frozen --no-sync lint-imports
```

The regression matrix executes real Hydra launches with a recording task boundary
and real queue snapshot serialization. It checks shared tags, independent launches,
saved mode, one-job sweeps, user tag preservation and unchanged RUN behavior.
For an existing configured experiment, add `-m` to its normal direct command or queue
submission and filter its ClearML tasks by the new common `multirun-` tag.
These automated checks do not establish live ClearML upload or training outcomes.
