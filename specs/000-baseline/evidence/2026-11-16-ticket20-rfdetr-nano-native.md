# Ticket20 RF-DETR nano native execution and readback — 2026-11-16

Status: accepted within the native ticket20 scope. Execution, independent publication readback, acceptance review and protected cache cleanup passed. Coordinator review, commit and the native documentation verification route remain pending. [Paired JSON evidence](2026-11-16-ticket20-rfdetr-nano-native.json) binds retained receipts; the broader campaign remains open.

Applicable contracts are [estimated-batch acceptance](../../014-estimated-batch-acceptance/contracts/acceptance.md), [native detector checkpoints](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison), and the [publication inventory](../../../docs/experiment-records.md#publication-inventory). The coordinator executed GPU training and cleanup; a separate agent executed CPU readback. Independent review inspected RF-specific configuration, native CSV and helper behavior. This dated-record task made no live calls or test executions.

## Inputs and RF baseline

Actual launch source was `657edda357539fb6640533ca3de557c5f91f5970`. All 459 launch source hashes and 238 readback source hashes match ticket15, allowing shared source/fixture review reuse. Unchanged lock, launcher, asset bindings and service owner were verified. CPU preparation `ticket20-20261116T211443Z-c58141dc` and its fresh admission passed. Actual launch evidence is `ticket20-20261116T211922Z-3d8ba80d`, bound to environment `cy-it-ded7c4`. The five-second query timeout, 10 GiB reserve and two-epoch limit remained unchanged.

The frozen corpus identity is `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`, with seed 0 and disjoint 160/40/40 train/validation/test images. The paired JSON separately binds manifest file bytes.

Registered RF-DETR 1.11.2 nano initialization was rehashed as `d8d6b9ee57d4d0ed2b1f305163624712a0532cb7bce0c747317984fc5457440d`. Initial optimizer-parameter SHA256 is `a45679bd5c1cc935475000d0a3524115b2ad22229d86e7a80ca1cbc31b8b8d6e`. This is the first eligible completed RF-DETR nano baseline found in retained campaign readbacks; no DEIM-family parameter comparison was used. The separate RF/Torchvision readback helper was inspected and hash-bound as `19e906887619a983495c25b27b612963d1efc037f00739afdd1db62a00a53244`.

## Native execution and RF recipe

Case `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/rfdetr-nano-default-425203a1ae` passed in 187.321533 seconds; outer launcher elapsed time was 190.495321 seconds, exit 0. Fresh forced estimation passed batches 8 and 16, reached allocator OOM at 24 and reconfirmed 16. Successful probes each completed five warmup steps, ten measured AdamW steps and one validation step. Batch 16 peaks were 19,576,651,776 and 19,611,254,784 bytes.

Nominal resolution is 384; native scale jitter, expanded scales and per-batch multiscale yield an estimator maximum shape of 544. Actual native augmentation uses `aug_config=null` and the CPU augmentation backend. Capacity applies to this admitted allocator budget and maximum native probe shape, not unrestricted GPU capacity. No per-image transform trace is claimed.

Two epochs completed at batch 16 and seed 0, with 20 optimizer updates, zero skips and changed parameters. Native CSV records steps 9 and 19 and train/validation losses for both epochs. Execution is FP32: CY maps `amp=false` to `amp_dtype=null`, which RF's trainer resolves to `32-true`. Saved `model.amp=true` is a model-config default rather than the executed Lightning precision.

All 34 native CSV loss values and 42 remote scalar losses are finite. These are distinct populations; the producer field `verification.native_loss_values` contains the scalar population. Independent stdlib CSV parsing agreed with the pandas receipt within absolute tolerance 1e-14, with maximum difference 1.11e-16; native CSV bytes matched the recorded digest exactly. RF native epoch validation completed.

All 183 outer telemetry samples met the 10,240 MiB reserve and user's 8 GiB floor. Minimum free VRAM was 11,123 MiB; maximum completed sample gap was 1.084698 seconds. No outer query timeout occurred. These are sampled observations, not continuous reserve, playback frame-time or historical WSL hang proof.

## Publication and CPU readback

Project `cy-it-ded7c4 ticket20` produced task `32f5f1ee107244ebb143aadec900275a` and Output Model `8f7dd80b96d140b3b452b4254e470f1b`. The downloaded RF checkpoint is `checkpoint_best_total.pth`, SHA256 `3cbe74456ecca1783cd5ce51fea0e6f60c34a809fc796d9cef98a59851e61f02`. Fresh readback `readback/20261116T212322Z-f008c375` passed from 21:23:22 to 21:23:38 UTC; local admission and remote executor sessions exited 0.

Eight enabled artifacts and checkpoint bytes were forced through a fresh SDK cache and independently rehashed. Task/model identity, configuration, thresholds, RF descriptor and native CSV agreed. All 80 held-out images and 34 backgrounds were accounted for without decoded-pixel leakage. Native CY CPU prediction reloaded the checkpoint and processed 40 validation images, including 15 backgrounds, yielding 10,884 detections. Exact-threshold scoring totals were TP 7, FP 156, FN 57. This remains smoke execution/publication evidence, not scientific accuracy, separate upstream solver validation or CPU/GPU numerical parity.

## Protected cleanup and remaining scope

Independent review found no blocker. Launcher/worker cleanup passed. The coordinator confirmed five known native/readback PIDs absent, the exact-case process scan empty and cache open-handle scan empty. Unrelated user systemd PID 340 and sd-pam PID 344, whose environments were unreadable, were explicitly excluded. No global compute-empty claim is made.

The coordinator rehashed 119 protected case files before and after removing only:

- Case `dataset-cache`: 249 files, 24,346,043 logical bytes.
- Successful readback `cache`: 9 files, 136,838,416 logical bytes.

The passed cleanup receipt records 161,184,459 logical bytes removed. Every checkpoint, retained artifact, CPU prediction, native input/log, receipt, RF initialization asset, fixture, prior case and service remained protected. Other ticket workloads were untouched. Physical filesystem reclaim was not separately attributed.

Selected preparation, admission, training, capacity, RF recipe/precision, native CSV validation, initialization, source applicability, publication, CPU scoring, sampled reserve, independent review and cleanup checks passed. Physical multi-GPU, other backend cases, scientific accuracy and export compilation/runtime parity remain separate work. The historical WSL hang cause remains unproven and earlier failed campaign attempts retain their status.
