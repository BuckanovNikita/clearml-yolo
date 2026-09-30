# Ground-Truth Training Validation

Use the repository environment (`uv sync --dev` after submodule initialization). The input
CSV must follow [the CLI contract](contracts/cli.md) and reference accessible local images.
Configure ClearML through the environment's supported mechanism; do not put credentials
in command examples or tracked files. Use task-owned project names, tags, and output paths.

```bash
uv run cy-init-config configs
uv run cy-train ground_truth=truth.csv dataset_format=ndjson ultralytics.device=cpu ultralytics.epochs=1 clearml.project_name=csv-validation clearml.tags='[csv-validation]'
uv run cy-train ground_truth=truth.csv dataset_format=flat ultralytics.device=cpu ultralytics.epochs=1 clearml.project_name=csv-validation clearml.tags='[csv-validation]'
uv run cy ground_truth=truth.csv dataset_format=ndjson run_dir=runs/csv-validation-ndjson ultralytics.device=cpu ultralytics.epochs=1 clearml.project_name=csv-validation clearml.tags='[csv-validation]'
uv run cy ground_truth=truth.csv dataset_format=flat run_dir=runs/csv-validation-flat ultralytics.device=cpu ultralytics.epochs=1 clearml.project_name=csv-validation clearml.tags='[csv-validation]'
```

Substitute the environment's assigned project/tag and fresh output paths. Use its capacity
and cleanup guidance before real runs. Check the displayed dropped-box total, checkpoint,
class/split identity, cleaned-CSV performance artifact, consumed dataset Configuration Object,
run-configuration overrides, validation thresholds and test metrics. NDJSON, preparation JSON,
labels and native YAML stay local.
Use a completed tagged baseline to exercise paired current-test comparison and reports.
Repeat with mixed valid/invalid boxes and backgrounds in every split. Both modes must
preserve the same valid annotations and show the same error-box count before training.

Run `uv run pytest`, `uv run ruff check .`, `uv run mypy .`, and `uv run lint-imports`.
Mocked tests establish contracts only. Use `running-end-to-end-tests` for real acceptance,
performance-artifact downloads, Configuration Object inspection and failure checks, recording
commands and results in dated evidence.
