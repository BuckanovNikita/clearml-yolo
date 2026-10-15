# Bug Fix: Default queue worker diagnostics

- **Slug**: queue-default-logs (from assessment context)
- **Fixed**: 2026-10-15
- **Assessment**: [assessment.md](assessment.md)
- **Status**: applied

## Summary

The worker now renders useful INFO diagnostics to stderr by default. Scheduling
and child output capture retain their existing behavior.

## Changes

| File | Change |
| --- | --- |
| `src/clearml_yolo/application/queue.py` | Optional typed QueueView observer after registration and each tick; existing callers remain compatible. |
| `src/clearml_yolo/entrypoints/queue.py` | Worker log level, identity/root startup, deduplicated owner state/progress/wait/allocation/error messages, heartbeat and orderly shutdown. |
| `tests/test_queue_logging.py` | Real CLI default/DEBUG/WARNING, heartbeat/deduplication, redaction, completed history, waiting through real storage and failure cleanup. |
| `README.md`, `docs/queue.md` | Default diagnostics, level controls and retained child log location. |
| `CHANGELOG.md` | Native hook-generated committed-history refresh. |

## Local verification

Before production edits, the real idle-worker regression failed because stderr
was empty after successful startup and SIGTERM shutdown. After implementation,
`pytest tests/test_queue_logging.py tests/test_shared_queue_service.py
tests/test_queue_commands.py -q` passed 48 tests (initial four logging cases).
Additional behavior cases brought `pytest tests/test_queue_logging.py -q` to
seven passing tests. Existing CLI tests retain JSON and submitted-ID stdout checks.
Import-linter passed all 43 contracts; all 104 architecture tests passed, including
injected forbidden dependency cases. Ruff and Vulture passed. Mypy initially
rejected a test's module re-export assumption; using the imported standard-library
clock fixed it, and the final run passed all 318 checked files.

## Documentation update

Updated queue operations and Russian README guidance. Reviewed current-contracts,
project-contracts and diagnostics: their authority/ownership and execution policies
are unchanged, so they require no duplicate logging description. The original
queue feature specification remains historical intent. The canonical corp-skills
package has companion usage/evaluation changes, metadata/link/Markdown/discovery
checks and dated documentation evidence. Final verification and release details
belong in [test.md](test.md).

## Deviations from assessment

The assessment incorrectly named Hatch: inspected `pyproject.toml` and the successful
build establish `uv_build` as the unchanged backend. Use the actual terminal state `completed`; suppress replay of historical terminal
jobs while retaining counts. Job message text uses existing credential redaction
and escapes newlines. No persisted format, dependency, GPU, scheduling or child
process capture changes. The main checkout's concurrent compatibility work remains
excluded; master delivery will use an isolated checkout.

## Completion ledger

- [x] Reproduce original empty stderr and add meaningful regressions.
- [x] Validate architecture planning and implement explicit observation/rendering.
- [x] Pass focused behavior, full pytest, typing, lint and architecture checks.
- [x] Update and validate affected application and portable usage documentation.
- [x] Complete fresh independent code/architecture review and usage evaluation.
- [x] Reconcile actual diff and record acceptance evidence.

The assessment checklist preserves planning history; this ledger records executed
outcomes. Authorized master/tag delivery is recorded separately in the verification
report after the native commit and release hooks finish.
