# Research: Workspace-owned filesystem defaults

> **Historical research note (2026-10-01):** Decisions 1, 4, 5 and 6 below describe the original
> broad-routing design that informed the completed implementation and dated checks. The approved
> boundary was subsequently narrowed by Decision 7. These sections are retained as historical
> reasoning and must not be read as the current contract where they conflict with Decision 7 or
> [the maintained filesystem policy](../../docs/filesystem-policy.md).

## Decision 1: Capture one workspace root at startup

Use `CY_HOME`, defaulting to the launch working directory, as the root for automatic application
and dependency paths. Resolve a relative selection once before dependency imports. Environment
defaults are inherited by native workers.

**Rationale**: A stable root prevents later Hydra or library working-directory changes from moving
automatic outputs. Environment configuration reaches dependencies without importing them early.

**Alternatives rejected**:

- Reassigning `HOME` would redirect read-only user configuration and unrelated libraries.
- Re-evaluating `Path.cwd()` at every call would make defaults depend on later directory changes.
- Rejecting every path outside the workspace would break explicit outputs and shared caches.

## Decision 2: Preserve explicit destinations and warn on physical home writes

Apply default values only when the corresponding command option or environment setting is absent.
Before a known write, resolve the selected path and warn once when the physical target lies below
the physical home directory. Do not reject, relocate or override it.

**Rationale**: Explicit selections are part of the public compatibility contract. Physical
resolution describes where bytes land and handles symlinks in both directions.

**Alternatives rejected**:

- Lexical path checks misclassify symlinks.
- A hard error would prohibit intentional home-resident destinations.
- Silent relocation would violate explicit configuration and could separate related files.

## Decision 3: Stage native YAML datasets as real copies

Resolve the native dataset definition, derive a stable entry identity, copy each selected image
and matching label into `CY_HOME/.cache/clearml-yolo/native-datasets`, and hold a per-entry lock
through training. Publish a YAML whose root names the final cache entry.

Preserve native source ordering, duplicate entries and manifest path semantics. Include resolved
text-manifest membership in the identity because bare relative entries depend on the launch
directory. Make staged copies owner-writable without changing source permissions. Preserve
configured native dataset directories when converting NDJSON/platform references.

**Rationale**: Ultralytics may repair JPEGs and write `.npy` or label caches beside inputs.
Symlinks, read-only wrappers or configuration-only copies do not isolate those writes.

**Alternatives rejected**:

- Training against original inputs risks source mutation.
- Copying only YAML leaves image and label directories writable by the native runtime.
- Releasing the lock after staging permits concurrent native cache/repair writes.

## Decision 4: Scope native globals and restore them

During native execution, replace only upstream default dataset, weight and run directories with
workspace paths. Preserve explicitly configured values. Point the DDP launcher configuration at
an invocation-owned directory and restore settings, module globals and callback objects in a
`finally` boundary.

**Rationale**: Ultralytics caches path objects and global settings in multiple modules. Updating
the environment alone cannot constrain an already imported runtime.

## Decision 5: Move owned temporary work to `.tmp` while preserving semantics

Use workspace temporary directories for resolved execution configurations, inference manifests,
native runtime files and DDP relay data. When moving a rootless native dataset YAML, add its source
parent only to the unredacted execution copy. Keep sanitized publication fields unchanged.

Atomic comparison publication remains adjacent to the output because atomic replacement requires
source and destination on one filesystem. Cleanup owns the adjacent temporary file on every path.

**Rationale**: Workspace ownership and source-relative YAML semantics can coexist when execution
and publication representations remain distinct.

## Decision 6: Document the bootstrap boundary

Set the process bytecode prefix in the package bootstrap for subsequent imports. Document
`PYTHONPYCACHEPREFIX` and `PYTHONDONTWRITEBYTECODE` for launchers that must cover the interpreter's
first package import. Treat external runners and arbitrary plugins as separate processes requiring
their own settings.

**Rationale**: Application code cannot retroactively redirect an import cache written before that
code runs. Describing an OS sandbox would overstate the enforceable boundary.

## Decision 7: Limit workspace routing to application-owned storage (current)

Retain workspace defaults for runs and Hydra outputs; CSV/native dataset caches; Ultralytics
downloaded datasets, weights and settings; ClearML downloads/cache; FiftyOne dataset,
dataset-zoo and database directories; and application-owned temporary resources. A null
`dataset_cache_dir` always selects `CY_HOME/.cache/clearml-yolo/datasets` and ignores ambient XDG.

Leave general XDG, Python bytecode, Torch/CUDA/Triton/Numba/Hugging Face/Matplotlib, ETA,
FiftyOne model-zoo/plugins/config and generic process/tempfile defaults untouched. Preserve all
explicit destinations, including FiftyOne configuration data paths and ClearML's legacy
`TRAINS_CACHE_DIR` alias. Continue reading existing home configuration without rewriting it.

**Rationale**: `CY_HOME` is an ownership boundary for this application, not a replacement home or
a blanket policy for shared libraries. Directly selecting owned paths keeps cleanup and location
predictable without changing unrelated library behavior in the hosting process.

**Migration decision**: Do not migrate or delete data created under the earlier defaults. The
corrected defaults apply to subsequent process startup only.
