# Feature Specification: Local dependency copies

**Created**: 2026-10-06
**Input**: Drop submodules, work on simple local dependency copies, push to main,
and release 0.17.1.

## User Scenarios & Testing

### User Story 1 — Develop with local dependencies (Priority: P1)

Developers keep existing dependency source trees and editable installs without
managing parent-repository submodules.

Acceptance: dependency contents survive conversion; Git no longer tracks either
dependency directory; editable imports continue to use those directories.

### Edge Cases

Preserve untracked dependency files, existing local source overrides and upstream
Git history. Fresh checkouts need local copies before installing the editable lock.
The repository currently releases on master; publish the resulting history to the
explicitly requested main branch without changing remote default-branch settings.

## Requirements

- **FR-001**: Remove both gitlinks and .gitmodules; ignore both local dependency trees.
- **FR-002**: Preserve dependency contents, approved revisions, editable paths and
  dependency resolution; do not vendor upstream files into the parent repository.
- **FR-003**: Document local-copy setup and annotate superseded submodule requirements.
- **FR-004**: Run applicable checks, obtain independent review, create v0.17.1 through
  the existing release workflow and push the commit and tag to main.

## Success Criteria

No tracked submodules remain. Both editable packages import from their existing
local trees. All required checks pass and the requested remote refs match locally.
