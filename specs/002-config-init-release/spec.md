# Feature Specification: Configuration examples and 0.3.0 publication

**Feature Directory**: `specs/002-config-init-release`
**Branch**: `master`
**Created**: 2026-09-28
**Status**: Implemented, verified, and published as v0.3.0
**Input**: Restore `cy-init-config`, remove all current future-annotations imports,
document all changes through Spec Kit, commit, push, and make a release.

**Post-release amendment (2026-09-28)**: This feature remains the historical record for the
v0.3.0 initializer and publication. The later
[native configuration specification](../003-ultralytics-config-groups/spec.md) supersedes its
sparse-native-setting details: initialization now writes eight command examples plus
`ultralytics/default.yaml` and `ultralytics_predict/default.yaml`; model commands use those
top-level groups and reject raw/non-null `cfg`. The maintained package version is declared in
[pyproject.toml](../../pyproject.toml).
The original FR-002 intentionally required sparse native settings; that historical choice and
its rationale remain in the [research record](research.md), while the linked later feature
defines the current replacement.

This specification records the implemented changes retrospectively and governed the completed
release work. It supersedes the configuration-generation removal and non-publication scope
of [001-release-030](../001-release-030/spec.md). The user explicitly expanded publication
scope to include the concurrent dependency-source and shared-skill changes. Dependency
source code and pinned revisions stay unchanged; removed execution automation stays removed.

## User Scenarios & Testing

### User Story 1 - Start from editable examples (Priority: P1)

A practitioner initializes a directory and edits an example for the pipeline or an individual
stage instead of reconstructing the available settings manually.

**Why this priority**: Restore the requested starting point for configuring experiments.
**Independent Test**: Generate examples without service credentials and load each with its
corresponding installed command.

**Acceptance Scenarios**:

1. Given a missing destination, initialization creates its parents, eight command examples,
   and two native group files.
2. Given an existing example, initialization fails before writing any examples unless the
   user explicitly requests replacement. Unrelated files always remain intact.
3. Given generated examples, all eight execution commands load their defaults and accept
   user-supplied required inputs and native overrides.
4. Given no ClearML credentials, initialization succeeds without creating an experiment.

### User Story 2 - Use explicit annotation evaluation (Priority: P1)

A maintainer removes the prohibited future import from all first-party Python code while
keeping imports, validation, configuration composition, and tests operational.

**Why this priority**: Apply the user's coding convention throughout the current project.
**Independent Test**: Scan project Python sources and run the existing test and typing checks.

**Acceptance Scenarios**:

1. No first-party source or test file contains the prohibited import.
2. Self references and third-party generic annotations remain safe when modules load.
3. Existing runtime behavior and strict checking remain intact; dependency source code is unchanged.

### User Story 3 - Obtain a documented release (Priority: P2)

A user can inspect the specification, implementation decisions, completed work, verification
evidence, migration notes, and downloadable packages for the published version.

**Why this priority**: Make the requested changes reproducible and available from the repository.
**Independent Test**: Match the published tag to the pushed commit and verify release assets.

**Acceptance Scenarios**:

1. Current contracts and the constitution agree with the implemented behavior.
2. Both package distributions install in fresh environments and expose nine working commands.
3. The release points to the verified commit and includes packages, checksums, and migration notes.
4. Verification records distinguish current results, historical live evidence, and unavailable gates.
5. A recursive checkout installs pinned editable dependencies; package users can install the
   same upstream revisions explicitly without local submodules.
6. Codex and Claude Code read the same skill files with host-appropriate invocation syntax.

### Edge Cases

Existing files, live or dangling symlinks, directory collisions, paths with spaces, missing
parents, write errors, missing required inputs, runtime self references, stub-only generic
types, unavailable integration services, and an already-published tag.

## Requirements

### Functional Requirements

- **FR-001**: Restore `cy-init-config DIRECTORY [--force]` and retain the eight execution commands.
- **FR-002**: Generate one editable example per execution command from its current defaults,
  preserving required inputs, and generate shared and prediction native group files.
- **FR-003**: Preflight all example destinations; protect existing content by default, replace
  only regular example files with `--force`, and preserve unrelated files.
- **FR-004**: Initialization MUST remain local and independent of service credentials and model execution.
- **FR-005**: Examples MUST explain invocation, required inputs, path resolution, tracking identity,
  and applicable native settings; execution contracts remain unchanged.
- **FR-006**: Remove every first-party `from __future__ import annotations` import and repair
  dependent annotations without weakening typing or editing external dependencies.
- **FR-007**: Reconcile the constitution, active CLI contract, README, migration guide, and release
  verification guidance; preserve dated historical evidence as history.
- **FR-008**: Verify affected behavior, repository gates, both distributions, and release identity;
  report unavailable live prerequisites explicitly.
- **FR-009**: Commit task-owned changes, push to the existing origin, and publish the
  then-unpublished `0.3.0` with a wheel, source distribution, and checksums.
- **FR-010**: Include the approved editable submodules and their locked development sources;
  preserve both upstream revisions and document package installation without submodules.
- **FR-011**: Consolidate skills under `.agents/skills`, retain Claude compatibility through a
  relative symlink, and align Spec Kit instructions with the installed script interfaces.

### Key Entities

- Example set: eight command-named files plus two native group files, with editable defaults
  and usage comments.
- Destination: a user-selected directory with collision and replacement rules.
- Release: version, source commit, tag, packages, checksums, notes, and dated verification.

## Success Criteria

- **SC-001**: Every execution command can load its generated example and accept documented overrides.
- **SC-002**: Collision and replacement checks preserve all unrelated and external file contents.
- **SC-003**: No first-party future-annotations import remains and all required repository checks pass.
- **SC-004**: Both downloadable package formats expose all nine commands after installation.
- **SC-005**: The published release and checksummed assets identify the pushed, verified source.

## Assumptions

- At the publication decision point, the package was `0.3.0` and GitHub's latest release was
  `v0.2.0`; v0.3.0 was then published. The maintained version is read from `pyproject.toml`.
- Release means a GitHub release on the existing repository; registry publication is outside scope.
- The coding preference also persists in global instructions; that personal file is outside this Git repo.
- Local examples deliberately preserve missing inputs rather than selecting a user's dataset or device.
- The user explicitly authorized including the concurrent dependency/submodule and skill
  changes. The isolated release checkout contains the combined approved snapshot.
