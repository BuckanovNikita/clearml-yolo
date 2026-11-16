# Ticket101 Windows-local diagnostic pass — 2026-11-16

**Revision5 passed its bounded diagnostic and cleanup.** This establishes the
corrected diagnostic's observed outcome. It does not establish the historical
WSL telemetry stall cause, accept full training, or clear the remaining matrix.
The [companion receipt](2026-11-16-ticket101-windows-local-pass.json) binds the frozen
revision5 inputs, CPU proof history, independent review and live analysis of159 files.
The [prior failed attempts](2026-11-16-ticket101-windows-local.md) remain unchanged.

## Publication correction and CPU proof

A copied PowerShell helper changes only Save-Receipt: an explicit shared FileStream
with FileMode.Create, FileAccess.Write and FileShare.ReadWrite, followed by a UTF8
writer, flush and disposal, replaces in-place Set-Content. The original PowerShell,
C# child ownership and timers are unchanged. The staging adapter selects this copied
helper. Optional polling additionally treats the specifically observed ENODATA as
unavailable; unrelated I/O errors and strict final reads still fail. Unavailable data
adds no sample and refreshes no completion timestamp.

Two early CPU attempts remain failed. The first reproduced the original writer's
sharing conflict, then its generic retention path could not parse an empty receipt.
Later recovery used the separately captured writer identity and retained the exact
seven files without repairing that receipt before removing its owned directory.
The second reproduced the control failure; its candidate writer completed426 writes,
but the Linux reader failed with ENODATA. Its seven files were also retained and its
owned directory removed in a separate recovery. Original failure receipts remain
unchanged. Historical helper snapshots match their recorded hashes; the first helper
version was reconstructed to its exact recorded hash for audit.

The completed CPU comparison reproduced original ClearContent failure after6 writes
in0.052 seconds. The shared writer completed583 writes over10.006 seconds while a
Linux process held real read handles across writes. The reader observed865 valid
receipts,2 partial receipts and1 ENODATA. This supports the correction under that
exercised concurrency; it does not prove the exact competing handle in the earlier
live failure or indefinite reliability.

The exact staged harmless helper also passed normal exit, a5-second timeout and
Job Object close under concurrent Linux reading:2101 valid receipts and1 partial
receipt. Its14 files were retained and verified before exact owned-directory deletion.
Simulated PermissionError and ENODATA produced no new sample; ages1.0 and6.9 seconds
passed freshness, while7.1 seconds failed. Unrelated I/O and strict final-read errors
continued to propagate.

Fresh independent review rehashed33 preparation,395 execution,10 original,39 archived
and28 concurrent-proof retained-file bindings plus3 check logs. Eighteen controller
and15 I/O function/class AST blocks were unchanged. All3 original Linux guards,
10GiB reserve, Windows5-second query timer,7-second sample age,12-second readiness
and75-second combined-observation limit remained in force. R1/R2 ownership and
retention protections were preserved.

## Successful live observation

Run `windows-local-comparison-20261116T202154Z-14b427a5` used source
`15e47f2cd45550904dfd97af029e3fe798bf065e` and boot
`5e9f68d1-63db-4188-9995-e686745fda8c`. Its native output
`ticket101-20261116T202156Z-e2d415ed` completed batch8 with5 warmup,10 measured
and1 validation steps in21.848 seconds. Native wrapper exit0 and cleanup passed.

The Windows observer completed57 successful queries over60.850 seconds with no
query timeout or publication failure. Host minimum free memory was17496MiB;
maximum query process/supervision interval was0.081776 seconds, completed-sample
gap1.083393 seconds and calibrated oldest age at consumption0.584012 seconds.
The26 outer Linux samples had minimum17494MiB free and maximum completed-sample
gap1.089300 seconds. No slow/deadline-adjacent SMI snapshot was recorded. These are
sampled observations, not continuous reserve or internal NVML timing proof.

Cleanup passed:58 exact Windows identities absent,122 retained files independently
rehashed and exact nonce-directory deletion recorded. Root separately confirmed132
recorded Linux PIDs absent and an empty compute list. No signals or cleanup errors
were recorded. The83.340-second total includes separate staging and retention cleanup;
the75-second combined-observation bound did not expire.

## Full ticket15 acceptance and operational resumption

Independent review allowed **one fresh ticket15 attempt after new admission**.
The current boot/resource state differs from the two historical full-attempt failures
and now has two successful unchanged native batch8 probes, including this completed
host observation. All459 full-case source files,16 plan bindings, backbone bytes and
395 diagnostic inputs matched; the reviewed current owner hash and boot matched too.

The original full launcher starts no Windows observer. Its5-second telemetry timeout,
10GiB reserve,1800-second native budget and2040-second owner budget remain unchanged.
This readmission requires fresh capacity estimation, a new case, exactly2 epochs,
seed0,FP32 and the frozen160/40/40 split. Diagnostic batch8 is not a capacity result
for the full case. Any renewed failure stops this limited admission; no automatic
repeat or blanket matrix/queue continuation is covered.

Root recorded fresh boot, namespace UID, service lifetime, selected-GPU telemetry and
an empty compute list at 20:26:18Z, then started the single ticket15 run at 20:26:19Z.
**Full ticket15 native execution and independent remote/CPU readback passed.** Case
`deimv2-l-json-6735466407` took 203.831676 seconds; its launcher took 206.535121 seconds.
Fresh estimation passed at batch 8, reached an allocator-limited OOM at 16 and confirmed
8. Training completed two epochs and 40 optimizer updates. The 199 telemetry samples
had a minimum 10386 MiB free, above the unchanged 10 GiB reserve. Independent readback
verified eight artifact hashes, checkpoint identity and validation on 40 CPU images.
All 459 source bindings and the original full launcher matched. Independent native
acceptance passed with no findings; [ticket15 evidence](2026-11-16-ticket15-deim-l-json.md)
records the scoped outcome. Root removed two disposable caches, 562,496,094 logical
bytes, while preserving 116 case files. This review independently rehashed those
116 files and confirmed both cache paths and the three known native PIDs absent.
Root's cleanup receipt also records an empty owned-process scan and GPU compute list.

The initial conditional `101-resumption-review` remains preserved. The separate
`101-resumption-closure` confirms **acceptance and cleanup conditions are satisfied**:
ticket101's operational pause may close. Ordinary serial ticket-by-ticket work may
resume with fresh admission and capacity confirmation, the user's 8 GiB floor, the
existing 10 GiB guard and 5-second telemetry timeout. Each ticket still requires its
own readback, independent acceptance and cleanup. Any recurrence, reserve breach or
uncertain cleanup pauses further GPU work pending diagnosis and review. The repository
final gate remains pending before integration. This does not accept the remaining
feature matrix or establish the historical WSL stall's root cause. No new GPU work
ran for this review.

Native documentation consistency against the bound source/evidence passed; the final
project gate remains coordinator-owned after commit. Unchanged product checks remain
reusable. Kernel responsiveness required for timeout cleanup is not guaranteed by
these results. No historical WSL/driver cause, physical multi-GPU, numerical export
parity, queue parity, release or deployment outcome is claimed.
