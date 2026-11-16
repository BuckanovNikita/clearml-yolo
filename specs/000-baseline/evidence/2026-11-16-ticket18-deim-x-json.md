# Ticket18 DEIMv2 X JSON execution and readback — 2026-11-16

Status: accepted within the native ticket18 scope. Execution, independent publication readback, acceptance review and protected cache cleanup passed. Coordinator review, commit and the native documentation verification route remain pending. [Paired JSON evidence](2026-11-16-ticket18-deim-x-json.json) binds the retained receipts; the broader campaign remains open.

Applicable contracts are [estimated-batch acceptance](../../014-estimated-batch-acceptance/contracts/acceptance.md), [native detector checkpoints](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison), and the [publication inventory](../../../docs/experiment-records.md#publication-inventory). The coordinator executed GPU training and cleanup; a separate agent executed CPU readback. Independent review reconciled retained observations. This dated-record task made no live calls or test executions.

## Inputs and execution

Actual launch source was `657edda357539fb6640533ca3de557c5f91f5970`. All 459 launch source hashes and 238 readback source hashes match ticket15. Unchanged lock, launcher, asset bindings, fixture, owner and native source review were reused. CPU preparation `ticket18-20261116T205558Z-60b8aea9` and fresh admission passed. Actual launch evidence is `ticket18-20261116T210251Z-3077d729`, bound to environment `cy-it-ded7c4` and the recorded WSL boot and namespace UID. The five-second query timeout, 10 GiB reserve and two-epoch limit remained unchanged.

The frozen corpus identity is `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`, with seed 0 and disjoint 160/40/40 train/validation/test images. The paired JSON separately binds manifest file bytes. Rehashed X initialization matches ticket17's derived backbone; initial optimizer-parameter SHA256 `a9dbda79717f5b8e24dbf09a3ef7f75373bffbf3e05bcdde5276e8b743468b83` exactly matches that accepted X baseline. No L-family parameter comparison was used.

Case `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-x-json-ef8e9b197b` passed in 228.447376 seconds; outer launcher elapsed time was 231.511955 seconds, exit 0. Fresh forced estimation passed batch 8, reached allocator OOM at 16 and reconfirmed 8. Both successful probes completed five warmup steps, ten measured AdamW steps and one validation step. Peak observations were 21,074,018,304 and 21,042,561,024 bytes. Capacity applies to the admitted allocator budget and tested batches.

Training completed two epochs at batch 8, FP32, seed 0 and size 640, with 40 optimizer updates, zero skips and changed parameters. The count independently follows 2 × ceil(160 / 8), with drop_last false. All 136 native epoch losses and 262 remote scalar losses were finite and reconciled against their corresponding logs. The producer field `verification.native_loss_values` contains scalar observations; readback's same-named field contains native epoch values. Native epoch validation completed.

The applied JSON snapshot is `bfdd9c00d36be4d222068553563e91dcde506316a6b78751cfe45e769f975e09`: HorizontalFlip and RandomBrightnessContrast, each with probability 1. Snapshot, canonical/native recipe and unchanged executed adapter agree. Native mosaic/mixup/copyblend were disabled. No separate per-image transform trace is claimed.

All 223 outer telemetry samples met the 10,240 MiB reserve and user's 8 GiB floor. Minimum free VRAM was 10,371 MiB; maximum completed sample gap was 1.083232 seconds. No outer query timeout occurred. These are sampled observations, not continuous reserve, playback frame-time or historical WSL hang proof.

## Publication and CPU readback

Project `cy-it-ded7c4 ticket18` produced task `262536ab9dde42a69a5d5629329f1d45` and Output Model `0a75b888282644f5bb5fc17c1e5b3fbe`. Checkpoint SHA256 is `82c054f30340a1810954cab5fa46551e1fd686d8ce1ea654acdb632d1b15e069`. Fresh readback `readback/20261116T210735Z-512a26c1` passed from 21:07:35 to 21:08:26 UTC using the unchanged reviewed helper. Both its readback and executor receipts are hash-bound in the paired JSON.

Eight enabled artifacts and checkpoint bytes were forced through a fresh SDK cache and independently rehashed. Task/model identity, configuration, thresholds and checkpoint metadata agreed. All 80 held-out images and 34 backgrounds were accounted for without decoded-pixel leakage. Native CY CPU prediction reloaded the checkpoint and processed 40 validation images, including 15 backgrounds, yielding 12,000 detections. Exact-threshold scoring totals were TP 0, FP 3, FN 64. This is execution/publication evidence, not scientific accuracy, separate upstream solver validation or export parity.

## Protected cleanup and remaining scope

Independent acceptance review found no blocker. Launcher/worker cleanup passed. The coordinator confirmed five known ticket18 native/readback PIDs absent, the exact-case process scan empty and the cache open-handle scan empty. The scan explicitly excluded unrelated user systemd PID 340 and sd-pam PID 344, whose environments were unreadable. This concerns ticket18 only and makes no global compute-empty claim.

The coordinator rehashed 117 protected case files before and after removing only:

- Case `dataset-cache`: 249 files, 24,344,597 logical bytes.
- Successful readback `cache`: 9 files, 836,212,407 logical bytes.

The passed cleanup receipt records 860,557,004 logical bytes removed. Every checkpoint, retained artifact, CPU prediction, native input/log, receipt, fixture, shared asset, previous case and service remained protected. Other ticket workloads were untouched. Physical filesystem reclaim was not separately attributed.

Selected preparation, admission, training, measured capacity, JSON recipe, X initialization, source applicability, publication, CPU prediction/scoring, sampled reserve, independent review and cleanup checks passed. Physical multi-GPU, other backend cases, scientific accuracy and export compilation/runtime parity remain separate work. The historical WSL hang cause remains unproven, and earlier failed campaign attempts retain their status.
