# Ticket15 DEIMv2 L JSON execution and readback — 2026-11-16

Status: accepted within the native ticket15 scope. Execution, independent publication readback, acceptance review and protected cache cleanup passed. Coordinator review, commit and the native documentation verification route remain pending. [Paired JSON evidence](2026-11-16-ticket15-deim-l-json.json) binds the retained receipts; the broader campaign remains open.

Applicable contracts are [estimated-batch acceptance](../../014-estimated-batch-acceptance/contracts/acceptance.md), [native detector checkpoints](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison), and the [publication inventory](../../../docs/experiment-records.md#publication-inventory). The coordinator executed the GPU run, separate CPU readback and cleanup. The independent audit reconciled retained evidence; this dated-record task made no live calls or test executions.

## Inputs and admission

The actual launch source was `15e47f2cd45550904dfd97af029e3fe798bf065e`. All 459 launch Python hashes and 238 readback product hashes matched; dependency lock, launcher, asset bindings and initialization bytes remained unchanged. The frozen corpus identity is `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`, with seed 0 and disjoint 160/40/40 train/validation/test images. The JSON record separately binds the prepared manifest file bytes.

CPU preparation passed at `ticket15-20261116T201135Z-5ef329fa`. Fresh admission at 20:26:18 UTC bound WSL boot `5e9f68d1-63db-4188-9995-e686745fda8c`, environment `cy-it-ded7c4`, its current namespace UID and remaining service lifetime. Admission observed 28,685 MiB free VRAM and no compute processes. The launcher retained its five-second query timeout, 10 GiB reserve and two-epoch limit. Actual preparation/launch evidence is under `.tmp/verification-gap-closure/backend-preparation/ticket15-20261116T202619Z-59d79204`.

The registered L-family backbone SHA256 is `8e720f25b9871695253f8392b4089aa27b2f48c22e4b769a7899f3ff886a882d`, with native DEIM revision `1d2ca42171570c713e78fc6a766ec5104b7f4724`. Initial optimizer-parameter SHA256 `020a40c391e18e0e92829139b4012c987a16a3460b12c0364326a084c8d5be11` matches the recorded ticket14 L-family baseline.

## Native result and sampled memory

Case `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-l-json-6735466407` passed in 203.831676 seconds; outer launcher elapsed time was 206.535121 seconds, exit 0. Fresh forced estimation succeeded at batch 8, encountered allocator OOM at batch 16, and reconfirmed batch 8. Both successful probes performed five warmup steps, ten measured AdamW steps and one validation step. Their peak observations were 15,666,511,872 and 15,665,463,296 bytes. This establishes tested capacity under the admitted allocator budget, rather than unrestricted physical capacity.

Training completed epochs 0 and 1 at batch 8, FP32, seed 0 and size 640, with 40 optimizer updates, zero skipped updates and changed parameters. All 96 native epoch loss values and 186 remote scalar loss values were finite; these are distinct populations. Native epoch validation completed. The JSON augmentation snapshot is `bfdd9c00d36be4d222068553563e91dcde506316a6b78751cfe45e769f975e09`: HorizontalFlip and RandomBrightnessContrast, each with probability 1. Snapshot, native recipe and unchanged adapter execution agree; additional native mosaic/mixup/copyblend were disabled. No per-image transform trace is claimed.

All 199 outer telemetry samples met the 10,240 MiB reserve and the user's 8 GiB floor. Minimum free VRAM was 10,386 MiB; maximum completed sample gap was 1.086254 seconds. No five-second outer query timeout occurred. These observations do not establish continuous reserve, playback frame times or the cause of the historical WSL hang.

## Publication and CPU readback

Project `cy-it-ded7c4 ticket15` produced task `dcd5ca36885948c1b6b3684813a4155e` and Output Model `3592db15f02143a9a8ed24210a4360c2`. The checkpoint SHA256 is `cd880153abffe67762a7cfb5a6e5b3375539bea559f0ecf5765003ecdd51f5ba`. Fresh readback `readback/20261116T203034Z-72bb8d59` passed from 20:30:34 to 20:31:13 UTC using the unchanged reviewed helper.

Readback forced all eight enabled artifact downloads and checkpoint bytes through a fresh cache. Artifact hashes, canonical configuration, task/model identity, calibration thresholds and checkpoint metadata agreed. All 80 held-out images and 34 backgrounds were accounted for without decoded-pixel leakage. Native CY CPU prediction reloaded the checkpoint and processed 40 validation images, including 15 backgrounds, yielding 12,000 raw detections and fixed-threshold scoring. This is execution and publication evidence, not scientific accuracy, separate upstream solver validation or export parity.

## Cleanup and remaining scope

Independent acceptance review found no blocker. Native launcher and worker cleanup passed; recorded launcher/pytest/scenario PIDs were absent and the exact-case process scan was empty. The coordinator then rehashed 116 protected case files before and after removing only:

- Case `dataset-cache`: 249 files, 24,344,597 logical bytes.
- Successful readback `cache`: 9 files, 538,151,497 logical bytes.

The passed cleanup receipt records 562,496,094 logical bytes removed, no matching owned processes and an empty compute list. All checkpoints, retained artifacts, CPU predictions, inputs, logs, receipts, fixtures, shared assets, previous cases and services were preserved. Physical filesystem reclaim was not separately measured.

Selected preparation, admission, native execution, measured capacity, JSON recipe, source applicability, publication, CPU prediction/scoring, sampled reserve, independent review and cleanup checks passed. Physical multi-GPU, other backend cases, scientific accuracy, export compilation and target-runtime parity remain separate work. Earlier failed ticket15 attempts retain their failed status; this fresh success does not diagnose or erase those failures.
