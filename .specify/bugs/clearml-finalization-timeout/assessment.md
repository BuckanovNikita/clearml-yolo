# Bug Assessment: ClearML finalization timeout

- **Slug**: clearml-finalization-timeout (generated)
- **Created**: 2026-10-16
- **Source**: pasted error and explicit user clarification
- **Verdict**: valid timeout report; underlying stall unconfirmed
- **Severity**: medium

## Report and requested outcome

Task `aea7c5c962944953863de33f6cd619f3` reported at 10:54:58.945:
`TaskFinalizationError: ClearML task finalization deadline expired <- _DeadlineInterrupt`.
The user confirmed a queued run, has no traceback, and explicitly requested a
10-minute limit. Acceptance is the requested budget extension; it is not proof
that the original remote stall is fixed. The original task is not modified.

## Evidence and remediation

`adapters.clearml.session.invocation` applies a shared 60-second aggregate deadline
after the workload returns. Finalizers, required uploads/flush, console barrier,
SDK close, readback and completion consume that budget. The same constant governs
separate failure cleanup, incomplete-owner handler cleanup and final console/status
handling. Change it to 600 seconds. Preserve publication failure handling, alarm
ownership, worker guards, owner quarantine and the console publisher's independent
shorter receipt timeout. No queue configuration, dependency or SDK changes.

An independent read-only SDK investigation confirmed flush/close wait paths; it
could not locate this particular stall without its traceback. Existing deadline
regressions reproduce blocked shutdown using shortened timers. No remote task,
GPU workload or live publication reproduction is available or needed to verify
this explicitly limited numerical change.

## Architecture and task contract

See [architecture.json](architecture.json). The existing outer ClearML session
adapter owns SDK/network effects and uses the existing owner-thread deadline
helper. No interfaces, imports, composition or effect ownership move. Existing
import-linter and architecture negative cases cover the module. Python remains
>=3.12.13,<3.14 with uv/uv_build, Ruff, mypy, Vulture and pytest.

Sequential work: validate the architecture plan, change the timeout/current docs,
run focused lifecycle and architecture checks, review the complete diff, record
acceptance and complete authorized native commit/tag/push hooks. Parent owns all
writes. Independent read-only investigation has no write ownership; this small
constant change needs proportionate review rather than parallel implementation.

Documentation scope: `docs/runtime-isolation.md` and `docs/diagnostics.md`.
Inspected README, tracking-publication contract, current-contract index and portable
usage skill: they contain no 60-second finalization value or affected command/example,
so no edits are required there. Preserve dated 15/60-second historical evidence.
The portable skill source inspected is corp-skills commit
`46b9aec0ddb92d1ef9d443abcf86f9e9bdcf5ee6`; its queue publication guidance remains valid.

## Acceptance checks and risks

- Inspect the effective constant and all its deadline call sites; confirm 600 seconds.
- Run existing console deadline and ClearML session tests; retain failure semantics.
- Run import-linter and architecture tests, including forbidden-edge rejection.
- Validate changed Markdown/local links and run required commit/release hooks.
- Reconcile task-owned changes with the architecture record before acceptance.

Longer finalization delays reporting an actual hang, and separate cleanup deadlines
can add to total exit time. This is not a ten-minute total queue-job deadline.
Preserve unrelated local dependency overrides and the existing untracked grid-search
document. Native release metadata/changelog changes belong to the authorized release.
