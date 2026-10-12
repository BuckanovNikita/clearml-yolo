# Validation quickstart: Workspace-owned filesystem defaults

> Current execution and configuration are amended by feature 024. Use the maintained
> [GPU quickstart](../022-simple-gpu-wait/quickstart.md),
> [runtime isolation](../../docs/runtime-isolation.md) and
> [filesystem policy](../../docs/filesystem-policy.md); original feature checks below
> do not establish current acceptance.

## Project workspace and ordinary SDK configuration

Choose a task-owned directory. Runner cache settings are optional and remain caller-owned:

```bash
export CY_HOME="$PWD/workspace"
uv run --frozen --no-sync cy-init-config "$CY_HOME/configs"
uv run --frozen --no-sync cy-train --help
```

Inspect `workspace/`: project runs, Hydra outputs, the CSV dataset cache and invocation
arenas must follow [the filesystem contract](contracts/filesystem-ownership.md). SDK stores
and settings remain selected by normal environment/user configuration, including paths
outside `CY_HOME`. XDG, bytecode, cwd configuration discovery and global temp defaults remain
unchanged. Project temporary callsites pass their directory explicitly.

Trace SDK reads from normal selected user settings. Reuse earlier project-local config/cache
files only through explicit SDK selectors; verify no migration/deletion or synthesized config.
Inspect retained arenas after success, failure and cancellation, including overlapping
invocations and children starting after parent scope exit. Startup must perform no scans,
recovery or recursive cleanup. Remove selected old scratch only during deliberate maintenance
with an idle workspace and descendants. Shared GPU coordination remains outside scratch.

## Explicit destination compatibility

Select an output or cache independently of `CY_HOME` and verify it remains selected:

```bash
uv run --frozen --no-sync cy-train dataset_cache_dir=/explicit/shared/cache \
  ultralytics.project=/explicit/run/output --help
```

A destination resolving physically beneath home emits a warning without failing or moving the
path. Test symlinks in both directions when validating home classification. Do not use a shared
or user-owned destination for destructive fixtures.

Also validate that `dataset_cache_dir=null` selects
`$CY_HOME/.cache/clearml-yolo/datasets` regardless of an external `XDG_CACHE_HOME`, while an explicit
`dataset_cache_dir` remains selected.

## Training source safety

Use a small ground-truth CSV with disjoint train/validation images. Run preparation and training,
then verify:

1. the complete entry is under `.cache/clearml-yolo/datasets`;
2. returned cleaned-ground-truth and native-data paths are present;
3. source CSV and images retain their original bytes;
4. a second consumer reuses the entry and waits on the same native lifetime lock;
5. invalid existing entries and peer staging remain untouched, with invalid entries causing
   an actionable error requiring idle-cache maintenance;
6. unsupported native locks and acquisition failures fail without a soft-lock fallback.

Verify native ClearML switches and callbacks restore in memory without settings-file writes,
including trainer construction and training in fresh DDP interpreters.

## Repository gates

Run the affected filesystem, dataset/runtime, configuration, model and training tests, then
the project gates:

```bash
uv run --frozen --no-sync pytest
uv run --frozen --no-sync ruff check .
uv run --frozen --no-sync mypy .
uv run --frozen --no-sync lint-imports
```

Validate changed Markdown and local links separately. Mocked tests establish routing and ownership;
they do not establish native GPU execution or ClearML uploads. Use the project end-to-end skill
for those claims.
