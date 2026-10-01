# Implementation Plan: Workspace-owned filesystem defaults

**Branch**: `master` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Route automatic filesystem writes through a captured workspace while preserving every
explicit destination and protecting native source data.

> **Materialization note:** Implementation was already substantially underway when this workflow
> artifact was required. This plan describes the approved final design and remaining acceptance
> work; it does not claim that unchecked gates have passed.

## Summary

Introduce a filesystem policy module initialized by every entrypoint before execution dependencies.
Capture `CY_HOME`, set missing dependency cache/configuration/temp defaults, warn on physical-home
write targets and leave explicit paths intact. Stage native YAML datasets as locked real copies,
scope Ultralytics directory globals to the workspace, move invocation-owned temporary work into
`.tmp`, and preserve atomic replacement beside explicit outputs. Document the bootstrap boundary.

## Technical Context

**Language/Version**: Python 3.12 with the existing uv toolchain.

**Primary Dependencies**: Existing pathlib, tempfile, filelock, Hydra/hydra-zen, Ultralytics,
ClearML, FiftyOne and Loguru interfaces; no dependency revision.

**Storage**: Local workspace directories, reusable locked native dataset entries and explicit
external destinations selected by the caller.

**Testing**: pytest behavioral and subprocess write-audit tests, Ruff, strict mypy, import-linter,
Markdown/local-link validation, and existing end-to-end workflow when real execution is claimed.

**Target Platform**: Existing CLI platforms supporting process locks, symlinks where tested and
atomic rename on each selected output filesystem.

**Project Type**: Nine-entrypoint Python CLI package.

**Performance Goals**: Reuse a staged native dataset without recopying it; do not add content
hashing of source images beyond the established immutable-source assumption.

**Constraints**: Preserve explicit paths, `HOME`, user configuration, native global state,
submodules and dependency revisions. Do not claim an OS sandbox or initial interpreter-write
coverage that application code cannot enforce.

**Scale/Scope**: Startup defaults, run/cache/config/temp routing, native dataset inputs, native
runtime directories, model download paths, configuration execution copies and atomic comparison
publication.

## Constitution Check

**Before research: PASS. After design: PASS.**

- Typed pathlib interfaces and Loguru warnings follow Principle I.
- `filesystem.py` remains a low-level dependency; application entrypoints initialize it before
  expensive dependencies, and existing ClearML/task boundaries remain intact under Principle II.
- Isolated runs, explicit routing, immutable source data and restored native globals strengthen
  Principle III without changing task ownership or publication contracts.
- Behavioral tests capture workspace routing, symlink classification, native source preservation
  and cleanup. Final project gates and documentation validation remain explicit under Principle IV.
- Existing changes, user configuration and explicit destinations are preserved under Principle V.
- No constitution amendment is required.

## Research and Design

[research.md](research.md) records the decisions and rejected alternatives.
[data-model.md](data-model.md) defines workspace, destination, native-entry and temporary-resource
state. [filesystem-ownership.md](contracts/filesystem-ownership.md) maps the public compatibility
surface to the maintained [filesystem policy](../../docs/filesystem-policy.md).
[quickstart.md](quickstart.md) defines proportional validation.

## Implementation Design

### Startup and destination policy

Add a bottom-layer `filesystem.py` with workspace, warning, model-path and temporary-root helpers.
The package bootstrap selects the bytecode prefix for subsequent imports; each apps package import
then initializes dependency environment defaults. Hydra run/sweep defaults and application run
identity use the captured root. Explicit values pass through the warning helper without relocation.

### Native input and runtime isolation

Add `native_dataset.py` to resolve a native YAML, create collision-resistant copied image/label
trees and atomically publish a reusable entry under a per-entry lock held through the training
consumer. Extend `native_runtime()` to scope upstream default dataset/weight/run directories and
DDP launcher storage, then restore all globals and environment state on exit.
Copies are owner-writable while source permissions remain intact. Preserve native membership and
ordering; include resolved text-manifest membership in entry identity to capture cwd-relative
targets without hashing source image contents. NDJSON conversion honors configured native
dataset directories before staging.

### Temporary and model routing

Route resolved execution configuration copies, inference manifests, DDP relay/runtime state and
other owned temporary directories through `.tmp`. Preserve rootless native-YAML relative paths by
injecting the source parent into the execution representation only. Keep existing and explicit
checkpoints unchanged; route only absent bare `.pt` assets to the workspace weight cache.

Keep comparison partial files beside the output so `replace()` remains atomic across explicit
filesystems; cleanup stays in `finally` boundaries.

### Documentation update

Reconcile the CLI, dataset-tracking and configuration-attachment contracts; annotate superseded
historical intent without rewriting completed history. Maintain the normative policy in
`docs/filesystem-policy.md`, link it from `docs/current-contracts.md`, update README user guidance
in Russian, and update the repository end-to-end skill and prerequisites. Validate Markdown and
local links after the final code diff is known.

## Project Structure

```text
src/clearml_yolo/
├── filesystem.py
├── native_dataset.py
├── native_runtime.py
├── apps/
├── tasks/
└── comparison/

tests/
├── test_filesystem.py
├── test_native_dataset.py
├── test_native_runtime.py
└── affected integration modules

docs/
├── filesystem-policy.md
└── current-contracts.md

specs/011-workspace-filesystem/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/filesystem-ownership.md
├── checklists/requirements.md
└── tasks.md
```

**Structure Decision**: Extend the existing package and colocated test structure. Keep the
maintained normative contract in `docs/` and the feature's design and task history here.

## Complexity Tracking

No constitution deviation, new service or dependency is required. Adjacent atomic temporary files
are a deliberate exception to the workspace default because cross-filesystem rename is not atomic;
their explicit ownership and cleanup preserve the requested behavior.
