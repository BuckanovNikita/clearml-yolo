# Tasks: Local dependency copies

## Implementation

- [x] T001 Snapshot dependency contents and remove gitlinks, .gitmodules and local
  registration while preserving both trees and Git history (FR-001, FR-002).
- [x] T002 Ignore the local copies and update dependency comments (FR-001, FR-002).

## Documentation update

- [x] T003 Update development setup, current contract index, active specification
  and quickstarts; preserve historical evidence and README scope (FR-003; after T002).
- [x] T004 Verify contents/imports, Markdown/links and repository checks; obtain
  independent review and record evidence (FR-002, FR-003; after T003).
- [ ] T005 Commit through hooks, release 0.17.1 and push main plus the Git tag;
  restore local overrides (FR-004; after T004).
