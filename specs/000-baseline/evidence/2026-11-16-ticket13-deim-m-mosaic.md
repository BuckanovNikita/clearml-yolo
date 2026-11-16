# Ticket13 DEIMv2 M JSON+Mosaic execution and readback — 2026-11-16

Status: accepted for ticket13; native execution, independent readback/review and protected cache cleanup passed. [Paired JSON evidence](2026-11-16-ticket13-deim-m-mosaic.json) binds the retained observations and protected handoff for `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-m-json_mosaic-64c66241b4`.

The applicable contracts are [estimated-batch acceptance](../../014-estimated-batch-acceptance/contracts/acceptance.md), [native detector checkpoints](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison), and the [maintained publication inventory](../../../docs/experiment-records.md#publication-inventory). The coordinator executed the native GPU job and separate CPU readback. This task only audited retained artifacts and prepared the handoff; it did not rerun training, prediction or service calls.

## Source and scientific inputs

The actual producer and launch HEAD is `ba56e2f2751954fb9c65799817d22b9e51b36b89`. Its `src/`, `tests/` and `scripts/` Git tree identities are exactly equal to those at `5c0ece16a73ecc9ce279b564b7d69471c69007fa`; the successor contains documentation changes. The offline audit matched all 552 tracked inputs to the actual producer commit, rehashed all 459 launch Python inputs, and checked the readback's product hashes, dependency lock and registered asset bindings. Detailed identities are in `readback/20261116T174305Z-2d91dc08/source-applicability.json`. Its `launch/` directory retains byte-identical copies of all seven launcher files.

The initial offline audit safely refused a copied assertion expecting the older HEAD before writing evidence or a handoff. The corrected audit binds the actual recorded producer and proves product-tree equivalence. The retained `initial-audit-source-head-refusal.txt` distinguishes this local audit assumption error from the successful native execution and readback.

The frozen manifest is `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`: seed 0, disjoint 160/40/40 images and ordered classes 1–4. Request, resolved inputs, estimate and canonical configuration hashes match. The registered M-family `vittplus_distill.pt` backbone and DEIM source revision `1d2ca42171570c713e78fc6a766ec5104b7f4724` were locally rechecked against the successful readback. Initial optimizer-parameter SHA256 `35ceec789217dba1fecbe4aae9b97331128e73a542fa7cfd5540b6157f24774b` matches both M-family native and JSON cases; S-family initialization is not used for this comparison.

## Native execution and reserve

The native scenario passed in 208.04 seconds; launcher elapsed time was 211.05 seconds, exit 0, with owned worker cleanup complete. Its native pytest wrapper reported one passed case in 209.86 seconds. The recipe retained `deimv2/m`, FP32, seed 0, nominal/effective size 640 and EMA.

Fresh estimation succeeded at batches 8 and 16, reached the configured allocator limit at batch 24, then successfully reconfirmed batch 16. Successful trials executed five warmup steps, ten measured AdamW steps and one validation step at their actual requested batch. Batch-16 peak observations were 22,300,852,224 and 22,296,657,920 bytes. Validated raw capacity 16 selected training batch 16 without fallback. This establishes capacity under the admitted budget and 10 GiB reserve, not unrestricted physical GPU capacity or untested intermediate sizes.

Native epochs 0 and 1 completed with 20 optimizer updates, zero skipped updates and changed parameters. Native scalar/log losses and both epoch validation summaries are finite. Canonical augmentation matches retained `pipeline.json`: a 2×2 Mosaic targeting 640×640, HorizontalFlip and RandomBrightnessContrast, each with probability 1, Pascal-VOC boxes and class labels. Snapshot SHA256 is `049739959eebe7b4291c3b22a4d56b9eb3b105e277f0c422a5d956a89ec353ff`. Resolved inputs, actual native training and remote canonical configuration retain this JSON recipe. No separate rendered augmentation-image audit is claimed.

All 197 retained NVML samples for RTX 5090 UUID `GPU-7459c4c9-b94d-ca31-17b0-fc63140c4dc1` were valid. Minimum free memory was 10,390 MiB, above the 10,240 MiB internal reserve and user's 8 GiB floor. Maximum sampled used memory was 21,798 MiB, maximum utilization 99%, and maximum sample gap 1.492 seconds. These finite observations do not prove continuous memory or frame-time behavior.

## Fresh-client publication and CPU readback

The unchanged reviewed helper SHA256 is `25be67d9975f6c2266bd4681ae92219cca0bdb22c06facca7c344b4c5cb492ab`. Readback ran from 17:43:05 to 17:43:33 UTC with CUDA hidden and two numerical threads. The passed receipt is `readback/20261116T174305Z-2d91dc08/receipt.json`; coordinator session 27615 exited 0 and retained launcher/readback logs report success.

Environment: `cy-it-adb183`; project: `cy-it-adb183 ticket13`; task: `fd8141f44ce245599b0152ad2bc15d7d`; sole best Output Model: `e3843e508dab41d4b1c4e73d27ed236c`. Downloaded `best_stg1.pth` SHA256 is `6d7c9bcaab952e5be10aeeb7f143ff03de1bfb2a29a2da22fdc26ef8aeb7931e`, matching native checkpoint bytes and producer verification.

The independent client forced all eight enabled publication downloads and the checkpoint through a fresh SDK cache. It checked completed stage outcomes, canonical configuration, native General arguments, asset/source provenance, embedded descriptor and class order, exact calibration CSV and typed threshold metadata. Four full/DTRK val/test workbooks retain 376 finite available numeric cells while preserving unavailable values. Ninety scalar-loss observations and 96 native log loss values are finite. Published results retain all 80 held-out images and 34 backgrounds without decoded-pixel leakage. The offline audit repeated download hashes, population checks and exact-threshold checks locally.

The downloaded checkpoint loaded through CY's public descriptor reader and native DEIM CPU predictor. All 40 validation images, including 15 backgrounds, produced 12,000 finite raw detections. Scoring with the exact published thresholds and canonical IoU/matching policy yielded TP 0, FP 2, FN 64, accounting for every GT object. This is native CPU prediction plus CY scoring, not a separate upstream solver-validation loop, CPU/GPU numerical parity, accuracy qualification or export verification.

## Protected handoff and authorized cleanup

`case/handoff.json` retains its provisional `accepted` status until coordinator acceptance and now protects 129 files, including the final cleanup receipt. All 128 original protected files totaling 971,904,066 logical bytes were rehashed unchanged before and after removal. The manifest retains native checkpoints, probes, input/configuration/source receipts, artifacts, CPU predictions and copied launch evidence, together with reusable checkpoint/task/model identities, exact thresholds and corpus/source identity. It excludes itself and the two duplicate cache trees.

The original protected `readback/20261116T174305Z-2d91dc08/cleanup-plan.json` identifies these exact paths. Root independently reviewed the scientific evidence, rehashed all 128 protected files and 238 product sources, and inspected containment, absence of symlinks, counts and bytes before authorizing deletion. Those checks were repeated immediately before removal:

- Case `dataset-cache`: 249 files, 24,346,284 logical bytes.
- Successful readback `cache`: 9 files, 310,604,262 logical bytes.

Actual removal totaled 334,950,546 logical bytes across 258 files. `readback/20261116T174305Z-2d91dc08/cleanup.json` records authorization, exact removals and unchanged protected hashes. Physical filesystem reclaim was not separately attributed during concurrent campaign work. No separate CPU media duplicates were created. Shared assets, services, checkpoints and earlier cases remain intact. No task-owned evidence process remains.

Native training, measured capacity, JSON+Mosaic identity, independent publication, CPU prediction/scoring, native validation, source applicability, sampled reserve, launcher cleanup, independent review and authorized cache removal passed. Ticket13 is accepted within the stated native, readback and sampled-reserve scope; the broader campaign remains open.
