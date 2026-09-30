# Validation Guide

Generate examples with `uv run cy-init-config <new-directory>`. Inspect both native group
files, then compose `cy --config-dir <absolute-directory> --config-name cy --cfg job`.
Verify refs, imgsz=960, compile/nms=true and prediction stage defaults. Repeat with shared
and prediction CLI overrides, including false/null where supported.

Run `uv run pytest`, `uv run ruff check .`, `uv run mypy .`, `uv run lint-imports` and
applicable pre-commit hooks. Behavioral tests capture native calls without service access.

For real checks use the running-end-to-end-tests and environment skills. Run short CSV
training and pipeline inference using the agreed compile/nms/image defaults, then paired
comparison on an explicit standalone split (default test); the pipeline uses test. Inspect local requested/effective native YAML and the run
Configuration Object's normalization record; native YAML is not a ClearML artifact. Include
explicit override runs and failure checks. Use fresh task-owned
outputs, explicit ClearML project/tags, and clean up only task-owned temporary resources.
Record commands, task IDs, outcomes and limitations in dated evidence.
