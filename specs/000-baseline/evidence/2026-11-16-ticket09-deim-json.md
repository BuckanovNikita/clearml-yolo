# Ticket09 DEIMv2 S JSON execution and independent readback — 2026-11-16

Status: accepted after independent review and coordinator reconciliation; execution, readback and authorized cache cleanup passed. [Paired JSON evidence](2026-11-16-ticket09-deim-json.json) records raw receipt locations, identities and observations. The case is `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-s-json-22b56424f0`.

This observation follows the [estimated-batch acceptance contract](../../014-estimated-batch-acceptance/contracts/acceptance.md), [native detector checkpoint contract](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison) and [maintained publication inventory](../../../docs/experiment-records.md#publication-inventory). Ticket99 owns the memory-basis correction and its live revalidation criterion; these results do not retroactively accept the earlier failed JSON case.

## Source applicability

The launch recorded root HEAD `0e1d03920725b33c2a6aed68c8ecaa089af17892`, which alone does **not** identify its uncommitted verified ticket99 source. Before launch, the coordinator compared537 tracked source/test inputs with verified commit `ba2b98436638f361c25ce786d5e51e9602190b21`, finding no differences, with full offline coverage and final automatic gate exit0. That original receipt is retained under the successful readback as `ticket99-prelive-source.json`.

This readback independently compared all537 current `src/` and `tests/` Git blob identities against that verified commit, also finding no differences, and rehashed all459 launch Python inputs unchanged. `source-applicability.json` retains the per-file Git and SHA-256 identities. The successful readback directory also retains copies of all six original launcher inputs/results/log/telemetry files. Verified commit identity, launch HEAD and actual working-tree applicability remain distinct.

## Native execution and reserve: passed

Root alone launched and supervised the GPU job. It completed in214.57s; launcher217.91s, exit0, with native worker cleanup complete. Selection `deimv2/s`, variant `json`, seed0, FP32, nominal/effective size640, and the frozen160/40/40 corpus were retained. Corpus manifest SHA: `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`.

Fresh estimation succeeded at batches8,16 and24; batch32 hit the configured allocator limit; a fresh batch24 confirmation succeeded. Both successful batch24 trials recorded warmup, measured optimizer and validation execution. The recorded peak for the first batch24 trial was23,312,728,064 bytes. Raw validated capacity24 selected training batch24, with no silent fallback. This is observed capacity under the admitted memory budget and10GiB reserve, not unrestricted physical GPU capacity or proof of untested intermediate batch sizes.

Training completed exactly two native epochs0,1 and14 optimizer updates, with zero skipped updates and changed parameters. The same initialization hash was verified against the earlier native variant (one initialization comparison). Native losses and both epochs' validation summaries are finite. Smoke completion does not qualify scientific accuracy.

The canonical augmentation snapshot exactly matches retained `pipeline.json`: Albumentations HorizontalFlip and RandomBrightnessContrast, both configured with probability1, Pascal-VOC boxes and class labels. Snapshot SHA: `bfdd9c00d36be4d222068553563e91dcde506316a6b78751cfe45e769f975e09`. Native arguments, resolved inputs and remote canonical configuration agree with two epochs/batch24 and the JSON recipe.

The selected RTX5090 UUID is `GPU-7459c4c9-b94d-ca31-17b0-fc63140c4dc1`. All207 NVML samples were valid, with minimum10,347MiB free, above both the internal10,240MiB reserve and user's8GiB floor. Maximum sampled used memory21,841MiB; maximum gap1.177s. This is sampled evidence, not continuous hardware proof. The earlier `deimv2-s-json-4ac8ff2faa` failure and its distinct allocator OOM remain failed and untouched.

## Fresh-client readback and CPU loading: passed

Unchanged independently reviewed helper SHA: `25be67d9975f6c2266bd4681ae92219cca0bdb22c06facca7c344b4c5cb492ab`. Invocation:

```bash
env CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 nice -n 19 taskset -c 0,1 uv run --locked python .tmp/verification-gap-closure/readback_backend_case.py runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-s-json-22b56424f0 --cpu-timeout 600
```

Independent client readback passed in `readback/20261116T165927Z-9766962d/receipt.json` (16:59:27–16:59:48UTC). Environment `cy-it-adb183`; project `cy-it-adb183 ticket09`; task `5b4fcfbe70674ffab4ad18fe303c5060`; single best model `e0c9e77a44e742839528e45291290f93`. Freshly downloaded `best_stg1.pth` SHA: `d83a8aef60020a1cef44d8d6886167a44d6134108f799e8f000113b11545359e`.

Forced downloads verified all eight enabled publications and checkpoint bytes in a new SDK cache, along with completed stage outcomes, canonical JSON configuration, native scientific General settings, model asset provenance, architecture/class order/source revision, exact calibration CSV and typed threshold metadata. The val/test full/DTRK workbooks retain376 finite available numeric cells and preserve unavailable values. Ninety native scalar loss observations and96 native log loss values are finite. Published results retain all80 held-out images, including34 backgrounds, without decoded-pixel leakage between splits.

The independently downloaded checkpoint loaded through CY's public descriptor reader and native DEIM CPU prediction adapter. It completed all40 frozen validation images, including15 backgrounds, producing12,000 finite raw detections. Fixed-threshold scoring used the published exact calibration and canonical IoU/matching policy, yielding TP0, FP3, FN64 and preserving all64 GT objects. This is native CPU prediction plus CY scoring; it is not a separate upstream DEIM solver validation run, CPU/GPU numerical parity, export validation or accuracy qualification.

## Protected handoff and authorized cleanup

`case/handoff.json` is `accepted` for tickets09 and99, references the verified commit and independent source applicability, and binds129 retained files to their SHA-256 hashes, including the final cleanup receipt. All128 pre-cleanup protected files were rehashed before and after deletion without changes. It carries the downloaded checkpoint/task/model identities, exact thresholds and corpus manifest for later consumers.

Root and the independent reviewer inspected the128 protected entries and exact two cache paths before root authorized deletion. The original `cleanup-plan.json` remains protected as historical planning evidence. Only these directories were removed:

- Case `dataset-cache`:249 files,24,344,597 logical bytes.
- Successful readback SDK `cache`:9 files,173,626,284 logical bytes.

Actual removal:197,970,881 logical bytes across258 files. `readback/20261116T165927Z-9766962d/cleanup.json` records deletion and unchanged protected hashes. Physical filesystem reclaim was not separately attributed during concurrent campaign work. No CPU media duplicates were created. All checkpoints, source/native inputs, logs, artifact copies, CPU predictions, receipts, earlier failed cases, shared assets and services remain protected. All readback child processes exited; service lifecycle ownership remains with root.

Native training, fresh estimation, source applicability, independent publication, CPU checkpoint prediction/scoring, sampled reserve, owned-worker cleanup and authorized cache removal passed. Independent reviewer `count_review` and the coordinator verified all129 final protected hashes and retained failure evidence without outstanding findings. This closes ticket09 and ticket99's T018. There is no broader campaign, physical multi-GPU, unrestricted capacity, accuracy or export claim.
