# Bug Fix: Restore ClearML console logs

- **Slug**: clearml-console-logs
- **Fixed**: 2026-10-02
- **Assessment**: [assessment.md](assessment.md)
- **Status**: applied

## Summary

The invocation owner now enables SDK stdout/stderr capture. Default Loguru and native
terminal messages can reach the same task Console while remaining visible locally.

## Changes

| File | Change |
|---|---|
| src/clearml_yolo/clearml_session.py | Enable auto_connect_streams; explain both-stream capture. |
| tests/test_clearml_session.py | Update initialization expectation and add real offline SDK subprocess coverage. |
| docs/project-contracts.md | Summarize owner console publication. |
| docs/migration-030.md | Replace superseded local-only console policy. |
| specs/010-native-clearml-integration/contracts/tracking-publication.md | Define Console publication and its lifetime limits. |

## Tests Added or Updated

- test_invocation_owns_one_task_and_nested_stages_reuse_it retains ownership and disabled
  framework/argument-capture checks and now requires stream capture.
- test_console_streams_reach_offline_sdk_without_duplicates exercises the actual SDK
  through invocation(), verifies stdout/stderr/Loguru in offline log events after a
  controlled failure, and asserts each message remains visible once locally. It creates
  no remote task and isolates stream patches and files in a fresh subprocess.

## Local Verification

Both updated regressions failed before the source change: disabled capture and absent
offline console markers. After the change, uv run --locked --no-sync pytest -q
tests/test_clearml_session.py passed all 71 tests. Ruff, mypy and all nine import contracts
passed. Complete regression, live delivery, documentation validation and independent
review outcomes are recorded in [test.md](test.md).

## Deviations from Assessment

None. Framework captures, argument capture, lifecycle, worker guards and nested-stage
reuse were preserved. No dependency file, upstream code or installed tooling changed.

## Documentation Stage

The three affected maintained documents were updated together. The contract index still
points to the same authority. README and quickstarts contain no conflicting local-only
console assertion, so they need no change. Historical evidence remains unchanged.

## Follow-ups

No backfill, DDP worker stream forwarding or post-closure traceback capture is included.
