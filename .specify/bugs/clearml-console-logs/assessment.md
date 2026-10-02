# Bug Assessment: Empty ClearML console logs

- **Slug**: clearml-console-logs
- **Created**: 2026-10-02
- **Source**: pasted user report and approved implementation plan
- **Verdict**: valid
- **Severity**: medium

## Report

> Restore stdout logs at clearml page. Now is empty

The user selected normal terminal output, including stdout, stderr and native YOLO
messages, and approved implementation of the proposed plan.

## Symptom and Reproduction

The invocation-owned ClearML task receives no normal console output because its
initialization explicitly sets auto_connect_streams=False. The existing ownership
test enforces this setting. An isolated pre-fix SDK stream probe captured no messages
with both streams disabled; enabling both captured stdout, stderr and Loguru once each
while retaining terminal output. No remote task was created during planning.

## Suspected Code Paths and Root Cause

High confidence: src/clearml_yolo/clearml_session.py disables all SDK stream capture
in invocation(). Project messages use Loguru's default stderr sink. The installed
SDK captures both streams and the default Loguru sink when capture is enabled.
docs/migration-030.md encodes the superseded local-only console policy.

## Proposed Remediation

Enable auto_connect_streams=True for the owner task. Preserve framework and argument
capture settings, worker guards, nested-stage reuse and task finalization. Update
tests/test_clearml_session.py and add a fresh-process offline SDK regression proving
stdout, stderr and Loguru delivery without duplicates. No dependencies change.

Documentation scope: docs/project-contracts.md, docs/migration-030.md and
specs/010-native-clearml-integration/contracts/tracking-publication.md. Update console
publication requirements while preserving configuration sanitization. Validate Markdown
and local links, and record verification in this bug's artifacts.

## Tests and Verification

Observe the updated regression fail before the fix. Run session tests, full pytest,
Ruff, mypy and import-linter with uv --locked --no-sync. On fresh tagged ClearML tasks,
verify stdout, stderr, Loguru and Ultralytics logger markers in backend console events
after success and failure; check terminal output and task status. Clean up only owned
resources. Retain the existing nested ownership, worker and flush-error coverage.

## Risks and Considerations

Normal console output is an unsanitized publication channel; the user explicitly chose
it over sanitized-only project messages. Configuration and failure-status sanitization
remain required. No historical tasks are modified or backfilled. DDP worker forwarding
and tracebacks printed after task closure are outside this fix. Preserve pre-existing
pyproject.toml and uv.lock changes; no commit or deployment is authorized.

## Open Questions

None. Slug generated for the automatically routed, approved remediation.
