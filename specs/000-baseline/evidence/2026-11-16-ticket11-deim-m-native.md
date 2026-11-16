# Ticket11 DEIMv2 M native execution and readback — 2026-11-16

Status: accepted for ticket11; native execution, independent readback/review and protected cache cleanup passed. [Paired JSON evidence](2026-11-16-ticket11-deim-m-native.json) binds the retained observations and protected handoff for `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-m-default-7aa523d541`.

The applicable contracts are [estimated-batch acceptance](../../014-estimated-batch-acceptance/contracts/acceptance.md), [native detector checkpoints](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison), and the [maintained publication inventory](../../../docs/experiment-records.md#publication-inventory). The coordinator executed the native GPU job and separate CPU readback. This task only audited existing artifacts and prepared the handoff; it did not rerun training, inference or service calls.

## Source, fixture and initialization

Actual producer source and launch HEAD are `5c0ece16a73ecc9ce279b564b7d69471c69007fa`. The later ticket10 documentation commit does not replace this execution identity. Independent offline reconciliation matched all 552 tracked `src/`, `tests/` and `scripts/` files to that commit's Git blobs, all 459 launch Python SHA256 values, and every product hash captured by readback. Dependency lock, registered asset bindings and retained request/resolved-input/estimate/canonical-configuration hashes also match. Detailed identities are in `readback/20261116T172855Z-b7392b58/source-applicability.json`; byte-identical copies of all seven launcher files are in its `launch/` directory.

The frozen manifest is `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`, with seed 0 and disjoint 160/40/40 train/validation/test images. The selected architecture is `deimv2/m`, with the registered `vittplus_distill.pt` initialization and pinned DEIM source revision `1d2ca42171570c713e78fc6a766ec5104b7f4724`. Their retained source/backbone identities were checked locally again against the successful readback.

The initial optimizer-parameter hash is `35ceec789217dba1fecbe4aae9b97331128e73a542fa7cfd5540b6157f24774b`. At audit time the subsequently completed M-family JSON case `deimv2-m-json-39f7a43a40` also had a passed native summary and the same initialization hash. The paired JSON binds those two comparison receipts. This is one within-M-family initialization comparison, not acceptance of ticket12 or a comparison with S-family parameters.

## Native execution, capacity and augmentation

The scenario completed in 175.39 seconds; launcher elapsed time was 178.96 seconds, exit 0, with worker cleanup complete. Its native pytest wrapper reported one passed case in 177.60 seconds. The recipe used two epochs, FP32, seed 0, nominal/effective size 640, native augmentation and EMA.

Fresh estimation succeeded at batch 8, encountered the configured allocator limit at batch 16, then independently reconfirmed batch 8. Both successful trials executed five warmup steps, ten measured AdamW steps and one validation step at actual batch 8. Peak observations were 18,611,961,856 and 18,607,767,552 bytes. Validated raw capacity 8 selected training batch 8 without fallback. This is capacity under the admitted budget and 10 GiB reserve, not unrestricted physical capacity or proof of untested intermediate batches.

Native epochs 0 and 1 completed with 40 optimizer updates, zero skipped updates and changed parameters. Finite scalar losses, native loss summaries and native validation results are retained. Canonical transforms remain exactly native mode with no JSON file or snapshot. Native arguments retain the selected DEIM transform sequence, including its Mosaic, photometric, zoom/crop, flip, resize, normalization and box-conversion configuration, with matching native loader batches. The full native augmentation and collator policy is recorded in the paired JSON. Epoch gates and probabilities remain part of that native recipe; this evidence does not claim that every optional transform fired during the two-epoch smoke run.

The selected RTX 5090 UUID is `GPU-7459c4c9-b94d-ca31-17b0-fc63140c4dc1`. All 170 retained NVML samples were valid. Minimum free memory was 10,374 MiB, above the 10,240 MiB internal reserve and user's 8 GiB floor. Maximum sampled used memory was 21,814 MiB; maximum utilization was 87%; maximum sampling gap was 1.276 seconds. These finite samples do not establish continuous memory or frame-time behavior.

## Independent publication and CPU checkpoint readback

The unchanged independently reviewed helper hash is `25be67d9975f6c2266bd4681ae92219cca0bdb22c06facca7c344b4c5cb492ab`. The successful fresh-client readback ran from 17:28:55 to 17:29:23 UTC with CUDA hidden and two numerical threads. Its receipt is `readback/20261116T172855Z-b7392b58/receipt.json`. Coordinator sessions 58101 and 80403 exited 0; the retained native and readback logs report success.

Environment: `cy-it-adb183`; project: `cy-it-adb183 ticket11`; task: `531b6870764942fd9db4118243e25a32`; sole best Output Model: `5b7d13cbbd8d4b75ba82ffd6ea8fb13f`. Downloaded `best_stg1.pth` has SHA256 `8a32aaea11a637260bf9b3d634f227edfc89d0d9c571f41d4db914b1febc7ab1`, matching the native checkpoint and producer verification.

Forced downloads independently verified all eight enabled publications and checkpoint bytes through a fresh SDK cache. The readback checked completed pipeline stages, canonical configuration, native General arguments, model/source/backbone provenance, embedded descriptor and class order, exact calibration CSV and typed threshold metadata. Four full/DTRK val/test workbooks retain 376 finite available numeric cells and preserve unavailable values. There are 186 finite scalar-loss observations and 96 finite native log loss values. Published results retain all 80 held-out images and 34 backgrounds without decoded-pixel leakage. This offline audit repeated local download hashes, population checks and threshold identity checks without repeating remote calls.

The independent checkpoint loaded through CY's public descriptor reader and native DEIM CPU prediction adapter. All 40 validation images, including 15 backgrounds, produced 12,000 finite raw detections. Scoring with the published fixed thresholds and canonical IoU/matching policy yielded TP 0, FP 1, FN 64, accounting for every GT object. This is native CPU prediction plus CY scoring, not a separate upstream solver-validation loop, CPU/GPU numerical parity, accuracy qualification or export verification.

## Protected handoff and authorized cleanup

`case/handoff.json` is `accepted` and now protects 123 retained files, including the final cleanup receipt. All 122 original protected files, totaling 971,759,780 logical bytes, were rehashed unchanged before and after deletion. The manifest includes native checkpoints, probe inputs/results, configuration/source receipts, artifact copies, CPU predictions and copied launch evidence. It retains reusable checkpoint/task/model identities, thresholds and the exact corpus/source identity. The manifest excludes itself and only the two identified duplicate caches.

The original protected `readback/20261116T172855Z-b7392b58/cleanup-plan.json` identifies these two trees. Root independently rehashed all 122 protected files and inspected the exact cache paths/counts/bytes before authorizing deletion. Containment, absence of symlinks and exact file counts/bytes were checked again immediately before removal:

- Case `dataset-cache`: 249 files, 24,345,320 logical bytes.
- Successful readback `cache`: 9 files, 310,580,291 logical bytes.

Actual removal was 334,925,611 logical bytes across 258 files. `readback/20261116T172855Z-b7392b58/cleanup.json` records the authorization, exact removals and unchanged protected hashes. Physical filesystem reclaim was not separately attributed during concurrent campaign work. No separate CPU media duplicates were created. Checkpoints, earlier cases, shared assets and services remain intact; no task-owned evidence process remains.

Native training, capacity estimation, native recipe identity, independent publication, CPU checkpoint prediction/scoring, native validation, source applicability, sampled reserve, launcher cleanup and authorized cache removal passed. Independent reviewer `final_recipe_review` approved the evidence, and root rehashed all 123 final protected files and verified exact cache absence. Ticket11 is accepted within the stated native, readback and sampled-reserve scope; ticket12 and the broader campaign have separate evidence.
