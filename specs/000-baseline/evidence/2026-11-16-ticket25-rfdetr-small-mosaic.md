# Ticket 25 — RF-DETR Small JSON Mosaic verification

The selected native execution, fresh capacity estimate, publication readback,
CPU scoring and protected cleanup passed. Coordinator delivery remains pending.
The [paired JSON](2026-11-16-ticket25-rfdetr-small-mosaic.json) binds the retained
preparation, admission, execution, independent review and cleanup receipts.
This record applies the [estimated-batch acceptance contract](../../014-estimated-batch-acceptance/contracts/acceptance.md),
[backend comparison contract](../../../docs/multi-model-backends.md#data-checkpoints-and-comparison)
and [publication inventory](../../../docs/experiment-records.md#publication-inventory).

Case `rfdetr-small-json_mosaic-0a85680979` ran from source `9676174` in
`cy-it-ded7c4`, project `cy-it-ded7c4 ticket25`. Review at `c0b6065` confirmed
that the intervening changes were dated evidence only. Preparation reused the
reviewed 459-file source map; acceptance independently rehashed 238 product
sources. The registered Small asset and initial optimizer parameters match
the two accepted Small cases. No other model family's initialization or
capacity result was reused.

The forced estimate observed batch 8 success, 16 success, 24 allocator OOM,
then confirmed 16. The fixed JSON Mosaic profile used nominal and effective
512-pixel inputs. Two FP32 epochs with seed 0 performed 20 optimizer updates,
zero skips and changed parameters. Native execution took 195.808 seconds;
the outer launcher took 198.744 seconds. Native CSV contains 40 finite loss
values; remote scalars contain 48, representing distinct recorded inventories.
The canonical recipe `201d589d…` combines 512-pixel Mosaic2x2, HorizontalFlip
and RandomBrightnessContrast, each with probability 1. Overlapping native
augmentation was disabled. No per-image transform trace was collected.

All 187 completed memory samples met the conservative 10,240 MiB guard;
minimum free memory was 10,367 MiB and the maximum completed sample gap was
1.215 seconds. No query failure or outer query timeout occurred. This is
sampled evidence under the admitted allocator budget.

ClearML task `47a64ef602c544d884837eb622db3af4` published model
`558f39eeceb545cb8999dc1b2ff56fa6`. Fresh readback rehashed eight artifacts
and checkpoint `856fe3f9…`, checked the four workbooks, and reconciled all
240 images, including 80 held-out images and 34 held-out backgrounds without
pixel leakage. The checkpoint reloaded through CY and scored 40 CPU validation
images, including 15 backgrounds: TP 8, FP 144 and FN 56. All 11,700 raw
prediction rows remained in evaluation; the reviewed
[ticket 103 geometry boundary](2026-11-16-ticket103-readback-geometry.md)
excluded zero rows. Raw and evaluation bytes match.

The executor observed readback parent PID 3848155, birth 1035418, with CUDA
hidden. The CPU child finished before live capture: no child PID or birth is
claimed. Normal bounded subprocess completion, the passed CPU receipt and
the empty matching post-scan support completion. Independent acceptance
review `ae51b914…` found no blocking issue.

Cleanup at 22:27:10 UTC removed only the dataset cache and successful readback
cache: 168,718,548 logical bytes. It verified 123 protected files before and
after, the four known native/readback PIDs absent, and empty exact-case process
and cache-handle scans. Checkpoints, predictions, evidence, fixtures, assets
and other cases remain protected. Physical disk reclamation was not measured;
no global compute-empty claim is made.

This two-epoch single-GPU result does not establish scientific accuracy,
convergence, upstream solver validation, export/runtime numerical parity or
physical multi-GPU operation. Sampled reserve does not establish uninterrupted
playback, and the historical WSL hang remains unexplained. No live tests or
service calls were repeated to prepare this dated record.
