# Bug Verification: Restore ClearML console logs

- **Slug**: clearml-console-logs
- **Tested**: 2026-10-02
- **Assessment**: [assessment.md](assessment.md)
- **Fix**: [fix.md](fix.md)
- **Result**: verified

## Summary

The original missing-console-marker failure no longer reproduces. The actual SDK
records stdout, stderr and default Loguru messages offline. Fresh remote tasks receive
stdout, stderr, Loguru, installed Ultralytics LOGGER and nested-stage messages once each,
both while active and after successful or failed owner closure. Terminal output remains
visible and task status matches the outcome.

## Checks Performed

All uv commands used --locked --no-sync, preserving dependencies and the lockfile.

| Check | Command / Action | Result | Notes |
|---|---|---|---|
| Pre-fix reproduction | pytest -q tests/test_clearml_session.py -k 'invocation_owns_one or console_streams' | expected failure | 2 failed: disabled capture and absent offline console markers. |
| Session regressions | pytest -q tests/test_clearml_session.py | pass | 71 passed. |
| Full regression suite | pytest -q | pass | 750 passed, 9 skipped, 4 warnings. |
| Ruff | ruff check . | pass | All checks passed. |
| mypy | mypy . | pass | No issues in 96 source files. |
| Import contracts | lint-imports | pass | 9 kept, 0 broken. |
| Live successful invocation | Actual owner/nested contexts, flush and events.get_task_log | pass | Five markers once each before and after closure; task completed. |
| Live failed invocation | Actual owner/nested contexts and controlled RuntimeError | pass | Five markers once each before and after closure; task failed. |
| Cleanup | Tag-scoped environment cleanup and final listing | pass | Owned project/tasks removed; zero matching projects/tasks remained. |

Live verification used two separate fresh processes and explicit tagged project identity.
Each queried backend console events after flush while the owner was active, then again
after closure. The native check emitted through the installed Ultralytics logger; it
does not claim an actual training run. Machine-specific task records are stored with the
global clearml-yolo-environment skill rather than repository instructions.

## Documentation Stage

Updated the project summary, migration guide and maintained native tracking publication
contract together. Console streams are normal raw terminal output; published configuration
and failure status keep their existing sanitization. The contract index retains the same
authority. README and quickstarts had no conflicting console assertion. Historical evidence
was preserved. Final Markdown/link validation and independent acceptance are recorded below.

## Residual Risks

- Historical empty tasks are not backfilled; new invocations receive capture.
- Raw terminal output is not sanitized. The user chose this policy during planning.
- DDP worker streams and tracebacks printed after task closure are outside this change.
- Nine opt-in integration tests were skipped. Four warnings concern deprecated Pydantic
  field access inside hydra-zen; they did not fail the suite.
- No native training, GPU execution, artifact/model release acceptance, commits or
  deployment were performed. These checks establish console delivery and lifecycle.

## Recommendation

The bounded console-capture fix resolves the reported failure. Retain the stated
historical-task and task-lifetime limitations.

## Final Documentation Validation and Independent Acceptance

Markdown parsing passed for all six changed/new documentation files; all 10 local links
and heading anchors resolved. git diff --check passed. The dependency-file SHA256 values
match the pre-task snapshot. Owned live resources and temporary verification scripts were
removed; pre-existing services and experiments were preserved.

Fresh read-only reviewer /root/review_console_fix returned **ship**, with no findings,
after inspecting the scoped diff and evidence and independently rerunning both targeted
tests successfully (2 passed). It retained the documented raw-console, DDP and native
training limits. Requested model/effort: gpt-5.6-sol / medium; runtime model/effort and token
usage were not exposed by native metadata. The parent inspected the combined diff and owns
the full regression and live acceptance evidence.
