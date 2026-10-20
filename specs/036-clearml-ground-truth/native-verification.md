# Native ground-truth verification — 2026-10-20

## Inputs and scope

Real ClearML dataset retrieval, paired local/dataset metrics, and one-epoch CPU
and single-GPU YOLO pipelines were executed against the feature working tree.
The populated development environment was used without synchronization or
dependency changes. Package installation and dependency-floor acceptance are
separate checks; these results do not establish compatibility at minimum versions.

The CSV describes 16 distinct synthetic images: eight training, four validation,
and four test images, including one background in every split. All 16 image
content hashes are distinct. Existing images and architecture configuration were
read without modification. Only the annotation CSV was uploaded to each positive
ClearML dataset; its absolute image references remained external.

| Input or output | SHA-256 |
| --- | --- |
| Original and downloaded root `dataset.csv` | `b0acf3ba920a02080c72df54086a74f848251995bd40b668eb890259e20139e6` |
| Hand-authored identical prediction input | `b2db745bbea3fa7cc7f33d295d21bbe1c0bf1c3fc271017eac1be9caa68e0887` |
| Native CPU best checkpoint | `b2a9d5c0c92e76e6845e7bc508344958ce5c5f47207a267abfc5b5738cb11533` |
| Native GPU best checkpoint | `2c445b8adaa2512a43de40b50d914b34ca766e529448b10365838f8c9303c77d` |

Full commands, source/package manifests, original logs, source/media hashes,
server configuration readback, downloads and verification scripts are retained
in the ignored acceptance archive identified by `.tmp/cy036-native-evidence`.
Synthetic fixtures establish execution and preservation, not trained-model
accuracy or generalization.

## Executed scenarios

| Scenario | Observed result |
| --- | --- |
| Dataset ID selector | Resolved finalized version `1.0.0`; CSV bytes and digest exactly matched the source |
| Project/name plus explicit version | Resolved the same `1.0.0` dataset |
| Project/name without version | Selected semantic version `2.0.0`, although `1.0.0` was created afterward |
| Unfinalized dataset | Rejected with `Ground-truth ClearML dataset must be finalized` |
| Finalized dataset without root `dataset.csv` | Rejected with `Ground-truth ClearML dataset requires root dataset.csv` |
| Mixed absolute/relative media CSV | Source bytes/values unchanged; the execution view kept the absolute reference and resolved the relative reference beside downloaded `dataset.csv`; no images were downloaded |
| Local versus dataset `cy-metrics` | Identical validation/test evaluation payloads after sorting only unordered match records; exact threshold CSV and equal ground-truth/prediction match tables |
| Local warning | One occurrence in the local metrics invocation; zero in dataset metrics and both nested pipelines |
| CPU pipeline | Completed training, validation, prediction, metrics and candidate-only comparison using project/name/version |
| Single-GPU pipeline | Completed the same stages using dataset ID |

The paired metrics commands used the same prediction CSV, explicit model label,
`splits=[val,test]`, default evaluation settings, and disabled FiftyOne publication.
The hand-authored exact boxes produced F1 equal to 1 on both splits, with threshold
`0.9` calibrated on validation and preserved for test. These scores concern the
synthetic evaluator fixture, not either trained checkpoint.

Native pipelines used a local YOLOv8n architecture, no pretrained download, one
epoch, image size 64, batch 4, zero loader workers, AMP disabled, and explicit
eager execution. Both native configuration groups selected CPU or the available
single GPU explicitly. Prediction used image size 64, batch 4, confidence 0,
IoU 0.7 and at most ten boxes per image. Each invocation supplied an explicit
tag-scoped ClearML project, tag list, and output directory. FiftyOne was disabled.
The two training runs are execution checks; their independently trained checkpoints
are not a claim of numerical CPU/GPU training parity.

Both pipelines recorded the absence of a completed production-tagged baseline
and retained candidate evaluation with the comparison skip reason. No paired
model-comparison result was fabricated.

## Server readback and downloaded evidence

Four successful application invocations were read back as completed:

- Local metrics: `1f912df4784c41ddbf86ab9d5ebd72dd`.
- Dataset metrics: `25acfb6eb02942f388f5c86cd91616ad`.
- CPU pipeline: `ed8f9180143148ed9939aef0f7f380fc`.
- GPU pipeline: `420e79a7aa39491b8955774d0b0935c6`.

All 36 published artifacts and both native best Output Models were force-downloaded.
Each metrics task had seven artifacts and no model; each native pipeline had
eleven artifacts and exactly one model. Downloaded models loaded through native
YOLO, retained the `object` vocabulary and training settings, and matched their
local best-checkpoint hashes. Fresh model metadata matched those hashes, the exact
downloaded validation threshold mapping, and calibration split `val`.

Canonical run configurations preserved the requested dataset selector. Separate
`ground_truth_source` records retained the actual dataset ID, project, name,
version and unchanged CSV digest. Nested training and evaluation preserved that
source record after preparing the native training dataset.

Downloaded metrics ground truth retained all 16 original source rows, order,
media values and unique source IDs. Native pipeline publication retained all
16 image identities and published the existing prepared-ground-truth view;
its sorted row order was not represented as the original CSV order.
The original annotation CSV remained byte-identical after execution.

## Attempts, cleanup and limits

The first dataset-metrics attempt failed before ground-truth resolution when the
existing task-naming lookup received an nginx HTTP 400 for `tasks.get_all`.
The unchanged retry completed and supplied the parity evidence above. The failed
task and original diagnostic log remain represented in the local archive.
No application or infrastructure repair was made for that transient failure.

Hardware capacity was inspected before GPU execution, and no other compute
workload or shared service was stopped or changed. Owned command processes exited,
and no task-owned GPU compute process remained before cleanup.

After the complete evidence archive was preserved, the environment helper deleted
the owned tagged project and its contents. Its final readback reported zero
projects and zero tasks under the exact run tag, then removed only the owned run
directory. The local acceptance archive retains the inputs, outputs, downloads
and original failure/cleanup logs; the server objects are no longer live.

This run did not exercise physical multi-GPU/compiled execution, interactive
browser charts, FiftyOne publication, remote queue replay, or every detector
family/export target. Those outcomes are not implied by these native source
checks. Unit, architecture, packaging, dependency-floor and release checks are
reported separately by the parent implementation workflow.

## Integrated-tree follow-up — 2026-10-20

After incorporating upstream `41a4036` (`v0.35.0`), the local/dataset metrics pair
and CPU pipeline were repeated with a fresh isolated tag and the task-owned
normal-lock environment, using `uv run --frozen --no-sync`. The earlier sections
remain evidence of the original pre-integration runs.

| Integrated invocation | Completed task |
| --- | --- |
| Local CSV metrics | `6227e41d0588483ab9412749358f48c9` |
| Dataset-ID metrics | `ff67852fd1184c69bd4679efe45b7b77` |
| CPU pipeline with unversioned project/name | `8fc653a8b0874a78a57b5338b57810ec` |

All three invocations passed on their first attempts. Metrics parity remained
exact under the same match-record sorting described above, with an unchanged
source digest and validation/test thresholds. The unversioned pipeline selector
resolved dataset version `2.0.0`; fresh server readback retained the original
project/name selector and recorded the actual ID, version and digest separately.
The pipeline completed native training, prediction, evaluation and the recorded
missing-baseline comparison path.

All 25 application artifacts and the single best Output Model were
force-downloaded and verified. The downloaded model loaded through native YOLO;
its hash matched the local best checkpoint and both checkpoint/calibration
metadata fields:
`d8444f5739c3a16f646f21625b3bb93ed0d76fd2ba6591749f92c4154c752947`.
The exact downloaded validation thresholds matched fresh model metadata.
Metrics publication preserved all original source rows; native publication
retained all 16 image identities.

Invocation logs confirmed the integrated early-publication behavior: each metrics
run uploaded `gt_csv` before scoring the first split, and the CPU pipeline
uploaded it before native training began. Each invocation logged exactly one
`gt_csv` and one `predicts_csv` upload. Local CSV execution warned once; neither
dataset invocation emitted that warning. This establishes publication order from
the execution logs and complete final server readback, not browser visibility
latency.

After those positive runs, the adapter received the additional CSV-only inventory
guard. A real finalized dataset containing root `dataset.csv` plus an external
`images/external.png` link was rejected with the expected inventory error.
The task-owned external target was made unavailable before resolution. An
observer that would delegate to the original SDK method recorded zero
`get_local_copy` calls, while lookup and inventory remained real server operations.
A positive CSV-only dataset was resolved again with the guard and retained the
original bytes and digest.

The inventory guard constrains the logical dataset and materialized input to the
CSV. ClearML can transport historical archive chunks containing files removed
from a dataset's current inventory; this test does not establish a guarantee
about every byte transported by SDK internals. Image handling remains outside the
ground-truth adapter.

The separate ignored archive `.tmp/cy036-native-integrated-evidence` retains
commands, source snapshots verified against the pre-run hashes, the later guard's
source/hash, logs, server readback, all downloads and the external-link check.
After preserving that archive, exact-tag cleanup deleted the owned project and
its contents, reported zero remaining projects/tasks, and removed the owned run
directory. All verification processes had exited.
The single-GPU pipeline was not repeated after integration; its earlier result
is explicitly pre-integration evidence. Other limitations above remain unchanged.
