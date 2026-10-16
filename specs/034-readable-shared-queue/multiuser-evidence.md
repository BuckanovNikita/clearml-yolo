# Real two-user queue acceptance

Latest verified outcome (2026-10-16 09:14 UTC): **PASSED**. Two complete runs passed.
The history below retains an initial harness setup error and an intentional failure used
to verify cleanup after both accounts were created. A final independent lookup found no
temporary accounts, groups, fixture directories or mailboxes remaining.

Date: 2026-10-16 09:10 UTC

Result: FAILED

This setup attempt stopped before either test account was created. Its group and fixture
directory were removed. The unsupported mail-spool override was a harness error; removing
it retained the installed account tool's existing mail-spool default. This attempt did
not exercise application behavior.

Command: `python tests/queue_multiuser_harness.py --run --evidence <this-file>` (root controller).

## Executed checks

- All task-owned processes, temporary accounts, group and fixture files were removed; account absence was checked afterward.

## Boundaries

These checks used two actual temporary Unix accounts, real file permissions, flock locks, owner workers, guardians and subprocesses. Root performed provisioning, identity switching and cleanup only. Queue operations ran as the test users.

A synthetic host with a fixture-only bootstrap path left production coordination untouched. The existing test NVML module supplied synthetic device/memory facts. No physical GPU, network filesystem, ClearML service, model training, or production host configuration was exercised. Recovery visibility used an injected recovery state; guardian-crash recovery remains covered by separate process tests.

## Failures

CalledProcessError: configuration error - unknown item 'CREATE_MAIL_SPOOL' (notify administrator)


---

# Real two-user queue acceptance

Date: 2026-10-16 09:11 UTC

Result: PASSED

Command: `python tests/queue_multiuser_harness.py --run --evidence <this-file>` (root controller).

## Executed checks

- Both real Unix users loaded the same group-readable configuration and shared roots under umask 077.
- Concurrent submissions committed twelve unique stable job numbers; both users read identical shared history.
- Public summaries were readable; private snapshots and foreign record writes were denied by real filesystem permissions.
- Foreign cancellation, update, archive, restore, recovery and execution were refused; both users could reorder the other's pending job.
- Both users rejected a conflicting coordination root without creating it.
- Owner archive/restore persisted across fresh processes and both users' views; repeat archive was idempotent. Injected recovery-required state resurfaced in the main view.
- A real advisory GPU reservation held by one user excluded the other user through a second metadata root.
- Two real owner workers and independent guardians completed controlled subprocess workloads under their respective UIDs, with one synthetic-device allocation at a time. Duplicate owner workers were refused.
- Guardian payloads retained the configured coordination path; actual logs and progress stayed private in each owner's project while public progress was published.
- All task-owned processes, temporary accounts, group and fixture files were removed; account absence was checked afterward.

## Boundaries

These checks used two actual temporary Unix accounts, real file permissions, flock locks, owner workers, guardians and subprocesses. Root performed provisioning, identity switching and cleanup only. Queue operations ran as the test users.

A synthetic host with a fixture-only bootstrap path left production coordination untouched. The existing test NVML module supplied synthetic device/memory facts. No physical GPU, network filesystem, ClearML service, model training, or production host configuration was exercised. Recovery visibility used an injected recovery state; guardian-crash recovery remains covered by separate process tests.

---

# Real two-user queue acceptance

Date: 2026-10-16 09:13 UTC

Result: FAILED

This failure was intentional; cleanup verification passed. The controller was invoked
through a small Python wrapper that replaced only the harness exercise function with a
deliberate exception after both accounts were provisioned. The wrapper required the
controller to return its failure status. Production queue code was unchanged.

Command: `python tests/queue_multiuser_harness.py --run --evidence <this-file>` (root controller).

## Executed checks

- Both temporary accounts were provisioned before a deliberate cleanup-verification failure.
- All task-owned processes, temporary accounts, group and fixture files were removed; account absence was checked afterward.

## Boundaries

The harness uses actual temporary Unix accounts, file permissions, flock locks, owner workers, guardians and subprocesses. Root performs provisioning, identity switching and cleanup only. The executed-check list records which stages completed; queue operations run as the test users.

A synthetic host with a fixture-only bootstrap path left production coordination untouched. The existing test NVML module supplied synthetic device/memory facts. No physical GPU, network filesystem, ClearML service, model training, or production host configuration was exercised. Recovery visibility used an injected recovery state; guardian-crash recovery remains covered by separate process tests.

## Failures

RuntimeError: Deliberate failure verifies cleanup after account provisioning

---

# Real two-user queue acceptance

Date: 2026-10-16 09:14 UTC

Result: PASSED

Command: `python tests/queue_multiuser_harness.py --run --evidence <this-file>` (root controller).

## Executed checks

- Both real Unix users loaded the same group-readable configuration and shared roots under umask 077.
- Concurrent submissions committed twelve unique stable job numbers; both users read identical shared history.
- Public summaries were readable; private snapshots and foreign record writes were denied by real filesystem permissions.
- Foreign cancellation, update, archive, restore, recovery and execution were refused; both users could reorder the other's pending job.
- Both users rejected a conflicting coordination root without creating it.
- Owner archive/restore persisted across fresh processes and both users' views; repeat archive was idempotent. Injected recovery-required state resurfaced in the main view.
- A real advisory GPU reservation held by one user excluded the other user through a second metadata root.
- Two real owner workers and independent guardians completed controlled subprocess workloads under their respective UIDs, with one synthetic-device allocation at a time. Duplicate owner workers were refused.
- Guardian payloads retained the configured coordination path; actual logs and progress stayed private in each owner's project while public progress was published.
- All task-owned processes, temporary accounts, group and fixture files were removed; account absence was checked afterward.

## Boundaries

The harness uses actual temporary Unix accounts, file permissions, flock locks, owner workers, guardians and subprocesses. Root performs provisioning, identity switching and cleanup only. The executed-check list records which stages completed; queue operations run as the test users.

A synthetic host with a fixture-only bootstrap path left production coordination untouched. The existing test NVML module supplied synthetic device/memory facts. No physical GPU, network filesystem, ClearML service, model training, or production host configuration was exercised. Recovery visibility used an injected recovery state; guardian-crash recovery remains covered by separate process tests.
