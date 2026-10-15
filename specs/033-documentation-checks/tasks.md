# Tasks: Read-only documentation checks

## Planning

- [x] T001 Record approved requirements and design in `spec.md` and `plan.md`.
- [x] T002 Validate pre-implementation `architecture.json` and analyze artifacts.

## User Story 1

- [x] T003 [US1] Add positive/negative parser, link, anchor and boundary fixtures in `tests/test_check_docs.py`.
- [x] T004 [US1] Implement read-only checking and diagnostics in `scripts/check_docs.py`.
- [x] T005 [US1] Promote markdown-it-py 4.2.0 in `pyproject.toml` and root `uv.lock` metadata only.

## User Story 2

- [x] T006 [US2] Verify tracked selection, exclusions and read-only execution in `tests/test_check_docs.py`.

## Verification and Documentation

- [x] T007 Run scoped behavior/static checks and record dated results in `verification.md`.
- [x] T008 Validate feature Markdown and deliver all-document findings for parent correction.
- [x] T009 Parent integrates maintenance guidance and obtains fresh independent review; reconcile `architecture.json` and validate acceptance.

The checker owner implements T001–T008 without shared-file overlap beyond the
authorized dependency hunk. Parent owns T009 and release after integrated checks.

## Release-hook fixture follow-up — 2026-10-16

- [x] T010 Isolate temporary Git fixtures from inherited Git environment variables; reproduce the release-hook index failure, verify the parent index stays unchanged, and reconcile acceptance evidence.
