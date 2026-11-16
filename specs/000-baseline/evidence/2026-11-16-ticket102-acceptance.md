# Ticket 102: accepted queue lifecycle observation correction

Date: 2026-11-16. Scope: test-only correction and selected CPU pairing verification.
The correction is accepted on isolated queue commit
`349c13b2729ade73cd944c5839854574eb407b19`, paired with CY
`a71737e0dc0b756a8e0428318f31713ca740091f`. This resolves ticket 102's CPU
verification prerequisite for ticket 92. It does not establish queue/direct GPU
scientific parity or clear the separate ticket 101 diagnostic hold.

The [machine-readable record](2026-11-16-ticket102-acceptance.json) binds source
identities, retained artifacts, observed checks and cleanup. The earlier
[diagnosis](2026-11-16-ticket102-queue-observation-diagnosis.md) and its JSON remain
unchanged; their correction-pending statements describe that earlier stage.

## Contract and exact change

Queue `specs/baseline.md` and `docs/interfaces.md` distinguish a terminal public
outcome from verified capacity release. The guardian publishes terminal state
before releasing its lease. Deferred admission separately publishes pending state
and its waiting reason; `start()` returning does not promise atomic publication of
that diagnostic. No runtime contract defect was established.

Five product-test files now wait for the complete observation within their
existing deadlines and polling intervals:

| Queue test file | Required observation |
| --- | --- |
| `tests/test_guardian_grace.py` | Cancelled state and empty reservations |
| `tests/test_queue_admission.py` | Pending and exact waiting reason; terminal state and exact expected reservations, including the sibling allocation |
| `tests/test_queue_handoff.py` | Terminal state and only the intentionally retained GPU-a/GPU-c lease |
| `tests/test_shared_queue_processes.py` | Terminal state and empty reservations after owned-process cleanup |
| `tests/test_shared_queue_service.py` | First cancellation retains only GPU-b; second cancellation releases the remainder, within the original shared deadline |

Assertions for refused launch, fresh strict below-threshold admission, owner and
descendant lifetime, final publication, persisted identities and exact sibling
ownership remain. No fixed delay substitutes for a state observation; no timeout
was increased. The five final file hashes are in the JSON record.

The reviewed commits, in order, are:

1. `9e720d6ca081178f814e10772a08c141f3464ed6`: initial observation correction.
2. `79a944ed831dac40f8ee4bbe40886d0ebc52df41`: separate automatic formatting.
3. `36c8f77d0e396f68c12ea860bab77f14ed9d8d5f`: remaining observations in the first three files.
4. `859cc2cf4e8974b0f8bd93d717665d9d9c00fb39`: handoff and shared-service observations found by the invariant audit.
5. `349c13b2729ade73cd944c5839854574eb407b19`: separate automatic formatting.

The isolated worktree is clean. All 78 other tracked files were rehashed and
compared with the clean original queue checkout at
`d3627a0da85968429ddeaff4920c05825e6e05e2`. Product source has the identical Git
tree `5347629f3889cccca94400e909e3493f0ebdf85d`; `pyproject.toml` is unchanged.
The original checkout, runtime source and dependency pins were not updated.
Versions remain CY 0.48.2 and cy-queue 0.1.10. Nothing was pushed or released.

## Executed verification and retained failures

| Check | Outcome |
| --- | --- |
| Five affected modules | Passed: 49 tests, 29.44 seconds |
| Handoff module after formatting | Passed: 15 tests, 3.73 seconds |
| Affected mypy, Ruff, format and diff checks | Passed for the final five-file input |
| Fresh independent review | Passed; `count_review` found no blockers in the final five-file change |
| Full actual-v3 queue suite | Passed: 527 tests, 7 deselected, 176.49 seconds |
| Selected native `paired-check` | Passed: 527 tests, 7 deselected, 176.01 test seconds; entire gate 245.67 seconds |
| Physical multi-GPU suite | Waived under maintained queue policy; seven opt-in tests remain deselected |

Both full runs retained 19 dependency deprecation warnings. The actual-v3 run
used its existing interpreter with the isolated queue source selected explicitly;
its installations and editable bindings were not changed. The independent native
gate used the unchanged Task command with normal dependency resolution in its own
temporary environment. It verified 284 installed packages, queue source/installed
identity, Ruff, formatting of 78 files, mypy on 70 files, both import contracts,
the full queue suite and CLI help. CUDA was hidden and CPU affinity was bounded
to cores 0 and 1. These are real owned subprocess checks with controlled device
telemetry, not physical GPU execution.

Earlier outcomes remain preserved and are not reclassified as passes:

| Retained run | Observed outcome |
| --- | --- |
| Historical CY `60b5c63` / queue `d3627a0` | 527 passed, 7 deselected, 136.20 seconds; historical context only |
| Original selected pair, CY `ba56e2f` / queue `d3627a0` | 3 failed, 524 passed, 7 deselected, 181.56 seconds |
| Original actual-v3 suite | 2 failed, 525 passed, 7 deselected, 179.74 seconds |
| Intermediate correction `79a944e` | 2 failed, 525 passed, 7 deselected, 179.14 seconds |
| Intermediate correction `36c8f77` | 1 failed, 526 passed, 7 deselected, 174.25 seconds |

The intermediate failures exposed additional terminal-before-release assertions,
which were corrected and independently reviewed before the final passing runs.
The four original deferred-admission public records still match their recorded
hashes and exact eventual pending diagnostics. Failed logs, receipts, public
records and pytest directories remain available.

## Evidence, cleanup and limits

Primary local receipts under
`.tmp/verification-gap-closure/ticket102-20261116/` are:

- `completion.json`: actual-v3 success and implementation cleanup, SHA256
  `5226d4709d38898e4d172a86e95c5b0ffd88209977f09804e7695384b376d2b7`.
- `native-paired-final/completion.json`: selected pairing success, SHA256
  `aaae0025d1061af32ba37283889e16544164ed5a8d4f795bc75d957af10240ef`.
- `native-paired-final/gate.log`: SHA256
  `bd4f2544d34d512b5ec92255f1ddf2cbeea1361db4323a562e679dc342eb70f0`.
- `native-paired-final/cache-cleanup.json`: separate cleanup receipt, SHA256
  `bbefdab2663dcfbcf4ac694267a63f16232c61df8900d1f3eb51cc6f46cf9b6c`.

Closure rechecked these artifact bindings, all final source hashes, the original
diagnosis bindings and process ownership evidence. All 78 recorded native-gate
PIDs are absent; no task-owned command matches remain. The native temporary
environment is absent. Earlier implementation cleanup removed its owned mypy
cache: 19,136,736 bytes. Newly approved pairing-cache cleanup removed only
`ruff-cache`, `mypy-cache`, `hypothesis`, `pytest-cache` and `tmp`: 161 files,
180,606,599 logical bytes. All 2,775 protected entries outside those roots were
reverified unchanged, including the frozen gate receipts and pytest evidence.
The v3 environment, v3 uv-cache, shared services and original queue checkout remain.

No tests or native execution were rerun while authoring this closure record.
Executed results were reused after verifying their inputs and retained artifacts.
This acceptance covers the test observation correction and CPU compatibility gate;
it makes no claim about GPU numerical parity, training, remote publication,
physical multi-GPU behavior or closure of the wider verification campaign.
Root owns integration of these dated documents and the final automatic
documentation verification route.
