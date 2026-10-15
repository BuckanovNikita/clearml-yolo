# Tasks: Python compatibility

## Setup and foundations

- [x] T001 Inspect compatibility, native workflow, dependency sources and existing
  changes; record scope in `spec.md`, `research.md` and `plan.md`.
- [x] T002 Validate `architecture.json` planning and analyze spec/plan/task coverage.

## User Story 1: supported interpreter range

- [x] T003 [US1] Update `pyproject.toml` and regenerate `uv.lock`, reviewing version
  changes and preserving approved external sources.
- [x] T004 [US1] Verify both minors with the existing `tests/` suite and static
  gates; record actual results in `verification.md`.
- [x] T005 [US1] Build and install the wheel in isolated 3.12/3.13 environments;
  check metadata boundaries, both distributions, command entrypoints and process
  supervision; complete scoped real CPU/single-GPU release verification.

## Documentation, acceptance and delivery

- [x] T006 Update maintained setup/compatibility guidance listed in `plan.md`,
  validate Markdown/local links and record companion skill impact.
- [x] T007 Reconcile the full diff and evidence in `architecture.json`; obtain
  fresh independent review and pass architecture acceptance validation.
- [ ] T008 Follow the commit/release procedure in `docs/development.md`, push
  authorized refs and preserve unrelated local work on master.

T001 -> T002 -> T003 -> T004/T005 -> T006 -> T007 -> T008. Static checks may run
in parallel after T003. cveta2 and ed-killer implementation is independently owned
outside this repository. CPU distributed suites run sequentially on this host.
