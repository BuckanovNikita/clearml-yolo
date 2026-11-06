# Tasks: Plain prek hooks with cached pytest

Inputs: [specification](spec.md), [plan](plan.md), [architecture](architecture.json).
Checkboxes record current status. [verification.md](verification.md) holds the dated
evidence.

- [x] T001 Swap `pre-commit` for `prek` and add `pytest-testmon` to the dev group. Lock
  with temporary local sources. Confirm the lock diff is limited to those packages and
  that the external entries are unchanged. Add `.testmondata*` to `.gitignore`. (FR-001)
- [x] T002 Testmon go/no-go: run the full suite under testmon, then an unchanged
  testmon run. Record times and selected-test counts. (FR-003)
- [x] T003 Move `version_bytes` and a bytes `git show` helper into
  `scripts/local_release.py`. Switch hook installation, the launcher and tag recovery
  to prek. Set `SKIP` for heavy hooks on the generated commit and during recovery.
  (FR-004/005)
- [x] T004 Replace the `verify` hook with the plan's hooks and update the header
  comments. (FR-002)
- [x] T005 Delete `scripts/verify.py` and `tests/test_verify.py`. Move the
  `version_bytes` cases into `tests/test_local_release.py`. Replace the
  one-suite test with a hook-skip test. Isolate the fixture from
  `SKIP`/`PREK_*`/`PRE_COMMIT*`. Update the tooling-boundary allowlists. (FR-004/005)
- [x] T006 Update current guidance: `AGENTS.md`, `docs/development.md`,
  `docs/agent-workflow.md`, `docs/static-analysis.md`, `docs/current-contracts.md`,
  `docs/local-documentation.md`, `specs/000-baseline/spec.md` and the
  `running-end-to-end-tests` skill. Validate Markdown and links. (FR-006)
- [x] T007 Run focused and full checks, check cache behaviour, and reinstall hooks.
  Get a fresh independent review. Reconcile the diff and validate architecture
  acceptance.
- [x] T008 Commit through the real hooks and confirm the release-commit hook skips.
  Evaluate the release workflow. Delivery is blocked by the queue range; see verification.
- [x] T009 Follow-up: give the `changelog` hook `fail_fast` (with a regression), amend the
  constitution's hook command (9.0.1) and delete `.git/verification/`, all as requested by
  the user.
