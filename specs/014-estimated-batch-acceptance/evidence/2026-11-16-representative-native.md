# Representative native acceptance — 2026-11-16

**Execution passed; final acceptance review and ledger reconciliation pending.**
The fourth representative case, `ultralytics-default-2e66fec4f0`, completed in
273.38 seconds. It supports the same recipe required by tickets03 and05; no
duplicate training is needed. Earlier failed attempts remain failed evidence.

## Source, inputs and capacity

The launch receipt's 459 tracked Python inputs match managed commit
`e38ab36f1099dd67f68f7f824c7b1bf89a6c240c`; the source checkout's root HEAD was
`e1fe64e` with the integrated task-owned working changes. Remote references were
not fetched. The [machine-readable evidence](2026-11-16-representative-native.json)
retains source hashes, complete resolved receipt, runtime identity and checksums.

The immutable seed-0 Severstal subset remained 160/40/40 images, four classes,
with disjoint validation/test populations and empty images. Native YOLO26n used
640×640 nominal resolution, FP32, compilation disabled and native augmentation.
The GPU was the single RTX5090 identified in the receipt; services were the owned
`cy-it-adb183` environment. This establishes no physical multi-GPU outcome.

Fresh recipe-bound measurement returned **validated capacity 72**, selected batch 72,
and a successful independent confirmation. Batch 80 produced allocator OOM, with
owned-worker cleanup and no training fallback. Both AdamW and MuSGD paths were
measured. This is capacity under the configured 8 GiB reserve and actual host
conditions, not unconstrained full-device capacity or a promise for other recipes.

The scenario enforced its reserve during execution. The independent one-second
telemetry log contains 262 samples, no query errors and no sample below 8192 MiB;
the minimum reported free memory was 8286 MiB. Sampling is not a continuous record.
The complete script, telemetry, probe outcomes and launch receipt remain retained.

## Training and scientific/publication observations

- **Passed:** exactly two completed epochs, selected batch 72 and six optimizer
  updates; observed parameters changed and twelve reported loss values were finite.
- **Passed:** prediction population covered all 80 held-out images and 34 held-out
  backgrounds, with correct split assignments and no decoded-pixel split leakage.
- **Passed:** native checkpoint hash matched the forced remote download and native
  inference reload. A separate client/cache fetched the required artifacts, including
  `pipeline_outcome`, and checked stage outcomes, canonical inputs, native arguments
  and the stable scientific General subset.
- **Passed:** four dashboard workbooks contained available finite numerical values;
  threshold vocabulary/ranges and typed model calibration metadata agreed exactly.
  This does not independently recompute all metric algorithms or render the reports.
- **Passed:** separate CUDA-hidden native validation of the downloaded checkpoint on
  all 40 frozen validation images. The low two-epoch smoke scores do not qualify model
  accuracy, export parity or deployment quality.

Task ID: `d6158c43c4fa4b88b9cca75a7d6fd55b`.
Output Model ID: `ff7aee50c13e4488bf47fbfeb1c8d401`.
Checkpoint SHA-256: `49cd94e5b561cc67ac7d9a0c4738cd794c5324fa4f9b134ab4d14d5d58c1d171`.

The independent readback is retained under the case's
`readback/20261116T142920Z-f1e26b43/`. Two preceding readback attempts failed before
remote access because the check script compared the SDK's backported Path object
with a standard-library Path. Normalizing that return value to a standard Path
corrected the check; no product or SDK source changed. Every attempt retained its
own script/receipt. The successful script SHA-256 is
`a50df8ad5eb7d9945c4ae3fe1e392478b5b60ac3d2a6e37b9f48c45a2c5cd662`.

## Handoff, verification and cleanup boundary

The case's `handoff.json` lists checksummed launch/native/readback evidence and the
downloaded checkpoint for downstream consumers. Source data, model assets, native
checkpoint and durable consumer evidence must remain. Case-owned disposable caches
and copied CPU-validation media may be removed after review with deletion recorded.
Shared services remain owned by the coordinator until ticket93's final cleanup.

The source fixes passed focused checks, independent product review and canonical
automatic verification. Mutation follow-up strengthened device/boundary/PID tests;
their final test-only commit and final evidence reconciliation remain coordinator
work. No blanket campaign completion, push, deployment or release is claimed.
