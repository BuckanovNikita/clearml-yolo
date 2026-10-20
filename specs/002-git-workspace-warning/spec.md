# Feature Specification: Git workspace startup warning

**Feature Branch**: `002-git-workspace-warning`
**Created**: 2026-10-20
**Status**: Approved for implementation
**Input**: Warn users starting cy outside a Git-controlled directory; land on master and release.
The user selected all experiment commands and every launch, including help/config inspection.
This feature extends the [baseline](../000-baseline/spec.md#commands-and-configuration).

## User Scenarios & Testing

### User Story 1 - Notice unversioned experiment configuration (Priority: P1)

As an experiment operator, I want to notice when my launch directory is outside
a Git working tree so I can version my experiment configuration without blocking work.

**Independent Test**: Launch command help from a plain directory and a Git working tree.

**Acceptance Scenarios**:

1. A plain launch directory produces one actionable warning on stderr; help and
   configuration stdout and exit status retain their ordinary behavior.
2. A repository root, nested directory, unborn repository, linked worktree or
   submodule produces no workspace warning.
3. Missing Git, failed inspection and a bare repository produce one advisory
   warning; inspection failure is not presented as proof that a repository is absent.
4. A multirun warns once before its jobs execute, using the original launch cwd
   even when Hydra changes directories or CY_HOME points elsewhere.

## Requirements

- **FR-001**: Cover cy, cy-train, cy-predict, cy-val, cy-metrics, cy-report,
  cy-compare, cy-export and cy-ground-truth, including help/config inspection.
- **FR-002**: Check the actual launch cwd once per invocation before Hydra chdir;
  do not infer Git membership from CY_HOME or installed-package source identity.
- **FR-003**: Recognize valid Git working trees including the cases above;
  bare repositories do not count as working trees.
- **FR-004**: Warn through the existing stderr diagnostics, suggest using a Git
  checkout or deliberately initializing Git to version experiment configuration,
  and continue without modifying Git state or changing workload exit semantics.
- **FR-005**: Bound Git inspection to five seconds, ignore inherited Git repository
  selectors and report unavailable/failed verification without raw Git diagnostics.
- **FR-006**: Preserve bootstrap import isolation, public signatures/configuration,
  dependencies, queue/config-export/dedup behavior and ClearML source metadata.
- **FR-007**: Update maintained documentation and portable usage guidance; complete
  verification, independent review, master integration and Git-only release.

## Success Criteria

- **SC-001**: Every supported command passes real help/config subprocess checks
  with exactly one workspace warning outside Git and none inside Git.
- **SC-002**: Git failure cases remain nonfatal, stdout remains machine-usable,
  and a two-job Hydra multirun emits the warning once.
- **SC-003**: Applicable behavior, architecture, documentation and release checks
  pass, with remote master and annotated version-tag identities verified.

## Assumptions

The warning is advisory and has no opt-out flag. Git control means membership in
a working tree, not a clean tree, tracked individual files, commits or remotes.
No native model execution or ClearML publication behavior is changed.
