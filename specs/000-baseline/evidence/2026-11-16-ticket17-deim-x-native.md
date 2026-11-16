# Ticket17 DEIMv2 X native execution and readback — 2026-11-16

Status: accepted within the native ticket17 scope. Execution, independent publication readback, acceptance review and protected cache cleanup passed. Coordinator review, commit and the native documentation verification route remain pending. [Paired JSON evidence](2026-11-16-ticket17-deim-x-native.json) binds the retained receipts; the broader campaign remains open.

Applicable contracts are [estimated-batch acceptance](../../014-estimated-batch-acceptance/contracts/acceptance.md), [native detector checkpoints](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison), and the [publication inventory](../../../docs/experiment-records.md#publication-inventory). The coordinator executed GPU training and cleanup; a separate agent executed CPU readback. Independent review reconciled retained observations. This dated-record task made no live calls or test executions.

## Inputs and X-family baseline

Actual launch source was `657edda357539fb6640533ca3de557c5f91f5970`. All 459 launch source hashes and 238 readback source hashes match ticket15. Unchanged lock, launcher, asset bindings, fixture, service owner and native source review were reused. CPU preparation `ticket17-20261116T205006Z-75dd8d59` and fresh admission passed. Actual launch evidence is `ticket17-20261116T205539Z-5bec4388`, bound to environment `cy-it-ded7c4` and the recorded current WSL boot and namespace UID. The five-second query timeout, 10 GiB reserve and two-epoch limit remained unchanged.

The frozen corpus identity is `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`, with seed 0 and disjoint 160/40/40 train/validation/test images. The paired JSON separately binds prepared manifest file bytes.

The X-specific derived backbone was independently rehashed as `0eef1d947c36b7201439f5506c4b1262e7a1a75ed1de565b4a17418f5080575d`, bound to HF source revision `c93d816fc9e567563bc068f01475bec89cc634a6`, converter `hf-dinov3-to-deim-v1` and native DEIM revision `1d2ca42171570c713e78fc6a766ec5104b7f4724`. Initial optimizer-parameter SHA256 is `a9dbda79717f5b8e24dbf09a3ef7f75373bffbf3e05bcdde5276e8b743468b83`. This is the first eligible completed X-family baseline found in retained campaign readbacks; no L-family parameter comparison was used.

## Native execution and memory

Case `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-x-default-c2a101d30f` passed in 262.809247 seconds; outer launcher elapsed time was 266.190266 seconds, exit 0. Fresh forced estimation observed batch 8 allocator OOM, batch 4 success, batch 6 success, batch 7 allocator OOM and batch 6 confirmation. Each successful probe completed five warmup steps, ten measured AdamW steps and one validation step. Successful batch 6 peaks were 23,320,068,096 and 23,321,116,672 bytes. Capacity applies to the admitted allocator budget and tested batches.

Two epochs completed at batch 6, FP32, seed 0 and size 640, with 54 optimizer updates, zero skips and changed parameters. The update count independently follows 2 × ceil(160 / 6), with drop_last false. All 136 native epoch loss values and 398 remote scalar loss observations were finite and reconciled against their respective logs. The producer field `verification.native_loss_values` contains the scalar population; readback's same-named field contains native epoch losses. Native epoch validation completed.

Canonical transforms retain native mode with no JSON snapshot. The loader/collator preserve the X recipe: policy epochs 4/29/50, mosaic probability 0.5, mixup/copyblend probability 0.5, base size 640 and stop epoch 50. The full recipe is retained in the paired JSON. Configuration does not prove every optional or epoch-gated transform fired during this two-epoch run.

All 256 outer telemetry samples met the 10,240 MiB reserve and user's 8 GiB floor. Minimum free VRAM was 10,339 MiB; maximum completed sample gap was 1.246298 seconds. No outer query timeout occurred. These are sampled observations, not continuous reserve, playback frame-time or historical WSL hang evidence.

## Publication and CPU readback

Project `cy-it-ded7c4 ticket17` produced task `96137d22aa344cedbefdbf6e08919a4c` and Output Model `c0546ba3bd44420789f10b672ea8c501`. Checkpoint SHA256 is `cb5efefc12a26baaa2a564b8233497cd5dc56904ab4b0051ca40dd2e1af2fed7`. Fresh readback `readback/20261116T210148Z-6e27fb3b` passed from 21:01:48 to 21:02:37 UTC using the unchanged reviewed helper.

Eight enabled artifacts and checkpoint bytes were forced through a fresh SDK cache and independently rehashed. Task/model identity, configuration, thresholds and checkpoint metadata agreed. All 80 held-out images and 34 backgrounds were accounted for without decoded-pixel leakage. Native CY CPU prediction reloaded the checkpoint and processed 40 validation images, including 15 backgrounds, yielding 12,000 detections. Exact-threshold scoring totals were TP 0, FP 3, FN 64. This is execution/publication evidence, not scientific accuracy, separate upstream solver validation or export parity.

## Protected cleanup and remaining scope

Independent acceptance review found no blocker. Launcher/worker cleanup passed. The coordinator confirmed known native and CPU readback PIDs absent and the exact-case process scan empty, then rehashed 122 protected case files before and after removing only:

- Case `dataset-cache`: 249 files, 24,345,320 logical bytes.
- Successful readback `cache`: 9 files, 836,219,539 logical bytes.

The passed cleanup receipt records 860,564,859 logical bytes removed. Every checkpoint, retained artifact, CPU prediction, native input/log, receipt, fixture, shared asset, previous case and service remained protected. Ticket18's separate readback was untouched; no global process or compute-empty claim is made. Physical filesystem reclaim was not separately attributed.

Selected preparation, admission, training, measured capacity, native recipe, X initialization, source applicability, publication, CPU prediction/scoring, sampled reserve, independent review and cleanup checks passed. Physical multi-GPU, other backend cases, scientific accuracy and export compilation/runtime parity remain separate work. The historical WSL hang cause remains unproven, and earlier failed campaign attempts retain their status.
