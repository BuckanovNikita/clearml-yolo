# WSL interruption and verification disposition — 2026-11-16

Times below use Europe/Moscow unless UTC is explicit. This is dated operational
evidence, not a change to project policy or an accepted full verification result.

## Observations

- During severe shell/tool delays, a process snapshot showed unrelated Node PID
  3998340, `verify/team-analytics-page/settings.test.cjs`, using 50,729,868 KiB RSS
  (48.4 GiB). Its ancestor was a CVAT worktree red-check runner. The two CY pytest
  workers in the same snapshot used approximately 1.1 GiB combined. No campaign
  GPU training or supplemental mutation execution was active.
- Read-only inspection found that runner uses `subprocess.run(..., capture_output=True)`
  without a timeout or memory limit. It temporarily substitutes committed source,
  retaining restoration copies only in memory. It was not rerun or edited.
- Independent static inspection identified an expected failed assertion carrying
  a React/jsdom DOM element as its actual value. Failure serialization of the
  attached object graph is a possible allocation amplifier, not a proven cause.
  No concrete infinite application update loop was established.
- Boot history confirms the previous WSL boot ended at 00:14:30 and the new one
  began at 00:14:44. Previous process identities no longer exist. The old journal
  reports an unclean journal and kernel-buffer message loss around shutdown.
- The retained previous-boot kernel search found older container-scoped OOM events,
  but none matching this incident. Windows System queries for resource exhaustion,
  display reset and Kernel-Power events in the preceding hour returned zero matches.
  Missing events, especially with journal loss, do not rule out memory pressure.
- After restart, WSL reported about 47 GiB available RAM and all 16 GiB swap free;
  Windows reported 64.98 GiB free of 127.41 GiB physical RAM. No current process
  exceeded 1 GiB RSS in the later snapshot. The workspace had 697 GiB free.
  A read-only Git operation completed in 0.002 seconds. I/O pressure remained
  elevated during recovery; its post-restart values cannot establish the prior cause.

The large unbounded Node workload is the strongest observed suspect. The exact
mechanism behind the WSL hang is unconfirmed. This diagnosis did not reproduce a
machine-wide freeze, signal unrelated processes, alter other repositories, or
change user host controls.

## Verification and recovery

The frozen integrated `task coverage` run collected 4,767 cases, then terminated
with status 143 during WSL shutdown. Its log is retained locally as
`.tmp/verification-gap-closure/integrated-coverage-final.log`. This is **incomplete**;
it establishes neither a successful full suite nor the global coverage floor.
All 33 files in `integrated-inputs-final.json` still match their recorded hashes.
Previously completed focused checks and reviews retain their stated scope.

Old coverage workers and recorded service-forward processes are gone. The owned
service environment `cy-it-e3dd8d` must be inspected and renewed through its native
lifecycle before further publication checks; the record is retained for guarded
recovery. Durable fixture, asset and service handoff bundles remain intact.

At 00:19 the host control reported video activity and `pcboardd` down since 00:14,
with no live load figures or wake-ups. Its instruction requires postponing heavy
jobs in that state. Full coverage, pending scoped mutation, final automatic gates,
and native GPU/publication acceptance are **deferred**, not waived. No automatic
wake-up is promised. Resume resource admission and owned-service recovery before
restarting these checks; do not repeat the unrelated unbounded Node test.
