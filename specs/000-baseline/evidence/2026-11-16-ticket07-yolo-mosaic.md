# Ticket 07: YOLO26n JSON and Mosaic native verification

Date: 2026-11-16. Scoped native execution and independent readback **passed**;
coordinator acceptance follows the reviewed launcher diagnosis below. This adds
evidence for existing behavior, with no product or dependency change.

## Inputs and native outcome

The run used source `60b5c63aebd70fbe6329f6e0534bd1cccfc6832b`; all 459 recorded
Python hashes still matched at acceptance. The frozen seed-0 corpus contains
160 train, 40 validation and 40 test images. Its manifest SHA-256 is
`356d4c02883226678e4ae474d54f21a8820fb31fc8f3eefe13ac177684396a33`.
The maintained YOLO26n preset used 640 pixels, FP32, compilation disabled and
exactly two epochs. The resolved JSON/Mosaic snapshot matches its published
canonical configuration. Full commands, source/input identities and results are
in the [machine record](2026-11-16-ticket07-yolo-mosaic.json).

The real capacity search succeeded at batches 8, 16, 48, 56 and 64, encountered
allocator OOM at 72 and independently confirmed 64. Training selected **64**,
completed two epochs and six optimizer updates, changed parameters and emitted
12 finite loss values. Initial optimizer parameters matched both accepted native
and JSON cases. The native scenario passed in 367.858 seconds; pytest reported
one passing test in 368.83 seconds.

- Case: `ultralytics-json_mosaic-133fbc61a3` under
  `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/`.
- ClearML task: `ea1945d23cf24ee180f5cce0f7bb654b`.
- Output Model: `26d3bba5d17243cb96a67c9ae5abd179`.
- Checkpoint SHA-256:
  `ea7e6fce3024aec6d867ead22af8d5e373bdb5425d606714068b889a1b88b262`.

## Independent readback and reserve evidence

A new SDK process and cache forced downloads of the checkpoint and all eight
required artifacts. It verified task completion, canonical settings, calibration,
prediction context, finite workbook values and both epoch records. All 80 held-out
images, including 34 backgrounds, are represented without train/evaluation pixel
leakage. Native CPU validation reloaded the downloaded checkpoint on 40 validation
images. Receipt: `readback/20261116T150024Z-b3fc7ed9/receipt.json` within the case.
These outcomes establish execution and publication, not model accuracy.

The outer launcher was **interrupted with exit 143**, without a completion receipt.
Its 289 supplemental samples cover only the first 302.559 seconds and observed a
minimum 8,343 MiB free. No full-case minimum is claimed. The surviving pytest
process independently enforced the 8 GiB reserve through worker completion and
required successful owned-descendant cleanup. The separate independent
[launcher investigation](2026-11-16-ticket07-launcher-diagnosis.md) supports reuse
of that native result; it leaves the signal sender unresolved. No missing receipt
or telemetry was reconstructed, and no extra training was run.

## Cleanup and acceptance

No matching launcher, pytest or native worker remains. After retaining the
checkpoint, receipts, inputs and logs, cleanup removed **49,488,399 bytes** from
the case dataset cache and independent-readback cache/validation copies. All 23
protected files were rehashed unchanged. The accepted `handoff.json` identifies
their locations and checkpoint for later consumers. Shared assets, fixtures and
environment `cy-it-adb183` remain owned by the campaign.

Native contract consistency review found no new behavior or missing scoped
assertion. The final automatic documentation gate is recorded by the coordinator
after committing this evidence. Physical multi-GPU, export parity and embedded
ClearML UI are not established by this run.
