# Independent review: ClearML script metadata

- Date: 2026-10-15
- Final reviewer: `/root/review_script_metadata_acceptance`
- Requested controls: GPT-6.1 Sol, high effort, fresh isolated context.
  Actual model/effort telemetry was not exposed by the collaboration tool.
- Ownership: read-only review, no further delegation or file writes.
- Verdict: **ship**, conditional on successful final hooks and architecture/documentation acceptance.

## Findings and resolution

The first reviewer found that repository URL sanitation removed SSH transport
usernames and IPv6 brackets. Five new regression cases reproduced the issue.
The adapter now removes passwords/HTTP userinfo before query sanitization and
preserves SSH login names and bracketed authorities. Nine origin cases pass.

The second reviewer reproduced false success through the SDK public reload method:
failed server reads retained the cache modified by the setter. The adapter now
uses the SDK field request, which propagates online retrieval failures. Regression
cases cover failed readback and disagreement between persisted and cached fields.

The fresh final reviewer inspected the complete final implementation and tests,
SDK setter/readback methods, owner lifetime, import boundaries, documentation and
architecture record. Independent URL, failed-fetch and saved/cache mismatch probes
passed. No actionable findings remained. Parent verification includes 260 focused
checks and the final real-task API readback in [test.md](test.md).

## Reconciliation and limits

The task-owned diff adds one outer ClearML adapter, invokes it inside the existing
owner lifetime, adds its exact SDK import-contract edge, extends behavioral tests
and test doubles, and updates the maintained publication contract and bug evidence.
Generated changelog changes follow the existing hook; no dependency, CLI, core or
application-policy changes are introduced. Queue code belongs to the existing base.

Private SDK initialization/readback remains version-sensitive, covered by offline
SDK execution and live online verification. Source-less wheels cannot invent Git
identity. Final successful commit hooks and the architecture acceptance validator
are recorded after execution; this review does not claim those pending gates passed.

## Supplemental review after Git-environment isolation

Fresh reviewer `/root/review_git_isolation` (requested GPT-6.1 Sol, high effort)
inspected the complete 13-path diff after the source-hook isolation correction.
It independently ran all 21 metadata tests and the complete whitespace check,
and inspected the SDK initialization/setter/field-read implementation. Verdict:
**ship**, with no actionable findings, conditional on successful final hooks and
documentation/architecture acceptance. No file writes or delegation occurred.

The parent also ran all 21 metadata tests with simulated Git-hook selectors; the
disposable repository's config, HEAD and index remained byte-identical. The final
focused suite passed 261 cases. Production Git reads ignore inherited repository
selectors; fixture Git calls additionally disable user/system configuration.

## Parent gate completion

Source commit `2170b7912e7835e27dc72e20e14a954c0c3c8a5c` passed all required hooks, including full pytest,
after the final review and Git isolation correction. The parent reconciled the
module/effect inventory with the complete source diff; [test.md](test.md) records
executed evidence. Native release delivery remains a separate pending step.
