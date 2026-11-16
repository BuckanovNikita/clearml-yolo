# Ticket12 DEIMv2 M JSON execution and readback — 2026-11-16

Status: accepted for ticket12; native execution, independent readback/review and protected cache cleanup passed. [Paired JSON evidence](2026-11-16-ticket12-deim-m-json.json) binds the retained observations and protected handoff for `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-m-json-39f7a43a40`.

The applicable contracts are [estimated-batch acceptance](../../014-estimated-batch-acceptance/contracts/acceptance.md), [native detector checkpoints](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison), and the [maintained publication inventory](../../../docs/experiment-records.md#publication-inventory). The coordinator executed the GPU job and separate CPU readback. This task only reconciled existing artifacts and prepared the handoff; no training, inference or remote service check was rerun.

## Source, fixture and initialization

Actual producer source and launch HEAD are `5c0ece16a73ecc9ce279b564b7d69471c69007fa`. The offline audit matched all 552 tracked files under `src/`, `tests/` and `scripts/` to that commit's Git blobs, all 459 launch Python hashes, and the product hashes captured by readback. Dependency lock, registered bindings and retained request/resolved-input/estimate/canonical-configuration hashes also match. `readback/20261116T173602Z-89cfed78/source-applicability.json` retains detailed identities; its `launch/` directory preserves byte-identical copies of all seven original launcher files.

The frozen manifest is `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`, with seed 0 and disjoint 160/40/40 train/validation/test images. The selected architecture is `deimv2/m`, using the registered `vittplus_distill.pt` and DEIM source revision `1d2ca42171570c713e78fc6a766ec5104b7f4724`. Their exact source/backbone identities were locally rechecked against the readback. Initial optimizer-parameter SHA256 `35ceec789217dba1fecbe4aae9b97331128e73a542fa7cfd5540b6157f24774b` matches ticket11's M-family native case. No S-family initialization comparison is used.

## Native execution, capacity and JSON augmentation

The scenario completed in 201.92 seconds; launcher elapsed time was 205.72 seconds, exit 0, with worker cleanup complete. The native pytest wrapper reported one passed case in 204.00 seconds. The recipe retained two epochs, FP32, seed 0, nominal/effective size 640 and EMA.

Fresh estimation succeeded at batches 8 and 16, encountered the configured allocator limit at batch 24, then reconfirmed batch 16. Every successful trial recorded five warmup steps, ten measured AdamW steps and one validation step at its actual requested batch. Batch-16 peak observations were 21,761,884,160 and 21,759,787,008 bytes. Validated raw capacity 16 selected training batch 16 without fallback. This is capacity under the admitted allocator budget and 10 GiB reserve, not unrestricted physical GPU capacity or proof of untested intermediate batches.

Native epochs 0 and 1 completed with 20 optimizer updates, zero skipped updates and changed parameters. Native scalar/log losses and both epoch validation summaries are finite. The canonical Albumentations snapshot exactly matches retained `pipeline.json`: HorizontalFlip and RandomBrightnessContrast, each with probability 1, Pascal-VOC boxes and class labels. Snapshot SHA256 is `bfdd9c00d36be4d222068553563e91dcde506316a6b78751cfe45e769f975e09`. Resolved inputs, native execution and remote canonical configuration retain the same JSON recipe. No separate rendered augmentation-image audit is claimed.

The selected RTX 5090 UUID is `GPU-7459c4c9-b94d-ca31-17b0-fc63140c4dc1`. All 193 retained NVML samples were valid, with minimum free memory 10,490 MiB, above the 10,240 MiB internal reserve and user's 8 GiB floor. Maximum sampled used memory was 21,698 MiB, maximum utilization 79%, and maximum sample gap 1.353 seconds. These finite samples do not establish continuous memory or frame-time behavior.

## Fresh-client publication and CPU checkpoint readback

The unchanged reviewed helper SHA256 is `25be67d9975f6c2266bd4681ae92219cca0bdb22c06facca7c344b4c5cb492ab`. Its successful independent-client readback ran from 17:36:02 to 17:36:31 UTC, with CUDA hidden and two numerical threads. Receipt: `readback/20261116T173602Z-89cfed78/receipt.json`. Coordinator session 25265 exited 0; retained launcher and readback logs report success.

Environment: `cy-it-adb183`; project: `cy-it-adb183 ticket12`; task: `c2fd03170005460d8e6c4e93601a0244`; sole best Output Model: `6a1bae674cd04a1985357cf918bbf004`. Downloaded `best_stg1.pth` has SHA256 `14f188ab4f97fccbc48ac6d40895bbdd1b3494db8971852031a2568d1b94e01e`, identical to the native checkpoint and producer verification.

The readback forced downloads of all eight enabled publications and checkpoint bytes through a new SDK cache. It verified completed stage outcomes, canonical configuration, native General arguments, asset/source identities, descriptor architecture and class order, exact calibration CSV and typed threshold metadata. The four val/test full/DTRK workbooks retain 376 finite available numeric cells while preserving unavailable values. Ninety scalar-loss observations and 96 native log loss values are finite. Published results retain all 80 held-out images and 34 backgrounds without decoded-pixel leakage. The offline audit independently rehashed these downloads and repeated local population and exact-threshold checks.

The downloaded checkpoint loaded through CY's public descriptor reader and native DEIM CPU prediction adapter. It processed all 40 validation images, including 15 backgrounds, and produced 12,000 finite raw detections. Scoring used the exact published thresholds and canonical IoU/matching policy, yielding TP 0, FP 2, FN 64 and preserving every GT object. The published class-2 threshold is exactly 0.0 and was preserved. This is native CPU prediction plus CY scoring, not a separate upstream solver-validation loop, numerical parity, accuracy qualification or export validation.

## Protected handoff and authorized cleanup

`case/handoff.json` retains the provisional `accepted` status until coordinator acceptance and now protects 127 files, including the final cleanup receipt. All 126 original protected files totaling 971,861,764 logical bytes were rehashed unchanged before and after cleanup. Checkpoints, probe inputs/results, configuration/source receipts, artifact copies, CPU predictions and copied launch evidence remain protected. The handoff retains reusable checkpoint/task/model identities, exact thresholds and corpus/source identities, excluding itself and the two identified duplicate caches.

The original protected `readback/20261116T173602Z-89cfed78/cleanup-plan.json` identifies these exact trees. Root independently reviewed the scientific evidence, rehashed all 126 protected files and 238 product sources, and inspected containment, absence of symlinks, counts and bytes before authorizing deletion. Those path and file checks were repeated immediately before removal:

- Case `dataset-cache`: 249 files, 24,344,597 logical bytes.
- Successful readback `cache`: 9 files, 310,594,540 logical bytes.

Actual removal was 334,939,137 logical bytes across 258 files. `readback/20261116T173602Z-89cfed78/cleanup.json` records authorization, exact removals and unchanged protected hashes. Physical filesystem reclaim was not separately attributed during concurrent work. No separate CPU media duplicates were created. Checkpoints, prior cases, shared assets and services remain untouched; no task-owned evidence process remains.

Native training, measured capacity, JSON recipe identity, independent publication, CPU prediction/scoring, native validation, source applicability, sampled reserve, launcher cleanup, independent review and authorized cache removal passed. Ticket12 is accepted within the stated native, readback and sampled-reserve scope; the broader campaign remains open.
