# Validation quickstart: Workspace-owned filesystem defaults

## Isolated workspace

Choose a task-owned directory and set runner caches before starting a cold process:

```bash
export CY_HOME="$PWD/workspace"
export UV_CACHE_DIR="$CY_HOME/.cache/uv"
export PYTHONPYCACHEPREFIX="$CY_HOME/.cache/python"
export TMPDIR="$CY_HOME/.tmp"
mkdir -p "$CY_HOME/.tmp"
uv run cy-init-config "$CY_HOME/configs"
uv run cy-train --help
```

Inspect `workspace/`: automatic runs, dependency caches/configuration and owned temporary work
must use the locations in [the filesystem contract](contracts/filesystem-ownership.md). A normal
exit must not leave invocation-owned directories in `.tmp`.

## Explicit destination compatibility

Select an output or cache independently of `CY_HOME` and verify it remains selected:

```bash
uv run cy-train dataset_cache_dir=/explicit/shared/cache \
  ultralytics.project=/explicit/run/output --help
```

A destination resolving physically beneath home emits a warning without failing or moving the
path. Test symlinks in both directions when validating home classification. Do not use a shared
or user-owned destination for destructive fixtures.

## Native source safety

Use a small native dataset with disjoint train/validation images and matching YOLO labels. Run the
native staging regression, then verify:

1. staged image and label files are real files under `.cache/clearml-yolo/native-datasets`;
2. native `.npy` and label-cache files appear only in the staged entry;
3. source YAML, images and labels retain their original bytes;
4. a second consumer reuses the entry and waits on the same lifetime lock.

## Repository gates

Run the affected filesystem, native dataset/runtime, configuration, model and training tests, then
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
