# Feature Specification: Automatic multirun tags

**Created**: 2026-10-14
**Status**: Implemented, verified and released in v0.28.0
**Input**: "Add autotag of tasks that launched from one multirun with random tag"

## User Scenarios & Testing

### User Story 1 - Find tasks from one launch (Priority: P1)

An experiment author filters ClearML tasks by an automatically assigned tag to see
all tasks from one multirun, without manually choosing a group tag.

**Independent Test**: Launch two jobs, inspect their tracking configuration, then
repeat the launch. Each launch has one shared tag and the launches differ.

**Acceptance Scenarios**:

1. A direct multirun adds the same random tag to every job, preserving user tags.
2. A queued multirun stores the shared tag before execution; delayed workers retain it.
3. Repeating the launch creates a new tag even in the same process.
4. An ordinary single run adds no automatic tag.

### Edge Cases

- A multirun with one job still receives a tag.
- Saved MULTIRUN mode and explicit `-m` use the same grouping semantics.
- Per-job tag overrides and empty tag lists retain their meaning.
- A generated tag is added at most once; user-supplied historical tags are preserved.
- Help/configuration inspection does not start tasks or persist random defaults.

## Requirements

- **FR-001**: Every direct multirun adds one shared random `multirun-` tag to its tasks.
- **FR-002**: Each queued multirun freezes its shared tag in every job before execution.
- **FR-003**: Each separate launch generates a fresh tag; no process-global group leaks.
- **FR-004**: Explicit user tags are preserved, including per-job overrides.
- **FR-005**: Ordinary single runs retain their supplied tags without automatic additions.
- **FR-006**: Effective multirun mode controls tagging, including one-job and saved sweeps.

### Key Entities

- Multirun group: one launch and the random tag shared by all jobs it creates.
- Job tags: user-supplied tracking labels plus the current multirun group when applicable.

## Success Criteria

- **SC-001**: All jobs in each tested multirun share exactly one new group tag.
- **SC-002**: Repeated launches have different group tags, with no lost user tags.
- **SC-003**: Single-run tag lists remain identical to their configured values.

## Assumptions

Tasks means ClearML tasks. Both direct commands and queued submissions are in scope.
The tag is always automatic for multiruns; no new configuration option is needed.
Existing task creation, remote replay, model-tag inheritance and queue policy remain
owned by their existing modules. Regression checks use real Hydra composition and
launching with recording execution boundaries; they do not claim live server publication.

## Presentation amendment — 2026-10-16

The historical display requirements above are superseded by the
[readable shared queue feature](../034-readable-shared-queue/spec.md) and
[current readable-output contract](../../docs/readable-output.md).
Raw identity and grouping semantics are preserved; new human-facing names and tags
contain no opaque task IDs or hashes. Completed implementation history is unchanged.
