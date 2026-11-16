# Ticket 06: YOLO26n JSON augmentation — 2026-11-16

**Accepted.** The unchanged maintained scenario and supplemental independent
readback passed for `ultralytics-json-9a23ee0417`. No product fix was needed.
[Machine-readable evidence](2026-11-16-ticket06-yolo-json.json) retains the source,
input, augmentation, native execution, publication, telemetry and cleanup receipts.

The launch used local `master` at `60b5c63aebd70fbe6329f6e0534bd1cccfc6832b`;
all tracked Python source/test/script hashes match that commit. Remote references
were not fetched. The immutable seed-0 160/40/40 corpus, four classes, native preset
640 resolution and FP32 recipe were preserved. The canonical custom augmentation
snapshot equals the executed JSON file and its measured fingerprint. The native
initial optimizer-parameter hash matches accepted ticket05, making the variant
comparison reproducible at initialization.

| Selected check | Result |
| --- | --- |
| Fresh exact-recipe GPU capacity | Passed: independently confirmed capacity 64; batch 72 allocator OOM retained as a search boundary |
| Selected training recipe | Passed: batch 64, exactly two completed epochs, six updates, changed parameters and finite losses |
| Prediction and publication | Passed: required artifact inventory and successful pipeline stages; both held-out splits and backgrounds retained without pixel-identity leakage |
| Independent remote readback | Passed: separate client/new cache, forced artifact/model downloads, exact hashes, canonical/native/General inputs, lineage and calibration metadata |
| Downloaded checkpoint execution | Passed: native CPU validation on all 40 frozen validation images; original harness also reloaded for prediction |
| Reserve and ownership | Passed monitored run; 286 error-free samples, minimum 8342 MiB free, none below 8192 MiB; owned scenario cleanup succeeded |
| Timing | 299.53 seconds for estimation, training and maintained readback; separate supplemental readback recorded its own timestamps |

Task: `92d91a2e913047eda4abed3f4665d4dd`.
Output Model: `0589089840564146a3382a73bf90b2e3`.
Checkpoint SHA-256: `9b0fe35c1f2b20f84da806ee7d8a463feef300be31e7ae36068e7f55e7fdc637`.
Owned services: `cy-it-adb183`; the coordinator retains lifecycle ownership.

The ignored launch command was `run_representative_gpu.py --variant json --ticket 06`;
its exact pytest arguments and source are preserved in launch `20261116T144009Z`.
Supplemental `readback_native_case.py CASE` was extended to validate supported YOLO
augmentation variants against their canonical snapshots. Its exact executed source
is retained in `readback/20261116T144533Z-39c54bb3/`; no product or SDK was changed.
The original native readback remains preserved separately for ticket05.

After checking receipts, the coordinator removed only this case's dataset cache
and the successful readback's cache/copied CPU-validation dataset, freeing 54,632,424
bytes. All 23 protected handoff files were rehashed afterwards and matched. The case's
`handoff.json` and `cleanup.json` record exact paths, identities and absence proof.
Native and downloaded checkpoints, reports, manifests, logs, immutable inputs and
shared services remain for downstream consumers, including ticket87.

This establishes one reserve-constrained single-GPU recipe. Sampled telemetry is not
continuous measurement. Low two-epoch smoke scores do not establish model accuracy,
quality-qualified export, numerical parity, physical multi-GPU or report rendering.
Applicable product checks and mutation review are reused from the unchanged accepted
implementation; no new product tests, mutation run or global coverage claim is needed
for this evidence-only execution. No push, deployment or release occurred.
