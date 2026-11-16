# Ticket10 DEIMv2 S JSON+Mosaic execution and readback — 2026-11-16

Status: accepted after independent review and coordinator reconciliation. Execution, independent fresh-client readback and authorized cache cleanup passed. [Paired JSON evidence](2026-11-16-ticket10-deim-mosaic.json) binds the retained receipts and protected handoff for case `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-s-json_mosaic-ffbd901c0a`.

This observation follows the [estimated-batch acceptance contract](../../014-estimated-batch-acceptance/contracts/acceptance.md), [native detector checkpoint contract](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison) and [maintained publication inventory](../../../docs/experiment-records.md#publication-inventory). The coordinator executed the native GPU job and separate CPU readback. This evidence task only reconciled and rehashed their retained artifacts; it did not rerun training, prediction or service calls.

## Source and immutable inputs

The actual committed producer source is `5c0ece16a73ecc9ce279b564b7d69471c69007fa`, matching the launch HEAD. Independent offline audit compared all 552 tracked files under `src/`, `tests/` and `scripts/` against their Git blob identities, with no differences, and rehashed all 459 launch Python inputs unchanged. It also verified the readback's product-source hashes, dependency lock and asset binding hashes. `readback/20261116T172011Z-4e38813b/source-applicability.json` retains the per-file identities. All seven original launcher files, including telemetry and readback logs, have byte-identical protected copies in that readback's `launch/` directory.

The frozen corpus manifest is `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`: seed 0, disjoint 160/40/40 images and ordered classes 1–4. Retained request, resolved inputs, estimate and canonical configuration hashes match the measured training receipt. The registered DEIM source tree and initialization backbone were checked locally again; their identities remain identical to the successful readback.

## Native execution and sampled reserve

The native scenario passed in 195.71 seconds; launcher elapsed time was 199.14 seconds, exit 0, with owned worker cleanup complete. The native pytest wrapper reported one passed case in 197.24 seconds. The run used `deimv2/s`, JSON+Mosaic, FP32, seed 0 and nominal/effective resolution 640.

Fresh estimation succeeded at batches 8 and 16, reached the configured allocator limit at batch 24, then successfully reconfirmed batch 16. Each successful trial recorded five warmup steps, ten measured AdamW steps and one validation step at the requested actual batch. The first batch-16 peak was 17,498,374,144 bytes; confirmation peak was 17,496,276,992 bytes. Raw validated capacity 16 selected training batch 16, without silent fallback. This is measured capacity under the admitted allocator budget and 10 GiB reserve, not unrestricted physical GPU capacity or proof of untested intermediate batches.

Training completed native epochs 0 and 1 with 20 optimizer updates, zero skipped updates and changed parameters. Its initial optimizer-parameter hash matches both earlier DEIMv2 S default and JSON cases. Native loss values and both epoch validation summaries are finite. These smoke results do not qualify accuracy.

Canonical augmentation exactly matches retained `pipeline.json` and snapshot SHA `049739959eebe7b4291c3b22a4d56b9eb3b105e277f0c422a5d956a89ec353ff`. The executable Albumentations pipeline contains a 2×2 Mosaic targeting 640×640, followed by HorizontalFlip and RandomBrightnessContrast, each with probability 1, Pascal-VOC boxes and class labels. Resolved inputs, completed native training and remote canonical configuration retain this recipe. This establishes execution with the configured recipe; no separate rendered augmentation-image audit is claimed.

The selected RTX 5090 UUID is `GPU-7459c4c9-b94d-ca31-17b0-fc63140c4dc1`. All 189 retained NVML samples were valid, with minimum free memory 10,362 MiB, above the 10,240 MiB internal reserve and user's 8 GiB floor. Maximum sampled used memory was 21,826 MiB and maximum sample gap 1.158 seconds. These are finite sampled observations, not continuous hardware proof.

## Fresh-client publication and CPU checkpoint readback

The unchanged reviewed helper hash is `25be67d9975f6c2266bd4681ae92219cca0bdb22c06facca7c344b4c5cb492ab`. The coordinator's successful readback ran from 17:20:11 to 17:20:33 UTC, with CUDA hidden and two numerical threads. Its receipt is `readback/20261116T172011Z-4e38813b/receipt.json`; root sessions 99422 and 15125 completed with exit 0 according to the coordinator, and the retained launcher/readback outputs report success.

Environment: `cy-it-adb183`; project: `cy-it-adb183 ticket10`; task: `1b7880df683a49ea90898910f4181a76`; sole best model: `16f16aecd98d4e389b795805bd426d12`. Forced download of `best_stg1.pth` yielded SHA256 `c5f9d08a4b505a3b09708650d6cd7a4e908b77adf6d700fc681a3b6fffa274f1`, identical to the native checkpoint and producer verification.

Independent client readback forced all eight enabled artifact downloads and checkpoint bytes through a new SDK cache. It checked completed stage outcomes, canonical configuration, native General settings, asset/source provenance, descriptor architecture and class order, exact calibration CSV and typed threshold metadata. The four val/test full/DTRK workbooks contain 376 finite available numeric cells while preserving unavailable values. Ninety scalar loss observations and 96 native log loss values are finite. Published populations retain all 80 held-out images and 34 backgrounds without decoded-pixel leakage. The offline evidence audit independently rehashed all downloads and repeated local population and threshold identity checks.

The downloaded checkpoint loaded through CY's public descriptor reader and native DEIM CPU prediction adapter. It processed all 40 frozen validation images, including 15 backgrounds, producing 12,000 finite raw detections. Fixed-threshold scoring used the exact published calibration and canonical IoU/matching policy, yielding TP 1, FP 42, FN 63 and accounting for all 64 GT objects. This is native CPU prediction plus CY scoring; it is not separate upstream solver validation, CPU/GPU numerical parity, export validation or accuracy qualification.

## Protected handoff and authorized cleanup

`case/handoff.json` is `accepted` for ticket10 and protects 127 files with sizes and SHA256 hashes, including the final cleanup receipt. Its reusable checkpoint/task/model identities, exact thresholds, manifest and committed source identity are retained. The handoff excludes itself and the two explicitly disposable caches; it includes native checkpoints, probe evidence, original input/configuration receipts, artifact copies, CPU predictions and copied launch evidence. All 126 original protected files were rehashed unchanged before and after cleanup.

The original cleanup plan remains protected as `readback/20261116T172011Z-4e38813b/cleanup-plan.json`. Root independently rehashed all 126 protected files and checked the exact two trees for containment, symlinks, counts and bytes. Independent reviewer `final_recipe_review` approved the evidence before root authorized deletion. Only these trees were removed:

- Case `dataset-cache`: 249 files, 24,346,284 logical bytes.
- Successful readback `cache`: 9 files, 173,586,921 logical bytes.

Actual removal totals 197,933,205 logical bytes across 258 files. `readback/20261116T172011Z-4e38813b/cleanup.json` records the authorized deletion and unchanged protected hashes. Physical filesystem reclaim was not independently attributed during concurrent campaign work. No separate CPU media duplicate directory was created. Shared assets, services, checkpoints and earlier cases remain untouched. No task-owned process remains from this bounded offline evidence and cleanup task.

Native training, measured capacity, JSON+Mosaic identity, independent publication, CPU prediction/scoring, native epoch validation, source applicability, sampled reserve, launcher worker cleanup, independent review and authorized cache cleanup passed. The coordinator independently verified all127 final protected hashes and cache absence. Ticket10 is accepted; the final evidence-only commit uses the native automatic gate. This does not close the broader campaign.
