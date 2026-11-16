# Ticket88: independent ClearML readback — 2026-11-16

**Accepted: all four execution criteria passed.**
This audit consumes the accepted ticket05 native YOLO handoff, without another
training run, GPU operation, model upload or environment mutation. The maintained
[publication inventory](../../../docs/experiment-records.md#publication-inventory)
and [model identity contract](../../../docs/experiment-records.md#model-verification-and-source-identity)
define the applicable destinations.

Worktree: `/mnt/wsl/data/nkt/clearml-yolo`, local `master` at
`60b5c63aebd70fbe6329f6e0534bd1cccfc6832b`, equal to local master. Remote references
were not fetched. Existing instruction/document changes were preserved. No product
or test source changed; this is verification evidence for existing behavior, not a
new capability or specification change.

## Reused successful live evidence

The accepted case is `ultralytics-default-2e66fec4f0`, under
`runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/`. Its successful
separate-client readback is `readback/20261116T142920Z-f1e26b43/receipt.json`.
The [representative acceptance record](../../014-estimated-batch-acceptance/evidence/2026-11-16-representative-native.md)
records source/runtime identities, execution and independent acceptance. All 459
Python launch inputs matched `e38ab36`; subsequent accepted changes did not modify
the product inputs exercised by that case.

- Task: `d6158c43c4fa4b88b9cca75a7d6fd55b`.
- Output Model: `ff7aee50c13e4488bf47fbfeb1c8d401`.
- Checkpoint SHA-256: `49cd94e5b561cc67ac7d9a0c4738cd794c5324fa4f9b134ab4d14d5d58c1d171`.
- Owned environment: `cy-it-adb183`; lifecycle ownership remains with the coordinator.

That readback used a newly created SDK cache, forced downloads of all required
artifacts and the single associated best Output Model, and checked downloaded paths
were inside that cache. It compared artifact/checkpoint hashes against the native
result, verified completed task status, task/project ownership and model lineage,
canonical inputs, scientific General/native argument agreement, architecture,
vocabulary, role and exact typed validation calibration metadata. It retrieved
scalars and checked finite values and available workbook numbers. All 80 held-out
images, including 34 backgrounds, retained their split/checkpoint identities.

The downloaded checkpoint was then loaded by native YOLO for CUDA-hidden CPU
validation on the frozen 40-image validation split. That executed successfully;
this ticket reuses that actual native execution rather than counting a receipt or
upload request as proof of loading. Low smoke metrics do not qualify accuracy.

Reuse is applicable because the accepted task/model/checkpoint and recipe are the
same ticket88 inputs. The fresh audit below rehashed all 22 protected handoff files
and all eight downloaded artifacts after the coordinator's disposable-cache cleanup.
All matched. The two earlier readback attempts failed at the local Path-type cache
check before remote access; those failed receipts remain retained and are not passes.

## Fresh ticket88 audit

**Passed:** a separate bounded read-only SDK process ran on 2026-11-16 from
14:40:51.797674 to 14:40:53.104485 UTC. It obtained credentials in memory through
`recorded_environment`, required agreement with the campaign owner and receipt,
and used `Task.get_task`; it never initialized or modified a task. The command was:

```bash
timeout --signal=TERM --kill-after=10s 120s env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 nice -n 19 taskset -c 0,1 uv run --locked python .tmp/ticket88-readback/audit.py
```

The retained script snapshot is
`runs/verification-gap-closure/ticket88-readback/audit.py`, SHA-256
`32d0b0a59a77ccee1e3c9d41ff2c9a4dfd1f41a5f061e7359935fa340f0ae8e0`.
[Machine evidence](2026-11-16-clearml-independent-readback.json) records the receipt,
source identity and hashes/sizes for all six new retained audit files.

| Applicable inventory | Observed evidence |
| --- | --- |
| Best Output Model | Unique association remains the accepted model ID; forced bytes/lineage/metadata/native loading established by the reused readback |
| Ground truth and predictions | `gt_csv`, `predicts_csv`; fresh remote inventory and retained downloaded hashes match |
| Validation calibration | `metrics_best_confidences_val`; exact threshold values/types/checkpoint association checked by reused readback |
| Evaluated split dashboards | Full and DTRK workbooks for val and test; all four present and byte-identical |
| Pipeline outcome | `pipeline_outcome` reports successful training/prediction/metrics and explicit disabled comparison/report stages |
| Configuration Objects | Freshly retrieved `run`, `run_overrides`, `dataset`; canonical run equals source result, overrides are a matching subset, dataset vocabulary/splits/prepared root agree |
| General | Stable scientific subset checked against actual native arguments by the reused readback |
| Scalars and plots | Fresh scalars equal the prior snapshot; 13 plot records include current-model val/test confusion matrices, test precision-recall and native telemetry; no native PR-curve image record |

The resulting remote artifact set is exactly the eight enabled artifacts. Comparison,
paired reports and export were not enabled; no fabricated outputs are required.
YOLO uses its native model selector, so no non-YOLO resolved-asset Configuration
Object applies. There was no explicit report configuration. Optional FiftyOne was
disabled. Plot payload retrieval establishes availability, not rendering or hover
behavior; those remain separate visualization verification.

## Disposition and cleanup

Ticket88's fresh-client retrieval, forced-download identity, native checkpoint
usability, and secret-free retained IDs/evidence criteria are **passed**, combining
the explicitly identified reused live checks with the new API/byte audit. No selected
check is failed, deferred or waived. No product tests or mutation rerun were selected:
there is no product/test change, and these would not add remote-readback evidence.
Native consistency review found the evidence scope consistent with the unchanged
publication contract; final documentation integration belongs to the coordinator.

The bounded process exited zero. It created no download cache and no descendants
requiring cleanup. Six small reproducibility files remain in the ticket-owned ignored
directory; no shared cache, dataset, checkpoint, protected receipt or service was
deleted. Prior cache cleanup remains recorded in the accepted case's `cleanup.json`.
No credentials were persisted, user SDK configuration changed, or new CPU validation
run launched. Shared services remain available for later consumers; final teardown
belongs to ticket93. No campaign, export, browser-rendering or release completion is
claimed.

Coordinator acceptance, 2026-11-16: all six newly retained audit files were
independently rehashed and matched, and the reused source/task/model/readback
identities match the accepted ticket05 handoff. This accepts ticket88 remote
retrieval only; plot rendering remains separate. No additional resources remain.
