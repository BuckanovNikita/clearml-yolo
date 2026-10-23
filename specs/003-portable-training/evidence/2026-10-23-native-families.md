# Native pretrained detector acceptance, 2026-10-23

This record covers short direct training through the existing `cy-train` entrypoint,
automatic pretrained asset preparation, ClearML publication, forced downloads and
native reload. It does not establish detector quality, every-preset training,
multi-GPU behavior, queue execution, ClearML Agent scheduling or live Artifactory
connectivity. The other feature evidence owns those checks and their limitations.

## Method

The project and machine end-to-end skills supplied the authorized shared ClearML
identity, capacity check, minted per-run tags and exact-prefix cleanup. Each family
ran sequentially on one CUDA device in its own `CY_HOME`. Existing workloads were
preserved. No dependency, approved source revision or external service was modified.

The six-image fixture has disjoint train/validation/test membership, two 96×64 RGB
images per split, one empty image per split and the exact foreground label `object`.
The task-owned copy pads the existing square fixture horizontally and shifts the
bounding-box x coordinates accordingly; original inputs remain unchanged.

The command shape was:

```bash
python -m clearml_yolo.entrypoints.train \
  model=BACKEND/PRESET ground_truth="$CY_HOME/ground_truth.csv" \
  model.train.device=0 model.train.epochs=1 model.train.batch=2 \
  model.train.imgsz=SIZE model.train.workers=0 model.train.amp=false \
  clearml.project_name="$CY_RUN_TAG clearml-yolo" \
  clearml.tags=[$CY_RUN_TAG] clearml.task_name=portable-BACKEND-pretrained
```

`model.train.pretrained=true` remained the default. No command supplied
`model.source_dir`, `model.train.weights` or `model.train.backbone_weights`.
DEIM's approved source archive and matching downloaded backbone were copied into
their exact managed-cache destinations in a fresh workspace, without a receipt or
extracted tree. Execution validated the archive and extracted source automatically.
The other families used their automatic asset resolution path.

The verification process used fresh SDK reads after each training command. It
force-downloaded every task artifact and the single Output Model, calculated SHA-256,
read the checkpoint's embedded descriptor, then loaded that downloaded checkpoint
through its native backend and predicted both current test images. It checked that
canonical `run` retained the original null selectors and pretrained flag, while the
separate `model_assets` Configuration Object contained source URLs, resolved paths
and hashes matching the actual asset bytes. Native scalar publication was required.
An archive audit also compared every original CSV field after numeric-coordinate
normalization, checked all six source/object lineage identifiers, and matched each
downloaded checkpoint hash to the native selected checkpoint retained in its run.

Task-owned scripts, commands, raw logs, fixture manifests, checkpoints and detailed
verification JSON are retained under `.tmp/portable-families/`. This ignored evidence
contains environment-specific paths; this record keeps the portable findings.

## Results

| Family/preset | Training image size | Training/publication | Downloaded model reload |
| --- | --- | --- | --- |
| DEIMv2/s | 128 | Completed one native epoch; one best Output Model and `gt_csv`; native scalar telemetry | Two images, 20 prediction rows |
| RF-DETR/nano | 384 | Completed one native epoch; one best Output Model and `gt_csv`; native scalar telemetry | Two images, one prediction row |
| Faster R-CNN/resnet50_fpn | 128 | Completed one native epoch; one best Output Model and `gt_csv`; native scalar telemetry | Two images, 20 prediction rows |

DEIM's observed training loss was finite (`54.9155`); validation AP was zero on this
tiny smoke fixture. This is execution and asset-loading evidence, not an accuracy
claim. Its pretrained backbone SHA-256 was
`2053b865f4e2673fba3f95f7e7e54ad5ee18143885e3ad27eaabb5b3b9919738`.
The archive SHA-256 was
`14a0048bcfc5e4ac7403792ef23210e4a7658d31f93895210cedb7e609a72d37`,
for approved revision `1d2ca42171570c713e78fc6a766ec5104b7f4724`.

RF-DETR's native small-dataset sampler produced five training batches, its epoch
limit stopped training at one, and its own EMA selection produced the best total
checkpoint. The SDK verified the registry asset's MD5 and the CY adapter verified
that the native backbone projection matched the pretrained checkpoint. Native
class-head replacement for the single foreground class remained active. The
reported validation AP50:95 was `0.95` on this synthetic smoke fixture, which is
not a representative quality estimate. The resolved pretrained asset SHA-256 was
`d8d6b9ee57d4d0ed2b1f305163624712a0532cb7bce0c747317984fc5457440d`.

Faster R-CNN's native training loss was finite (`1.5985573530197144`); its validation
AP was zero. It used the selected Torchvision ResNet-50 pretrained backbone,
SHA-256 `11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca`.

All three process exit codes were zero. The remote task state was `completed`,
each task had exactly one Output Model and only the required `gt_csv` artifact,
and checkpoint descriptors preserved backend, preset, class vocabulary,
preprocessing and dependency/source identity. Every downloaded ground-truth file
preserved six original rows, three empty images and unique source/object IDs.

| Family | Task ID | Output Model ID | Downloaded checkpoint SHA-256 | Downloaded `gt_csv` SHA-256 |
| --- | --- | --- | --- | --- |
| DEIMv2 | `71d7a08c12ce4f77ad0dc666c764263a` | `6652eef1f769494c942e32a926ca73a4` | `85759003abfda3827672198abcb9ef6da7ac77306623ee339b68aaf2e41ae0ee` | `fdd5a0afb714e0d97b1cf30a0a55ca34abaad1528500b0d1c02221cba5e8c6ba` |
| RF-DETR | `5ad5fd794da24e349ec61b0bc63e77bc` | `10e5e44456fb49e6a733e873b57cf697` | `830d0eb0454df5a7b72afbf4a471cb16e5768c66f4adb9d0982c026153f20387` | `7b0267572af3386ce49a05cc7854b2f66e19bc8e3b1087d2097e476e49a18bdd` |
| Faster R-CNN | `e40e2b3ebef34280b7d62112c42410f8` | `c503d4a104984d909cb63839a2de4c4a` | `7ab399f4763c656a4ced19c240efaf5f7c412b8c0cb2443c16dbaed2d0e6840f` | `cbdc64fed21c97b7ca3ee28e955bc38ed872dacb6d9a6e4e171088c5504b6eef` |

## Cleanup and limits

Every exact-prefix cleanup deleted its owned project and task; each subsequent
listing reported zero projects and tasks. No task-owned training process remains.
The local archives are:

- `.tmp/portable-families/archive-clearml-yolo-codex-20261023-portable-deimv2-yofs`
- `.tmp/portable-families/archive-clearml-yolo-codex-20261023-portable-rfdetr-jsic`
- `.tmp/portable-families/archive-clearml-yolo-codex-20261023-portable-faster-twdd`

The final local artifact/cleanup audit is
`.tmp/portable-families/archive-audit.json`.

These short runs intentionally do not claim all-preset native
training, meaningful nonzero mAP, export parity, performance or physical multi-GPU
acceptance. Automatic download behavior is distinguished from local-cache reuse;
DEIM used manually placed valid cache content in this run. RF-DETR and Faster R-CNN
used automatically resolved pretrained assets; this harness did not separately
instrument cache-versus-network selection, so it does not claim a particular
transport path. Live Artifactory connectivity was unavailable and remains
unverified. No failure was observed in the three scoped family runs.
