# Ticket08 DEIMv2 S native execution and independent readback — 2026-11-16

Status: execution and independent coordinator review passed; accepted for the recorded source. No product changes or new release are claimed. Machine-readable evidence is in [the paired JSON](2026-11-16-ticket08-deim-native.json).

This evidence applies the [estimated two-epoch acceptance contract](../../014-estimated-batch-acceptance/contracts/acceptance.md), [native detector checkpoint contract](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison) and [publication inventory](../../../docs/experiment-records.md#publication-inventory). The accepted ticket03 prerequisite supplies the maintained harness; this is a new real DEIMv2 S observation, not a reuse of YOLO execution.

## Native execution: passed

Case: `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-s-default-1f5714771d`. Root launched the reviewed backend launcher with ticket08, selection `deimv2/s`, variant `default`, FP32, seed0, nominal size640 and native effective probe size800. The frozen manifest SHA is `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`, with disjoint train/val/test populations160/40/40. The approved source and backbone identities are retained in launch/input/readback receipts.

Source commit: `137079d099490e2153405f042befe8325e9a38bc`; all459 launch Python input hashes were rechecked unchanged. Reviewed launcher SHA: `fe12c144ba6a8d80484df8d8ffaa644a3aa1a1ca09980c3df61641e35832cc9c`. The case retains all six launcher inputs/results/log/telemetry files under `launch/`. Native case elapsed170.35s; launcher174.63s, exit0, with owned-worker cleanup complete.

Fresh capacity probing executed batch8 successfully, batch16 hit the configured allocator budget, and a fresh batch8 confirmation passed. Both successful probes included5 warmup,10 measured and1 validation step through AdamW; peak allocated memory was16,628,318,208 bytes in the confirmation. Raw validated capacity8 selected training batch8. There was no training fallback. This is measured capacity under the admitted memory budget and10GiB reserve, not unrestricted physical GPU capacity.

Native training completed exactly two epochs (upstream epoch indices0,1),40 optimizer updates, zero skipped updates and changed observed parameters. Native losses and both epochs' native COCO validation summaries are finite. The validation AP/AR values were zero; smoke completion does not qualify accuracy. The native training YAML retains the registered augmentation chain, size640 resize, multiscale collate configuration and EMA. The canonical transform mode is `native`; no claim is made that every stochastic/epoch-gated augmentation branch fired within two epochs.

The sole GPU was NVIDIA GeForce RTX5090, UUID `GPU-7459c4c9-b94d-ca31-17b0-fc63140c4dc1`. All167 telemetry samples were valid; minimum sampled free memory10,456MiB exceeded the configured10,240MiB reserve and user's8GiB minimum. Maximum sampled used memory21,732MiB; maximum sampling gap1.109s. Sampling is not a continuous hardware proof. This source includes ticket98's whole-device availability correction and the operational10GiB floor. It predates ticket99's later discovery of mixed CUDA/NVML total bases; no ticket99 correction or verification is claimed here. Earlier failed campaign cases remain invalid.

## Independent remote and CPU readback: passed

Owned service environment: `cy-it-adb183`. Project: `cy-it-adb183 ticket08`. Task: `42147a8f03b54a41a3b6c280982edd99`. Single best Output Model: `574f1ddbb733404ebd1c768c2f93ce8e`. Downloaded `best_stg1.pth` SHA: `efadbbfa7205bce7591802144cefb6dfce8c6cdaded462f0a958f3c8c2ba79f8`.

The separate client forced artifact and checkpoint downloads into a new case-owned cache. Successful receipt: `readback/20261116T160841Z-db3f8697/receipt.json`. It verified all eight enabled publications, canonical configuration, model asset provenance, native scientific General settings, two-epoch native log and batch8 loaders, unique model association and checkpoint bytes. Embedded and remote descriptors agree on DEIMv2/S architecture, ordered classes1–4, preprocessing, source revision and checkpoint hash. Exact calibration CSV floats and metadata agree. Full/DTRK validation/test workbooks contain376 finite available numeric cells; unavailable cells remain unavailable. Publication covers all80 held-out images including34 backgrounds; decoded-pixel identities do not cross splits.

Independent CPU loading used CY's public descriptor reader and native DEIM prediction adapter at deviceCPU, batch1, CUDA hidden. It completed the exact40 validation images including15 backgrounds and produced12,000 finite raw detections. CY fixed-threshold scoring used the published exact thresholds with canonical IoU/matching settings. Counts were TP0, FP3, FN64, preserving all64 validation objects. This is a native checkpoint reload and CPU prediction plus scoring check, **not** an independent run of upstream DEIM's solver validation loop, numerical CPU/GPU parity or scientific accuracy qualification.

Invocation:

```bash
env CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 nice -n 19 taskset -c 0,1 uv run --locked python .tmp/verification-gap-closure/readback_backend_case.py runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/deimv2-s-default-1f5714771d --cpu-timeout 600
```

The first readback (`20261116T160628Z-6c98c8cb`) remains **failed**: remote checks and40-image CPU inference completed, then the helper incorrectly accessed `predictions.image_path`; CY's native frame stores input paths under `image_name`. Only that scratch expression changed. Independent reviewer `/root/count_review` approved the exact one-line correction at helper SHA `25be67d9975f6c2266bd4681ae92219cca0bdb22c06facca7c344b4c5cb492ab`; Ruff F/format passed. The fresh client/cache rerun completed successfully. Failed receipt/log/checkpoint and original helper copy remain preserved; there was no product defect, product edit, new training, GPU use or remote mutation by the readback agent.

## Handoff and cleanup: passed

`case/handoff.json` is marked `accepted`, references the independently downloaded checkpoint, task/model IDs, thresholds and manifest, and hashes139 retained files including cleanup evidence. All138 pre-cleanup protected files were hashed before and after removal and remained unchanged.

Only the case's dataset-cache and duplicate SDK caches of both readback attempts were removed:371,634,510 logical bytes across267 files. Physical filesystem reclaim was not separately attributed while other campaign work continued. No checkpoints, receipts, logs, native inputs, shared assets, shared services or user data were deleted. All readback processes exited; no CPU-validation media copies were created. Root retains service cleanup ownership.

Required execution/readback checks and coordinator review passed. Final automatic verification of this documentation commit is recorded in the campaign ledger. No export, physical multi-GPU, broader model matrix or overall campaign closure is claimed.

## Coordinator review

The coordinator independently checked the successful native exit/cleanup, capacity
history,40 parameter-changing optimizer updates and sampled reserve observations.
The protected handoff inventory is verified against retained bytes before acceptance.
Readback limitations remain explicit: CPU prediction/scoring is distinct from the
upstream validation performed during training. This is accepted historical evidence
for source137079d; subsequent reserve corrections require their own verification.
