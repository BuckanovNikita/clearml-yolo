# Grid search over `cls` and `cls_pw` with `cy-queue`

Use Hydra's `-m` option inside `cy-queue submit`. For example:

```bash
cy-queue submit --gpus 1 -- -m \
  --config-dir cy-config --config-name cy \
  ultralytics.cls=0.25,0.5,1.0 \
  ultralytics.cls_pw=0.0,0.5,1.0
```

This creates **nine jobs**, one for every parameter combination. A separate
`cy-queue worker` runs them when GPUs are available.

The steps below assume Linux/WSL, a working NVIDIA GPU, and access to a ClearML
server. Replace `/path/to/clearml-yolo` with your checkout's actual path.

## 1. Prepare the Python environment

In an existing checkout:

```bash
cd /path/to/clearml-yolo
```

On a new machine, first clone it:

```bash
git clone git@github.com:BuckanovNikita/clearml-yolo.git
cd clearml-yolo
```

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv python install 3.12
```

A **fresh checkout** also needs the two external dependencies. Run these only if
their directories are absent:

```bash
mkdir -p external

git clone git@github.com:Wasilkas/digital-metrics.git external/digital-metrics
git -C external/digital-metrics checkout 6e801be1564dce458294eb23592cc1aa0939c4d9

git clone git@github.com:Wasilkas/report-generator.git external/report-generator
git -C external/report-generator checkout d10aa395d08f738e92e04e076cee93b3a993bf8f
```

Then install and activate:

```bash
uv sync --frozen --extra queue-ui --inexact
source .venv/bin/activate

cy-queue --help
```

`queue-ui` enables the optional terminal dashboard. The dependency setup and
approved revisions are maintained in [development.md](development.md#external-dependencies).

## 2. Set the workspace and check GPU access

Run from the repository root:

```bash
export CY_HOME="$PWD"
export CY_QUEUE_ROOT="$CY_HOME/.cy-queue"

nvidia-smi
python -c 'import torch; print("CUDA available:", torch.cuda.is_available()); print("GPU count:", torch.cuda.device_count())'
```

CUDA should be available, with at least one GPU. Use the **same workspace, queue
root, environment, and Unix user** for submission and the worker.

## 3. Configure ClearML

If this environment already connects to your ClearML server, keep that
configuration. Otherwise:

```bash
clearml-init
```

Open your ClearML web interface, create API credentials under **Settings →
Workspace**, and follow the wizard. ClearML documents this in its
[SDK setup guide](https://clear.ml/docs/latest/docs/clearml_sdk/clearml_sdk_setup/).

Training needs working tracking and artifact storage.

## 4. Prepare your dataset

`cy` trains from a ground-truth CSV. It needs nonempty `train`, `val`, and `test`
splits. The columns are:

```text
image_name,image_path,instance_label,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br,split
```

Boxes use **pixel corner coordinates**. Image paths inside the CSV resolve relative
to the CSV's directory.

If you already have a YOLO dataset with `data.yaml`, convert it once:

```bash
cy-ground-truth \
  data_yaml=/absolute/path/to/data.yaml \
  output=./ground_truth.csv \
  clearml.project_name=cls-grid \
  clearml.task_name=prepare-dataset \
  'clearml.tags=[dataset-preparation]'
```

Existing test images are preserved. If the dataset has no test images, the
converter moves half of the validation images into a test split by default.
Review that split before starting the experiments.

## 5. Generate and edit the configuration

```bash
cy-init-config cy-config
```

Edit the following fields in the generated files, **preserving `defaults` and
other generated settings**.

In `cy-config/cy.yaml`:

```yaml
ground_truth: ./ground_truth.csv

clearml:
  project_name: cls-grid
  task_name: "yolo11n-cls-${ultralytics.cls}-pw-${ultralytics.cls_pw}"
  tags: [cls-grid-v1]

skip_compare: true
skip_report: true

fiftyone:
  enabled: false
```

This keeps training, prediction, evaluation, and ClearML publication enabled. It
skips baseline comparison, paired reports, and optional FiftyOne publication for
this introductory search.

Leave `run_dir: null` so each experiment gets its own output directory.

In `cy-config/ultralytics/default.yaml`:

```yaml
model: yolo11n.pt
epochs: 50
imgsz: 640
batch: 8
seed: 0
deterministic: true
compile: false
device: null

cls: 0.5
cls_pw: 0.0
```

These are example training settings; adjust the model, image size, and batch size
for your dataset and GPU.

In `cy-config/ultralytics_predict/default.yaml`:

```yaml
device: null
batch: 8
conf: 0.001
iou: 0.7
compile: false
```

**Use `device: null` for queued GPU stages.** The queue supplies their devices.

The parameters you are searching mean:

| Parameter | Meaning |
| --- | --- |
| `cls` | Classification loss multiplier |
| `cls_pw` | Class-frequency weighting power: `0` disables weighting, `0.5` gives partial weighting, `1` gives full inverse-frequency weighting |

Keep `cls_pw` between `0` and `1`. See
[Ultralytics training documentation](https://docs.ultralytics.com/modes/train).

## 6. Start a worker in a second terminal

```bash
cd /path/to/clearml-yolo
source .venv/bin/activate
export CY_HOME="$PWD"
export CY_QUEUE_ROOT="$CY_HOME/.cy-queue"

cy-queue worker
```

Leave this terminal running; for a remote session, use a persistent terminal such
as `tmux`.

One worker can run multiple jobs concurrently on separate available GPUs. With one
GPU, your jobs run sequentially.

## 7. Submit one smoke-test job first

Back in your first terminal:

```bash
cy-queue submit --gpus 1 -- \
  --config-dir cy-config --config-name cy \
  ultralytics.epochs=1 \
  ultralytics.cls=0.5 \
  ultralytics.cls_pw=0.0 \
  clearml.task_name=grid-smoke \
  'clearml.tags=[grid-smoke]'
```

Submission prints a job ID. Monitor it:

```bash
cy-queue list
```

Or open the dashboard:

```bash
cy-queue tui
```

Wait for successful completion and check that the `grid-smoke` task appears in
ClearML with its model and results. This validates dataset access, training,
evaluation, and uploads before spending time on the grid.

## 8. Submit the nine-job grid

```bash
cy-queue submit --gpus 1 -- -m \
  --config-dir cy-config --config-name cy \
  ultralytics.cls=0.25,0.5,1.0 \
  ultralytics.cls_pw=0.0,0.5,1.0
```

The search is the Cartesian product:

| `cls` | `cls_pw` values |
| --- | --- |
| `0.25` | `0.0`, `0.5`, `1.0` |
| `0.5` | `0.0`, `0.5`, `1.0` |
| `1.0` | `0.0`, `0.5`, `1.0` |

Hydra's comma syntax defines the choices; `-m` enables the sweep. See
[Hydra multirun](https://hydra.cc/docs/tutorials/basic/running_your_app/multi-run/).

`--gpus 1` means **one GPU per experiment**. To restrict every experiment to GPU 0,
replace it with `--devices 0`.

Submission freezes the configuration. Subsequent YAML edits do not change
submitted jobs. Avoid changing the installed code or environment while jobs are
pending: workers verify its identity and can require resubmission.

## 9. Monitor and compare the results

```bash
cy-queue list --json
cy-queue tui
```

In ClearML, open project **`cls-grid`** and filter by **`cls-grid-v1`**. Names
identify each combination, for example:

```text
yolo11n-cls-0.25-pw-0.0
yolo11n-cls-0.5-pw-0.5
yolo11n-cls-1.0-pw-1.0
```

Compare a consistent validation metric across experiments and inspect per-class
performance, especially rare classes. Use the held-out test split for the final
assessment. Keep the dataset, model, training budget, and other settings
consistent.

Local outputs are under:

```text
runs/cls-grid/<task-name>-<task-id>/
```

To cancel a particular job:

```bash
cy-queue cancel JOB_ID
```

If jobs remain pending, inspect the waiting reason. By default, a GPU must have
**less than 2 GiB of used memory** before the worker admits a job. Passing this
threshold does not guarantee that your chosen batch fits in memory.

The maintained queue reference is [queue.md](queue.md).

## Verification note — 2026-10-14

The example configurations were composed with the repository's real configuration
export and queue-composition functions in a temporary directory. They produced
one smoke-test job and nine grid jobs, with nine distinct parameter pairs and task
names. No jobs were submitted and no training was run during that check.

<!-- Architecture assessment: impact=none. This task only saves the checked
walkthrough as documentation. It changes no runtime modules, dependency
contracts, composition targets, or executable architecture checks. Existing
unrelated working-tree changes are outside this task's scope. -->
