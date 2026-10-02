# Validation quickstart: Workspace-owned filesystem defaults

## Isolated workspace

Choose a task-owned directory. Runner cache settings are optional and remain caller-owned:

```bash
export CY_HOME="$PWD/workspace"
uv run cy-init-config "$CY_HOME/configs"
uv run cy-train --help
```

Inspect `workspace/`: application runs, Hydra outputs, the prepared CSV dataset cache, named
Ultralytics/ClearML/FiftyOne stores and owned temporary work must use the locations in
[the filesystem contract](contracts/filesystem-ownership.md). General XDG, Python, compute-library
and process temp defaults must remain unchanged. A normal exit must not leave invocation-owned
directories in `.tmp`.

Set `UV_CACHE_DIR`, `PYTHONPYCACHEPREFIX`, `TMPDIR` or other runner/library settings explicitly in
the launcher only when the validation environment itself requires broader isolation.

## Explicit destination compatibility

Select an output or cache independently of `CY_HOME` and verify it remains selected:

```bash
uv run cy-train dataset_cache_dir=/explicit/shared/cache \
  ultralytics.project=/explicit/run/output --help
```

A destination resolving physically beneath home emits a warning without failing or moving the
path. Test symlinks in both directions when validating home classification. Do not use a shared
or user-owned destination for destructive fixtures.

Also validate that `dataset_cache_dir=null` selects
`$CY_HOME/.cache/clearml-yolo/datasets` even with an ambient `XDG_CACHE_HOME`, while an explicit
`dataset_cache_dir` remains selected.

## Training source safety

Use a small ground-truth CSV with disjoint train/validation images. Run preparation and training,
then verify:

1. the complete entry is under `.cache/clearml-yolo/datasets`;
2. returned cleaned-ground-truth and native-data paths are present;
3. source CSV and images retain their original bytes;
4. a second consumer reuses the entry and waits on the same lifetime lock.

## Repository gates

Run the affected filesystem, dataset/runtime, configuration, model and training tests, then
the project gates:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
```

Validate changed Markdown and local links separately. Mocked tests establish routing and cleanup;
they do not establish native GPU execution or ClearML uploads. Use the project end-to-end skill
for those claims.
