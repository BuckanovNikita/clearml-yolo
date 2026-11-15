# Verification campaign: frozen fixtures and handoffs — 2026-11-15

Ticket: [01: Freeze campaign fixtures and handoffs](../../../.scratch/verification-gap-closure/issues/01-freeze-campaign-fixtures-and-handoffs.md).
Source: `bce7df823f85f4c52ad7785ca2800dce691e20c1`, current `master`, without a remote fetch.
Scope: existing [baseline models and augmentation requirements](../spec.md#models-augmentation-and-training-capacity),
[Severstal recipe](../../../docs/augmentation.md#severstal-execution-checks), and
[export quality contract](../../../docs/tensorrt-deployment.md#acceptance-and-reported-measurements).
No product behavior, dependency, or upstream source was changed.

## Durable inputs

The local bundle is `runs/verification-gap-closure/fixtures-v1/`, retained outside temporary storage.
Machine-specific source paths and binding locations are recorded only inside this ignored local bundle.
Its `handoff.json` lists 496 files and their byte sizes and SHA-256 digests; `SHA256SUMS` permits an independent
consumer to check every member before use. The frozen members occupy 45,993,935 bytes (about 44 MiB).
The manifest file hash is `af32131f248354a9bfa25a74be35896412b3b5d2a8fe901ac5252d818356bc43`.

- `prepared/` contains the native harness's `manifest.json`, `full.csv`, and `smoke.csv`.
  The seed-0 subset remains 160 train, 40 validation, and 40 test images. Each split contains all four
  literal classes; respectively 72, 15, and 19 images have no boxes. Exact decoded-content identities
  are disjoint across the source splits. Near-duplicate/scene independence remains unestablished.
- The previously retained manifest content identity is
  `e5ad3e3d0dda8e4a7ce10e3e53c961d8b36366a2362210e4dcc319bd71452f94`.
  Reconstructed full/smoke CSV bytes exactly reproduced its recorded hashes before relocation.
  Current source annotations still match `5c69184e1457596ad5a96e40c1c25d20510c0393f6bc9d653280a40aba5dc839`.
- All 240 smoke images and 80 additional quality images were independently copied into `images/` after
  checking their original byte hashes. Their copied bytes were checked again. Sources were not edited.
  Selected input paths now point into durable campaign storage. The relocated native prepared-manifest
  content identity is `356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`.
  Nonselected `full.csv` rows retain source references; full-dataset execution is not authorized here.
- `quality.csv` and `quality-membership.json` freeze 80 non-smoke test images, disjoint from the entire smoke
  population, covering classes `1`–`4`, including 33 empty images and crowded images with up to 17 boxes.
  Selection covers every class, takes eight empty and eight most crowded cases, then fills by a seed-0
  name digest. Labels retain the source's documented connected-component conversion limitations.
  The quality CSV hash is `855bf00010f0b386f2f3e405b9f87c297166a8a4d4e25209064a1ffc716be8b1`.
- `configs/` freezes 63 complete resolved YAML configurations, override lists, and the 42 JSON augmentation
  files. JSON configurations include validated portable transformation snapshots. `configuration-index.json`
  identifies all 21 selections, three variants, preset resolutions, and config hashes. Canonical executable
  inputs are separate from `input-provenance.json` and observed validation receipts.
- These configurations explicitly capture the **current one-epoch, batch-one baseline**. They are not
  evidence that ticket 03's new recipe exists. Ticket 03 must derive and freeze a new canonical run with two
  epochs and the exact-case measured batch, retaining seed, resolution, augmentation and FP32 identity.
  Actual environment project/tag, output destination and device bindings must also produce a new canonical
  run; do not edit these immutable baselines or use baseline batch one as an estimator fallback.
- `export-policy.json` freezes prediction defaults, preprocessing semantics, evaluator implementation identity
  and source hashes, maxDets=100 COCO bbox mAP50–95 policy, and FP32/FP16 loss limits. Checkpoint-specific
  normalization and meaningful-detection qualification remain the responsibilities of tickets 68–73.

## Executed checks

All operations used `nice -n 19`, idle I/O priority, CPU library thread limits of two, and no GPU work.
The three transient preparation/consumer scripts are archived in the local campaign evidence directory,
with hashes in its `SHA256SUMS`; they are execution evidence, not new project tooling or tests.

| Check | Outcome | What it establishes |
| --- | --- | --- |
| Historical manifest digest and source annotation hash | passed | Current annotations agree with the preserved source manifest |
| Reconstruct historical full/smoke CSV bytes | passed | Frozen split and labels agree with the historical input identities |
| Original and copied hashes for 320 selected images | passed | Durable copies preserve the selected image bytes |
| `scripts.severstal.verify_prepared(prepared)` in producer and separate consumer | passed | Current product preparation verifier accepts manifest, CSV and selected image identities |
| Compose all 63 configurations and validate JSON transform snapshots | passed | Current executable configuration schema accepts each baseline cell; no training claim |
| `validate_ground_truth(quality.csv, required_splits=('test',), require_training=False)` | passed | 80 native product image records, four classes, zero invalid boxes |
| `sha256sum --check --quiet SHA256SUMS` from bundle root | passed | A separate process checked all 496 handed-off files |
| Disposable consumer copy, changed bytes then missing member | passed | Standard consumer checksum validation rejects corruption and absence before consumption |
| Consumer temporary directory removal | passed | Temporary fault-injection copies were removed |

Local receipts are `runs/verification-gap-closure/fixture-consumer-receipt.json` and
`runs/verification-gap-closure/quality-validation.json`. No training, service, checkpoint qualification,
export compilation, numerical parity, or physical topology was executed by this ticket.
No checkpoint was required or supplied; tickets 68–73 own that gate.

## Retention and cleanup

Retain the 44 MiB frozen bundle and small evidence files until their dependent consumers finish and ticket 93
reconciles cleanup. Reuse these files rather than cloning the bundle per native case. Per-case derived dataset
caches and temporary downloads can be removed after their evidence and any selected downstream checkpoint are
retained. The original dataset, historical release evidence, user caches and other sessions' resources remain
untouched. The producer and consumer processes exited; no task-owned service or GPU process remains.
