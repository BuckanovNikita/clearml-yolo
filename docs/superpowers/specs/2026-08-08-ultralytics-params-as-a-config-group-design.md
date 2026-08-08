# Every ultralytics parameter is visible in the config, as its own file

## Problem

`train_kwargs: {}` and `predict_kwargs: {}` are the only way to reach ultralytics from a
config file, and they show nothing. A user who wants to change the learning rate, the
optimizer, the augmentation block or early stopping has to already know that `lr0`,
`optimizer`, `mosaic` and `patience` exist, how they are spelled, and what they default
to — none of which is in the dumped config folder. `cy-train.yaml` is 46 lines and
declares eleven ultralytics parameters out of roughly a hundred and thirty; the other
hundred and nineteen are reachable but invisible.

The two dicts also carry a precedence rule that is stated only as a comment at the point
of use — `**(train_kwargs or {})` is spread last "so a run reproducing older numbers can
turn either of the two above back off" — and `inference._precision` carries a second,
different one for `half` versus `quantize`. Two overriding mechanisms, both invisible in
the config.

## What changes

The ultralytics parameters become a Hydra config group of their own: two flat YAML files
that list every parameter ultralytics accepts for that stage, with upstream's own inline
documentation kept.

```
src/clearml_yolo/conf/
    __init__.py
    ultralytics/
        train.yaml
        predict.yaml
```

`cy-train.yaml` and `cy-predict.yaml` keep only clearml-yolo's own keys plus one
`ultralytics:` node. There is no `train_kwargs`, no `predict_kwargs`, and no nested
section inside the `ultralytics:` node — it is one flat list of keys.

```yaml
# conf/cy-train.yaml
defaults:
  - _self_
  - /ultralytics@ultralytics: train

auto_gpu: {...}
clearml: {...}
```

```yaml
# conf/ultralytics/train.yaml
# ---- read by detection training ----
model: yolo11n.pt
data: coco8.yaml
epochs: 100              # (int) number of epochs to train for
imgsz: 640               # (int | list) train/val use int (square)
batch: null              # null -> auto_gpu sizes it to this model on these cards
device: null             # null -> auto_gpu picks the cards
name: null               # null -> the ClearML task name
amp: null                # null -> on iff this run is on a GPU
compile: null            # null -> on iff this run is on a GPU
optimizer: auto          # (str) SGD, MuSGD, Adam, Adamax, AdamW, NAdam, RAdam, RMSProp, auto
lr0: 0.01                # (float) initial learning rate
mosaic: 1.0              # (float) mosaic augmentation probability
...

# ---- ignored by detection training ----
# Ultralytics accepts these, but detection training does not read them. Uncommenting one
# changes nothing; they are listed so the file is the whole of `ultralytics --help`.
# format: torchscript
# overlap_mask: true
# dropout: 0.0
# pose: 12.0
# tracker: tracktrack.yaml
```

### The group is referenced absolutely

Each stage's field set carries

```python
"hydra_defaults": ["_self_", {"/ultralytics@ultralytics": "train"}]
```

The leading `/` makes the group reference absolute, so **one** `ultralytics/` directory
serves both the standalone apps and the stage blocks nested inside the pipeline. Written
relatively, Hydra would look for `train/ultralytics/` and `predict/ultralytics/` and the
same file would have to exist three times.

```
cy-train ultralytics=highlr                 # swap the whole parameter set
cy-train ultralytics.lr0=0.02               # poke one key
cy ultralytics@train.ultralytics=highlr     # swap train's, inside the pipeline
cy train.ultralytics.epochs=5
```

The package directory is reached with `hydra.searchpath: [pkg://clearml_yolo.conf]`,
declared in each **primary** config. It does not work from the `hydra/config` store
entry: Hydra resolves the search path before that entry is composed, and the group is
simply not found.

### `null` means the run works it out

One rule, in one named place — `clearml_yolo/ultralytics_params.py::fill_unset(params,
**computed)`. A computed value fills a key **only** where the file left it `null`.
Anything written in the file is passed to ultralytics verbatim and code never overrides
it.

| key | what fills a `null` |
|---|---|
| `batch` | `auto_gpu`, sized to this model on these cards |
| `device` | `auto_gpu`, or the card training just used |
| `amp`, `compile` | on iff this run is on a GPU |
| `quantize` (predict) | 16 on a CUDA card, 32 otherwise |
| `name` | `clearml.task_name` |
| `imgsz` (predict) | the resolution recorded in the checkpoint |

This replaces both existing precedence mechanisms. `train_kwargs` spread last, and
`_precision`'s check for whether the caller already named `half` or `quantize`, both
become the same rule, stated in the config file next to the key it governs.

`project` is not on this list: it is not filled, it is transformed. Whatever the file
says is resolved to an absolute path, because a relative project is otherwise resolved
against ultralytics' configured `runs_dir` rather than the working directory.

### The file is clearml-yolo's, not a drop-in ultralytics one

`yolo train cfg=<file>` and `YOLO(...).train(cfg=<file>)` do accept a file like this —
`engine/model.py:782` loads the YAML and uses it as overrides. But ultralytics'
`check_cfg` (`cfg/__init__.py:424`) raises `TypeError` on `None` for any key whose own
default is not `None` and that is type-checked. Measured against ultralytics 8.4.115:

| key | ultralytics default | `null` accepted? |
|---|---|---|
| `device`, `name`, `quantize` | `None` | yes |
| `amp` | `True` | yes — not in `typed_keys` |
| `imgsz` | `640` | yes — not in `typed_keys` |
| `batch` | `16` | **no** — `'batch=None' is invalid` |
| `compile` | `False` | **no** — `'compile=None' is invalid` |

Those two cannot hold a real value instead. `batch: 16` written literally is honoured
verbatim even on the auto path (`gpu.py:781`), so a number there switches auto-sizing off
permanently, and ultralytics has no native "auto" for either key.

This is accepted rather than worked around, because the resolved configuration already
exists: ultralytics writes every filled-in argument to `runs/detect/<name>/args.yaml`
(`trainer.py:153`). That file is directly `cfg=`-able and reproduces the run exactly. The
authored file is for editing; `args.yaml` is for replaying.

### Signatures

```python
train(ultralytics: dict[str, Any], auto_gpu: AutoGpuConfig, clearml: ClearMLConfig) -> TrainResult

predict(weights, ground_truth, output, clearml, auto_gpu, model, splits, image_name,
        ultralytics: dict[str, Any]) -> Path
```

`model`, `data`, `epochs`, `imgsz`, `batch`, `device`, `project`, `name`, `conf` and
`iou` all move into the `ultralytics` dict. `model` survives on `predict` because it is
not an ultralytics predict parameter at all — it names the architecture a batch table is
keyed by, and nothing is loaded from it.

`predict_on_images` stops taking `conf`, `iou`, `imgsz`, `batch`, `device` and
`**model_kwargs` as separate parameters and takes the settled dict instead. It keeps
setting `source`, `stream` and `verbose` itself; those three are in the ignored section.

### Two pipeline fills are retired

`PIPELINE_FILLED_KEYS` drops a key from a stage's config so the pipeline cannot declare
what the run fills. That cannot be done to a key inside the shared group file — the file
is one file — and overwriting it instead would create exactly the defect
`test_the_comparison_declares_only_the_inference_it_owns` exists to prevent: a key a run
can set that the pipeline then silently overwrites. So both are retired into the `null`
rule, which produces the same value from a source that cannot go stale:

- **`train.name`** — `null` resolves to `clearml.task_name` inside `train()`, standalone
  and in-pipeline alike, instead of the pipeline filling it.
- **`predict.imgsz`** — `null` is already read from the checkpoint by `resolution_of`,
  and the checkpoint records exactly the number the pipeline was copying across. Same
  guarantee, from the one source that cannot disagree with the weights it describes.

`PIPELINE_FILLED_KEYS` becomes:

```python
"train":   frozenset({"clearml", "auto_gpu"}),
"predict": frozenset({"clearml", "auto_gpu", "ground_truth", "splits", "weights", "model"}),
```

`_comparison_inference` reads `conf`, `iou`, `imgsz` and `batch` out of
`predict_cfg["ultralytics"]` instead of out of `predict_cfg`; `image_name` and `model`
stay where they are.

## Which keys are live and which are commented

The partition is per stage and decided by reading ultralytics 8.4.115. A key is
commented when detection at that stage does not read it, or when clearml-yolo sets it
itself.

**Commented in `train.yaml`** — set by ultralytics itself (`task`, `mode`, `cfg`);
predict-only (`source`, `vid_stride`, `stream_buffer`, `visualize`, `augment`,
`agnostic_nms`, `classes`, `embed`, `max_det`, `quantize`, `end2end`, `dnn`); the
visualization block (`show`, `save_frames`, `save_txt`, `save_conf`, `save_crop`,
`show_labels`, `show_conf`, `show_boxes`, `line_width`); the export block (`format`,
`keras`, `optimize`, `dynamic`, `simplify`, `opset`, `workspace`, `nms`); other tasks
(`overlap_mask`, `mask_ratio`, `retina_masks`, `dropout`, `pose`, `kobj`, `rle`, `angle`,
`dlog`, `dgrad`, `dlam`, `copy_paste`, `copy_paste_mode`, `auto_augment`, `erasing`); and
`tracker`.

Training's own validation pass is real, so `val`, `split`, `conf`, `iou`, `plots` and
`save_json` stay live.

**Live in `predict.yaml`** — `conf`, `iou`, `imgsz`, `batch`, `device`, `max_det`,
`quantize`, `compile`, `rect`, `augment`, `agnostic_nms`, `classes`, `channels_last`,
`dnn`, `end2end`. Everything else is commented, including the whole save/show block:
`predict_on_images` returns a DataFrame and saves nothing, so those keys would write
files no stage reads.

`half` is commented in both, superseded by `quantize`.

## Guarantees that must survive unchanged

- `clearml.task_name=exp-42` still names the whole run, including the training run
  directory.
- `auto_gpu` still sizes the batch and picks the cards when the file leaves them `null`,
  and still logs what it chose.
- Inference still runs at the resolution the weights were trained at, and still warns
  when asked for another one.
- Half precision and `torch.compile` are still on by default on a CUDA card and still
  turn off from config — now by writing `false` in the file rather than by an entry in
  `predict_kwargs`.
- The comparison still re-infers exactly as the predict stage did.
- Stage configs still resolve to plain, picklable Python before reaching ultralytics,
  which pickles `trainer.args` into every checkpoint.

## Behaviour changes

1. **Standalone train's run directory moves** from `runs/detect/train` to
   `runs/detect/<clearml.task_name>`, default `runs/detect/yolo-run`, because `name: null`
   now resolves the same way everywhere. `RUN_NAME` disappears and `DEFAULT_CHECKPOINT`,
   which is what a standalone `cy-predict` reads with no weights named, becomes
   `runs/detect/yolo-run/weights/best.pt` — built from `ClearMLConfig.task_name` rather
   than from a second constant that could drift from it.
2. **`half` is no longer honoured.** It was already deprecated upstream and only reachable
   through `predict_kwargs`; `quantize: 32` replaces it.
3. **`cy-init-config` writes a subdirectory.** The dumped folder gains
   `conf/ultralytics/train.yaml` and `conf/ultralytics/predict.yaml`, copied verbatim from
   the package so the comments survive, and the stage files carry the `defaults:` entry
   instead of an inlined block. The dumped header gains a line saying where the ultralytics
   parameters went and how to swap the whole set. An existing `conf/` folder must be
   re-dumped, and the README note that already says so is extended to mention the
   subdirectory.

The two YAML files must reach an installed wheel. `uv_build` ships everything under the
module directory, so no `pyproject.toml` change is expected — but it is checked by
building the wheel and listing it, not assumed.

## Tests

- **`test_every_ultralytics_param_is_live_or_commented`** — for each file, the live keys
  and the commented-out keys together equal the installed `default.yaml`'s keys, and the
  two sets are disjoint. An ultralytics upgrade that adds a parameter fails the suite
  instead of hiding it. This test reads `ultralytics.cfg`; the package itself must not,
  and the import-linter contract "Model weights are only ever loaded in one place" already
  forbids it in `configs` and `config_tree`.
- **`test_every_live_param_is_one_ultralytics_accepts`** — each file, with its `null`s
  filled the way `fill_unset` fills them, passes `get_cfg` without raising.
- **`test_a_value_written_in_the_file_is_never_overridden`** — `fill_unset` leaves
  `amp: false`, `batch: 8`, `compile: false` and `quantize: 32` alone.
- **`test_ultralytics_params_are_picklable`** — replaces
  `test_train_kwargs_are_picklable`. Ultralytics pickles `trainer.args` when saving a
  checkpoint, and a `DictConfig` backed by a generated dataclass cannot be pickled.
- `test_every_stage_config_key_is_a_parameter_of_its_task` and
  `test_a_pipeline_stage_declares_nothing_the_run_fills_in` continue to hold against the
  shortened `PIPELINE_FILLED_KEYS`.
- `test_inference_runs_at_the_resolution_the_model_was_trained_at` moves from asserting
  the pipeline copies `imgsz` across to asserting the predict block leaves it `null` and
  `resolution_of` reads it from the checkpoint.
- `test_config_tree` gains: the dump contains `ultralytics/train.yaml`, the copy still
  carries its comments, and the folder still composes back to the built-in defaults.

## Out of scope

**`compare.inference` keeps its closed pydantic field set.** It is the prediction-cache
key: a cache named after fewer settings than it was filled under scores one checkpoint's
detections under another's name, which is the substitution the whole comparison exists to
remove. Widening it to every ultralytics parameter means either an unkeyed cache or a
hash over a hundred and thirty keys. It goes on inheriting `conf`, `iou`, `imgsz` and
`batch` from the predict stage.

**The ground-truth, metrics, report and compare stages are untouched.** None of them
calls ultralytics.

## Mechanics verified before writing this

- `- /ultralytics@ultralytics: train` composes standalone and inside a nested stage
  block from one directory; `ultralytics=<name>`, `ultralytics.<key>=<v>`,
  `ultralytics@train.ultralytics=<name>` and `train.ultralytics.<key>=<v>` all resolve.
- `hydra.searchpath: [pkg://...]` works from a primary config and not from the
  `hydra/config` store entry; the target directory needs an `__init__.py` or Hydra warns
  the provider is unavailable.
- A stage config that does not declare `ultralytics=None` fails composition with
  `ConfigKeyError: Key 'ultralytics' not in 'Config'`.
- `get_cfg` accepts the train file once `batch` and `compile` are filled, and rejects it
  while either is `null`.
- `Model.train` loads `cfg=` as overrides and lets explicit keyword arguments win over it.
