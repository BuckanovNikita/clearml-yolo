# Bug Fix: ClearML finalization timeout

- **Slug**: clearml-finalization-timeout (from assessment context)
- **Fixed**: 2026-10-16
- **Assessment**: [assessment.md](assessment.md)
- **Status**: applied

The shared `FINALIZATION_TIMEOUT_SECONDS` in the ClearML session adapter is now
600.0 instead of 60.0. It governs direct and queued invocation finalization and
separate owner cleanup scopes. Independent console receipt timeouts are unchanged.
Current diagnostics and runtime-isolation documentation describe the new budget
and distinguish it from a total job/exit timeout.

No imports, interfaces, dependencies, status transitions or queue logic changed.
Existing deadline/lifecycle tests provide behavioral coverage; no test duplicating
the constant was added. A direct production timer check armed a 600-second alarm
and confirmed it was cleared afterward. Existing 143 lifecycle tests and 224
architecture tests passed; all 43 import contracts were kept.

The user explicitly requested this extension without a traceback. It does not
establish the cause of the earlier remote stall or change that task's status.
See [verification](test.md) for acceptance evidence and limitations.

Documentation review found no affected portable command examples or installation
instructions, so the portable skill, README and historical evidence are unchanged.
There are no deviations from the assessed scope.
