# Implementation evidence — 2026-10-11

Completed on 2026-10-12 and released as annotated Git tag **v0.24.0** on `master`.
All 14 native presets, cross-family workflows, scheduling acceptance and six Faster
R-CNN FP32/FP16 quality/standalone matrices pass. The current QKV-Float policy uses
fresh transformer execution and exact transformed-graph byte equivalence for the
three accepted CNN engines. Parent verification, fresh independent T050 review,
documentation checks, owned-resource cleanup and required commit/release hooks pass.

The fixed small corpus establishes relative export quality, not general model accuracy.
CUDA 11.8 target execution and binary portability remain unverified. Earlier results
below preserve their original source/policy bindings and failed attempts; current
completion is recorded in [release closure](#release-closure--2026-10-12).

## Baseline and workflow

The isolated branch starts at `2114714`, preserving v0.23.0 and its follow-up evidence.
The original checkout and local dependency overrides remain intact. Spec Kit discovery
used explicit feature selection and read-only paths mode; `.specify/` is unchanged.
Specification quality passes 16/16 items. Parent analysis maps all 16 functional requirements
and seven success criteria to the 58 tasks, with no uncovered scope. The approved exception
to the older Ultralytics-only rule is recorded explicitly in spec/plan.

Baseline `uv run --frozen pytest -q`: **1681 passed, 30 skipped**. Skipped tests are not
native or publication evidence.

## Native compatibility probes

On Torch 2.13.0, torchvision 0.28.0, RF-DETR 1.11.2, transformers 5.19.0, Lightning 2.6.6
and faster-coco-eval 1.8.0:

- DEIMv2 S/M/L/X CPU construction, forward and postprocessing passed. S also completed an
  optimizer update, native solver epoch, COCO validation, best checkpoint and reload.
- RF-DETR Nano/Small/Medium/Large CPU construction and prediction passed. Nano also
  completed native training, validation, best checkpoint and reload.
- DEIM initially failed at torchvision's changed transform hooks. Project-owned transform
  bridging passed the original fit path without upstream source edits. Production must
  preserve the full augmentation recipe beyond the tiny feasibility fixture.
- RF's extra output column is its explicit background slot. Prediction filters through
  the checkpoint's foreground mapping.

Synthetic CPU fixtures with random weights establish execution, not useful quality,
GPU/DDP operation, pretrained downloads or ClearML publication. DEIM source is revision
`1d2ca42171570c713e78fc6a766ec5104b7f4724`.

## Shared implementation checks

- Model configuration: 11 tests passed, including invalid settings and SDK-free imports.
- Checkpoint binding: six tests passed, including standalone weights copies, stale hashes,
  conflicting metadata and actual Torch save/load with embedded metadata.
- COCO and existing dataset/cache checks: 28 tests passed, covering fractional geometry,
  exact numeric-looking labels, empty images, split mapping, source bytes and cache reuse.
- Scheduler: 188 focused tests passed; scoped Ruff/mypy and all 29 import contracts passed
  at that stage. Parent inspected phase discovery, demand, identity ordering and remapping.
- Model Hydra/config export: five new tests passed after fixing nested ConfigStore groups.
  The 54 existing export tests passed in the preceding combined run.

## Export feasibility

The complete ResNet-50 TensorRT 10.13.0 graph executed all 16 required size/batch combinations
with a pretrained COCO checkpoint and real images. The probe reported 1,218 detections,
equal counts and zero unmatched detections at class-aware IoU >= 0.99. Maximum TensorRT
versus ONNX Runtime difference was 0.001892 pixels and 0.00000385 score. This is feasibility
and raw-output evidence, not the labeled-corpus mAP acceptance gate.

ONNX Loop triggered a TensorRT builder crash. The successful graph uses tensorized batch
operations and per-level/per-class NMS batches to avoid fixed candidate caps. Project-owned
DINO interpolation decomposition is being verified against native antialias semantics.

## Initial open gates — 2026-10-11

Production integration, full native/download matrices, comparison, live scheduling,
all-backbone/precision export and quality matrices, documentation, final parent verification,
fresh review and release remain pending. Machine-specific scratch and hardware evidence
remain outside this portable repository record. CUDA 11.8 target execution is unverified.

## Lightweight continuation before the authorized workload window

The user authorized heavy work only after **2026-10-11 22:00 UTC / 2026-10-12 01:00 Moscow**.
This continuation used source inspection, metadata-only remote reads, SDK stubs, small
array fixtures, single-threaded focused checks and distribution packaging. It did not run
training, model forwards, tracing, engine builds, GPU execution, the full pytest suite or
large dependency/checkpoint downloads. Prepared acceptance drivers remain unexecuted and
require both the timestamp boundary and an explicit parent scheduling release.

The integrated code now includes all model groups, checkpoint descriptors, native adapters,
mixed comparison dispatch, ClearML model recovery/publication, selected configuration
export, scheduling/replay integration and `cy-export` operations. Implementation exists;
the outstanding native acceptance tasks still block completion and release.

Focused integration exposed and corrected these defects:

- Programmatic native training inherited the legacy NDJSON default; the selected native
  dataset adapter now consistently prepares COCO records.
- A native-selected mixed comparison omitted the complete YOLO prediction defaults. The
  legacy boundary now supplies them while preserving comparison-owned shared settings.
- Task recovery recognized only `.pt`. It now selects `.pth`/`.ckpt` best models/artifacts,
  validates embedded descriptors and hashes, and supports complete typed raw native
  assertions through local or task-backed `ModelRef` values. Conflicting assertions fail.
- Export result evidence used the executable `export` root. Generated records now use
  `export_result`, which replay excludes. Verification accepts a selected-split-only corpus
  and checks source bytes again after evaluation.
- Early independent review reproduced native training recipe logging failures: RF-DETR's
  nested `model` dictionary and DEIM's registry name were treated as checkpoint paths.
  Native recipe serialization now preserves both forms.
- Native selection silently replaced changed inactive YOLO settings; validation now rejects
  these changes before admission. Mixed comparisons reject unsupported population controls.
- Follow-up review reproduced native Python prediction ownership conflicts for source,
  task, mode and explicit weights. The four failing regressions now pass; matching explicit
  checkpoint references remain valid.
- DEIM's non-square postprocessor receives original width then height. Its private native
  COCO aliases are restored at the source/data boundary, and export evaluation records the
  actual evaluator module, version and source hash rather than assuming its identity.

Selected recorded commands/results, all using `uv run --frozen --no-sync` and
`OMP_NUM_THREADS=1 MKL_NUM_THREADS=1` for tests:

| Check | Result and scope |
| --- | --- |
| `pytest tests/test_detector_integration.py tests/test_detector_workflows.py tests/test_model_configs.py tests/test_model_replay.py tests/test_runtime_entrypoints.py -q --disable-warnings` | 57 passed after the first review fixes; no model SDKs loaded by the workflow fixtures |
| `pytest tests/test_detector_workflows.py tests/test_comparison_reinfer.py tests/test_comparison_recovery.py tests/test_comparison_identity_cache.py tests/test_calibration_metadata.py tests/test_detector_publication.py tests/test_export_quality.py tests/test_model_scheduling.py -q --disable-warnings` | 153 passed; mocked publication, real small-array metric calculations, comparison and admission contracts |
| `pytest tests/test_detector_integration.py tests/test_detector_workflows.py tests/test_model_configs.py tests/test_model_replay.py tests/test_inference.py -q --disable-warnings` | 81 passed after the programmatic ownership correction |
| Earlier focused export/recovery/dataset record batch | 178 passed; selected-split corpus, recovery and request validation |
| Earlier raw-reference recovery/legacy/workflow batch | 132 passed; raw task assertions preserve selected-source identity |
| `ruff check .` | Passed after the latest integration fixes |
| `mypy .` | 273 source files passed before the final review fixes; affected integration/validation modules passed again afterward |
| `lint-imports` | All 40 contracts kept after integration |
| `pytest tests/test_architecture.py -q --disable-warnings` | 94 passed after the review fixes |
| `uv build` and installed `cy-export --help` | Wheel/sdist and command help passed; optional-backend clean-install/native execution remains pending |

The earlier whole-tree formatting check found existing unrelated formatting differences;
only task-owned edited files were formatted. Ruff lint passed. No commit hooks, commits,
version tags, pushes or release were performed during this window. Protected external
dependency revisions and the exact local source-override section remain unchanged.

Documentation now covers the new groups, native/runtime ownership, checkpoint recovery,
export artifacts and deployment APIs. The prepared quality plan requires fixed disjoint
training/validation/test populations and validation-selected checkpoints; held-out test
results cannot guide further fitting. Fresh documentation checks passed for 27 Markdown
files, 255 local links/anchors, 32 CLI compositions and all 14 presets, without importing
model, ClearML or TensorRT SDKs. The checked fences included 32 shell blocks, one Python
example and four YAML examples. See [review.md](review.md) for the early findings and
documentation scope. Those reviews are not the required final fresh review after full
verification.

## Early workload release

The user explicitly lifted the original time restriction with "can start now".
The parent confirmed 2026-10-11 20:43:09 UTC before starting live environment
preparation. The earlier lightweight evidence remains historical; native and GPU
acceptance results must be recorded separately after execution.

## Live acceptance continuation — 2026-10-11

The fixed person-only corpus derives from the official COCO128 archive, whose SHA-256
is `61e5e3028863d8ffc3b81d6a514603954889f0edd5e4b44c4ce60b2da99aeb8e`.
An independent source audit found two images without annotation files and two annotation
files without images; these unmatched entries were excluded explicitly. Missing annotations
were not treated as negative images. Six-significant-digit source rounding is allowed only
within a normalized boundary tolerance of 0.000001, with every correction recorded and the
original bytes retained. Nine focused corpus-staging tests passed, followed by actual
staging with zero invalid derived boxes.

The deterministic quality split contains 40 training, 12 validation and 12 test images,
including 8/4/4 explicit negative images respectively. Foreground source category 0 maps
to the exact public string `0001`; other source categories are explicitly excluded. An
additional eight-image crowded set contains 62 person boxes. A separate 12-image native
execution cohort is disjoint from all quality training/validation/test images. These small
cohorts establish the recorded workflows and relative export behavior only, not broad
detector accuracy. COCO-pretrained source weights can overlap this source collection;
this is not an independent generalization benchmark.

Actual RF-DETR reload inspection found that reconstructing a checkpoint at the preset's
default resolution resized its learned position grid before prediction. A Nano checkpoint
trained at resolution 64 had 17 position tokens; the default 384 constructor created 577.
The constructor now receives the descriptor's training resolution, and native prediction
receives the requested inference shape separately. Two regression cases failed before
the correction; the affected backend/integration/workflow batch subsequently passed
40 tests. Actual retraining, forced download, copied-checkpoint reload, prediction and
validation passed with the corrected implementation.

RF-DETR Nano and DEIMv2-S each completed their three public commands through queued
automatic GPU admission. Fresh readback established one completed owner per invocation,
one best Output Model for training, no Output Models for prediction/validation, exact
embedded/server descriptor and checkpoint hashes, lexical foreground labels, forced
artifact downloads, original ground-truth retention and exact raw/published prediction
row multisets. Source corpus hashes were unchanged. These short execution checks do not
establish the separate meaningful-quality/export gates. Remaining presets and deployment
acceptance are still in progress.

The complete CPU/native regression suite then passed **2,037 tests with 30 skipped**
in 668.02 seconds. Ruff passed, strict mypy checked 273 files, and all 40 import
contracts were kept. The original YOLO pipeline completed native GPU training,
prediction and evaluation under one owner; its best checkpoint and required artifacts
were force-downloaded and hash-checked. The downloaded checkpoint retained class `0001`
and the exact validation threshold. The absent automatic baseline was recorded as a
comparison skip, with candidate evidence retained.

The first real ONNX publication exposed a recording defect after successful graph
generation: generic configuration cleanup removed `plugins: []` from `export_result`.
Two added regressions reproduced empty-list/mapping loss. Export evidence now preserves
those values after sanitization. The affected tracking/export/replay batch passed
**91 tests**, and affected Ruff/mypy checks passed. A fresh public ONNX command then
passed strict one-owner, zero-Output-Model, forced-download, artifact-hash and exact
metadata/run-configuration checks. The failed first readback remains retained as evidence;
its successful command alone was not counted as publication acceptance.

Validation-selected ResNet-50 and DINOv2 checkpoints now have nonzero native COCO mAP
at both profile families, using the frozen 12-image validation population only:

| Preset | Validation canvas H×W | Native mAP50–95 |
| --- | --- | --- |
| ResNet-50-FPN | 608×960 | 0.12881652933784796 |
| ResNet-50-FPN | 128×1536 | 0.12689476404235 |
| DINOv2-Small | 608×960 | 0.04157918423291627 |
| DINOv2-Small | 128×1536 | 0.007781912012793169 |

These values qualify the frozen checkpoints for the subsequent test-corpus comparison;
they are not TensorRT quality results. The remaining native/export/standalone acceptance
and fresh final review still block completion and release.

The first queued TensorRT build exposed an SDK-boundary error before engine generation:
the installed 10.13.0 Python `IOptimizationProfile.set_shape` method returns `None` on
success and raises `ValueError` for inconsistent bounds. The adapter had interpreted its
return value as a C++-style success flag. A failing regression reproduced that behavior;
the adapter now calls the setter and retains the separate profile-registration index
check. The affected export batch passed 72 tests, with Ruff and mypy passing for the
changed files. A fresh queued ResNet-50 FP32 build then completed successfully. Its
force-downloaded engine SHA-256 is
`282150df9b8122aaee75b1689764fc84b87baef2491697776929d75ae5435e5d`;
readback confirmed one completed owner, no Output Models, both artifact/server hashes,
both optimization profiles and the required `ROIAlign_TRT:2` plugin. This proves the
corrected build path; numerical quality and standalone execution remain separate gates.

The DEIMv2-M native train/predict/validate sequence also passed. The DEIMv2-L prediction
audit encountered three finite reversed-corner rows from the native model. The existing
publication contract retains such raw predictions, marks standalone prediction rows as
not evaluated, and excludes invalid geometry during evaluation. The scratch acceptance
checker was corrected to enforce that contract without changing the model outputs.
Fresh prediction and validation from the already frozen L checkpoint passed exact-row
and exclusion checks; training was not repeated, and the original failed-checker evidence
was retained. RF-DETR Nano and DEIMv2 S/M/L now have complete native workflow evidence;
the remaining native presets are still pending.

ResNet-50 FP32 verification subsequently passed all 22 public quality cases on the frozen
12-image test corpus, covering all 16 endpoint/batch combinations and six interior cases.
Every case had meaningful nonzero native mAP; the largest observed absolute mAP loss was
`0.00000027219379440668323`, below the FP32 limit of 0.001. Preprocessing checks and
out-of-profile rejection passed. Fresh owner/artifact readback also passed. This result
does not yet establish standalone execution, FP16 or other presets.

The first real mixed-family report exposed a lexical-label defect in the report integration:
the pinned upstream reader classified text `0001` as a numeric threshold footer and removed
the class. A project-owned reader now distinguishes original text cells from numeric cells,
preserving exact class labels and normal metric missing-value handling without changing the
dependency. A real-builder regression failed before the correction; the expanded reporting
and architecture batch passed **134 tests**. The checks cover leading zeros, literal `NA`,
whitespace, excluded-class retention, unchanged source bytes and invalid duplicate/ID rows.
The next public mixed-family report passed fresh artifact readback and semantic checks:
both developer/business workbooks retained class `0001`, its source metrics and eligible
class count `1/1`. Remaining comparisons and the original failed report rerun remain pending.

Fresh server inspection found no native `General` parameters on the first four Faster
R-CNN training owners, despite their local effective YAML and canonical `run` records.
The shared detector integration now records a separately sanitized effective-argument
tree on the existing owner before model publication, preserving null/default values and
propagating recording failures. New-family replay remains under `run.model`. Parent
integration also reproduced six remote train/pipeline failures caused by importing
detector `General` into the inactive YOLO settings, and restricted that legacy replay
step to YOLO. The combined detector/tracking/replay/scheduling batch passed **189 tests**;
actual fine-tune runs and fresh General readback are still required for live acceptance.

DINOv2-Small FP32 subsequently passed the same 22 public quality cases, with zero observed
mAP loss and nonzero native mAP in every case. Fresh one-owner/zero-model publication,
forced-download hashes and exact report readback passed. Its engine SHA-256 is
`b5cd30dba1b24835eebe0b508ced072142d65aba7e289aa045b6f18a17dadfde`.
Together with ResNet-50 this closes the dynamic rectangular/batch-four feasibility gate
T003. It does not close the remaining precision, preset or standalone acceptance gates.

ResNet-50 FP16 subsequently passed all 22 public quality cases; its maximum absolute
mAP loss was `0.0025839687112825527`, below 0.005. Both ResNet-50 precisions and DINOv2
FP32 also passed serialized-engine execution in the fresh minimal environment: each
ran 118 batch calls covering 24 distinct batch/canvas combinations and five repeated
profile switches, plus nine incompatible metadata/input rejection cases. The runtime
contained and imported no Torch, Torchvision, timm or ClearML. Separate CPU audits
checked every saved tensor, count, padding row, corpus membership and source-image hash.
Original-coordinate restoration matched native Torchvision bit-for-bit for every row.

An initial audit required mathematically exact original-image bounds and rejected
19 ResNet-50 FP16 case/image combinations with at most `0.000030517578125` pixels of
overshoot. Native float32 restoration produces exactly the same one-ULP result. The
corrected audit keeps strict resized-coordinate bounds and requires bitwise native
restoration instead of silently clipping output or applying an arbitrary tolerance.
The original failure receipt remains retained. A regression preserves this native
rounding behavior; no production inference change was needed. Empty-output contract
engines, the remaining precisions/presets and the final review are still pending.

After the report-label, effective-General and replay corrections, the full regression
suite passed **2,055 tests**, with **30 skipped** and **54 warnings** in 658.53 seconds.
The subsequently added native-rounding regression passed in the **51-test** export batch.
Repository-wide Ruff, strict mypy (**274 source files**) and all **40 import contracts**
passed. These are intermediate integration checks; unfinished real-run acceptance and
the required fresh final review still block release.

DINOv2 FP16 passed all 22 public quality cases (maximum mAP loss
`0.0006406717684404612`) and the same 118-call standalone matrix, including bitwise
native restoration and all nine rejection cases. All five DINOv2 command evidence
archives were copied outside the task cleanup directory and reverified byte-for-byte.

The opt-in FiftyOne publisher, native-result persistence and panel tests ran against the
isolated test database: **36 passed** in 25.42 seconds. Their UUID-owned datasets were
removed by test fixtures, and the outer process supervisor confirmed no owned live
processes remained. These checks exercise actual persistence, retry, concurrent-run
isolation, native evaluation lifecycle and panel callback data; they do not claim an
interactive browser inspection. Documentation validation passed **27 Markdown files**,
**256 local links**, **32 command examples**, **14 presets** and **3 model-reference
forms**, without importing detector, tracking or inference SDKs.

Separate ResNet-50 graphs with baked confidence `1.0` were built in FP32 and FP16
solely to exercise zero-detection outputs. Each serialized engine passed all 118
standalone calls, all 24 batch/canvas combinations, repeated switches and all nine
rejection checks, with every count and padded output equal to zero. The independent
audits also passed. These engines use the original frozen checkpoint, have separate
metadata and publication evidence, and are **not** substitutes for either nonzero
quality-gate engine or its fixed labeled test results. Both build/download archives
and standalone evidence remain outside the cleanup directory.

## Acceptance continuation — 2026-10-12

All six cross-family comparison/report pairs passed: YOLO with DEIMv2, RF-DETR and
Faster R-CNN, plus each pair of the three new families. The frozen three-image
population, exact validation thresholds, role/checkpoint identities, raw prediction
rows, ground truth and audit exclusions matched their source evidence. Every published
metric, count, mean and difference was checked against its workbook source, and both
report variants retained lexical class `0001`. Twelve accepted completed owners
published 60 accepted artifacts and no Output Models. The earlier report owner remains
server-completed but semantically rejected; it is preserved separately and is not
counted as accepted. The original failing YOLO/DEIM report path passed on rerun.

These short comparison runs had no retained predictions after their frozen thresholds;
the paired statistical exclusion was explicit. They establish execution and publication
contracts, not model accuracy. The complete comparison archive was verified after
copying outside cleanup scope; its SHA-256 is
`10cd46063f823943e5630cd53941af618576e4cbcf394693d29b025da62b7e1f`.

The bounded ledger audit confirmed that implemented adapter/export tasks and their
focused checks can close separately from outstanding native acceptance. RF-DETR tests
now explicitly cover finite epoch callbacks, train/validation callback exception
propagation, and rejection of a last-only checkpoint when the required best checkpoint
is missing. DEIM tests now exercise nonempty lexical class mapping, foreground-index
and confidence filtering, and native YAML/direct configuration propagation before
solver construction for CPU and CUDA settings. The combined adapter batch passed
**45 tests**; affected Ruff and strict mypy checks passed. These fixtures complement,
and do not replace, actual native runs.

The original YOLO regression item combines the recorded actual pipeline/download with
cache, callback, upload, flush, interruption and diagnostic-retention tests from the
full suite. Failure injection in those tests is fixture evidence; real new-family
scheduling, cancellation and publication-failure acceptance retain their separate gates.
Lifecycle test coverage includes actual descendant reaping and bounded worker processes,
with the real FiftyOne database checks recorded above.

DINOv3-Small FP32 passed all 22 quality cases with nonzero native mAP in every case
and no positive mAP loss. Its serialized engine also passed all 118 standalone calls,
24 distinct shapes, repeated switches and nine rejection cases. The independent audit
verified source hashes, counts/padding and bitwise native original-coordinate restoration;
its evidence was sealed outside cleanup scope. The other pending precision/preset,
scheduling, fine-tune, final review and release gates remain open.

The corrected source was rebuilt as a wheel and source distribution. Both installed
successfully into separate verification environments and passed all **11 command-help
checks** from installed package paths, with no detector, tracking, TensorRT or FiftyOne
SDK import. Both archives contain the queue worker, bounded FiftyOne worker, Hydra
launcher and export entrypoint. The wheel SHA-256 is
`462b460625337c612dcd2dd065a6b54aa37ea5d5f9c4b068a58b00a45b109918`;
the source archive SHA-256 is
`4e5c4fa5ed0a59fdf1379b00ff9e871b48f46428703eb2410f9f1b9f1394aff6`.
All 33 packaged export/core Python modules match the earlier standalone-test wheel
byte-for-byte; that minimal runtime was not modified during active inference jobs.

ConvNeXt-Tiny FP32 also passed the 118-call standalone matrix and independent tensor,
membership, rejection and bitwise native-restoration audit. Its labeled quality
verification remains a separate pending result.

Two bounded live publication failures passed against the actual ClearML SDK/server and
production session boundary. An unpicklable required artifact caused SDK serialization
failure; omitting a declared required artifact caused the production completion barrier
to fail. Each invocation created exactly one server-failed owner, zero Output Models,
and only its successfully uploaded diagnostic-prefix artifact. Forced downloads matched
producer/server hashes; the rejected or missing artifact was absent. Original diagnostics
and configuration survived, while owner context, signal handling, temporary configuration,
runtime directories and owned processes were restored or cleaned as required.
The parent independently rechecked both receipts and all three accepted archives; the
completion archive SHA-256 is
`dcdfdf1a177bcf58b04fce7a22ad028aa5788cc793da8bb7fc1a3bb37f71026a`.

These are real SDK/session failure checks with intentionally invalid inputs, not a
transport-outage, flush-false, native-model failure or public-export CLI claim. An earlier
scratch guard refused the first fixture before creating any owner because SDK automatic
pickling was enabled; that preparation refusal remains separate historical evidence.
Failed server resources are retained until final task-owned cleanup.

The actual public RF-DETR Nano pipeline also passed with FiftyOne enabled. One completed
owner (`0e07bcea14f3445db46c15f9b644c548`) published five canonical artifacts and no new
Output Model. A fresh process reloaded the isolated database dataset and checked all
12 samples, exactly three validation prediction/evaluation memberships, 64 preserved raw
rows, threshold exclusions and native evaluation results. Both observed bounded workers
returned complete envelopes, stripped inherited owner/admission variables and exited;
the supervisor found no surviving task-owned process or runtime directory. The source
checkpoint, ground truth and images remained unchanged. This is database/public-pipeline
evidence, not browser or model-accuracy evidence. Independently verified archives:
public pipeline `20f8f027abc665228de39a959ceaa5026dfd56d311d740fc9c713e6b0f2c8914`;
completion `39a74673724c35179062a9337a862f2e5b86ceecb79f6020564f928b287e2694`.

All six Faster R-CNN native matrices completed: 24 public training, prediction and
validation commands, six registered models, forced checkpoint downloads and standalone
descriptor reloads. The frozen candidates trained only on the designated training and
validation population. The parent verified the full archive, copied it outside cleanup
scope and reverified it: SHA-256
`a5f90af40c94da7547e03ff2eee5f4dc89e1b8a17dd0fb5f2ab6be01542bca2f`.
Separate fine-tunes are still checking the current General configuration publication;
they do not replace these frozen quality candidates.

ResNet-101 and ConvNeXt FP32 each passed all 22 labeled quality cases with no positive
mAP loss. Swin's original FP32 build failed at the 4 GiB workspace setting; the same
ONNX graph and metadata, verified byte-identical, built in both precisions with a 16 GiB
workspace. Swin FP32 passed the 118-call standalone matrix and independent tensor,
rejection and bitwise native-restoration audit. Workspace is a builder resource setting;
these outcomes do not imply a deployment memory bound or completed Swin quality gate.

Two real FP16 quality gates failed and remain release blockers. DINOv3 produced no
detections in every labeled case. ConvNeXt's maximum mAP loss was
`0.022882027715869606`, exceeding the unchanged `0.005` limit. Both owners correctly
failed after publishing their diagnostic verification report and corpus. A parent audit
confirmed exactly one failed owner per invocation, zero new models, matching producer,
server and forced-download hashes, unchanged sources/corpus and retained diagnostics.
The original Swin workspace failure also had one failed owner and zero artifacts/models.
Successful structural standalone checks do not override failed quality acceptance.

A bounded DINOv3 CPU investigation used one validation image, not the test population.
Every first-block attention score exceeded FP16's finite range; conversion produced
infinities and then NaN softmax values. FP32 score accumulation/output through softmax
remained finite. The original-operation prefix graph, inputs, measurements and scripts
were independently archived with SHA-256
`7bca20a30a040fa0cc6e9772a7e1e88fb5a0b9a63c3883e72af7009653061e7c`.
A targeted builder precision fix is undergoing actual TensorRT verification. The
ConvNeXt geometry investigation and all affected engine reruns remain outstanding;
neither thresholds nor checkpoint/corpus selection have changed.

The parent independently rechecked all eight DEIMv2/RF-DETR native matrices:
24 completed training, prediction and validation stages. Forced artifacts matched
their server hashes; each training owner registered exactly one model with an embedded
descriptor, and inference/validation owners registered none. Standalone copied
checkpoints required no sidecar, predictions retained the exact raw rows and validation
threshold artifacts were present. The three immutable archives remain outside cleanup
scope: `b8c876d37870ff44f915070d4d9d97e6c1388c77804de0544da9e6fb0fbb8272`,
`108f36ec7585eff13c305afa4d080209759e250bf28de416f1a971179cacee86`, and
`ad6c7baf54f6203ef416a90d6afc98dd85a90bbb198f4132e7d01bf30736ad6c`.
The first archive retains the earlier harness failure; accepted DEIM-L prediction and
validation come from its separate continuation. These one-epoch runs establish execution,
not accuracy. The five older fits still require their separate current-General check.

The focused export regression batch passed **99 tests** with four existing warnings;
Ruff passed and all **40 import contracts** remained intact. These intermediate checks
do not close the outstanding native quality, scheduling, final review or release gates.

All six FP32 engines have now passed both the 22-case labeled quality matrix and the
118-call standalone matrix, including Swin at the larger workspace setting. ResNet-101's
independent standalone audit was also sealed outside cleanup scope. This completes the
FP32 portion only; FP16 acceptance and required reruns remain open.

Real CPU native training-load failures passed separately for DEIMv2, RF-DETR and Faster
R-CNN. Tiny task-owned fixtures retained valid embedded descriptors but invalid native
weight payloads. A process observer confirmed entry into each backend's `train` and
Torch's actual checkpoint loader before failure; these were not application-preflight
rejections or mocked SDK failures. Each run left one failed owner, zero models/artifacts,
unchanged source checkpoint/corpus bytes and retained local diagnostics. The process
supervisor reaped all owned descendants. CPU telemetry bypass was observed; this does
not claim a GPU cancellation or optimizer-time failure. The parent rehashed the archive
and checked its three receipts: SHA-256
`043b24c3d6afab2b3616579bccd098e3d64ee27914d72c8e054002222df5495e`.

The actual DINOv3 TensorRT prefix probe confirmed the CPU diagnosis. The original
FP16 build overflowed its first attention matrix product and produced NaN softmax;
only five of 58 recorded intermediates remained finite. Applying the production
precision helper kept all 58 finite. Engine inspection confirmed FP32 score products
and softmax in all 12 blocks while projection layers retained FP16 eligibility.
The parent rehashed the immutable archive and independently checked all 47 payload
hashes: `bfa0fe50cc83f11dac5425e456c508b32c475fda1cab73fe5dad55bb53f94989`.
This validation-image diagnosis does not replace the full detector quality matrix.

A second validation-image investigation identified overflowing ROI box areas in
ConvNeXt FP16. The instrumented engine assigned 45 proposals to incorrect pyramid
levels after area overflow. The builder now protects floating ROI-level arithmetic
through its final clamp, without constraining the ROIAlign plugin. A broader initial
constraint failed because the plugin does not support the requested format; that
failed diagnostic is retained. The first narrow probe also exposed TensorRT's base
`ILayer` wrapper: operation inspection requires a local subclass downcast. Regression
tests reproduced that API failure and the floating-cast traversal gap before correction;
72 focused export tests passed, followed by six precision tests, Ruff and strict typing
after the final helper refactor. Actual engine and quality reruns remain pending.

ResNet-101's original FP16 quality gate also failed, with maximum mAP loss
`0.011796974691589746`. Its 118-call standalone structural audit passed but does not
satisfy quality acceptance. Swin's original 16 GiB FP16 build passed all 22 quality cases,
with maximum loss `0.004599123031606159`. All six FP16 engines are being rebuilt under
the corrected arithmetic policy against unchanged checkpoints, corpus and thresholds;
previous successes and failures remain immutable historical evidence.

Real isolation-conflict checks passed for all three native families. A conflicting
Torch cache selector outside the fixed invocation root was rejected before SDK imports,
native work or task creation. Parent environment and selector bytes were unchanged,
and owned descendants were reaped. The parent rehashed the accepted archive and checked
its three receipts: `caaf58576d446da01cd1e3bf6a0973a7d2d5ea2ddb230bd9f5124f7aa318954b`.
An earlier fixture tested a different root conflict and remains separate rejected
preparation evidence.

All six separate Faster R-CNN fine-tunes also passed. A fresh server audit found
exactly the 24 original native owners and six fine-tune owners. Each fine-tune owner
completed with one Output Model, exact `General` and canonical configuration, lexical
`0001` vocabulary and matching source/new-checkpoint identities. CPU checkpoint inspection
confirmed one actual training epoch, finite updated model tensors and byte-identical
trained-source, server and forced-download checkpoints. The six original quality
candidates remain unchanged. The parent verified every archive payload and preserved
copies outside cleanup scope: fine-tunes
`3e328e8af311f63e259efdf788f1d0f7f2d5f597aa4da2665182cae138abeadf`,
source inspection `7b291dce49d036417612cccbb9bfa0ddc29df6745b890fc3f017c0b73bd98c5b`.

The five remaining current-configuration fine-tunes completed for DEIMv2 S/M/L/X and
RF-DETR Nano. Their fresh readbacks confirm native `General` settings, canonical model
configuration and source checkpoint binding. Together with the earlier Small/Medium/Large
readbacks, all eight presets now have current configuration-publication evidence.
The parent rehashed the external archive and checked its five accepted receipts:
`db8d3371e3d271a8a628f8962f4132aabbc49dd8645ee56bef645faf249dce1b`.

The full suite passed **2,067 tests**, with **30 skipped** and 54 warnings, in 659.27 s.
This run precedes the final mixed-sweep fixes and does not close the final integration gate.
Actual sweeps exposed two initial-composition failures: the sparse default model group
rejected ordinary native overrides, then launcher inspection resolved job-number
interpolation before Hydra established a job. The first fix passed 181 affected tests
and exact SDK-free composition checks; live sweep retries and the second fix remain
under verification. Failed attempts created no owners or model work and are retained.

The corrected DINOv3 FP16 engine passed all 22 labeled cases with nonzero native mAP
and maximum loss `0.0019527692620386061`, below the unchanged `0.005` limit. Its engine
SHA-256 is `59a4999605d1d00d0ef59ccd1ca58772a036dc0d8f4fe8275fba500b8a2db2fb`;
verification owner `8fa975ff1a464852836d146a031d944d` published report SHA-256
`3387555ae6f8d34ee3e4474efddd1275ff356ca6b7b23c23cfd921c089652ba0`.
Source checkpoint, corpus and ONNX graph remained unchanged. The three accepted ONNX,
build and verification archives were independently preserved outside cleanup scope.
Its standalone run and other corrected FP16 presets are still pending.

The two sweep fixes and both-direction inactive-setting validation passed 125 affected
tests, followed by 11 final targeted cases. The exact failed sweep arguments pass
SDK-free full-sweep preflight in queued and direct modes. Whole-project Ruff, strict mypy
over 275 files and all 40 import contracts passed after integration. A new full-suite run
is in progress against this source snapshot; real sweep retries remain separate gates.

Portable wheel/source archives built from the integrated source snapshot, with only the
local `tool.uv.sources` section omitted from the build copy. The working overrides and
locked external dependency paths were unchanged. All 154 packaged Python modules match
the working source, including both bounded workers, queue launcher and export entrypoint.
Both installed archives passed all 11 SDK-free command-help checks. Wheel SHA-256:
`135306b386ac01d1ca64cb312c80750d2cb71863684b089acd9501793ac1b9af`;
source archive SHA-256: `bd02ffe9991460b96f7fe0d001122a569c4b158048f32b893ebc6ea2280b2d2e`.
The same wheel is installed in a fresh standalone environment without Torch, Torchvision,
timm, ONNX, ONNX Runtime, RF-DETR or ClearML. Documentation validation passed for 27 files,
257 local links, 42 fences, 32 command examples, 14 model selections and three references.

### 2026-10-12 — Integrated regression and remaining precision investigation

The integrated full suite passed **2,085 tests**, with **30 skipped** and 54 warnings,
in 682.09 s. The parent rehashed the 275-file source/test/configuration snapshot after
the run; every file remained unchanged. This establishes the current regression result,
while the remaining native and export acceptance gates still block completion.

Corrected DINOv3 FP16 also passed all 118 standalone calls over 24 shapes and 29 ordered
groups, including nine rejection checks. Independent inspection confirmed bitwise native
box restoration, finite outputs, counts from 1 through 300, exact source membership and
the fresh Torch-free environment using the recorded portable wheel.

The corrected ConvNeXt FP16 build still fails the unchanged quality gate: maximum loss
is `0.0055277153293578005`, affecting the four 608-by-960 batch cases. Its failed owner
`d744ede1e1014351aaf897c82aef63b2` retained the two required diagnostic artifacts and
zero Output Models; producer/server/forced-download hashes match. Checkpoint, graph,
corpus and thresholds are unchanged. Structural success cannot override this failure.

The parent rehashed every payload in eight preserved ConvNeXt diagnostic archives.
The narrow GPU probe now assigns all 1,000 proposals to the levels computed from their
own FP32 geometry, with zero routing mismatches. Its external diagnostic area binding
still contains overflow after Half materialization and a Float reformat; this binding
does not establish internal arithmetic precision. The saved inspector shows one
ROIAlign plugin already using Float/Float/Int32 inputs and Float output on both profiles.
The earlier broad constraint failure therefore does not establish a lack of FP32 plugin
support. A separate validation-image probe is tracing the remaining coordinate drift.

The real CPU mixed sweep retained the corrupt DEIM native-load failure while RF-DETR
and Faster R-CNN completed with 117 and 847 published prediction rows. Fresh readback
validated collision-suffixed display names, exact raw/published prediction multisets,
artifact hashes, no Output Models, unchanged inputs, no GPU telemetry and reaped owned
descendants. The original harness rejected the valid name suffixes; readback recovery
required no model rerun. Archive SHA-256:
`d76b2cb083577a1d2fb875fd387c25a1a8345c1910957234a213237bc235c586`.
The original before-ID snapshot was not persisted: the retained guard and later inventory
reconcile six known previous and three current owners, with no unknown owners. Future
sweep captures persist both before and new IDs. GPU sweeps and cancellation remain open.

Corrected Swin FP16 passed all 22 quality cases with maximum loss
`0.001049638352168654` and all 118 standalone calls. Independent inspection confirmed
24 shapes, 29 ordered groups, nine rejections, exact membership and bitwise native box
restoration. Counts range from 14 through 300; the maximum boundary roundoff is the
same native FP32 one-ULP value, `3.0517578125e-5` pixels. Corrected ResNet-101 still fails
seven quality cases, with maximum loss `0.014881226047676027`. Its three stage archives
and fresh failed-owner diagnostic audit are preserved separately from accepted results.

Parent integration review reproduced four silent metadata overwrites when candidate
and baseline referenced the same raw checkpoint with incompatible class names,
preprocessing, preset or backend interpretation. Binding now rejects a changed resolved
descriptor and restores the earlier reference; distinct display labels and thresholds
remain valid. The four regressions failed before the fix and the affected detector,
workflow, recovery and selection suite passed **75 tests** afterward. Ruff, formatting
and strict typing of the affected files passed. The preceding full-suite/package snapshot
predates this change; final integration checks will include it.

Release preparation exposed an existing incompatibility with the commit procedure:
`uv lock --offline` tried to resolve the registry dependencies after local source
overrides were removed. The approved dependency copies are represented by editable
lock nodes and must not be re-resolved. The release helper now updates only the source
commit's unique root-package version token, preserving every other lockfile byte and
retaining all later metadata, checked-commit, changelog and tag validation.

A protected-editable release regression failed at the old resolver call. All **42**
release-helper tests then passed, including real temporary Git/PSR/hooks/tag recovery,
unchanged dependency metadata, CRLF/comment preservation and rejection of missing,
duplicate or mismatched roots and prior lock drift. Ruff, formatting and strict typing
passed for both changed files. The parent inspected the implementation and tests;
this does not constitute the final independent review or an actual project release.

### 2026-10-12 — Scheduling, canonical replay and geometry diagnostics

All 15 real scheduling cases passed: each of DEIMv2-S, RF-DETR Nano and Faster R-CNN
ResNet-50 completed all four queue/autogpu combinations and a CPU bypass. The parent
rehashed the preserved archive and checked all accepted publication/provenance records,
exact native/published prediction retention, unchanged corpus and zero Output Models.
Archive SHA-256: `3bb70bad46d192094e2c0cc865cf196db92cb6ad489f08a205cfc30e11f2b3b2`.
Observed GPU telemetry was empty for CPU bypass and both-disabled children. This closes
the mode matrix, but the separate replay, sweep and cancellation gates remain open.

A real remote clone exposed two SDK integration problems: the inherited
`run/_ignore_remote_overrides_config_` parameter suppressed stored canonical values,
and connected nested proxy dictionaries could not be consumed by OmegaConf. Canonical
replay now reads the public configuration object directly, materializes plain detached
containers for execution, and writes a separately sanitized snapshot through the public
configuration setter. Only an absent object falls back to invocation defaults. A fresh
independent review found that the SDK normalizes present empty text to `None`; checking
the public raw-text reader now distinguishes this from absence and rejects it.

The seven original regressions and three empty-text cases failed before their fixes.
The affected session/replay/runtime/trace suite passed **221 tests**, with Ruff, formatting
and strict typing also passing. Independent review found no remaining issue in the
replay boundary. All six real policy/runtime rejection clones subsequently passed for
the three families, with one failed clone owner per invocation, no native work, no GPU
telemetry, no Output Models and unchanged source owners. The parent rehashed and checked
the six archived records: `f6d488dcbc95c4ac858a2c148a3713d7bb2876601f336b0feaf689fa4c8fab32`.
Compatible GPU replay and valid training-resource rejection remain separate gates. An
initial resource fixture incorrectly assumed inference could demand two GPUs; the
existing inference demand contract caps this at one, so that attempt is not accepted.

The parent also passed **100** affected comparison/cache/recovery/reinference tests
after the raw-checkpoint binding guard. The earlier full-suite and distribution evidence
predates these final integration changes and must be refreshed before completion.

FP16 v2 passed all 22 quality cases for ResNet-50 (maximum loss
`0.0002693845494128738`) and DINOv2 (`0.00037703469923387224`). Their three stage archives
were independently preserved. Together with DINOv3 and Swin this leaves ConvNeXt and
ResNet-101 failing the unchanged quality limit. No threshold, checkpoint or corpus has
been changed to obtain a pass.

A reduced ConvNeXt validation-image capture isolated coordinate arithmetic using each
engine's own anchors and regression deltas. GPU decoding differed from FP32 evaluation
of those same inputs by up to `0.941` pixels at the RPN and `0.6582` pixels at the final
ROI decoder; the CPU formula comparison stayed within `0.000122` pixels. Foreground
proposals above the fixed operating threshold also showed the drift, so it is not solely
an effect of background or out-of-bounds boxes. Weighted FP16 outputs also differ from
FP32; correcting geometry alone does not establish a quality pass. The parent rehashed
all payloads in the reduced capture and analysis archives, including SHA-256
`608847e4ba7fb656180fcf5df7a7ad074bb1612568957529d03f348dcffaca76` and
`c6ba41675532b5ef8dba6cced6f875341535ad164efe1196f3edf7f969b3c18b`.

A structural FP32 geometry policy is under native verification. It follows box/score
arithmetic back to weighted model boundaries and adds FP32 ROIAlign input boundaries;
weighted convolutions and projections remain eligible for FP16. An actual parser probe
identified Squeeze/Unsqueeze/Scatter nodes absent from the initial allowlist. A later
build rejected a floating computation constraint on integer-output NMS; the policy now
constrains its floating producers without setting NMS's own precision. Eight focused
regressions pass, but actual engine formats, coordinate accuracy and full quality still
require verification before this policy is enabled in the production builder.

All three compatible GPU replays now passed against stored canonical confidence and
device provenance. They retained one clone owner, exact published/native prediction
multisets, unchanged source owners and zero new Output Models. The parent rehashed the
partial DEIM archive and the two remaining accepted cases: respectively
`536e53f8e8807a33f2ab4cbfed58cd8e0f7d454a24f1c948a4405b4e2a563aee` and
`c6967ae29a96150361c64281a81d262d2caef5781ab7582dbfb93f677830c012`.

The corrected resource fixture used actual training entrypoints and cloned training
owners. All three rejected stored two-device demand against one admitted device before
calling a native backend. The parent rehashed and inspected all three failed-clone
records, with unchanged sources and no Output Models:
`e10afc92bf769cdbcbbc2a5a121d0c87429b9dd92c2ea25b73058d0bad85c3b5`.
Together with the six CPU policy/runtime cases, all twelve replay cases are accepted.
The first real queued mixed sweep then exposed another unresolved Hydra interpolation
in result collection after the job context closed. Its failure and completed first
owner are preserved; a focused fix and fresh sweep remain in progress.

Fresh ONNX preparation hit two failed ClearML naming lookups whose installed SDK
attempted to iterate `tasks=None`. Exact read-only repeats and an absent-name control
returned proper lists; the original raw response was not captured. The failures were
preserved, without treating missing lookup data as an empty collision result. ConvNeXt
passed a fresh retry; ResNet-101's next lookup also failed and is under observation.
ResNet-50, DINOv2 and Swin exports passed unchanged. The DINOv3 outer driver was
interrupted while its owned CPU export was finishing. Fresh readback recovered its
completed owner `f056fbf969a9423ca1c6cc491f28a85d`, exact one-owner delta, artifact hashes,
source lineage and zero Output Models; all three observed command identities were gone.
No CLI exit code is claimed for this recovery. Its sealed readback archive is
`61631e2f30a9c59014090b10cdc1cddab0c809d16765d5cea73587b406eb9cd4`.

The geometry probe progressed beyond NMS and ROIAlign format selection after removing
their incompatible computation-type constraints while retaining floating boundaries.
The next failure is TensorRT's mixed-precision lowering of a floating Pad/Slice with
implicit zero fill. Parser and official importer inspection confirm the zero fill is
legitimately omitted from the graph; its absence is not a malformed source model.
A minimal native probe is checking explicit typed zero fill before any production
policy change or quality claim.

### 2026-10-12 — Mixed sweeps accepted; precision and cancellation work continues

Queued result collection now copies literal override expressions without resolving them
against an absent or stale Hydra context. Four real fresh-CPU-worker regressions failed
before the fix and passed afterward, covering successful and failed jobs. The affected
queue/scheduling/resource/runtime/trace suite passed **218 tests**. A fresh independent
review passed nine focused lifecycle/override cases and found no remaining issue. The
parent inspected the integrated change; existing callback and cleanup paths are retained.

Both live GPU mixed-family sweeps then passed: queued and direct modes each produced
exactly three completed owners in DEIMv2, RF-DETR, Faster R-CNN order, with prediction
counts 1,800, 116 and 842. The parent rehashed the archive and checked ordered owners,
exact raw/published row retention and unchanged corpus. The archive's before/after
inventories, server artifact hashes, direct admission lifecycle and zero owned survivors
were independently verified. Archive SHA-256:
`80359ae9c4ec4a6616444e8949c36d96dbe128ca140428c395bf5372d8bc6e68`.
Together with the earlier CPU failed-sibling and isolation cases, this satisfies T036.

The cancellation observer initially missed Torch's inherited `Adam.step` implementation.
The task-owned training controller and descendants were stopped, and its reservation
closed; that training attempt is not an accepted first-step cancellation. A real tiny
CPU AdamW/SGD check verified the corrected observer without initializing CUDA. Fresh
cancellation probes use bounded first-step/wait deadlines and retain the already accepted
DEIM wait case; their server finalization remains under verification.

All six freshly published ONNX graphs are byte-identical to the previous accepted graphs.
ResNet-101's second fresh retry passed under a lazy diagnostic observer that preserved
normal SDK initialization and request behavior. The actual worker observed two HTTP 200
queries with populated raw and typed task lists; the earlier nullable response was not
reproduced. No naming-source patch or silent empty-result fallback was introduced.

Whole-project Ruff checking, strict mypy over 276 files and all 40 import contracts passed
after the replay and queued-result changes. Documentation validation passed for 28 files,
257 local links, 42 fences, 32 command examples, 14 presets and three references.
An additional repository-wide formatter check found 22 files requiring formatting,
including unrelated baseline content. The one new task-owned helper was formatted;
the existing formatting in untouched sections was preserved. Formatting the entire
repository is not a configured commit gate, and no repository-wide format pass is claimed.

The small native padding controls all build and run with exact values, including an
explicit FP32 Cast on payload and fill while the convolution remains Half. The small
fixture does not reproduce the full graph's Myelin failure. The next full diagnostic
probe therefore tests this value-preserving boundary as a candidate workaround against
the same validation image and graph; it is not yet a production or quality result.

### 2026-10-12 — Geometry padding workaround reproduced in the full diagnostic graph

Explicit FP32 casts on floating padding payloads and fills resolved the full diagnostic
graph's Myelin build failure. Ten selected FILL slices received twenty casts; five
implicit zeros became explicit scalar zeros, and five existing fills retained their
values. Integer shape inputs and the frozen source ONNX graph were unchanged. All five
RPN decoders and the final box decoder agreed with FP32 arithmetic on their own captured
inputs within 0.0001221 pixel, with no area overflow or pyramid-routing error. The engine
inspector showed all eight ROIAlign instances across the two profiles using
Float/Float/Int32 inputs and Float outputs; 156 weighted layers retained Half inputs.

The four NMS instances still used Half boxes and scores despite their producers' floating
constraints. Their precision boundary remains under investigation. These results prove
the diagnostic arithmetic correction, not the full quality gate. The capture archive is
`dd7884ca33d8ec14fb263ac8589a2d38a41dfb4cfe990ee54eb0c04af1392ce5`;
its separate analysis is
`76ef7619bd334ec4b4c87d5743e2ac274462aa0c40d8587a4f53742e224a9314`.
The admission ticket closed after its child exited.

The padding helper now has focused coverage for implicit zero, nonzero fill retention,
dynamic integer shape inputs, non-FILL slices and shape tensors. The export-focused suite
passed **110 tests**; targeted Ruff and strict mypy passed. TensorRT 10.13's Python binding
retains arrays passed directly to `add_constant` for the network lifetime, so the helper
does not retain raw pointers to expired temporary storage.

ResNet-101's first failed ONNX retry was also preserved outside cleanup scope, archive
`23aaa72b93661cc3b219bc214721ad5f889ab178fa7bf1d4566663119c46f2fd`.
It remains a failed SDK naming lookup, separate from the later successful observed retry.

### 2026-10-12 — Cancellation and scheduling acceptance complete

All six cancellation cases are accepted for DEIMv2-S, RF-DETR Nano and Faster R-CNN
ResNet-50-FPN: three while queued before owner/native SDK initialization, and three after
actual optimizer returns. The training observations recorded one, two and two optimizer
returns respectively. Each training owner finalized as failed with no checkpoint artifacts
or Output Models. All owned descendants were reaped before their admission reservations
closed, and the three source checkpoints and thirteen smoke-corpus files remained unchanged.

An independent saved-evidence audit rehashed both cancellation archives, inspected all
six cases and verified 59 critical archived case/control/log files. The parent verified
the audit receipt's hash and inspected its case records and limitations. Final-v2 archive:
`d6afbeed1aaca5ca7f02e1b1ab24c1ecf957bf92eacb579b625513308bd38bf6`.
The original accepted DEIM wait case remains in
`eaed76d7fb646dd79ec9c05499abdb5f1ed7dc502e2e7f5a039c25b1830493fd`;
its failed training-observer attempt is excluded. The external observer/admission helpers
were inspected at their current paths; they were not individually pinned inside those
cancellation archives. Saved readbacks were audited without repeating live cancellations.
Together with the fifteen mode cases and twelve replay cases, this completes T035.

The independent audit also rehashed the observed naming retry, both minimal padding
controls and the full geometry capture/analysis, verifying 105 archived payloads and their
inventories. Its receipt SHA-256 is
`3ec40393ba57729a938eb4e90a6bd94aaa8e6a5a8cc2619b33e44fc2d5220a4f`.
The NMS and quality limitations above remain unchanged. A separate parent check compared
all 119 digital-metrics and 27 report-generator source files against their approved Git
revision blobs and found no differences.

### 2026-10-12 — Explicit mixed precision passes the full diagnostic

A minimal NMS control demonstrated a selection error near the IoU boundary: weak FP16
optimization retained three boxes where FP32 retained two. Explicit Float input casts
still produced Half NMS inputs. Forcing Float computation failed format selection even
with explicit integer output types; disabling global FP16 rejected forced Half weighted
computation. A strongly typed graph with explicit Half weighted computation and Float
NMS produced the expected two boxes. The unsuccessful controls remain preserved.

The production builder now lowers weighted Conv/Gemm/MatMul operators in memory with
explicit Half inputs and Float return boundaries, then builds a strongly typed FP16
network. Dynamic attention/interpolation products and other operations remain Float.
The superseded weak precision helpers were removed after preserving their source and
tests externally. No checkpoint, training recipe, evaluation threshold, corpus or source
ONNX file changed.

All six original graphs passed full ONNX checking and strict type inference after this
lowering. Weighted operation counts are 80 ResNet-50, 131 ResNet-101, 85 ConvNeXt,
76 DINOv2, 76 DINOv3 and 79 Swin. Their external tensor declarations remain byte-identical;
the dynamic products remain Float. Independent helper review found an unused graph-input
name collision; a real ONNX checker regression reproduced it, and the expanded namespace
reservation fixed it. Five focused checker/reference-evaluator tests then passed.

The full ConvNeXt validation diagnostic built and ran. Across both profiles, the actual
engine inspector records four Float NMS instances, eight Float ROIAlign instances and
164 weighted records with Half inputs. All outputs are finite; all 1,000 own proposals
have correct ROI routing. Each decoder's error matches its CPU FP32 arithmetic baseline,
with maximum 0.0001220703125 pixel. Production lowering and the pinned diagnostic lowering
are byte-identical before instrumentation. This is diagnostic proof; extra outputs can
change tactics, so the full public quality matrix remains a separate gate.

The parent rehashed eight archives and all 105 members. Stable six-graph CPU archive:
`b32ff3f2d065ed94b413f3d7ef94b0dce3ed712c76cde2adb0ac2e2a35f238ec`.
Full GPU diagnostic:
`2cf001444ddead2043d4bce4f48fb3faf5826d20626956d883def2ebc7b77f9b`.
Own-input analysis:
`0a6f44e574f86d0ec5014ff91a485c9ea2258066aa876779c2cc4388bbcd243b`.
The diagnostic child exited and ticket 215 closed before production acceptance started.

The integrated export-focused suite passed **102 tests**. Whole-project Ruff, strict
mypy over 276 files and all 40 import contracts passed. The fresh wheel and sdist contain
all 155 source modules byte-for-byte, and both installed distributions passed eleven
SDK-free command helps. Wheel SHA-256:
`86dd4b35f74ccedafd48c1fc23d7ceea8a64cabc778ac4281c1cd0be8658eae9`;
sdist: `ca7320f33763ab1710591f105dd0b8d6befbbc20961f66d19b3bfaac8f48b0fd`.
A new standalone environment contains no Torch, Torchvision, timm, ONNX, ONNX Runtime,
RF-DETR or ClearML; importing the runtime/preprocessing modules made no CDLL calls and
did not import TensorRT. Standalone runtime source bytes match the preceding FP32-tested
distribution. The full application suite and six production FP16 builds/quality checks
are running against the integrated source snapshot.

### Typed production matrix and parent regression follow-up — 2026-10-12

ConvNeXt-Tiny's explicit weighted-FP16 build passed all 22 frozen quality cases;
maximum absolute mAP loss was 0.0015758974543229817 (limit 0.005), with a positive
native reference in every case. Independent readback inspection verified the same
12 test images, 33 foreground boxes, four annotation-negative images, class `0001`,
checkpoint, original ONNX and inference settings. All three public stages retained
one owner and zero additional trained models. The six-preset FP16 matrix remains open:
ResNet-101's typed build failed all four batches at 736×960, with maximum loss
0.005436780722038778; its other 18 quality cases and preprocessing checks passed.
The failed owner `803339dfa45a4d6299a136520170ead2` retained the verification report
and corpus. Its local report SHA-256 is
`6ba77da628d12f09187cad1c1782e401210804a7910a0c792cda90fbbdae9a1a`;
this local inspection does not assert a forced server download for the failed stage.
Checkpoint, corpus and thresholds remain frozen while numerical diagnosis continues.

The parent ran ConvNeXt's downloaded typed engine in the fresh v5 minimal environment:
118 calls, 24 shapes, 29 sequence cases and all nine metadata/shape rejection controls
passed. The CPU audit found finite/bounded detections, correct padding and bitwise native
coordinate restoration. The eight stress images all contain annotations, including
crowded images; they are not an annotation-negative corpus. Annotation-negative coverage
comes from the labeled quality corpus, and the separately archived confidence-one engines
establish zero-output handling. The sealed standalone archive has SHA-256
`4aceba25a8e8ea28dcf5b2d3c5e5192e39508e86e0bd54023dbbf7f0503ee93d`.

Independent retrospective inspection accepted all six FP32 quality reports, each with
22 cases and the same meaningful frozen corpus. Maximum loss was
0.00000027219379440668323 for ResNet-50 and zero for the other five presets. ResNet-50's
11 saved verification files matched their original inventory but lacked a retained seal;
they were copied and sealed during this audit, leaving the originals unchanged. The new
archive SHA-256 is `bb9a14e4eca76282e4d7e61b61e4dfc28ddcd3f1857389e8349aba988c3c22ee`.
Its accompanying provenance explicitly says archived now, rather than claiming a
historical archive existed.

The first complete regression run finished with 2,108 passed, 30 skipped and two failures
in publication tests. Both failures were stale reads of the `configuration` keyword after
the production boundary switched to ClearML's public `set_configuration_object` method,
whose dictionary argument is `config_dict`. Independent reproduction failed both tests;
changing only those two assertion keys retained all behavior assertions. Publication and
session tests then passed together (102 tests); file Ruff/format/mypy checks passed.
No production change was needed. A full rerun with CUDA hidden is in progress. The first
suite's GPU context was observed, but static investigation did not establish its origin;
it must not be attributed to these assertion failures.

The original 278-file source snapshot has SHA-256
`25ceabb782e83b5f7ff1812cdcef54db209c1acda295cad891d20caed9db155f`.
The rerun snapshot changes only `tests/test_publication_commands.py` and has SHA-256
`ddc85e53135e4c2c84efd090e9c2ffe226a2e568a7c6bc00900aeeeee29b3463`.
The package and production acceptance source bytes remain unchanged. The guides now
link to this dated record for observed status rather than retaining stale pending banners.

The complete CPU regression rerun finished successfully: **2,110 passed, 30 skipped**
(54 warnings, 648.33 seconds). The parent verified all 278 source-snapshot hashes again
at completion; no files changed during the rerun. The skipped checks remain skipped,
and this suite result does not replace the actual native/export acceptance evidence.
The two publication failures above were resolved solely by correcting the public setter's
argument name in their assertions.

Typed ResNet-50 and DINOv2 subsequently passed all 22 public quality cases, with maximum
mAP losses 0.001636111482792163 and 0.00037225997983039195 respectively. ResNet-50 also
passed its 118-call standalone matrix and all nine rejection controls; its sealed archive
SHA-256 is `5cfad7660cd77dd3ea75127601d6cea0f4f8aff989765b256fe803f5bdcfdcfb`.
The parent independently rehashed that archive and ConvNeXt's archive, including all
123 payload members in each. ResNet-101's failed gate and the remaining matrix entries
still block final export acceptance and release.

### Detection-head numerical isolation — 2026-10-12

The ResNet-101 investigation used only the first frozen validation image, `000000000089`,
at 736×960. Two instrumented GPU engines captured the inputs and outputs of all 19
RPN/ROI detection-head operations. A CPU ONNX Runtime reference recomputed each operation
with its own captured GPU inputs and the original FP32 weights. This isolates head
arithmetic from upstream feature differences; it is not another test-corpus accuracy run.

| Head group | Largest FP16 arithmetic error | Largest FP32 arithmetic error |
| --- | ---: | ---: |
| RPN hidden convolutions | 0.2055969238 | 0.0000495911 |
| RPN objectness logits | 0.0393638611 | 0.0000171661 |
| RPN box regression | 0.0115900040 | 0.0000038147 |
| ROI hidden projections | 0.5010681152 | 0.0000267029 |
| ROI class logits | 0.0040388107 | 0.0000038147 |
| ROI box regression | 0.0012586117 | 0.0000009537 |

Both engines produced finite outputs. The candidate kept 112 weighted backbone/FPN
operations in FP16 and all 19 detection-head operations in FP32. TensorRT's inspector
confirmed these types in both optimization profiles. The inspector attached to the
execution context returned no layers, so the retained type evidence comes from the
contextless inspector. Upstream FPN arrays differed between the two builds; the local
arithmetic comparison therefore does not establish whole-pipeline parity or explain the
test mAP loss by itself. No checkpoint, corpus, threshold or training setting changed.

The parent independently verified five preserved archives and all 47 members. The actual
GPU archive SHA-256 is `2c053741e070b065c1b7f209b928c7f6c193ba4bed4a08a90b6766fac94c1c7c`;
the two-policy arithmetic analysis is
`56706cf7ad48600a938ec02785a1b3eedd249c793c5fa1170aeb15e7d0cbcea2`.
Source/checkpoint/input bindings, instrumented graphs, serialized engines, captured arrays,
inspector records and admission/process closure evidence are retained outside cleanup
scope. Four new Conv/Gemm/MatMul regression cases fail against the current lowering
because it also converts detection-head operations. A common FP32 detection-head policy
will require fresh six-preset quality and standalone acceptance before release.

The baseline typed matrix finished with five accepted presets and the ResNet-101
failure above. DINOv3 and Swin maximum losses were 0.0015630506709941872 and
0.0016081563485581957 respectively. Their standalone 118-call matrices also passed;
archive SHA-256 values are `cb60146c6befc188db309ff1228749d27795627e85dd055708cae95bb9f84032`
and `8b7cb4feb7f92ace308d36fc5b864423ef0195bc16a0e4ef8a1ee15cbde93d37`.
The independent baseline audit retained all 18 stage archives and found every native
reference identical to the earlier FP32 reports. Its compact sealed evidence SHA-256 is
`63fead425afb965536f995820e46cd14bd01a3d83a88db26251fa42becff3181`.
These results remain bound to the prior precision policy and v5 distribution.

The parent then integrated the common FP32-head policy. The four failing regressions
now pass; the affected export suite passes **106 tests**. All six real frozen ONNX
graphs pass full ONNX checking and strict type inference: their 19 head operations
are byte-unchanged FP32, their dynamic attention products remain FP32, and respectively
61/112/66/57/57/60 backbone/FPN weighted operations lower to FP16 for
ResNet-50/ResNet-101/ConvNeXt/DINOv2/DINOv3/Swin. Source ONNX bytes and external tensor
contracts remain unchanged. Whole-project Ruff, strict mypy (276 files) and all 40
import contracts pass. The new 278-file source snapshot SHA-256 is
`dd2815d8641df3ea4b10495e6845ec76ec8e224410153cc5c057e72218d74b0a`;
only `precision.py` and its regression test differ from the preceding passed suite.

The v6 wheel and sdist contain all 155 current source modules byte-for-byte, and both
installations pass all eleven SDK-free command helps. Wheel SHA-256 is
`72b1601be5bb9cdb79fa946020f5117fceb3cc71aadae3afea25960e3e503044`;
sdist is `6174ce080576a577e7114468115e0eac1f429a00e96ecdfeaae2037cc5d61b15`.
A fresh minimal environment contains this wheel, TensorRT/CUDA and ordinary array/config
dependencies, without Torch, Torchvision, timm, ONNX, ONNX Runtime, RF-DETR or ClearML.
Guarded runtime imports made no CDLL calls and did not import TensorRT. Its runtime,
preprocessing, metadata and core export/model modules remain byte-identical to the
previously tested FP32 distribution. A fresh six-preset public FP16 matrix and complete
regression suite are running; none of the old-policy FP16 results replaces those gates.

The complete v4 regression suite passed **2,114 tests, with 30 skipped** (54 warnings,
647.26 seconds). Its 278 source hashes remained unchanged throughout execution; log
SHA-256 is `7bf05f56e217a60d797f74bd77e2cd38c721835efdefc62ae1802681d5c85dca`.
Documentation validation passed for 28 Markdown files, 259 local links, 42 fences,
32 composed command examples, all 14 presets and three reference examples.

The fresh ResNet-101 FP16 gate nevertheless failed again: maximum mAP loss
**0.007796392527663301**, affecting all four 736×960 batches. The unchanged native
references, checkpoint/corpus and regenerated ONNX bytes were independently confirmed.
Failed verification owner `006795248f334453b5726e7c52a81e13` and its local producer report
remain recorded; the failed stage is not claimed as a successful forced server readback.
The local failed-report archive SHA-256 is
`65e22384822f4ab013b420a73fff4cf4dfde6589244391ffab4bb872175e18ad`.
ConvNeXt passed all 22 fresh v4 cases (maximum loss 0.0021799234357622876) and its new
118-call standalone matrix. ResNet-101 still blocks export acceptance and release.

A fresh read-only numerical review compared the two validation diagnostic inspectors.
Of 224 common backbone/FPN convolution records across both profiles, 144 changed tactics
between the two builds: 134 in the backbone and ten in the FPN. The parent reproduced
those counts and replayed five saved RPN class-convolution inputs on one CPU thread.
For the first level, actual GPU error against a Float reference was mean 0.00476954,
maximum 0.03936958. Rounding operands, bias and output to Half while accumulating in Float
produced mean 0.00231031, maximum 0.00904465. These results establish error beyond that
simple rounding simulation; they do not identify the GPU accumulator's type. The next
validation-only probes isolate FPN own-input arithmetic and the installed SDK's Conv
cast-up behavior. They do not change the quality corpus or use test-label analysis.

### FPN numerical isolation and shared precision boundary — 2026-10-12

The parent stopped the remaining v4 matrix after ResNet-101 failed. ConvNeXt retained
its accepted quality and standalone results. ResNet-50 completed ONNX generation and
engine build, but its queued verification was cancelled before creating an owner:
exit 130, identical saved project task sets and both owned processes reaped. DINOv2,
DINOv3 and Swin were not attempted under v4. The independent partial audit preserved
all nine stage archives; its compact evidence SHA-256 is
`bb7ec4786acd6ca44a393055ecc4cc5e404ca0b10805bd41c94516966175e1b6`.
This cancellation is distinct from a measured quality failure.

A bounded six-convolution micro-engine compared direct Half, Half-to-Float cast-up
and independent Float branches using two saved validation convolutions. Both cast-up
branches retained actual FP32 activation/filter/bias/output formats and Float tactics;
the casts remained separate. Their outputs equalled the independent Float controls
bit-for-bit. Thus this installed SDK did not establish Half multiplication with Float
accumulation for the tested pattern. Direct-Half numerical error exceeded a reference
that rounds operands and output to Half while computing in Float; that observation
does not itself establish the internal accumulator type. Ticket 242 closed after all
three owned processes were reaped. The parent verified all 472 archived payloads and
archive SHA-256 `452dccd1028cface4bb2eef8b610d1d4197542573fcd95489d93358f7a5002f2`.

The separate FPN probe used the same first validation image and 736×960 shape. Its
baseline retained eight Half FPN convolutions and Float detection heads; the candidate
kept both FPN and heads Float, leaving 104 backbone weighted operations Half. All
captured outputs were finite. Against each convolution's own-input Float reference,
the baseline's largest errors ranged from 0.0151 to 0.1748; the candidate ranged from
0.00000191 to 0.00003052. Baseline residual error against Half-rounded operands/output
with Float arithmetic remained substantial. All eight candidate FPN outputs also
improved in mean absolute error against the original native Float producer closure.
Only the first backbone-to-FPN input was bitwise identical between builds; the other
three changed with TensorRT tactic selection. This supports preserving local FPN
arithmetic, but it does not establish whole-pipeline quality or remove backbone drift.
The parent verified all 38 payloads across the three diagnostic archives. GPU evidence
SHA-256 is `0c488926ff210d5f33054c915c43dcabed7bca89bce0a0db16f95c1644313dc5`;
the own-input analysis is `64d48540a82e98cdc9523d718f222a7864ac8f71c2bd89e9c2b3402b9b20cd92`.
Ticket 240 closed with no owned descendants remaining.

The resulting common policy keeps backbone weighted operations Half and FPN plus
RPN/ROI heads Float. Two new FPN regression cases failed before integration and passed
afterward; the focused export suite passed **108 tests**. All six frozen ONNX graphs
passed full checking and strict type inference, with byte-unchanged external contracts,
27 unchanged Float FPN/head operations and respectively 53/104/58/49/49/52 Half
backbone operations for ResNet-50/ResNet-101/ConvNeXt/DINOv2/DINOv3/Swin. The source ONNX
files remained unchanged. Whole-project Ruff, mypy (276 files) and all 40 import
contracts passed. An initial mypy invocation omitted its target and failed usage;
the corrected documented `mypy .` command passed.

The new source snapshot SHA-256 is
`a5158f441fd30a1633b5cba9d0bb8488cb42987376de2ae1e12342e187f41879`;
only the precision helper and its tests differ from the v4 snapshot. Static six-graph
evidence SHA-256 is `d900f507d7d6cde994530b4483eea8037cfca9cbf0ce4e1db21853081499e5f1`.
Fresh public ResNet-101 acceptance runs first; the remaining five presets depend on its
unchanged 0.005 quality gate passing. No checkpoint, corpus, threshold or training
setting changed, and no previous-policy FP16 result is promoted to this policy.

The Float FPN/head ResNet-101 run completed all 22 quality cases but failed the same
fixed gate: maximum loss **0.007696958440674209**, at all four 736×960 batches. Its
engine SHA-256 is `1531171937ad174108198b724532ac485bb6a53040ea3ff30879df14480ba247`.
ONNX owner `fb43a8aa54fd49cb9084fe2a3bf33171` and engine owner
`757be999c61a46799193c39959db10bc` completed; verification owner
`c46fcda590d04e68b806b5cd1f8132b0` failed. The driver exited 1 after reaping its owned
children. No other preset was started under this policy. Further investigation targets
the SDK's accumulation controls using saved validation operands, without another
test-corpus run until a numerical mechanism has been established.

The v7 wheel and sdist passed byte comparison for all 155 source modules and all three
installed environments. Their hashes are
`59915d14f398cdc6e067f96867e819715b36ed3b6aabecb6c8eea1096d2487ab` and
`43d42ae8109862fb54e5fd3b069fb8cb08ccc0c9c285192ff217bd3df3b47c3b`.
All 22 installed command helps and seven guarded minimal-runtime imports passed, with
no heavy SDK imports or CDLL calls. The fresh minimal environment has the same ten
runtime dependency distributions as v6. Only the precision module differs from v5/v6;
the other 154 modules, including build and runtime, remain byte-identical. The parent
verified all 50 packaging-evidence payloads and archive SHA-256
`2e70e0b901e6384b87c390e3a73efdb8998a600b546b5316574b42a05f33cb51`.
These are packaging results, not acceptance of the failed precision policy.

An independent v5 audit confirmed all 22 native metrics/counts, checkpoint, corpus,
inference controls and regenerated ONNX match v4. It preserved the three public stages
and failed local report without claiming a successful failed-stage server readback.
The parent verified its 11-member compact archive, SHA-256
`b483544e6eec14ad46e294bd9a3ca3fa4df0dceb238e39cb4add167078871afe`.

The next bounded microprobe requested weakly typed Half convolution computation with
Float output, with FP16 enabled, TF32 disabled and `OBEY_PRECISION_CONSTRAINTS` set.
TensorRT failed the only build attempt because it could not find an implementation
for the first 1×1 candidate. No engine was serialized; no inference or accumulation
precision is claimed. The optimizer stopped before establishing support for the 3×3
candidate. Ticket 245 closed after all three owned processes were reaped. The parent
verified its 210-member archive, SHA-256
`a9a0d33bc9149d495cb91b2a89556e77a52c58091f1803caee2454290065ee20`.
Production remains frozen while a structural pointwise MatMul mechanism is investigated
using saved validation operands only.

### Pointwise multiplication mechanism — 2026-10-12

The preliminary pointwise probe was interrupted after its first execution because its
Half external inputs did not reproduce production's Float input boundary. Its candidate
multiplications used Float kernels. That graph also exposed the Float product before
the Half result cast, so it cannot establish whether an immediate result cast enables
fusion. Ticket 246 closed with all three owned processes reaped. The parent verified
all 1,139 archived payloads, SHA-256
`3b160aa2690857c65a0e99d31f707a071ff6af5b22dd8da03fdf166e4bdb7e47`.
This excluded attempt remains preserved rather than treated as mechanism evidence.

The corrected graph uses original Float validation activations and original Float
initializers for two actual ResNet-101 pointwise convolutions, including stride two.
It tests NCHW and NHWC matrix layouts, each with Float-result and immediate-Half-result
candidates plus independent quantized Float controls. Separate Float activation bindings
prevent common-subexpression merging of the candidate variants. CPU references cover
batch one, batch two and odd spatial dimensions; Half product rounding occurs before
Float bias addition. The exact graph hash is
`524a9fe19cfcb4b28b4350ff22b0fd77eeed7fcf9855e97d99c9cb9cbe767276`.

The first corrected build failed after a tactic requested 1,107,886,080 workspace bytes
against the 1,073,741,824-byte cap. It produced no engine, inference or inspector, so it
does not establish whether the cast pattern is supported. Ticket 247 closed with all
three owned processes reaped and source/input hashes unchanged. The parent verified
all 926 archived payloads, SHA-256
`edeb732996c5b1a427fbb43cbf9ba6cd1e40239a6f4ffad297e2176682b224f0`.
A bounded retry changes only the workspace cap to 2 GiB; production remains unchanged.

That exact-graph retry completed one engine build and all three executions. Each detailed
inspector exposes four mixed GEMMs with Half operands/results, fused Float MatMul and
immediate Half cast metadata, and `f16f16_f16f32_f32` tensor-core tactics. Eight other
GEMMs—the Float-result candidates and independent controls—use actual Float arithmetic.
Both NCHW and NHWC layouts demonstrate the mixed mechanism; none became a convolution
or an opaque ForeignNode. The parent reproduced these inspector checks for all shapes.

All outputs were finite. Against quantized operands accumulated in Float and then rounded
to Half, mixed-branch mean residuals ranged from 0.000000445 to 0.000000921, with maximum
residual 0.0078125. These numerical results corroborate the typed graph, fusion metadata
and selected tactics; numerical agreement alone is not the accumulator evidence.
Odd 183×239 inputs produced the expected 92×120 stride-two output. Ticket 248 closed
after all three owned processes were reaped. This proves the bounded multiplication
mechanism, not full-detector quality.

The next implementation uses NCHW pointwise products and preserves Float spatial
convolutions, FPN and heads. Before implementation, the expanded regression suite
reported **28 expected failures and eight passes**. The failing cases cover Float
accumulation/private product rounding, dynamic odd shapes and strides, unchanged Float
convolutions, nonzero bias, Gemm coefficients/transposes/broadcasting and MatMul operand
order/broadcasting. Whole-model validation and the fixed test gate remain pending.

The parent verified the successful microprobe's 989 archived payloads and archive hash
`55744d4376ad7df53d7d275d9eaac5ccb7e2944367278eb2e0a843e701755952`.
The integrated precision helper hash is
`2770d9adc128e34f56a9ffb0fdf14eca51f954ff2631c17f12fe01e7c7331988`.
All **133 focused export tests passed**. Whole-project Ruff and mypy initially found
one parameterization-style issue and three result-union indexing issues in the new tests;
the parent corrected those test-only issues, reran all 36 precision tests successfully,
and passed Ruff, mypy (276 files), formatting and all 40 import contracts.

All six frozen source graphs passed full ONNX checking and strict type inference.
The respective ResNet-50/ResNet-101/ConvNeXt/DINOv2/DINOv3/Swin mixed-product counts are
36/70/36/48/48/51, with 17/34/22/1/1/1 unchanged Float spatial convolutions. Each graph
retains 27 unchanged Float FPN/head operations, its original external contract and
source bytes; dynamic attention products remain Float. The parent verified the static
evidence archive, SHA-256
`551dcfd2a75b5c9faa47a04cf8b0680cccc3e01c964e3b8098a1ff0dc1788026`.
The corrected 278-file source snapshot hash is
`bace98ac1655f279ed96ac4409fcfe51dfc6a5f785f775df04e618e584af4500`;
only the precision helper and its tests differ from the prior Float-FPN snapshot.

A fresh focused read-only review returned **ship** for this rewrite after the parent
checks. It ran the 36 precision tests and 12 additional CPU probes covering atomic
rejection, tiny/asymmetric canvases, scalar/vector products and Gemm coefficients/bias
broadcasts. This does not satisfy T050 or full-model acceptance. One pinned full-model
validation diagnostic is now admitted, using only the same saved validation image.

The full ResNet-101 diagnostic completed one engine and one validation input. Across
the two compiled profiles, the usable contextless inspector maps all 140 pointwise
records to Half GEMMs with Float-accumulator tactics. All 114 physical convolution
records retain Float operands, weights and biases; the protected head products remain
Float as well. Only the full-frame profile executed in this diagnostic. TensorRT's
attached inspector returned an empty result with its slot-decoding assertion; that
limitation is preserved, while the 823 contextless records remain usable.

All 17 outputs were finite, with 34 detections. Against the unchanged original Float
reference, all 15 captured backbone/FPN tensors improved in both mean and maximum error
over the prior Float-FPN policy. The four backbone mean absolute errors decreased from
0.006670/0.005092/0.004274/0.000602 to 0.003520/0.002576/0.001999/0.000254. The parent
independently recomputed those comparisons from the frozen arrays. This is numerical
validation, not a detection-matching or AP claim. Engine SHA-256 is
`4b530f351348c9e7ee1a5152940e43fc87bae8941061fbad15ff0ff993d5801a`.
Ticket 249 closed after all three owned processes were reaped. The parent verified all
1,467 archived payloads and SHA-256
`85b9524d8c9fcadc1329b1ca5713709a1e095b5836e97b551855f8094a46eaed`.

The v8 wheel and sdist match all 155 source modules and the three installed environments.
All 22 guarded command helps and seven cold minimal-runtime imports passed; no heavy
SDK imports or CDLL calls occurred. The ten standalone dependencies match v7, and the
other 154 modules, including build/runtime, remain byte-identical. Wheel SHA-256 is
`222a3e9848164af4ddef08f343a52bc514fbe2527122528b85641c055f711509`; sdist SHA-256 is
`ed23e57c22f2d230d1d8318a8342443eefc60288ba15b8246f69e7d4689094f8`.
The parent verified all 52 packaging-evidence payloads and SHA-256
`20e89abb863858592082213e799ea1806ba62ba581be5c99d38de052930d87af`.
Public ResNet-101 quality and the full source-bound regression suite are running;
previous-policy FP16 results remain separate.


## Current pointwise policy: ResNet-101 acceptance and integrated suite — 2026-10-12

The fresh production ResNet-101 ONNX/build/verify sequence completed successfully with
owners `db9dffefbe2341cdb0236540b6f9575a`, `9662516e689e44ba8e2da333534aed0f`
and `c5f5ac7d38a849a7bd0d2063924c9f2c`. The force-downloaded quality report passes
all 22 cases at the unchanged 0.005 gate; maximum mAP loss is
**0.0006718693282109223**. Engine SHA-256 is
`c083ea3a566617e37c04724371aae2f00fd84bdc9cd1ec9adfce73f13316342a`;
checkpoint `49d3e814d6d47b3e5c39430bf477ced96824419280c0002e2c170d5f6fdc4e3f`,
source ONNX `ed0bf7d1c9cff8b44ec9283dd32f4c4b81d5fd060c37b8bbd33d5078f60b8290`
and corpus report `bef5c721108c5e6fc9f1b986b57373631819b18196f28d10473fb7f61d67230d`
remain frozen. This closes the previous ResNet-101 FP16 quality failure without changing
training, checkpoint, corpus, thresholds or the acceptance tolerance.

The v8 Torch-free standalone runtime also passes all 118 calls, 24 shapes, 29 sequences
and nine rejection checks. No forbidden SDK imports occurred. Independent finite-output,
strict resized-bound and bitwise native coordinate-restoration checks pass. The eight
stress images are annotation-positive, including three with at least ten person boxes;
this is distinct from the separately retained zero-output acceptance. Ticket 252 closed
and all owned processes were reaped. Parent verification confirms all 131 archive members
and archive SHA-256 `de3a35e136da60dadf5abd7f90b154b7ebbff6770970728321259dfa4ab0195c`.
Fresh current-policy quality and standalone acceptance for the other five presets is
in progress; these results do not claim their completion.

The current-source full suite completed: **2,141 passed, 30 skipped, 54 warnings** in
639.41 seconds. All 278 source/configuration/test hashes match the before/after snapshot
`bace98ac1655f279ed96ac4409fcfe51dfc6a5f785f775df04e618e584af4500`.
Suite log SHA-256 is `ce7e5614707188cc4acf8bba1e939579d963eecd1a06e8e3320a6ff3b1f5a057`;
execution receipt is `393a3b0d82ac474d951a25cbcae91cac547cd4b179f6c0c24b59e8d2a7ff2101`.
The owned runner verified process cleanup. Skips are not native execution evidence.


### Current-policy DINOv3 publication attempt — 2026-10-12

The first pointwise-policy DINOv3 attempt failed before ONNX execution under owner
`03f52cc8633646a0b7c53f518ebaf77c`. The unchanged naming boundary called
`Task.query_tasks`; installed ClearML raised `TypeError` at
`ret_tasks.extend(res.response.tasks)` because the response field was `None`.
No export stage completed and no model-quality result was produced. The original CLI
had no query observer, so its raw server response remains unavailable. Its owned runner
reaped three process identities. The failed evidence is retained separately with archive
SHA-256 `6484a249f2febde83ca9c05f20dcd080d3184867e644843710efd6aa3e3a3e25`.
A fresh observed retry is prepared without source, checkpoint, corpus, threshold or gate
changes; it must pass independently. Swin acceptance continues before that retry so
there is only one public ClearML matrix mutator.


### Current pointwise matrix and DINOv3 quality failure — 2026-10-12

The current-policy public matrix completed with five accepted presets. Each accepted
preset passed all 22 quality cases and its separately audited Torch-free standalone
matrix of 118 calls, 24 shapes, 29 sequences and nine rejection checks. The respective
maximum mAP losses are:

| Preset | Maximum mAP loss | Quality gate |
| --- | --- | --- |
| ResNet-101 | 0.0006718693282109223 | Pass |
| ConvNeXt | 0.0013790837041367798 | Pass |
| ResNet-50 | 0.0047069479472846565 | Pass |
| DINOv2 | 0.00008329501473760366 | Pass |
| Swin | 0.0016436599154593112 | Pass |
| DINOv3, fresh observed retry | 0.006491526836323883 | **Fail** |

DINOv3's fresh retry completed ONNX and engine publication, then failed quality at
736×960 for batches one through four. Its other 18 quality cases passed. Engine SHA-256
is `ac1e78a9390631fa589a9c2d87ba59c4b17855a3b53842adab89929b9e3efe97`;
checkpoint, original ONNX, corpus and inference controls remain unchanged. The
standalone coordinator correctly performed no inference for this failed-quality engine.
The original pre-ONNX SDK failure and this numerical failure remain distinct attempts.

The independent saved-evidence audit confirmed all 132 native-reference cases match the
prior FP32 metrics, counts and batch memberships, with identical checkpoint descriptors,
corpus and original ONNX hashes. Seventeen completed owners have verified downloaded
artifacts and zero attached OutputModels. This is not a project-wide model inventory
delta or a publication-acceptance claim for either failed owner. Nineteen stage archives
and the failed local quality report are preserved. Audit SHA-256 is
`1619a83044959bf84907991aec8b7161fb6f3c77335d2b11856622be5d964962`;
its sealed evidence archive SHA-256 is
`546613ee5d263a720e3986a444f7844c9cc84fdc1cfcbcedc1cdfd38e92131fb`.

A separate fresh read-only numerical review found no DINOv3-specific graph semantic
error: exactly 48 weighted MatMul operations are selected; all 4,132 other original nodes,
initializer bytes and external declarations remain unchanged. Full ONNX checking passes.
Half product rounding was already present in the earlier all-weighted-Half policy, so it
is not a newly introduced rounding boundary. Biases, normalization, rotary operations,
LayerScale and residual additions remain Float. Learned LayerScale values can amplify
errors; static inspection does not identify the cause of the quality failure.

The next diagnostic is restricted to the frozen first validation image, without labels
or AP calculations. It compares the original Float ONNX reference with intermediate
outputs from the unchanged current policy, before selecting any precision intervention.
Held-out results do not guide checkpoint selection, training, threshold changes or
operator-by-operator tuning. The fixed quality gate remains unchanged. This investigation
and its focused review do not satisfy T050 or complete the six-preset FP16 acceptance.


The parent independently verified the 18 current-attempt stage archives and both compact
matrix archives, covering 281 members in total; the original failed attempt was checked
separately. The five standalone archives were also independently rehashed. The compact
standalone aggregate SHA-256 is
`f2f2488a434c6985d819b892fa71f820af418697759c5230eca5fd6a8692c7d8`.
The completed retry observer is preserved separately with 18 verified members and archive
SHA-256 `19d449fcd95086a79e038eaee6b02d19705a12582025e9e79aad38da9a11ce6c`.
Its observations apply to the retry only, not the original unobserved SDK failure.


## QKV rounding diagnosis and correction — 2026-10-12

The unchanged-policy diagnostic used only validation image `000000000089` at 736×960.
Its 128 captured tensors were compared against the original Float ONNX closure on CPU;
this is not a newly executed native Torch forward. The source/checkpoint/input hashes
remain frozen. Patch embedding and the first normalization agree closely, while the
first QKV product has relative L2 error 0.0002109502. Same-input decomposition separates
operand rounding (mean error 0.0034194) from the additional Half result rounding
(mean increment 0.033723). First attention-value relative error reaches 0.006600576.
CPU score/Softmax calculations using saved post-rotary Q/K show 46 changed argmax rows
out of 16,590. This diagnoses numerical amplification without labels or AP calculations.

The actual TensorRT inspector identifies 48 Half products with Float accumulation per
compiled profile; the second profile fuses 12 with GELU. The first profile executed.
The original and instrumented engines match all 40 validation detections at IoU 0.99,
with maximum box difference 0.258217 pixels and score difference 0.000594. They are not
bitwise equivalent. Capture instrumentation is therefore held identical for the single
subsequent precision intervention.

Before building that candidate, the numerical decision rule required at least 50%
reductions in first-attention relative L2 and maximum error, lower mean error at all
four FPN inputs and all eight FPN convolution outputs, at least 10% geometric-mean FPN
error reduction, and finite shape-matching outputs for all 128 captures. The candidate
keeps all 12 combined QKV projections Float and retains the other 36 mixed products.
Actual inspector records confirm these types in both compiled profiles.

The parent independently rehashed the pinned inputs and recomputed all 128 comparisons.
Every predeclared criterion passes. First-attention relative L2 decreases from
0.006600576 to 0.0000272719, maximum error from 15.1668 to 0.102688, and the geometric
mean ratio of FPN convolution mean errors is 0.3942764. The four FPN input mean errors
decrease from 0.000184872/0.000697910/0.001365610/0.000549716 to
0.000118303/0.000269931/0.000557483/0.000229445. The analogous saved-Q/K CPU calculation
has zero changed argmax rows. This supports a shared attention precision boundary;
it does not establish the held-out quality gate.

The candidate engine hash is
`c55263695f7203bb18a112e02978a736d31f0f7fc57e44ff350d66fcb57f92ad`.
The baseline and candidate tickets 267 and 268 each closed after three owned process
identities were reaped. Their executed helper snapshots are preserved independently of
subsequent production edits. Baseline archive SHA-256 is
`6233240e464859df525154c76b870de3d140692949c2a381c6a2d52c74f8d4e4`;
candidate archive SHA-256 is
`8a4284ca3ad72783332b2b6253c96513f02ac3995bfaa3d23469e7d33773ca22`.

Production selection now traces the documented attention value branch rather than
anonymous weight names or backbone identity. Unsupported layouts/weights/biases/controls
and ambiguous producers reject before mutation. Output projections and MLP products
retain mixed precision. An ordinary static weighted product after Softmax remains
eligible. The test-first record contains 20 failures and one passing control under the
old policy, followed by a separate failing static-probability regression and its fix.
All 155 focused export tests now pass, as do Ruff, strict mypy on 278 files and all
40 import contracts. A fresh focused read-only review returned **ship**, independently
running 58 precision tests and seven additional atomic-rejection probes. This is not T050.

The new precision helper SHA-256 is
`e144ff0a801398ed4ea91d97de64b71c21723f14756dc50cd878730c258e3a1e`;
the attention selector SHA-256 is
`027a2a112bf495d2d5c25bba2571c3a1dbb79183e64ec27dd494202323d1e8f3`.
The 280-file source/configuration/test snapshot SHA-256 is
`02acdac9182952ccb437462d2682f178f992992eb03821790283fb74e6fab964`.
The full regression suite and fresh affected real acceptance remain in progress.


The parent verified both diagnostic TARs: 1,406 baseline and 1,369 candidate members.
The six-graph static archive has 29 verified payloads plus its inventory, SHA-256
`0df209b5354136d42256cf7492f59a3829967d0b0f6b3b06dff2fdd2b654fda6`.
All six full ONNX and strict type checks pass. ResNet-50, ResNet-101 and ConvNeXt
produce exactly the same lowered graph bytes as their accepted pointwise-policy
engines; their earlier runtime evidence is reused on that explicit equivalence basis.
DINOv2, DINOv3 and Swin have exactly 12 original Float QKV nodes each, with the remaining
lowered blocks unchanged modulo generated private names. Their fresh runtime gates
remain required.

The v9 wheel/sdist and three installed environments match all 156 source modules.
Only the precision module changes and the attention selector is added relative to v8;
all other 154 modules, including build and standalone runtime, remain byte-identical.
All 22 guarded CLI helps and eight independent cold imports pass without heavy SDK or
CDLL activity. Project-only offline installs preserve dependency versions and installed
dependency records. The minimal environment has no training or ClearML dependencies.
Wheel SHA-256 is `828d5014d26974d9ab38589f175b8abfd32771ec014487c0ef58208d6b509c11`;
sdist SHA-256 is `a94ffcd2b53103a7ad7fca69f60482c33323dc1db0cd0cc0cfbd9222025ac10d`.
The parent verified all 71 packaging archive members and archive SHA-256
`4c226533d13b0fc942e4719ec0699ece0c5b8e443550951d936804c9b7a5dafb`.

The first public QKV-policy attempt failed before ONNX under owner
`cf99dcaf24564911b5df7b4d14ab22df`; no quality case executed. Its observer records the
same process/thread/query identifier at task-list request entry, HTTP response parsing
and SDK return. The buffered HTTP 200 response identifies `tasks.get_by_id` and contains
`data.task`, while the SDK constructs a task-list response with `tasks=None`, causing
the existing iteration failure. This establishes an SDK-boundary mismatch, not its
transport/server cause: the prepared wire request and redirect history were not captured.
No SDK, dependency or shared-service patch was made. A fresh owner retries unchanged
source and inputs; the failed attempt remains separate evidence.


The current QKV-policy full suite completed: **2,163 passed, 30 skipped, 54 warnings**
in 627.39 seconds. All 280 source/configuration/test hashes match before and after.
Log SHA-256 is `5b84e84bf8a7059a7d44799292fea66998b287b1a073ff9589d90fc403e5ccc7`;
execution receipt SHA-256 is
`412fe7085837a31f49e0cb75820e36f62bb68165346b7c79f5988cc88689b2a1`.
The owned runner confirmed no remaining processes across 807 tracked identities.
The pending public build respected the shared queue while the suite held a CUDA context.
Skipped tests do not establish native execution or deployment outcomes.

### Fresh QKV-policy DINOv3 acceptance — 2026-10-12

The unchanged fresh retry passes all 22 quality cases with maximum mAP loss
0.000022587395822025458 against the fixed 0.005 gate. The native checkpoint, original
ONNX, corpus, class vocabulary and inference controls remain frozen. Build owner
`53007449405943f98a50fc34ee75bf48` and verification owner
`b4975ed3c7324802a485ba43f5e49141` completed with downloaded artifact hashes verified.
Engine SHA-256 is `34c816373deb1b3a8e8bce5a765b9c3ad434ae8e3e7c2c01adecc4b2db4d6321`;
verification report SHA-256 is
`a99d9f8b20ae45f57b37800693258cb3f14477fe398c909201acbb1529c23b8d`.

The v9 Torch-free runtime then passes 118 calls, 24 shapes, 29 sequences and nine
rejections. Independent finite-output, strict resized bounds and bitwise native-coordinate
restoration audits pass, with zero original-boundary roundoff in this run. The eight
stress images include three with at least ten annotated boxes and no annotation-negative
images; separate existing zero-output evidence supplies that case. Ticket 271 closed
after all three owned process identities were reaped. The parent independently verified
the 131-member standalone archive, SHA-256
`744898d813d81b69b661def6e99da2da9fcb484f024a5610f7b3e1208fec3ca5`.

The preceding pre-ONNX SDK failure remains separate. Its 28-member preservation archive
has SHA-256 `f9a4ef73b1694058a00ab5c90b1024f27ddc5b394ae3c1e0a2e9f2fa40f1dc71`,
also independently verified by the parent. It contains only that failed attempt's
observer, source snapshots and stage evidence. A later DINOv2 attempt fails at the same
SDK boundary before ONNX execution; it supplies no numerical result and requires its own
fresh attempt. No dependency or shared-service correction is inferred or applied.

Documentation validation at this point passes for 28 files, 261 local links, 42 fences,
32 shell examples, one Python example and four YAML examples. All 32 detected CLI examples,
14 presets and three reference forms compose without importing detector or tracking SDKs.
Final validation follows the remaining acceptance and documentation updates.

### ClearML reporting transport investigation — 2026-10-12

DINOv2's original QKV attempt and first retry, and Swin's first QKV attempt, fail before
ONNX execution at the same task-list boundary. Passive observation on the latter two
records a prepared GET `/v2.23/tasks.get_all`, the same final path and no redirects,
paired with an HTTP 200 body identifying `tasks.get_by_id` and containing `data.task`.
Only allowlisted fields and hashes are retained. Prepared-request objects are not an
independent network capture. The parent verified both original and fingerprint observer
archives and the failed-stage evidence; no model-quality claim attaches to these attempts.

On installed ClearML 2.1.10, requests 2.34.2 and urllib3 2.7.0, nine bounded read-only
sequential/fresh-session controls pass for both GET and POST. A single warmed-session
fork control then makes six read-only requests: two receive the opposite endpoint's
response. The parent task-list request receives `data.task`; the child's task-by-ID request
receives `data.tasks`. The owned child is reaped with exit zero. This reproduces a mechanism
consistent with the original failures; historical socket sharing remains unproven.

The supported SDK setting `sdk.development.report_use_subprocess=false` evaluates correctly
in an offline process with network connections forbidden and no Task or Session creation.
The next public attempt keeps GET, source, weights, corpus and quality gates unchanged,
while selecting thread-based reporting. An initial harness setup is rejected before CLI
or owner creation because its config file is outside the isolated runtime root. That
failed preflight is preserved separately. The corrected helper copies identical bytes
inside each fresh runtime root; an actual offline project-bootstrap check confirms that
the SDK reads the setting there. No production, SDK or shared-service patch is applied.

Configuration SHA-256 is
`b33267d04e98033dc2b9f46e25a7d00ebeb6557952f15336954518fe6274fa25`.
The sealed 21-member diagnostic archive SHA-256 is
`bbf8301f0621510855ec73648d183023dc6352dcb6fdca71bb3b2f2981977aa6`.
Fresh DINOv2 and Swin acceptance remains required; the transport reproduction alone does
not satisfy any model, publication or quality gate.


## Final acceptance and parent integration — 2026-10-12

All 14 native presets and the six cross-family comparisons pass the execution,
publication and fresh-download checks recorded above. All six Faster R-CNN presets
pass both FP32 and current FP16 quality and standalone execution. The fixed quality
limits remain 0.001 and 0.005 respectively; no test threshold, checkpoint or corpus
was changed to obtain acceptance.

| Faster R-CNN preset | Maximum current FP16 mAP50–95 loss | Cases | Current-policy evidence |
| --- | --- | --- | --- |
| ResNet-50-FPN | 0.0047069479472846565 | 22 | Exact lowered-graph byte equivalence with accepted engine |
| ResNet-101-FPN | 0.0006718693282109223 | 22 | Exact lowered-graph byte equivalence with accepted engine |
| ConvNeXt-Tiny | 0.0013790837041367798 | 22 | Exact lowered-graph byte equivalence with accepted engine |
| DINOv2-Small | 0.0000006041264665490077 | 22 | Fresh QKV-policy export/build/verification |
| DINOv3-Small | 0.000022587395822025458 | 22 | Fresh QKV-policy export/build/verification |
| Swin-Tiny | 0.0003432892541987004 | 22 | Fresh QKV-policy export/build/verification |

The aggregate independently reconciles 132 current FP16 cases with the frozen FP32
native-reference metrics, detection counts, image/batch membership, source ONNX,
checkpoint and corpus identities. All references have positive AP and detections.
Its 18 completed stage owners each have zero attached Output Models; this is an
owner-level check, not yet a project-wide model-delta claim. Four pre-ONNX SDK failed
owners and one harness-only configuration refusal remain separate preserved attempts.
All 23 referenced stage archives were verified. The parent additionally verified all
nine fresh transformer stage archives and the two newly preserved failed-stage archives.
Aggregate report SHA-256 is
`da481d7c9ceed2852d71e05a634dd96c3fabb1bde63fa628a70063b2335eb671`;
its 199-member evidence archive SHA-256 is
`a8297ba7ea7995e4afd71fd059f4e0ea4eec3f9c9394178b90e7ace5f1dec71a`.

Fresh DINOv2 and Swin engines have SHA-256
`b56b698bed8660eebb27a517a58bc6b527948b81b0d336e1941c4fc09b962637` and
`87f08ad3236e090d02b3c3a1cc2665b36317163474d1287a9612edd27cf836a4`.
Both pass 118 standalone calls, 24 shapes, 29 sequences and nine rejection cases
in the v9 minimal environment, plus independent finite-output, strict resized-bounds
and bitwise native-coordinate restoration checks. Their 131-member standalone archives,
independently verified by the parent, have SHA-256
`e63566399b2e3a2eeae650a7acbcbd2ffc246165782931189d0a4e1899b69a13` and
`f8963ac9488dbeaf2d87670c9d2d59cc98d94efcc6cad351fa13f01caefc9239`.
Together with DINOv3, the three exact-equivalent CNN engines and the six unchanged
FP32 engines, these complete T045–T048. Empty-output coverage is supplied by the
separate explicitly forced-zero control described above, not by relabeling the eight
positive stress images as negative images.

The supported process-local ClearML thread-reporting control was applied to all six
fresh DINOv2/Swin public commands before SDK import, using identical configuration bytes
inside each isolated runtime root. Passive observers correlate all six commands and
record correct task-list response types. The closed 38-member observer/helper/control
archive has SHA-256
`c6e2283c9887ed3854f048bf94f469d7553d107d1fa70a061d8d35fe5737edfc`.
The parent verified it independently. This successful control does not prove that the
historical failures shared a socket; the bounded fork reproduction and its limitations
remain the transport evidence.

The parent inspected the integrated task-owned diff and verified all 280 current
source/configuration/test hashes still match the successful full-suite snapshot.
T049 includes **2,163 passed, 30 skipped**, repository-wide Ruff, strict mypy on
278 files, all 40 import contracts, the v9 wheel/sdist/install checks, 22 guarded CLI
helps and eight cold minimal-runtime imports. Required commit/release hooks will run
at their own later stage. Protected dependency revisions, local source overrides,
installed workflow tooling and unrelated external source copies remain preserved.

These are relative export-quality and execution checks on the frozen 12-image,
single-class corpus, not broad model-accuracy or generalization claims. Latency/memory
scope and detection disagreement remain explicit in reports. CUDA 11.8 target execution
and binary portability remain unverified. Fresh T050 review, final documentation
validation, exact owned-resource cleanup and the authorized release are still pending.

Documentation validation after final acceptance passes for all 28 changed Markdown files,
263 local links and 43 code fences: 32 shell, one Python, four YAML and one HOCON
example. All 32 CLI examples, 14 model selections and three reference forms compose
without model/tracking SDK imports. The HOCON example matches the offline SDK-checked
control bytes. Required documentation scope is updated; later review/cleanup/release
ledger additions will receive the same validation.


## Final review, preservation and cleanup — 2026-10-12

The fresh independent T050 reviewer returns **ship**, with no blocking finding.
Its 206 targeted tests pass; all 125 review-file and 280 full-suite source hashes match.
It independently recomputes the 132 current FP16 quality cases. The complete scope,
command and limitations are recorded in [review.md](review.md#final-t050-independent-review--2026-10-12).
No implementation correction follows this review; T051 closes with no findings.

Final preservation reconciles all 154 sealed archives inside the 13 task-owned run
roots with external evidence: 121 unchanged previously audited copies and 33 later
stage archives. All 17 tasks added since the previous inventory map to preserved
success/failure evidence; 123 small attribution members were rehashed. Required native
states, exact thresholds, frozen Faster R-CNN states, diagnostic captures, scheduling,
cancellation, comparison, publication and standalone evidence remain outside cleanup
scope. There are no uncovered critical paths. The parent independently verifies the
16-member coverage archive, SHA-256
`9101baf4684e07b5fcff09f732478001737fb2f195e02a053145b06bec34572d`.

After all consumers and the final review ended, a fresh paginated inventory observed
13 owned projects, 249 terminal tasks and 27 models. The export project contains
88 tasks and zero models; the later export attempts added no models. Exact path,
owner, tag, helper-pin and dry-run checks pass. Cleanup removes only those projects
and their local tag directories, plus the single verified owned FiftyOne dataset in
the test database. Post-cleanup queries by every original project ID confirm zero
remaining projects, tasks or models. All 13 local tag directories are absent; the
owned dataset is absent, and the shared admission registry has no requests.
Shared services, external dependency sources, evidence archives, corpus and prepared
package/runtime environments remain intact. The read-only inventory helper's historical
`provisional` label is not used as a readiness assertion; the separate parent release,
exact deletion results and post-cleanup readback establish closure.

The commit-stage changelog generator adds only the already committed baseline
verification entry to Unreleased. That generated diff was inspected. The feature
commit will contain the 125 reviewed task files and that generated changelog; local
source overrides will be preserved verbatim and restored unstaged after hooks.
T057/T058 remain open until the actual commit/release checks and branch/tag pushes pass.


## Release closure — 2026-10-12

Feature commit `43f9e7dc85672bbb25f29e6abcb27344201ac443` contains the reviewed implementation
and documentation plus the inspected generated changelog. All applicable hooks pass:
large-file/conflict/TOML checks, whitespace, changelog, Ruff, strict mypy, import-linter
and the full pytest suite. YAML checking correctly skips because no YAML files were
staged. The feature-branch post-commit hook correctly skips automatic versioning.
The owned runner confirms closure of 862 tracked process identities.

`master` fast-forwards to that feature commit. The established release helper creates
`b7cd1f33666c4d0cce9b88c026cf9a6eb0ec22d6` with subject `chore(release): 0.24.0` only after
its required commit hooks, including the full pytest suite, pass. Its exact diff is
the generated changelog plus the root project version in `pyproject.toml` and `uv.lock`.
The parent verifies all other project metadata, dependency versions/sources and 278
source/test files remain unchanged. The owned release runner closes 845 process
identities. The prepared editable environment reports package version 0.24.0 afterward.

The 245-byte local source-override section is preserved verbatim and restored unstaged
in both checkouts; SHA-256 is
`4266f3c5c15df0a64a40ee158615a2f1665565d251b496805929c5b969cc5518`.
It is absent from both commits. No dependency resolver updates the protected lock.
No hook is bypassed; the release helper's existing recursion guard suppresses only
nested changelog/release execution, while quality hooks still run.

The annotated Git tag `v0.24.0` has object
`8a4f8a53e5d37a17728ee6c57949b2f7ee9be16b` and peels to the checked release commit.
An atomic push publishes only `master` and that explicit tag. Fresh remote readback
confirms both commit pointers and the annotated tag object. No GitHub Release object,
package upload, release asset or deployment is created. This final documentation
record is a follow-up to the released code; it does not change the version or tag.

The final pre-commit documentation check passes for 28 Markdown files, 264 local links,
43 fences, 32 CLI examples, all 14 presets and three model-reference forms. The full
current implementation suite has 2,163 passing and 30 skipped tests; the separate
206-test independent review also passes. Skips remain distinct from native acceptance.
The earlier cleanup readback and preserved evidence remain valid; no later check
creates a live ClearML training/export task or modifies shared services.


Final Spec Kit convergence checks 16 functional requirements, seven success criteria,
16 acceptance scenarios, 12 implementation-plan decisions and five constitution
principles, including the existing approved native-backend exception. No missing,
partial, contradictory or unrequested implementation work remains. All 58 existing
tasks are complete; convergence appends nothing and leaves the task ledger unchanged.
The documentation-only closure check validates three changed Markdown files and
12 local links; all 14 model selections still compose without SDK imports.

## Torch compatibility amendment — 2026-10-12

The [current ownership/Torch evidence](../024-runtime-isolation/verification-20261012-ownership.md)
records validation with Torch 2.14.1 and Torchvision 0.29.1. It identifies the rerun
representative native/export coverage separately from this release's earlier full matrix.
