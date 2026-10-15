# Native input-correctness acceptance — 2026-10-15

## Scope and identities

Real CPU and single-device CUDA pipelines, standalone prediction/comparison,
skipped training, dataset-cache preparation and ClearML publication were exercised.
The fixture has 21 distinct synthetic 96×64 images: seven each in disjoint
train/validation/test splits, including one explicit background per split.
Labels are `NA`, `NULL`, `nan`, `None`, `001` and `Класс猫`.
These checks establish execution, serialization and evaluation-contract correctness;
they do not measure model quality or generalization.

| Identity | SHA-256 / revision |
| --- | --- |
| Unchanged baseline source | Git `813ef01`; file-hash manifest `0432a4ca7ede068448e29f0cc07dee871952b270cac69ca1026f2ecd03e291dc` |
| Corrected source, including BOM handling | File-hash manifest `ce5c4886ff987428940765bb138a9f6ee21eec2f4f82ab3ba8736847432bc5ea` |
| Fixed checkpoint for unchanged-input comparison | `3580c9d8b6db6bf27d96c24b5f66803a66f67277ba87e3afd025ae098f704bcd` |
| Unchanged absolute-reference CSV | `fd72a0db2a1d3614b16dca38d2fcc0680f073b34742d788d258c3ff816b37af2` |
| Trained CPU checkpoint | `82f2162d300a483e09be457d344520a4fcccd2566beaba06adeca29a2685016c` |
| Trained CUDA checkpoint | `01cea36c7a5e81b2b04f2ad3930a71c1f3d987ed5a874fd27d79e8854c10c27b` |

Source snapshots, commands, input hashes, generated comparison YAML, task records,
download manifests and analysis outputs are retained in the ignored acceptance
archive identified by `correctness-docs-20261015/native`. The corrected runtime
tree matched its frozen manifest after execution. Source hashes are authoritative:
the existing model metadata version field reports `0.30.0` and is not evidence of
which working-tree source ran.

## Executed scenarios

Native training used one epoch, local YOLOv8n architecture, no pretrained download,
image size 64, batch 4, zero loader workers, AMP disabled and explicit eager mode.
Inference used image size 64, batch 4, confidence 0, IoU 0.7 and maximum 10 boxes.
Both native groups received explicit CPU or CUDA device selection. Each invocation
used its own output directory and one explicitly tagged ClearML task/project.
FiftyOne was disabled; this acceptance concerns ClearML row publication.

| Scenario | Result |
| --- | --- |
| CPU pipeline with relative CSV media and `hydra.job.chdir=true` | Completed; 11 artifacts and one native best Output Model |
| Single-device CUDA pipeline using the prepared cache | Completed; 11 artifacts and one native best Output Model |
| Baseline versus corrected source on ordinary labels, absolute media, identical fixed checkpoint/settings | Both completed; all 210 native prediction rows exactly equal |
| Unchanged calibration/evaluation comparison | All three image populations, thresholds, reports and numeric results exactly equal; only unordered match records were sorted for comparison |
| `skip_train=true` with relative media | Completed, including a rerun with conflicting same-named images in the actual Hydra working directory |
| Standalone canonical prediction with relative media | Completed; conflicting Hydra-working-directory images produced exactly the same 210 rows as the clean run |
| Raw `stem` and `path` prediction | Both completed; 210 rows each, unchanged coordinates/confidences and correct requested identifiers |
| Standalone comparison with relative media and conflicting Hydra-working-directory images | Completed on seven current test images using the CPU/CUDA checkpoints and each checkpoint's exact validation thresholds |
| Repeated standalone comparison | Completed; native logs confirm 70 cached prediction rows reused per side |
| Synthetic perfect-prediction CSV with all six literal labels | Standalone metrics completed; AP50/AP75/AP50_95 and F1 equal 1 for every class on each split |
| Identical relative CSV bytes in distinct source directories | Real NDJSON preparation produced distinct cache entries and distinct copied media |
| Identical absolute media references from distinct CSV directories | Reused one prepared entry |
| Repeated cache hit after changing bytes at an unchanged source path | Reused the entry with all prepared bytes and modification times unchanged, confirming explicit invalidation remains required |

The ordinary-label comparison uses one fixed untrained checkpoint on both sources;
it is separate from the six-label correction fixture. The perfect-prediction CSV
contains hand-authored synthetic boxes and confidence edge values, including
`0.30000000000000004`, `1/3`, `0.9999999999999999` and zero. Its unit scores validate
the evaluator and serialization path, not trained-model accuracy. Validation
thresholds were frozen for test; standalone comparison loaded them without
recalibrating on test.

## Downloaded publication evidence

Every completed invocation's artifacts were force-downloaded. Both native best
models were force-downloaded, loaded through native YOLO, and matched their local
checkpoint hashes and six-class vocabularies. Fresh server metadata matched exact
validation thresholds, calibration split and checkpoint SHA-256 associations.
Each training task had exactly one Output Model; nontraining tasks created none.

Downloaded `gt_csv` and `predicts_csv` retained all six lexical labels and explicit
backgrounds. Ground truth contained 21 unique source IDs. Standalone and skipped-
training source rows retained original row order, relative `image_path`, extra
`source_key` and positional lineage; trained pipelines exported their maintained
effective prepared ground truth. Per-context row IDs were unique, relationship
IDs referred to exported source rows, and every exported threshold flag matched
the strict numerical `<` comparison, including equality cases.

Raw `name`, `stem` and `path` exports each contained 21 GT rows plus 210 predictions,
all marked `not_evaluated`, assigned to the correct three splits. The two comparison
contexts each retained their seven test GT rows and 70 predictions. Native pipeline
results retained separate prediction and comparison-candidate contexts rather than
discarding or merging their source rows. Missing automatic production baselines
left completed candidate evaluation and the recorded comparison-skip outcome.

The two training task identities were `cf991b693afa4d6bbe9f9b77e8fd217d` and
`5940c3033d104809b5104fd0ae318649`. Standalone comparison and cache-hit task identities
were `66177651ed87471d93473d19382fd120` and `d20da7ded5f84e01b27a30eb4b318d8e`.
Their downloaded evidence remains available after tag-scoped server cleanup.

## Attempts, cleanup and limits

The first CPU attempt inherited `compile=true` and was deliberately interrupted
during warmup after 96.5 seconds; it is retained as failed and is not acceptance
for compiled execution. An initial ordinary-label run correctly rejected missing
model provenance until the harness supplied an explicit label. Two comparison
harness attempts failed before task creation due to Hydra argument syntax/order;
a further attempt correctly rejected comparing a checkpoint with itself. The
successful comparison used generated editable YAML and distinct trained checkpoints.
These original attempts and logs were preserved rather than overwritten.

Upstream chart generation warned that its selected font lacks the CJK glyph; CSV,
JSON and checkpoint label values remained intact. Browser rendering, physical
multi-GPU/NCCL, five-GPU behavior, and multi-user/multi-host NFS acceptance were not
tested here and remain outside this result. No shared infrastructure was changed.

Final evidence contains 13 completed tasks, three failed diagnostic tasks, 91
force-downloaded artifacts and two force-downloaded models. The lexical perfect-
prediction artifact retained all 18 authored prediction rows and exact float values;
every foreground GT/prediction row was TP and every class AP variant was 1.

The environment helper's exact-tag cleanup deleted the owned project and its tasks,
then reported zero remaining projects/tasks under that tag. It removed only the
owned scratch directory after inputs, producer outputs and downloads were archived.
No task-owned runner or GPU compute process remained. The failed attempts remain
represented in the local evidence; no server task is being presented as still live.
