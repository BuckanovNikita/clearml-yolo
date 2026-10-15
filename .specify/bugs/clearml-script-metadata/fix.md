# Bug Fix: ClearML script metadata

- **Slug**: clearml-script-metadata (from assessment context)
- **Fixed**: 2026-10-15
- **Assessment**: [assessment.md](assessment.md)
- **Status**: applied

## Summary

Local task owners publish and read back their source identity before executing the
workflow. Source Git identity comes from the imported checkout, including linked
worktrees; script execution uses the canonical stage module and repository root.
Remote-agent script metadata is preserved. Missing Git information is reported
honestly, without adopting an unrelated checkout or inventing values.

## Changes

| File | Change |
| --- | --- |
| `adapters/clearml/script.py` | Bounded Git reads, credential sanitization, SDK script publication and readback. |
| `adapters/clearml/session.py` | Publish once inside the established owner lifetime and failure handling. |
| `tests/test_clearml_script.py` | Real disposable Git repositories/worktrees, missing Git/origin, detached HEAD, redaction, remote replay and rejected-write coverage. |
| `tests/test_clearml_session.py` | Publication-before-workflow, nested reuse, remote preservation and failed-owner integration; extend the recording SDK double. |
| `tests/test_trace_subprocess.py` | Isolate the watchdog SDK double from script publication; all 20 subprocess tracing checks pass. |
| `pyproject.toml` | One exact ClearML SDK ownership edge for the new adapter. |
| Tracking publication contract | Document fields, timing, unavailable identity, excluded raw data and unchanged historical tasks. |

## Local verification

The initial regression failed because no script update was made. The original
session baseline passed 131 tests. After implementation, 248 focused session,
script and architecture cases passed, including injected forbidden dependencies.
All 43 import contracts passed. Ruff, mypy (324 files) and Vulture passed after
installing the existing locked queue-ui/export extras needed by repository checks.
The full suite and final review are recorded in [test.md](test.md).

Fresh real CPU task `de2b8dcf2b0a4b6fa9d2e314eca95389` completed with all five fields
verified by independent API readback and exactly one task in its isolated project.
It records the pre-commit base revision, because verification preceded the fix commit.

## Deviations from assessment

The installed SDK leaves offline tasks without a script object. Initialize that
object through its bounded script-update adapter before the public setter; the
existing real offline SDK subprocess regression verifies this compatibility path.
This requires an explicit `clearml.script -> clearml` import contract edge. No wider
SDK exception or architecture-helper modification was needed.

The full baseline run exposed missing optional detector packages and a host queue
protocol mismatch with the concurrently updated checkout. Installing the existing
locked extras resolved the 19 detector failures (45 focused checks passed). The
metadata patch was transferred unchanged onto the latest committed queue code,
without modifying shared host records. The watchdog test double was also isolated
from metadata publication, retaining its task-closure assertions.

Independent review found that generic URL sanitization removed SSH transport
usernames and IPv6 brackets. Five new regression cases reproduced the issue.
The adapter now strips passwords/HTTP userinfo before generic query sanitization,
preserves bracketed authorities, and restores SSH transport usernames. Nine origin
cases cover HTTP, SSH, SCP syntax, IPv6 and secret query parameters.

A second independent review reproduced false confirmation through the SDK public
reload method, which suppresses failed reads and leaves the setter-mutated cache.
Publication now uses the SDK field request directly, so online retrieval errors
propagate. Regression cases cover unavailable reads and saved/cache disagreement.
The existing real offline subprocess case verifies offline compatibility.

The first source-commit hook attempt exposed inherited Git environment in the new
Git fixture. It changed shared Git settings and the isolated index. The parent
stopped only the owned hook process, restored repository mode/known author identity
and the exact task-owned index, and verified application files remained intact.
Following the existing release-fixture pattern, test Git calls now discard Git
environment variables and user/system Git configuration. Production identity reads
also ignore inherited Git repository selectors. A new regression fails without
this correction; all 21 metadata cases pass under simulated hook variables while
the canary repository config, HEAD and index remain byte-identical.

## Documentation and remaining acceptance

The maintained tracking contract now covers automatic metadata publication. The
inspected portable usage skill needs no command/example change, as recorded in the
assessment. No dependencies, CLI flags or user configuration files were changed.
Final suite, documentation checks, review and release follow in [test.md](test.md).
