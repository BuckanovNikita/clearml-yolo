# Confirmed companion queue completion race — 2026-11-01

**Status**: Confirmed; proposed cross-repository remediation awaits scope approval.
**Source**: Required final CY/queue integration run and read-only deterministic probe.

## Observation and reproduction

Committed CY 0.44.6 / queue 0.1.6 final pairing resolved normally with matching source,
installed metadata and editable locations. Static/import/help/pip checks passed.
Integration failed one existing queue admission case: 543 passed, one failed,
7 deselected, 19 warnings in 137.69 seconds. The second job did not reach completed
within the unchanged ten-second test bound. No push occurred after this failed gate.

Artifacts show first job completed. The second job had a successful launch, then
recovery_required revision 7 and “Execution state is uncertain; owner recovery
required”. Its revision sequence is consistent with running revision 5, guardian
completion revision 6 and stale refresh overwrite revision 7. Guardian cleanup did
not report a failure; its earlier admission-deferred attempt is separate history.

A bounded read-only agent invoked actual QueueProcesses._refresh_job and actual
NFSQueueStore update/transaction_update with in-memory reads and intercepted atomic
publication: current completed revision 6 plus stale running revision 5 produced
recovery_required revision 7 with the exact observed error. It performed zero disk
writes and created no subprocesses. This establishes the stale-write mechanism;
the precise historical interleaving is inferred from the persisted revisions.

## Root cause and proposed remediation

Queue refresh reads a public job before checking capacity/launch liveness. Guardian
completion publishes a newer terminal record, releases the claim and exits. Refresh
can then observe no claim/dead launch and unconditionally overwrite that completion.
The dead-claim recovery branch has the same stale-write window. CY native traversal
is not the cause, and increasing deadlines or retrying until green is insufficient.

The minimal fix belongs in cy-queue storage/runtime: atomically compare the observed
job revision and state within the storage transaction before publishing recovery.
Leave a newer record unchanged. Preserve genuine lost-execution recovery, including
an unchanged terminal job whose dead claim still requires ownership recovery; do not
blanket-exempt terminal states or release unverified leases. Both refresh recovery
writes must use the guarded transition. Existing expected_state exceptions alone
would turn this normal race into an exception and miss same-state revision races.

Add deterministic interleaving regressions for both branches against concurrent
completion, failure, cancellation and newer launch revisions, plus genuine unchanged
loss and terminal-with-retained-claim protection. No timeout increase, test removal,
protocol change, CY bound change or monkeypatch of a dependency is proposed.

## Architecture, workflow and authorization

Storage continues to own transaction locks and public-record publication; runtime
owns process/claim observations and requests the conditional transition. Core and
application effects and CY shared interfaces remain unchanged. Record a queue-local
architecture plan and executable coverage before implementation. Queue instructions
require a patch version (proposed 0.1.7), configured pytest/Ruff/format/mypy/imports,
documentation checks, fresh independent review and a Conventional Commit/main push;
there is no queue tag/GitHub Release/package publication workflow.

The accepted CY plan authorized paired checks, not companion runtime delivery.
A scope question is pending before queue source edits. If approved, use an isolated
queue checkout and pairing environment, preserve the primary accepted CY inputs,
verify the latest pair with normal resolution, obtain fresh integrated review and
publish only after all gates pass. Otherwise CY 0.44.6 remains locally tagged and
blocked from delivery. Preserve all failed evidence; do not characterize it as a pass.

## Resumed remediation — 2026-11-02

The user reactivated the blocked delivery goal after the bounded companion fix and
delivery question. Parent proceeds with that necessary interoperability scope in an
isolated latest-source queue checkout. Queue-local plan/architecture were validated
before implementation. A bounded agent owns only storage/runtime/regression tests;
parent owns version/docs and final integration/review/delivery. Earlier waiting and
failed-run observations above remain historical. No unrelated scope is included.

## Resolution — 2026-11-02

Queue 0.1.7 now preserves newer public records and revalidates retained claims after
dead liveness. Both observed orderings have deterministic RED/GREEN regressions.
Parent full latest-pair verification passed 582 cases; original+new regressions
passed 39 cases. Fresh corrected independent review returned ship, architecture and
docs checks passed, and queue implementation b976789301d814a4249d3683739b8d6918819a73 plus closure
4e539f227f06e600d95753e27049baf6df517398 are published and remote-verified. No CY runtime changes were
needed. The [cleanup execution record](../../../specs/010-cleanup/execution.md) owns
paired evidence and final CY delivery. Earlier pending/failed observations above
remain historical; the companion source blocker is resolved.
