# Ticket 26 RF-DETR Medium native execution — 2026-11-16

Status: accepted within the bounded native ticket 26 scope. Preparation, execution,
fresh publication/CPU readback, independent acceptance and protected cleanup passed.
Coordinator review, commit and native documentation verification remain pending.
[Paired JSON](2026-11-16-ticket26-rfdetr-medium-native.json) binds the retained evidence.
This dated-record task made no live calls or new test executions.

Applicable contracts are [estimated-batch acceptance](../../014-estimated-batch-acceptance/contracts/acceptance.md),
[native checkpoints](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison),
and [publication](../../../docs/experiment-records.md#publication-inventory).
Actual preparation `ticket26-20261116T222659Z-7e47aaf6` used source
`c0b6065572ac6e1b92147acd58f667a72bc5eac6`. Independent input review bound the exact
request and launcher/pytest/worker ancestry to `rfdetr-medium-default-374477a5cd`.
All 459 launch source hashes and 238 readback product hashes match their reviewed
inputs; unchanged fixture/source evidence was reused.

The registered RF-DETR Medium asset has SHA256
`749ff6071828aaffac63e204c4f4135ed3d6cdae4d702e086c360edc3b5768c8` and upstream
MD5 `7223f764a87b863f02eb8d52bf0ce2ee`. Medium uses nominal size 576, four decoder
layers, patch size 16, two windows and positional encoding 36. Native augmentation
remains enabled with per-batch multiscale, expanded scales and scale jitter; the
maximum probe size is 736. No custom JSON snapshot or per-image transform trace is
claimed. Small initialization and capacity were not reused.

Fresh estimation succeeded at batch 8, reached allocator OOM at 16 and independently
confirmed 8. Successful probes completed five warmup, ten measured AdamW and one
validation step. Two FP32 epochs at batch 8, seed 0, EMA and accumulation 1 used the
disjoint 160/40/40 corpus and produced 40 updates (`2 * 160 / 8`), native metric
steps 19 and 39, zero skips and changed parameters. Native `amp_dtype` is null,
the execution setting mapped from `amp=false`; the saved model configuration's
independent AMP default does not establish execution precision. The 46 native CSV
loss entries and 54 remote scalar losses are distinct finite, reconciled inventories.
Native execution took 193.422 seconds; the outer launcher took 196.619 seconds.

This is the first accepted Medium initializer:
`e282f644c541e9ebb098790eac437d2a50de446590250afb7434efd01a801544`.
Zero prior initialization comparisons is appropriate for this first family baseline;
later Medium variants must compare against it. All 183 outer telemetry samples met
the 10,240 MiB reserve, with minimum free VRAM 10,656 MiB and maximum completed
sample gap 1.237 seconds. Existing five-second query and 1800/2040-second
scenario/owner bounds remained unchanged; no outer query errors occurred.

Task `9596d8947c3842ee9f2be52ae5187645`, model `84b3325053a04180a35bb521ca225f29`
and checkpoint SHA256 `7509415bb3bbc38aa6f81594e9445ef7a39dc16b66b08f71cd3d22a794545a64`
agree across native and remote evidence. Eight artifacts and the checkpoint were
freshly downloaded and independently rehashed. All 80 held-out images and 34
backgrounds were accounted for without decoded-pixel leakage.

The reviewed [ticket 103 helper](2026-11-16-ticket103-readback-geometry.md) passed
CUDA-hidden checkpoint loading, prediction and fixed-threshold scoring on all 40
validation images, including 15 backgrounds, with the Medium descriptor at size 576.
All 11,192 raw rows have valid geometry; raw and evaluation CSVs are byte-identical
and zero rows were excluded. Totals are TP 15, FP 255, FN 49. This establishes
native CY prediction/scoring, not separate upstream solver validation or accuracy
qualification.

Cleanup at 22:34:36 UTC removed only the dataset cache (249 files, 24,346,525 bytes)
and successful readback cache (9 files, 150,160,391 bytes), totaling 174,506,916
logical bytes. The coordinator verified 119 protected files unchanged before and
after deletion. Five known native/readback PIDs were absent; exact-case process
and cache-handle scans were empty with the existing unrelated systemd/sd-pam
PID 340/344 exclusions. Native and downloaded checkpoints, predictions, artifacts,
logs, receipts, shared assets/fixtures and other workloads remain protected. No
global compute-empty or separately measured physical-reclaim claim is made.

Remaining limits include convergence, accuracy, CPU/GPU numerical parity,
export/runtime parity and physical multi-GPU operation. Sampled reserve does not
establish continuous reserve or playback quality. Historical WSL hang causality
remains unproven.
