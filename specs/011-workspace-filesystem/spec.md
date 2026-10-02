# Feature Specification: Workspace-owned filesystem defaults

**Feature Branch**: `master` (feature directory is independent of the branch)

**Created**: 2026-10-01

**Status**: Implemented and verified within the scope of
[dated evidence and limitations](verification-2026-10-01.md)

**Input**: Keep automatic application writes under the launch working directory, or under
`CY_HOME` when it is explicitly selected. Preserve explicit destinations anywhere. Warn when
a write resolves physically beneath the user's home without rejecting or relocating it.

> **Workflow note:** This feature was materialized after implementation had begun. The artifacts
> record the approved behavior and remaining completion gates without rewriting earlier history.
>
> **Boundary correction (2026-10-01):** The current intent limits automatic routing to
> application-owned storage and the named Ultralytics, ClearML and FiftyOne data stores below.
> Earlier dependency-wide routing statements are superseded by this correction; dated verification
> remains evidence of what was checked before the correction, not evidence for the corrected code.
>
> **Current-only amendment (2026-10-02):** The
> [remove-legacy-compatibility feature](../012-remove-legacy-compatibility/spec.md) removes direct
> native-dataset training, native staging and the `TRAINS_CACHE_DIR` alias. CSV preparation owns
> training data, and `CLEARML_CACHE_DIR` is the supported explicit ClearML cache setting.

## Clarifications

### Session 2026-10-01

- `CY_HOME` defaults to the launch working directory. Relative `CY_HOME` is resolved against that
  directory once during startup; later working-directory changes do not move the workspace.
- Explicit command paths, dependency environment settings and configured native directories are
  valid anywhere. A physical home destination emits a warning and remains unchanged.
- Home detection follows resolved symlink targets. A path lexically below home but resolving
  outside it does not warn; a path elsewhere that resolves into home does warn.
- Existing ClearML and FiftyOne configuration may be read from home. It is not copied, rewritten
  or treated as an automatic output. Explicit FiftyOne dataset, dataset-zoo and database directory
  values remain authoritative. `CLEARML_CACHE_DIR` is the supported explicit ClearML cache setting.
- `dataset_cache_dir=null` always uses `CY_HOME/.cache/clearml-yolo/datasets`, even when
  `XDG_CACHE_HOME` is set. An explicit `dataset_cache_dir` remains authoritative.
- General XDG, Python bytecode, Torch/CUDA/Triton/Numba/Hugging Face/Matplotlib, ETA,
  FiftyOne model-zoo/plugins/config and process temporary defaults are outside workspace routing.
  Application-owned temporary resources still use `CY_HOME/.tmp` explicitly.
- CSV training preparation owns the native data reference in its reusable, locked dataset cache;
  source images are immutable until the unused cache entry is explicitly invalidated.
- Temporary comparison files remain beside an explicitly selected output to preserve atomic
  same-filesystem replacement. They are task-owned and cleaned on success and failure.
- The policy covers application-owned storage and the named dependency data stores. It is not an
  operating-system sandbox for arbitrary user scripts or plugins. Callers configure bytecode,
  runner caches and other general dependency state when broader isolation is required.

## User Scenarios & Testing

### User Story 1 - Launch in an isolated workspace (Priority: P1)

An operator starts any command in a task directory and finds automatically created runs and
application-owned temporary files in that workspace. Named Ultralytics downloads/settings,
ClearML cache/downloads and FiftyOne dataset/database storage also default there.

**Why this priority**: Automated runs must not silently populate shared user locations or collide
with another invocation's files.

**Independent Test**: Start representative application and native-runtime paths with no related
environment overrides, audit selected destinations, and verify every documented workspace default
is under the launch directory while excluded general defaults remain unchanged.

**Acceptance Scenarios**:

1. **Given** no `CY_HOME`, **When** a command starts, **Then** the launch directory becomes the
   fixed workspace root and defaults remain below it after later directory changes.
2. **Given** a relative or absolute `CY_HOME`, **When** a command starts, **Then** it resolves once
   against the launch directory and supplies the automatic run and application-owned storage roots.
3. **Given** a native worker, **When** it inherits the invocation environment, **Then** its native
   dataset, weight, run, DDP and temporary defaults use the same workspace.

### User Story 2 - Keep explicit storage choices (Priority: P1)

An operator selects an output, cache or dependency directory and the command uses it exactly,
including when it is outside the workspace.

**Why this priority**: Existing automation and shared-storage deployments depend on explicit path
selection remaining compatible.

**Independent Test**: Select explicit command and environment destinations outside `CY_HOME`,
including symlinks into and out of home, and inspect the resolved writes and warning stream.

**Acceptance Scenarios**:

1. **Given** an explicit command path or supported dependency environment value, **When** the
   destination is used, **Then** it is not overridden or relocated.
2. **Given** a write destination whose resolved target is below physical home, **When** it is first
   used in a process, **Then** one warning is emitted and the operation continues at that path.
3. **Given** an existing user configuration used as read-only input, **When** startup initializes
   defaults, **Then** that file remains unchanged and its configured directories remain selected.
4. **Given** general dependency or process cache/config/temp defaults are absent, **When** startup
   initializes application storage, **Then** those general defaults remain absent and retain their
   ordinary library behavior.

### User Story 3 - Protect CSV training sources (Priority: P1)

An operator trains from ground-truth CSV without allowing dataset preparation or native execution
to modify source images or the source table.

**Why this priority**: Native training can write beside dataset inputs; source datasets are user
data and must remain unchanged.

**Independent Test**: Prepare and train the CSV dataset, then compare all source bytes with their
originals and inspect the returned prepared paths.

**Acceptance Scenarios**:

1. **Given** a ground-truth CSV, **When** training starts, **Then** preparation publishes a complete
   reusable workspace-cache entry and returns its cleaned CSV and native data paths.
2. **Given** two invocations selecting the same CSV and format, **When** training runs, **Then**
   one cache entry is used under an exclusive lock held through training.
3. **Given** an existing explicit checkpoint path, **When** a model loads, **Then** the original
   path remains the input; an absent bare checkpoint name uses the workspace weight cache.

### User Story 4 - Clean owned temporary state (Priority: P2)

An operator completes, fails or interrupts a command without leaving its owned configuration,
inference, DDP or atomic-publication temporary files behind.

**Why this priority**: Predictable cleanup prevents stale private inputs and partial outputs.

**Independent Test**: Exercise success and injected-failure paths for configuration preparation,
inference manifests and atomic replacement, then inspect the selected temporary locations.

**Acceptance Scenarios**:

1. **Given** a resolved execution configuration, **When** it is moved to workspace temporary
   storage, **Then** its sanitized publication retains the supported source fields.
2. **Given** an atomic comparison write to an explicit output filesystem, **When** serialization or
   replacement fails, **Then** the previous output remains and the adjacent partial file is removed.
3. **Given** native runtime completion or failure, **When** its scope exits, **Then** modified native
   globals are restored and owned temporary directories are removed.

### Edge Cases

- Explicit relative command paths keep their existing command working-directory semantics.
- Remote model references and non-checkpoint strings are not rewritten as local cache paths.
- A broken or invalid existing FiftyOne JSON configuration fails explicitly without being changed.
- CSV paths resolve according to the dataset contract, and background rows remain valid negative images.
- Read-only source images remain unchanged during preparation and training.
- Startup recognizes `CLEARML_CACHE_DIR`, not `TRAINS_CACHE_DIR`, as the explicit ClearML cache selection.
- `XDG_CACHE_HOME` does not change the null CSV dataset cache default.
- Existing cache contents are neither migrated nor deleted when `CY_HOME` changes.

## Requirements

### Functional Requirements

- **FR-001**: All nine command entrypoints MUST initialize filesystem defaults before importing
  execution dependencies. `CY_HOME` MUST default to the launch working directory, and relative
  values MUST be resolved against that directory once.
- **FR-002**: Automatic run and Hydra output paths MUST use `CY_HOME`. The CSV dataset cache,
  Ultralytics downloaded datasets/weights/settings, ClearML downloads/cache and FiftyOne
  dataset/dataset-zoo/database storage MUST use their documented locations beneath `CY_HOME` when
  no explicit selection exists. Owned temporary files MUST use `CY_HOME/.tmp`.
- **FR-003**: Explicit command destinations, supported dependency environment settings and
  configured native directories MUST remain valid anywhere and MUST NOT be relocated or overridden.
- **FR-004**: A destination resolving physically beneath the user home MUST warn once per resolved
  destination per process without rejection. Home classification MUST follow existing symlinks.
- **FR-005**: Startup MUST NOT reassign `HOME`, rewrite existing user configuration or migrate or
  delete existing caches. Existing ClearML/FiftyOne configuration may remain a read-only input,
  and explicit FiftyOne data paths plus `CLEARML_CACHE_DIR` MUST be preserved.
- **FR-006**: CSV training preparation MUST own the native data reference in the shared workspace
  cache and MUST hold per-entry ownership through training. Original sources MUST remain unchanged.
- **FR-007**: Native default dataset, weight and run directories plus DDP launcher storage MUST be
  scoped to the workspace for an invocation, while explicit configured native values remain
  selected and every modified native global is restored afterward.
- **FR-008**: Resolved execution configuration copies, inference manifests and DDP relay/runtime
  files MUST use owned temporary storage and be cleaned on success, failure and interruption.
  Sanitized publications MUST retain supported source fields without temporary execution paths.
- **FR-009**: Existing explicit checkpoint inputs and remote references MUST remain unchanged.
  Only an absent bare `.pt` checkpoint name MUST select the workspace weight cache.
- **FR-010**: Atomic comparison publication MAY create its temporary file beside the explicit
  output to preserve same-filesystem replacement, and MUST clean that file on every exit path.
- **FR-011**: Startup MUST leave general `XDG_CACHE_HOME`/`XDG_CONFIG_HOME`, Python bytecode,
  Torch/CUDA/Triton/Numba/Hugging Face/Matplotlib caches/configuration, ETA state, FiftyOne
  model-zoo/plugins/config paths and generic process/tempfile defaults unchanged. Application-owned
  temporary helpers MUST select `CY_HOME/.tmp` without changing those generic defaults.
- **FR-012**: The filesystem policy MUST be documented as supported default routing rather than an
  operating-system sandbox, and must preserve arbitrary explicit destinations.
- **FR-013**: `dataset_cache_dir=null` MUST select
  `CY_HOME/.cache/clearml-yolo/datasets` regardless of `XDG_CACHE_HOME`; an explicit value MUST be
  honored.

### Key Entities

- **Workspace**: Captured absolute `CY_HOME`, launch directory and application-owned
  run/cache/Ultralytics-settings/temp roots.
- **Destination selection**: Automatic default or explicit path plus its physical home-warning
  classification.
- **Prepared dataset entry**: CSV/format/version identity, cleaned CSV, native data reference and
  lifetime lock.
- **Owned temporary resource**: Invocation-scoped file or directory with a defined cleanup owner.
- **Native runtime scope**: Selected native directories and the original global state restored on
  exit.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Startup selection auditing confirms all documented application-owned defaults use
  the selected workspace while every excluded general dependency/process default stays unchanged.
- **SC-002**: Every tested explicit output/cache/configuration destination remains unchanged; each
  physical-home target produces exactly one warning and zero rejections or relocations.
- **SC-003**: CSV preparation and training tests return required prepared paths while every
  source CSV and image byte remains unchanged.
- **SC-004**: Success and injected-failure tests leave zero owned configuration, inference, DDP and
  atomic-publication temporary files.
- **SC-005**: Repository tests, Ruff, strict mypy and import-linter pass, and changed Markdown and
  local links validate before completion is reported.

## Assumptions

- Source images are immutable while a reusable cache entry exists; corrections
  are followed by explicit invalidation when no invocation holds the entry.
- Filesystems used for shared dataset caches support process locks and atomic rename.
- External scripts, plugins, runners and the Python interpreter before package bootstrap may need
  their own cache or temporary settings.
- No dependency revision, submodule change, commit, push, cache migration or cache cleanup is part
  of this feature.
