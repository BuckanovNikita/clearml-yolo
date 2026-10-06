# Error diagnostics: live verification — 2026-10-06

The diagnostics change was exercised against real native execution and an isolated
ClearML project. The working tree reported version 0.17.1; this record describes the
change under development, not a published release. Machine-specific commands, logs,
fixture data, downloaded artifacts, checkpoint copies and source hashes are retained
in the global `clearml-yolo-environment` skill's dated
`error-diagnostics-20261006-live` and `error-diagnostics-20261006-boundaries`
evidence directories.

## Checks performed

A synthetic CSV dataset contained four training images, two validation images and two
test images. Validation and test membership was disjoint, with one empty image in each
split. Generated editable configuration examples supplied the current top-level native
groups. Training used one epoch, image size 64, batch 2, workers 0, AMP disabled and
compilation disabled. Every invocation passed an explicit project and run tag.

| Check | Observed result |
|---|---|
| CPU pipeline without promoted baseline | Completed; evaluation succeeded and comparison recorded its skip reason without paired reports |
| GPU pipeline after promoting the CPU baseline with `prod` | Completed on the retry; native training, prediction, paired comparison and reports succeeded |
| Standalone `cy-compare` | Completed with current test images, matching inference settings, continuous AP integration, IoU 0.45 and prediction reuse disabled |
| Standalone `cy-val` | Completed for validation/test with IoU 0.45 |
| Standalone `cy-report` | Completed from the standalone comparison manifest |
| Native FiftyOne publisher/results/panel tests | 36 passed using the dedicated external test database; included persistence, fresh-process readback, evaluation rename/delete and interrupted retry |
| Enabled standalone `cy-metrics` publication | Completed; six-image dataset, one owner receipt, canonical run link and three persisted native evaluations verified; exact owned dataset deleted |
| Injected optional publication `OSError` | Real ClearML invocation completed, computation artifact downloaded unchanged, no success receipt created, safe warning verified in the server Console |

The injected failure used the real invocation lifecycle and a deliberately failing
publisher implementation. Its warning identified `OSError`, `operation=publish`, the
task and ground-truth context. A credential-like sentinel and its MongoDB URI were
absent from the persisted Console. This verifies the optional exception boundary and
remote logging; it does not reproduce an operating-system permission failure inside
FiftyOne itself.

## Required failure boundaries

Five additional subprocesses used real isolated ClearML invocations. Failures were
injected on the invocation-owned task instance at its upload, model update, General
parameter registration or flush boundary; dependency source files and shared services
were not modified. Native model/callback checks executed the installed Ultralytics
callbacks under the project's native runtime wrapper. The model rejection fixture
was a nonempty local checkpoint marker; it verifies rejection handling, while the
successful CPU/GPU checks above establish valid model upload and load behavior.

| Injected boundary | Exit | Server task status | Local diagnostics |
|---|---|---|---|
| Required artifact upload returns rejection | 1 | failed | retained |
| Native model update returns no accepted model | 1 | failed | retained |
| Native General registration raises | 1 | failed | retained |
| Final flush returns rejection | 1 | failed | retained |
| Actual SIGTERM during the invocation | 143 | failed | retained |

Each task was freshly read from the server after its subprocess exited. Its local
marker remained until archival and intentional cleanup. These are controlled boundary
injections with real task lifecycle effects, rather than failures of a physical
storage device or the shared server itself.

## Publication and readback

All recorded artifacts were force-downloaded and checked against the
[current publication contract](../../specs/014-evaluation-publication/contracts/publication.md).
The CPU/GPU/compare/val/report invocations had respectively 11/17/8/7/2 artifact keys.
Canonical ground truth retained all eight source rows. Combined result tables retained
context identity and source/object IDs, and their pre/post-threshold relationship
fields parsed as JSON. Deprecated evaluation-summary and match/threshold/methodology
sidecar uploads were absent. Paired comparison and developer/business workbooks were
present, with the comparison workbook retaining its `Сравнение` sheet and exclusions CSV.

Both models inferred the same two current test images with matching confidence, IoU,
image size, batch and device settings. Validation thresholds were reused unchanged
for train/test. Baseline thresholds in canonical comparison rows exactly matched the
baseline's validation thresholds; exported below-threshold flags followed strict `<`.
Each pipeline had one downloadable native best Output Model. Fresh server readback
confirmed checkpoint SHA-256 binding and exact validation threshold metadata.

Remote Plotly payloads were checked for 13 evaluated contexts: 13 raw confusion
matrices, 39 normalized matrices and 13 class PR plots. Raw counts and class order
matched local authoritative matrix workbooks. Row/column/global normalizations matched
0–100 percentage arithmetic, including zero denominators. PR plots retained [0, 1]
axes, AP50 annotations and consistent hover-array lengths. Native scalar groups and
Configuration Objects were present on the pipeline tasks.

## Failures and limits

The first GPU invocation trained and predicted successfully, then failed during
calibration's fresh model readback with ClearML SDK
`AttributeError: 'NoneType' object has no attribute 'task'`. Later readback found that
model with the correct task association and native metadata, but without calibration
metadata. The failed task, traceback and checkpoint were archived. One retry with a
fresh output directory completed all pipeline checks; no application, SDK or shared
service repair was made for the incident. A network decoding retry was also observed
and recovered. This record establishes successful CPU/GPU execution while preserving
that intermittent service/SDK limitation.

One standalone attempt encountered a transient import `SyntaxError` while another
agent was editing the shared working tree. It failed before task creation. After the
file was valid, the standalone checks completed; the initial log was preserved.

Physical multi-GPU execution and interactive FiftyOne App/browser behavior were not
exercised. Wheel/sdist installation, repository checks and independent review belong
to the parent task's separate verification. This evidence does not establish those
gates or failures outside the controlled boundaries described above.

## Cleanup

Selected local producer outputs and downloads were archived before guarded cleanup.
Credential caches and invocation temporary directories were excluded from the archive.
The exact tag-scoped ClearML cleanup removed the owned tasks/project and confirmed no
remaining matching objects. The matching task-owned run directory was removed. Native
FiftyOne tests cleaned their own dataset prefixes. The enabled metrics dataset was
deleted by its exact receipt identity and absence was verified before tag cleanup.
The second failure-verification tag also returned zero matching tasks/projects after
archival and guarded cleanup. Pre-existing services, application
datasets, caches and shared infrastructure were preserved.
