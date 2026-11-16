# Ticket14 DEIMv2 L native execution and readback — 2026-11-16

Status: accepted for ticket14; native execution, independent readback/review and protected cache cleanup passed. [Paired JSON evidence](2026-11-16-ticket14-deim-l-native.json) binds the retained observations and protected handoff for `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-l-default-a384da92a0`.

The applicable contracts are [estimated-batch acceptance](../../014-estimated-batch-acceptance/contracts/acceptance.md), [native detector checkpoints](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison), and the [maintained publication inventory](../../../docs/experiment-records.md#publication-inventory). The coordinator executed the native GPU job and separate CPU readback. This task only reconciled retained artifacts and prepared the protected manifest; it did not rerun training, prediction or service calls.

## Source, fixture and L-family initialization

Actual producer and launch HEAD is `ba56e2f2751954fb9c65799817d22b9e51b36b89`. Its `src/`, `tests/` and `scripts/` trees are exactly equal to those at `5c0ece16a73ecc9ce279b564b7d69471c69007fa`. Offline reconciliation matched all 552 tracked inputs against the producer commit, all 459 launch Python hashes, and every product hash captured by readback. Dependency lock, registered asset bindings and retained request/resolved-input/estimate/canonical-configuration hashes also match. Detailed identities are protected in `readback/20261116T174737Z-c420f862/source-applicability.json`, with byte-identical copies of all seven launcher files in its `launch/` directory.

The frozen manifest is `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`, with seed 0, disjoint 160/40/40 images and ordered classes 1–4. The selected model is `deimv2/l`; the approved derived initialization is `hf-dinov3-to-deim-v1.pth`, SHA256 `8e720f25b9871695253f8392b4089aa27b2f48c22e4b769a7899f3ff886a882d`. Its registered derivation binds the HF DINOv3 source commit `114c1379950215c8b35dfcd4e90a5c251dde0d32`, source weight SHA256 `4610ad75edef83e75afdebf162d148dc628045ea6cbb83d67d4708c709c4f91d`, converter `hf-dinov3-to-deim-v1`, and native DEIM revision `1d2ca42171570c713e78fc6a766ec5104b7f4724`. The launcher/readback checked the registered derived asset; this audit rechecked backbone bytes and the cached native source identity locally.

Initial optimizer-parameter SHA256 is `020a40c391e18e0e92829139b4012c987a16a3460b12c0364326a084c8d5be11`. No other completed L-family case was available at audit time, so this records the L-family baseline with zero cross-variant comparisons. M/S-family parameters are not used as substitutes.

## Native execution and memory observations

The scenario completed in 237.32 seconds; launcher elapsed time was 240.30 seconds, exit 0, with worker cleanup complete. The native pytest wrapper reported one passed case in 238.92 seconds. The recipe retained two epochs, FP32, seed 0, nominal/effective size 640, native augmentation and EMA.

Fresh estimation succeeded at batch 8, encountered the configured allocator limit at batch 16, then reconfirmed batch 8. Both successful trials recorded five warmup steps, ten measured AdamW steps and one validation step at actual batch 8. Peak observations were 22,435,069,952 and 22,430,875,648 bytes. Validated raw capacity 8 selected training batch 8 without fallback. These measurements establish capacity under the admitted allocator budget and 10 GiB reserve, not unrestricted physical GPU capacity or untested intermediate batch sizes.

Native epochs 0 and 1 completed with 40 optimizer updates, zero skipped updates and changed parameters. Native scalar/log losses and both epoch validation summaries are finite. Canonical transforms retain native mode with no JSON file or snapshot. The paired JSON preserves the selected DEIM augmentation sequence and collator policy; native loader batches and resize configuration agree with the selected recipe. The presence of configured probabilistic/epoch-gated transforms does not prove every optional transform fired during this two-epoch smoke run.

All 213 retained NVML samples for RTX 5090 UUID `GPU-7459c4c9-b94d-ca31-17b0-fc63140c4dc1` were valid. Minimum free memory was 10,488 MiB, above the 10,240 MiB internal reserve and user's 8 GiB floor. Maximum sampled used memory was 21,700 MiB, maximum utilization 71%, and maximum observed sample gap 3.092 seconds. This gap is retained rather than represented as a continuous or fixed-frequency measurement. No continuous reserve or frame-time proof is claimed.

## Independent publication and CPU checkpoint readback

The unchanged reviewed helper SHA256 is `25be67d9975f6c2266bd4681ae92219cca0bdb22c06facca7c344b4c5cb492ab`. The fresh-client readback ran from 17:47:37 to 17:48:25 UTC with CUDA hidden and two numerical threads. The passed receipt is `readback/20261116T174737Z-c420f862/receipt.json`; coordinator session 50026 exited 0 and retained native/readback logs report success.

Environment: `cy-it-adb183`; project: `cy-it-adb183 ticket14`; task: `1cd852821dda4b9a84c53e1a71553bd0`; sole best Output Model: `2fdf61138d4743b7b4488aba06dffc81`. Downloaded `best_stg1.pth` has SHA256 `ea2adf44d240480d2d11b19586d931ec71c347648b694e7ffe07f9c787b97ced`, matching the original native checkpoint and producer verification.

The readback forced all eight enabled artifact downloads and checkpoint bytes through a fresh SDK cache. It checked completed pipeline stages, canonical configuration, native General arguments, source/derived-backbone provenance, descriptor architecture and class order, exact calibration CSV and typed threshold metadata. The four val/test full/DTRK workbooks retain 376 finite available numeric cells while preserving unavailable values. There are 186 finite scalar-loss observations and 96 finite native log loss values. Published results retain all 80 held-out images and 34 backgrounds without decoded-pixel leakage. The offline audit independently rehashed downloads and repeated local population and exact-threshold checks.

The downloaded checkpoint loaded through CY's public descriptor reader and native DEIM CPU predictor. It processed all 40 validation images, including 15 backgrounds, producing 12,000 finite raw detections. Scoring with exact published thresholds and canonical IoU/matching policy yielded TP 0, FP 0, FN 64, accounting for all GT objects. This is native CPU prediction plus CY scoring, not a separate upstream solver-validation loop, numerical parity, scientific accuracy qualification or export verification.

## Protected handoff and authorized cleanup

`case/handoff.json` retains its provisional `accepted` status until coordinator acceptance and now protects 123 files, including the cleanup receipt. All 122 original protected files totaling 1,654,658,462 logical bytes were rehashed unchanged before and after removal. It retains native checkpoints, probe inputs/results, source/configuration receipts, artifacts, CPU predictions and copied launch evidence, together with reusable checkpoint/task/model identities, exact thresholds and corpus/source identity. The manifest excludes itself and the two duplicate caches.

The original protected `readback/20261116T174737Z-c420f862/cleanup-plan.json` identifies these exact trees. Root independently rehashed all 122 protected files and inspected paths/counts/bytes/symlinks, and reviewer `final_recipe_review` independently approved the evidence before root authorized deletion. Containment, absence of symlinks and exact counts/bytes were rechecked immediately before removing:

- Case `dataset-cache`: 249 files, 24,345,320 logical bytes.
- Successful readback `cache`: 9 files, 538,148,058 logical bytes.

Actual removal totaled 562,493,378 logical bytes across 258 files. `readback/20261116T174737Z-c420f862/cleanup.json` records authorization, exact removals and unchanged protected hashes. Physical filesystem reclaim was not separately attributed during concurrent campaign work. No separate CPU media duplicates were created. Shared assets, services, earlier cases and checkpoints remain intact; no task-owned evidence process remains.

Native training, measured capacity, native recipe identity, independent publication, CPU checkpoint prediction/scoring, native validation, source applicability, sampled reserve, launcher cleanup, independent review and authorized cache removal passed. Ticket14 is accepted within the stated native, readback and sampled-reserve scope; the broader campaign remains open.
