# Tasks: Cache image deduplication

## Implementation

- [x] T001 Record approved spec, plan, research and CLI contract; check consistency (FR-001–006).
- [x] T002 [P] [US1] Implement core and test preservation, matching, skips, races and native reflinks
  in src/clearml_yolo/dedup.py and tests/test_dedup.py (FR-002–006; depends T001).
- [x] T003 [P] [US2] Implement lightweight CLI, registration and subprocess tests in
  src/clearml_yolo/dedup_cli.py, pyproject.toml and tests/test_dedup_cli.py
  (FR-001, FR-005, FR-006; depends T001, integrates T002).
- [x] T004 Run full repository checks and fresh independent review (depends T002, T003).

## Documentation update and validation

- [x] T005 Update README.md, docs/filesystem-policy.md, docs/project-contracts.md,
  docs/current-contracts.md and specs/001-release-030/contracts/cli.md (depends T002, T003).
- [x] T006 Validate Markdown, local links and changed examples; record dated evidence
  (depends T004, T005).
- [x] T007 Complete authorized checked commit and local annotated release (depends T006).
- [x] T008 Push the branch and release tag only; record remote acknowledgement and readback (depends T007).
