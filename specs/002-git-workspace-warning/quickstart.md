# Validate Git startup warnings

Use the prepared development environment and run:

```bash
uv run --frozen --no-sync pytest tests/test_git_workspace.py tests/test_architecture.py
uv run --frozen --no-sync lint-imports
```

The subprocess fixtures run actual experiment command help/config inspection from
isolated plain and Git directories, with isolated CY_HOME scratch. Expect exactly
one workspace warning on stderr outside Git, no warning inside Git, unchanged
stdout/exit status, and one warning for a two-job inert Hydra sweep. Adapter tests
cover linked worktrees, submodules, unborn/bare repositories and Git failures.
These checks do not execute models or establish ClearML publication evidence.
