# Ticket 07: interrupted launcher and completed native child

Date: 2026-11-16. Recommendation: **reuse the completed native case and independent
readback; this launcher interruption alone does not require another GPU run**.
The launcher remains **interrupted**, with observed tool exit 143. Its supplemental
telemetry is truncated. Neither a successful launcher result nor missing telemetry
samples have been reconstructed.

## Evidence and source identity

Case: `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/ultralytics-json_mosaic-133fbc61a3`.
Launch: `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/launches/20261116T144840Z`.
The case-local `launcher-diagnosis.json` records source and retained-file hashes;
its SHA-256 is `ac0f08b365e535927768b891f2a728793a56e4277f5a545aaea66f520dfc8c91`.

The launch recorded source `60b5c63aebd70fbe6329f6e0534bd1cccfc6832b`.
Investigation began on that local master and continued after the coordinator's
documentation-only fast-forward to `755bee1`. All **459 Python source files**
recorded in launch inputs still have identical hashes, including the harness,
reserve monitor, GPU inventory and process-ownership implementation. Remote
references were not fetched. This investigation ran no GPU work, sent no signals,
changed no product/test code and created no temporary process or environment.

## What stopped, and what continued

The retained coordinator tool history establishes:

- At `14:48:40.547Z`, an ordinary `exec_command` launched the ticket 07 wrapper,
  with `yield_time_ms=1000`, returning session 24945. The command and tool call
  contained no explicit 300-second timeout.
- At `14:53:33.874Z`, polling still returned the running session.
- At `14:55:20.995Z`, polling returned exit **143**, without launcher completion
  output. The launch directory has no `result.json`; none was created by recovery.

The outer wrapper's background telemetry thread recorded **289 successful samples**,
from elapsed 0.00036 through **302.55870 seconds**, with no logged query errors.
The greatest recorded interval was 1.106 seconds; minimum observed free memory was
**8,343 MiB**, above the selected 8,192 MiB floor. These numbers apply only to the
recorded prefix. The last sample is not an exact signal timestamp.

The child continued and wrote `verification.json`, then `summary.json` with
`status=passed` and elapsed **367.85820 seconds**. `pytest.log` ends with
**1 passed in 368.83 seconds**. Thus approximately the final 66 seconds lack outer
supplemental numeric telemetry. That observation does not make the native safety
monitor disappear: it is owned by the surviving pytest process.

## Independent reserve enforcement and cleanup

The launch command selected `--severstal-free-vram-mib 8192` and
`--severstal-timeout 1800`. The unchanged
[native harness](../../../tests/severstal_harness.py) checks reserve before worker
start and throughout `_run_worker`, before polling worker completion. After at
least 0.25 seconds since the preceding completed check, it calls
`severstal_batch.check_reserve`; the loop sleeps 0.05 seconds between iterations.
These thresholds are not a guaranteed 250 ms wall-clock cadence: queries and
ownership scans take time.

`check_reserve` uses the selected device UUID and fresh `gpu_states()` whole-device
free-memory accounting. Missing/invalid telemetry, failed queries and reserve
breaches raise. Each native nvidia-smi query has a 15-second timeout. The outer
thread merely records additional observations and is not this enforcement loop.

The surviving harness returns success only after `IndependentWorkerPool.poll()`
reports worker exit zero **and** `cleanup_complete=true`; its context exit must
also complete. Cleanup terminates/verifies the owned descendant tree, waits/reaps
and closes owned streams. A failed guard, worker exit, timeout or cleanup would
instead produce a failed summary and failing pytest result. `summary.json` is
written as passed only after this path and optimizer/initialization checks succeed.
Follow-up exact-argument `/proc` inspection found no matching ticket 07 launcher,
pytest or case worker remaining.

This establishes that the maintained reserve guard and owned-worker cleanup
covered the native worker lifetime, including the period after the outer wrapper
stopped. It does **not** provide a numeric guard-sample history, a precise final
free-memory minimum, or proof about transients between samples.

## Cause assessment and independent recovery

Exit 143 is compatible with SIGTERM. The retained launcher has no whole-command
timeout or signal handler and writes its receipt only after its child returns.
Termination of that wrapper explains both the stopped telemetry thread and absent
receipt while the child continued. The source contains an 1,800-second native case
deadline, and separate 300-second batch-trial timeouts; neither is evidence of a
300-second wrapper deadline or a mechanism that signals its ancestor.

A scoped host-journal search from `14:48Z` to `14:55Z` found no OOM, killed-process,
SIGTERM, termination or timeout entry. It did contain repeated WSL dxg ioctl `-22`
messages and an unrelated agent-connectivity warning. These do not identify the
signal sender or establish causation. An external approximately 300-second tool or
process timeout is **a hypothesis, not a diagnosed cause**. Available evidence
does not attribute the signal to a specific service or user action.

The coordinator subsequently ran independent forced-download/API readback and CPU
validation, retained under `readback/20261116T150024Z-b3fc7ed9/receipt.json` in the
case directory. This investigation read that passing receipt and verified its
checkpoint bytes against both native verification and the downloaded file:

- Task: `ea1945d23cf24ee180f5cce0f7bb654b`.
- Output Model: `26d3bba5d17243cb96a67c9ae5abd179`.
- Checkpoint SHA-256: `ea7e6fce3024aec6d867ead22af8d5e373bdb5425d606714068b889a1b88b262`.

The receipt reports two completed epochs, passing publication checks and CPU
checkpoint validation. Those recovered outcomes support reuse independently of
the wrapper's missing receipt; they do not repair or replace its exit status.

## Acceptance boundary

Native execution, maintained reserve enforcement, owned-worker cleanup and the
recovered checkpoint/publication evidence are reusable. Outer launcher completion
is interrupted; supplemental telemetry has explicitly partial coverage; the signal
source remains unresolved. Do not label the outer launch passed or claim a
full-case observed free-memory minimum. The coordinator retains responsibility for
the other ticket 07 criteria and integrated documentation review/gate. No new
scientific-accuracy, export-quality or GPU-rerun claim is made here.
