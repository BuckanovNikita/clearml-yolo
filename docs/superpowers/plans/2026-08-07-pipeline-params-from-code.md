# Pipeline Params From Code Implementation Plan

> **STATUS: LANDED — historical record, do not execute.** The work shipped; `PIPELINE_FILLED_KEYS` and
> `stage_configs()` are in `src/clearml_yolo/tasks/pipeline.py`. The unchecked boxes below are how the
> plan was written, not work outstanding. Parts of it were superseded before landing — notably the
> `train.name` and `predict.imgsz` fills, retired in
> `docs/superpowers/specs/2026-08-08-ultralytics-params-as-a-config-group-design.md`. Read that spec,
> and the code, for current behaviour.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every value more than one pipeline stage needs is handed to that stage by `run_pipeline` in Python, so no `${...}` interpolation survives in the `cy.yaml` that `cy-init-config` writes.

**Architecture:** `tasks/pipeline.py` gains two units: `PIPELINE_FILLED_KEYS`, naming per stage the keys the pipeline supplies, and `stage_configs()`, which builds all five stages' keyword arguments from their own config block plus the run-level values. `configs.py` imports the constant and omits exactly those keys from the pipeline variant of each stage config, so a key can be neither declared-and-unfilled nor filled-and-still-declared. The spec is `docs/superpowers/specs/2026-08-07-pipeline-params-from-code-design.md`.

**Tech Stack:** Python 3.12, hydra-zen + hydra + omegaconf, pydantic models, pytest, ruff, mypy strict, loguru.

## Global Constraints

- Run `uv run pytest`, `uv run ruff check .` and `uv run mypy .` before every commit. Zero failures, zero errors.
- Run `pre-commit run --all-files` before committing. If hooks fail on unstaged changes, `git stash`, run hooks, `git stash pop`.
- Never use quoted strings, `$(...)`, or HEREDOCs in shell commands. Commit with backslash-escaped spaces: `git commit -m feat:\ some\ message`.
- Logging is `loguru`, never `print`. Configs and models are `pydantic`. No bare `except Exception`. No `getattr`/`hasattr` outside third-party SDK wrappers.
- Comments only where the code cannot be made to say it; prefer better names. Avoid functions under four lines unless used four or more times.
- Docs are English except `README.md`, which is Russian.
- Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.

## File Structure

| File | Responsibility after this plan |
|---|---|
| `src/clearml_yolo/tasks/train.py` | Owns the run-directory layout: adds `CHECKPOINT`, the template for the file training writes. |
| `src/clearml_yolo/tasks/pipeline.py` | Owns what each stage is handed: adds `PIPELINE_FILLED_KEYS` and `stage_configs()`; `run_pipeline` gains `auto_gpu`, `ground_truth`, `splits`, `weights`. |
| `src/clearml_yolo/configs.py` | Declares each stage twice from one field set: whole for the standalone app, minus `PIPELINE_FILLED_KEYS[stage]` inside the pipeline. Loses `SharedKeys`, `PipelineStageClearMLConf`, `PipelineInferenceConf`, `PipelineBaselineModelConf`. |
| `src/clearml_yolo/config_tree.py` | Unchanged behaviour; its `HEADER` stops explaining interpolations. |
| `tests/test_configs.py` | Every shared-value guarantee, re-pinned against `stage_configs()` output. |
| `tests/test_pipeline.py` | Stage wiring and pickling, including the injected values. |
| `tests/test_config_tree.py` | The dumped folder is honest and free of `${`. |
| `tests/test_train.py` | The checkpoint template names the file training actually writes. |
| `README.md` | «Общие ключи конвейера» describes code injection, and documents the new top-level `weights`. |

---

### Task 1: The checkpoint layout moves to the module that decides it

`configs.py` uses the `{project}/{name}/weights/best.pt` template for the standalone
predict default. `tasks/pipeline.py` will need the same template for the `skip_train`
path, and `configs.py` will import `PIPELINE_FILLED_KEYS` from `tasks/pipeline.py` — so
the template cannot stay in `configs.py` without a cycle. It moves to `tasks/train.py`,
which is where the layout is decided (`save_dir / "weights" / "best.pt"`) and which both
modules may import. The import-linter "Package layers" contract puts `configs` above
`tasks`, so `configs` → `tasks.train` is allowed.

**Files:**
- Modify: `src/clearml_yolo/tasks/train.py` (add `CHECKPOINT` above `TrainResult`, use it at line 105)
- Modify: `src/clearml_yolo/configs.py:31-35` (import `CHECKPOINT`, drop the local definition)
- Test: `tests/test_train.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `clearml_yolo.tasks.train.CHECKPOINT: str` — a `str.format` template taking
  `project` and `name`, e.g. `CHECKPOINT.format(project="runs/detect", name="exp")` →
  `"runs/detect/exp/weights/best.pt"`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_train.py`:

```python
def test_the_checkpoint_template_names_the_file_training_writes(tmp_path: Path) -> None:
    """The pipeline predicts this path when training is skipped, so a template that drifts
    from the layout training uses would point a skipped run at a file nobody wrote."""
    selection = DeviceSelection(devices=[0], batch=16, batch_per_gpu=16)
    project = str(tmp_path / "runs")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "clearml_yolo.tasks.train.resolve_devices", lambda *_args, **_kwargs: selection
        )
        result = train(
            model="yolo11n.pt",
            data="data.yaml",
            epochs=1,
            imgsz=640,
            batch=16,
            project=project,
            name="run",
            auto_gpu=AutoGpuConfig(),
            clearml=DISABLED,
        )

    assert str(result.weights) == CHECKPOINT.format(project=project, name="run")
```

Extend the existing import at `tests/test_train.py:19` to
`from clearml_yolo.tasks.train import CHECKPOINT, train`.

- [ ] **Step 2: Run the test and watch it fail**

Run: `uv run pytest tests/test_train.py::test_the_checkpoint_template_names_the_file_training_writes -v`
Expected: FAIL — `ImportError: cannot import name 'CHECKPOINT' from 'clearml_yolo.tasks.train'`.

- [ ] **Step 3: Add the template to `tasks/train.py`**

Insert after the imports (before `class TrainResult`):

```python
# Where ultralytics puts a run's checkpoint. Named here because two other places have to
# predict this path without a trainer to ask: the standalone predict default, and the
# pipeline when training is skipped.
CHECKPOINT = "{project}/{name}/weights/best.pt"
```

- [ ] **Step 4: Run the new test and the rest of the train suite**

Run: `uv run pytest tests/test_train.py -v`
Expected: PASS, including `test_the_checkpoint_comes_from_the_trainer_not_the_requested_name`.

- [ ] **Step 5: Point `configs.py` at the moved template**

In `src/clearml_yolo/configs.py`, add to the imports:

```python
from clearml_yolo.tasks.train import CHECKPOINT
```

and delete the local definition and its comment (`configs.py:31-34`), keeping:

```python
DEFAULT_CHECKPOINT = CHECKPOINT.format(project=TRAIN_PROJECT, name=RUN_NAME)
```

- [ ] **Step 6: Verify nothing else referenced the old location**

Run: `uv run pytest && uv run ruff check . && uv run mypy . && uv run lint-imports`
Expected: all pass. `lint-imports` must report no broken contracts — `configs` → `tasks.train`
is a downward layer import, and `train`'s `ultralytics` import is indirect from `configs`,
which the "Model weights are only ever loaded in one place" contract allows.

- [ ] **Step 7: Commit**

```bash
git add src/clearml_yolo/tasks/train.py src/clearml_yolo/configs.py tests/test_train.py
git commit -m refactor:\ name\ the\ run\ layout\ where\ training\ decides\ it
```

---

### Task 2: `stage_configs()` hands each stage what the run decided

The pipeline starts filling the shared values from code while the config still declares
them. Every injected value equals what the interpolation resolved to, so the suite must
stay green throughout — this task is behaviour-preserving by construction, and Task 3 is
what makes it load-bearing.

**Files:**
- Modify: `src/clearml_yolo/tasks/pipeline.py`
- Test: `tests/test_configs.py`, `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `clearml_yolo.tasks.train.CHECKPOINT` (Task 1).
- Produces:
  - `PIPELINE_FILLED_KEYS: dict[str, frozenset[str]]` — stage name → keys `run_pipeline`
    supplies. Keys: `"train"`, `"predict"`, `"metrics"`, `"report"`, `"compare"`.
  - `stage_configs(train, predict, metrics, report, compare, clearml, auto_gpu, ground_truth, splits, weights) -> dict[str, dict[str, Any]]`
    — keyed by the same five stage names; each value is the complete keyword arguments for
    that stage's task, minus `compare["candidate_model"]`, which `run_compare_stage` fills
    from the model the run just trained.
  - `run_pipeline` gains parameters `auto_gpu: AutoGpuConfig`, `ground_truth: str`,
    `splits: list[str]` after `clearml`, before the skip flags.

- [ ] **Step 1: Write the failing tests**

In `tests/test_configs.py`, replace the `_pipeline_stages` helper (lines 64-73) with one
that composes and then fills:

```python
def _pipeline_stages(overrides: list[str]) -> dict[str, dict[str, object]]:
    """Compose the pipeline and build each stage's kwargs the way run_pipeline does.

    Composing alone proves nothing about what a stage receives: the shared values are not
    in the stage blocks at all, they are handed over by ``stage_configs``.
    """
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline", overrides=overrides)
    return stage_configs(
        train=config.train,
        predict=config.predict,
        metrics=config.metrics,
        report=config.report,
        compare=config.compare,
        clearml=instantiate(config.clearml),
        auto_gpu=instantiate(config.auto_gpu),
        ground_truth=config.ground_truth,
        splits=list(config.splits),
        weights=config.get("weights"),
    )
```

Change the imports at the top of the file: drop `from clearml_yolo.tasks.pipeline import _as_dict`
and add `from clearml_yolo.tasks.pipeline import PIPELINE_FILLED_KEYS, stage_configs`.

Replace `FILLED_IN_AT_RUNTIME` (lines 32-34) and the parity test (lines 76-87) with:

```python
@pytest.mark.parametrize("stage", ALL_STAGES)
def test_every_stage_config_key_is_a_parameter_of_its_task(stage: str) -> None:
    """The pipeline calls a stage with its whole block plus what the run filled in.

    A key that is not a parameter is a setting the run accepts and silently ignores; a
    parameter that is neither a key nor filled in is a TypeError raised an hour into a run.
    Neither is visible to the type checker once the block is a dict, so it is checked here.
    """
    keys = set(_pipeline_stages([])[stage]) | PIPELINE_FILLED_KEYS[stage]

    assert keys == set(inspect.signature(TASK_OF_STAGE[stage]).parameters)
```

Rewrite `test_clearml_name_reaches_every_pipeline_stage` (lines 50-61), which reads the
per-stage `clearml` blocks straight off the composed config:

```python
def test_clearml_name_reaches_every_pipeline_stage() -> None:
    """One override must name the whole experiment, not just the top-level block."""
    stages = _pipeline_stages(["clearml.project_name=my-proj", "clearml.task_name=exp-42"])

    for stage in ALL_STAGES:
        clearml = stages[stage]["clearml"]
        assert isinstance(clearml, ClearMLConfig)
        assert clearml.project_name == "my-proj", stage
        assert clearml.task_name == "exp-42", stage
```

Add `from clearml_yolo.clearml_session import ClearMLConfig` to the imports.

Add the two behaviours that are new rather than moved:

```python
def test_a_skipped_training_stage_predicts_where_training_would_have_written() -> None:
    """Nothing produced a checkpoint this run, so the path has to be built from the run's
    own project and name — the same two values training would have used."""
    stages = _pipeline_stages(["skip_train=true", "clearml.task_name=kitti-candidate"])

    assert stages["predict"]["weights"] == "runs/detect/kitti-candidate/weights/best.pt"


def test_the_comparison_keeps_the_inference_settings_it_owns() -> None:
    """Everything else about inference is the predict stage's, merged in over these two."""
    stages = _pipeline_stages(["compare.inference.reuse_existing=false", "predict.conf=0.02"])

    inference = stages["compare"]["inference"]
    assert isinstance(inference, InferenceConfig)
    assert inference.reuse_existing is False
    assert inference.device is None
    assert inference.conf == 0.02
```

In `tests/test_pipeline.py`, widen the pickling net so it covers the injected values, not
only the composed blocks. Read `test_no_omegaconf_containers_survive` and
`test_whole_stage_config_is_picklable` (lines 52-73) and point whatever helper they use at
`stage_configs()` output — the same helper shape as `_pipeline_stages` above. This is the
one place the pickling guarantee can silently regress: `splits` arrives from the top level
as a `ListConfig` and must reach a stage as a plain `list`.

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/test_configs.py -v`
Expected: FAIL — `ImportError: cannot import name 'stage_configs' from 'clearml_yolo.tasks.pipeline'`.

- [ ] **Step 3: Add `PIPELINE_FILLED_KEYS` and `stage_configs()`**

In `src/clearml_yolo/tasks/pipeline.py`, add to the imports:

```python
from clearml_yolo.gpu import AutoGpuConfig
from clearml_yolo.tasks.compare import InferenceConfig
from clearml_yolo.tasks.train import CHECKPOINT
```

Add below `_as_dict`:

```python
# What run_pipeline hands each stage, and therefore what the stage's config block inside
# the pipeline does not declare. configs.py drops exactly these keys, and
# test_every_stage_config_key_is_a_parameter_of_its_task holds the two lists in step: a key
# dropped without being filled, or filled while still declared, fails the suite.
# `compare.inference` is deliberately absent: the comparison declares the two fields it
# owns and the predict stage's settings are merged over them.
PIPELINE_FILLED_KEYS: dict[str, frozenset[str]] = {
    "train": frozenset({"clearml", "auto_gpu", "name"}),
    "predict": frozenset(
        {"clearml", "auto_gpu", "ground_truth", "splits", "weights", "imgsz", "model"}
    ),
    "metrics": frozenset({"clearml", "ground_truth", "splits", "predictions"}),
    "report": frozenset({"clearml", "splits", "metrics_dir"}),
    "compare": frozenset(
        {
            "clearml",
            "auto_gpu",
            "ground_truth",
            "baseline_model",
            "candidate_model",
            "iou_threshold",
            "matching_strategy",
        }
    ),
}


def stage_configs(
    train: Any,
    predict: Any,
    metrics: Any,
    report: Any,
    compare: Any,
    clearml: ClearMLConfig,
    auto_gpu: AutoGpuConfig,
    ground_truth: str,
    splits: list[str],
    weights: str | Path | None,
) -> dict[str, dict[str, Any]]:
    """Give every stage its own block plus everything the run decided for it.

    A value more than one stage reads is named once — on the command line or in the top
    level of the config file — and reaches each stage from here, so it cannot be changed
    for one stage and silently left stale for another. Producer-to-consumer keys work the
    same way: the metrics stage is told the CSV inference wrote, not a second path that
    was supposed to match it.
    """
    shared_splits = list(splits)
    train_cfg = _as_dict(train) | {
        "clearml": clearml,
        "auto_gpu": auto_gpu,
        "name": clearml.task_name,
    }
    predict_cfg = _as_dict(predict) | {
        "clearml": clearml,
        "auto_gpu": auto_gpu,
        "ground_truth": ground_truth,
        "splits": shared_splits,
        # Inference belongs at the resolution the weights were trained at, on the model
        # the run trained: a batch table is keyed by the architecture.
        "imgsz": train_cfg["imgsz"],
        "model": train_cfg["model"],
        # Training overwrites this with the checkpoint it produced. The template is what a
        # run with skip_train has instead: where training would have written.
        "weights": weights
        or CHECKPOINT.format(project=train_cfg["project"], name=train_cfg["name"]),
    }
    metrics_cfg = _as_dict(metrics) | {
        "clearml": clearml,
        "ground_truth": ground_truth,
        "splits": shared_splits,
        "predictions": predict_cfg["output"],
    }
    report_cfg = _as_dict(report) | {
        "clearml": clearml,
        "splits": shared_splits,
        "metrics_dir": metrics_cfg["output_dir"],
    }
    compare_cfg = _as_dict(compare)
    return {
        "train": train_cfg,
        "predict": predict_cfg,
        "metrics": metrics_cfg,
        "report": report_cfg,
        "compare": compare_cfg
        | {
            "clearml": clearml,
            "auto_gpu": auto_gpu,
            "ground_truth": ground_truth,
            # The report reads the baseline's stored dashboards while the comparison
            # re-infers its checkpoint, and two independent searches of one project can
            # answer with two different runs. `source` is not shared: "local" means a folder
            # of workbooks to the report and a checkpoint path to the comparison.
            "baseline_model": _baseline_model(report_cfg["baseline"]),
            # Scored at the IoU its thresholds were calibrated at, or the diff is not the
            # model.
            "iou_threshold": metrics_cfg["evaluation"].iou_threshold,
            "matching_strategy": metrics_cfg["evaluation"].matching_strategy,
            "inference": _comparison_inference(compare_cfg["inference"], predict_cfg),
        },
    }


def _baseline_model(baseline: BaselineConfig) -> ModelRef:
    """Point the comparison at the task the report compares against, not at another one."""
    return ModelRef(
        source="clearml",
        task_id=baseline.task_id,
        project_name=baseline.project_name,
        task_name=baseline.task_name,
        tags=list(baseline.tags),
    )


def _comparison_inference(
    inference: InferenceConfig, predict_cfg: dict[str, Any]
) -> InferenceConfig:
    """Re-run both checkpoints exactly as the candidate was predicted.

    `device` and `reuse_existing` stay the comparison's own: it resolves one card for both
    models itself, and inheriting a device would put a hardware difference inside a
    comparison meant to isolate the model.
    """
    return inference.model_copy(
        update={
            key: predict_cfg[key]
            for key in ("conf", "iou", "imgsz", "batch", "model", "image_name")
        }
    )
```

Add `BaselineConfig` to the existing `tasks.report` import and `ModelRef` is already
imported from `tasks.compare`.

- [ ] **Step 4: Have `run_pipeline` use it**

Change the signature (`pipeline.py:59-71`) to add the three parameters after `clearml`:

```python
def run_pipeline(
    train: Any,
    predict: Any,
    metrics: Any,
    report: Any,
    compare: Any,
    clearml: ClearMLConfig,
    auto_gpu: AutoGpuConfig,
    ground_truth: str,
    splits: list[str],
    skip_train: bool = False,
    skip_predict: bool = False,
    skip_metrics: bool = False,
    skip_report: bool = False,
    skip_compare: bool = False,
) -> dict[str, Any]:
```

Replace the five `_as_dict` calls (`pipeline.py:78-82`) with:

```python
    configs = stage_configs(
        train=train,
        predict=predict,
        metrics=metrics,
        report=report,
        compare=compare,
        clearml=clearml,
        auto_gpu=auto_gpu,
        ground_truth=ground_truth,
        splits=splits,
        weights=None,
    )
    train_cfg = configs["train"]
    predict_cfg = configs["predict"]
    metrics_cfg = configs["metrics"]
    report_cfg = configs["report"]
    compare_cfg = configs["compare"]
```

Change `_check_split_choices(list(metrics_cfg["splits"]), ...)` to
`_check_split_choices(list(splits), ...)`.

Drop the now-redundant `clearml` injections at the three call sites: `run_training(**train_cfg)`,
`compute_metrics(**metrics_cfg)`, and remove `"clearml": clearml` from the dicts in
`run_predict_stage` and `run_compare_stage`; drop the `clearml: ClearMLConfig` parameter
from both helpers and from their call sites.

- [ ] **Step 5: Correct the `_as_dict` docstring**

Its first paragraph says a stage is called by forwarding its whole block. Replace that
paragraph with:

```
    A stage is called with this block plus what ``stage_configs`` fills in, and between
    them they cover the task's parameters exactly — checked by
    ``test_every_stage_config_key_is_a_parameter_of_its_task``, so a setting cannot be
    configured and silently unread.
```

Keep the second paragraph about pickling unchanged.

- [ ] **Step 6: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS. Every guarantee test in `tests/test_configs.py` now runs through
`stage_configs()` and still holds, because each injected value equals what the
interpolation resolved to.

- [ ] **Step 7: Lint and type-check**

Run: `uv run ruff check . && uv run mypy . && uv run lint-imports`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/clearml_yolo/tasks/pipeline.py tests/test_configs.py tests/test_pipeline.py
git commit -m refactor:\ hand\ each\ stage\ the\ values\ the\ run\ decided
```

---

### Task 3: The stage blocks stop declaring what the pipeline fills

With the values arriving from code, the interpolations are dead weight. Removing them is
what empties `cy.yaml` of `${...}`, and it is what makes Task 2's tests load-bearing: from
here, a guarantee that breaks has nothing else holding it up.

**Files:**
- Modify: `src/clearml_yolo/configs.py`
- Test: `tests/test_configs.py`

**Interfaces:**
- Consumes: `PIPELINE_FILLED_KEYS` and `stage_configs` from Task 2, `CHECKPOINT` from Task 1.
- Produces: top-level pipeline key `weights: str | None = None`; `run_pipeline` gains a
  matching `weights: str | Path | None = None` parameter. The store no longer registers the
  `compare/baseline_model` group.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_configs.py`:

```python
@pytest.mark.parametrize("stage", ALL_STAGES)
def test_a_pipeline_stage_declares_nothing_the_run_fills_in(stage: str) -> None:
    """A key that is both declared and filled is a setting a run can change with no effect."""
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline")

    assert not set(config[stage]) & PIPELINE_FILLED_KEYS[stage]


def test_a_named_checkpoint_wins_over_the_one_training_would_have_written() -> None:
    """Which is the whole point of the key: skip_train with weights from somewhere else."""
    stages = _pipeline_stages(["skip_train=true", "weights=runs/old/best.pt"])

    assert stages["predict"]["weights"] == "runs/old/best.pt"
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `uv run pytest tests/test_configs.py::test_a_pipeline_stage_declares_nothing_the_run_fills_in -v`
Expected: FAIL — the composed stage blocks still declare `clearml`, `auto_gpu` and the rest.

- [ ] **Step 3: Turn each stage factory into a field set**

In `src/clearml_yolo/configs.py`, replace the five `*_config(shared)` factories and the
`SharedKeys` dataclass with plain field sets that carry the standalone defaults:

```python
def _train_fields() -> dict[str, Any]:
    return {
        "model": "yolo11n.pt",
        "data": "coco8.yaml",
        "epochs": 100,
        "imgsz": IMAGE_SIZE,
        # Unset, so auto_gpu sizes the batch to this model on these cards. A number here
        # is used as it stands, on the auto path too.
        "batch": None,
        "project": TRAIN_PROJECT,
        "name": RUN_NAME,
        "device": None,
        "auto_gpu": AutoGpuConf,
        "clearml": ClearMLConf,
        "train_kwargs": {},
    }


def _predict_fields() -> dict[str, Any]:
    return {
        "weights": DEFAULT_CHECKPOINT,
        "ground_truth": "ground_truth.csv",
        "output": PREDICTIONS_CSV,
        "auto_gpu": AutoGpuConf,
        # Which architecture the weights are of: a batch table is keyed by it. Unset, the
        # checkpoint is not asked — nothing is loaded from this name.
        "model": None,
        "conf": 0.001,
        "iou": 0.7,
        # Unset means "read it out of the checkpoint" — the one source that cannot
        # disagree with the weights it describes. There is no training stage to ask here.
        "imgsz": None,
        "batch": None,
        "device": None,
        # No downstream split list to honour, so every image in the ground truth is scored.
        "splits": None,
        "image_name": "name",
        "clearml": ClearMLConf,
        "predict_kwargs": {},
    }


def _metrics_fields() -> dict[str, Any]:
    return {
        "predictions": PREDICTIONS_CSV,
        "ground_truth": "ground_truth.csv",
        "output_dir": METRICS_DIR,
        "splits": ["train", "val", "test"],
        "calibration_split": "val",
        "evaluation": EvaluationConf,
        "clearml": ClearMLConf,
    }


def _report_fields() -> dict[str, Any]:
    # The group is named relatively: standalone it resolves to "baseline", and inside
    # the pipeline Hydra prefixes it to "report/baseline" on its own.
    return {
        "hydra_defaults": ["_self_", {"baseline": "clearml"}],
        "metrics_dir": METRICS_DIR,
        "output_dir": "runs/reports",
        "splits": ["train", "val", "test"],
        "report_config_path": None,
        "baseline": None,
        "clearml": ClearMLConf,
    }


def _compare_fields() -> dict[str, Any]:
    return {
        "hydra_defaults": [
            "_self_",
            {"baseline_model": "clearml"},
            {"candidate_model": "clearml"},
        ],
        "baseline_model": None,
        "candidate_model": None,
        "ground_truth": "ground_truth.csv",
        "output_dir": "runs/comparison",
        # Thresholds are calibrated on val and must be reported on images val never saw.
        "split": "test",
        "inference": InferenceConf,
        "auto_gpu": AutoGpuConf,
        "iou_threshold": 0.5,
        "matching_strategy": "iou_prior",
        "q": 0.05,
        "bootstrap_iterations": 10000,
        "seed": 0,
        "clearml": ClearMLConf,
    }


STAGE_FIELDS: dict[str, Callable[[], dict[str, Any]]] = {
    "train": _train_fields,
    "predict": _predict_fields,
    "metrics": _metrics_fields,
    "report": _report_fields,
    "compare": _compare_fields,
}
```

Add `from collections.abc import Callable` to the imports and drop `from dataclasses import dataclass, field`.

- [ ] **Step 4: Build the two variants from one field set**

Replace `PipelineInferenceConf` (`configs.py:82-91`) with the comparison's own fields, and
add the builder. Delete `PipelineStageClearMLConf`, `PipelineBaselineModelConf`, `STANDALONE`
and `PIPELINE` entirely.

```python
# Inside the pipeline the comparison declares only the inference settings it owns; the
# rest are the predict stage's, merged in by run_pipeline. `device` is one of these on
# purpose: the comparison resolves one card for both models itself, and inheriting a
# device would put a hardware difference inside a comparison meant to isolate the model.
ComparisonInferenceConf = builds(InferenceConfig, device=None, reuse_existing=True)

PIPELINE_FIELD_OVERRIDES: dict[str, dict[str, Any]] = {
    "compare": {"inference": ComparisonInferenceConf}
}


def _stage_config(stage: str, *, in_pipeline: bool) -> Any:
    """Build one stage's config, without what run_pipeline fills in when it is a stage of one.

    Both variants come from one field set, so a default cannot be changed for the
    standalone app and left behind inside the pipeline.
    """
    filled: frozenset[str] = PIPELINE_FILLED_KEYS[stage] if in_pipeline else frozenset()
    fields = {key: value for key, value in STAGE_FIELDS[stage]().items() if key not in filled}
    if in_pipeline:
        fields.update(PIPELINE_FIELD_OVERRIDES.get(stage, {}))
    defaults = fields.pop("hydra_defaults", None)
    if defaults is not None:
        # A group whose key the pipeline fills has nothing left to select.
        fields["hydra_defaults"] = [
            entry for entry in defaults if isinstance(entry, str) or not set(entry) & filled
        ]
    return make_config(**fields)
```

Add `from clearml_yolo.tasks.pipeline import PIPELINE_FILLED_KEYS` to the imports.

- [ ] **Step 5: Register from the builder and add the top-level `weights`**

In `register_configs`, replace the stage loop:

```python
    for stage in STAGE_FIELDS:
        store(_stage_config(stage, in_pipeline=False), name=stage)
        store(_stage_config(stage, in_pipeline=True), group=stage, name="default")
```

and drop `"compare/baseline_model"` from the model-group loop, leaving:

```python
    for group, model_conf in (
        ("baseline_model", BaselineModelConf),
        ("candidate_model", CandidateModelConf),
    ):
        model_store = store(group=group)
        model_store(model_conf, name="clearml")
        model_store(ModelLocalConf, name="local")
```

Add the key to `PipelineConf`, next to the other run-level values:

```python
    ground_truth="ground_truth.csv",
    splits=["train", "val", "test"],
    # Unset means the checkpoint this run's training stage writes. Set it when skip_train
    # points the run at a model somebody else trained.
    weights=None,
```

Finally, the module docstring's second paragraph still says each stage is registered under
a group "whose shared values are interpolations" and points at `SharedKeys`, which is gone.
Replace that paragraph:

```
Each stage is registered twice, from one field set: at the top level under its own name, so
it runs as a standalone app with its own settings, and under a group without the keys the
pipeline fills in, so a full pipeline run names each of those exactly once. Which keys those
are is :data:`clearml_yolo.tasks.pipeline.PIPELINE_FILLED_KEYS`.
```

- [ ] **Step 6: Let `run_pipeline` take it**

In `src/clearml_yolo/tasks/pipeline.py`, add `weights: str | Path | None = None` after
`splits` in `run_pipeline`'s signature, and pass `weights=weights` to `stage_configs`
instead of `weights=None`.

- [ ] **Step 7: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS. Watch in particular
`test_folder_composes_back_to_the_built_in_defaults`,
`test_the_baseline_can_be_pinned_whichever_report_the_run_asks_for`,
`test_the_standalone_comparison_still_names_both_sides` and
`test_baseline_group_swaps_standalone` — the standalone comparison keeps both model groups
and only the pipeline loses them.

- [ ] **Step 8: Look at the file this produces**

`cy-init-config` is plain argparse: a positional directory and `--force`.

```bash
uv run cy-init-config /tmp/cy-check-1 --force
```

Read `/tmp/cy-check-1/cy.yaml`. Expected: no `${` anywhere; `clearml`, `auto_gpu`,
`ground_truth`, `splits` and `weights` appear once each, at the top level; each stage block
holds only its own settings.

- [ ] **Step 9: Lint and type-check**

Run: `uv run ruff check . && uv run mypy . && uv run lint-imports`
Expected: all pass. `lint-imports` confirms `configs` → `tasks.pipeline` respects the layer
contract.

- [ ] **Step 10: Commit**

```bash
git add src/clearml_yolo/configs.py src/clearml_yolo/tasks/pipeline.py tests/test_configs.py
git commit -m refactor:\ let\ a\ stage\ declare\ only\ what\ it\ alone\ decides
```

---

### Task 4: The dumped file stops defending interpolations it no longer has

**Files:**
- Modify: `src/clearml_yolo/config_tree.py:39-54`
- Test: `tests/test_config_tree.py:15,31-35`

**Interfaces:**
- Consumes: the config shape from Task 3.
- Produces: nothing other modules use.

- [ ] **Step 1: Replace the interpolation test with its inverse**

In `tests/test_config_tree.py`, delete the `INTERPOLATED` constant and replace
`test_interpolations_are_dumped_unresolved` with:

```python
def test_the_pipeline_file_has_nothing_left_to_resolve(tmp_path: Path) -> None:
    """Shared values are named once at the top level and handed to stages by run_pipeline,
    so a stage block pointing at another key would be a reference nothing keeps true."""
    dump_config_tree(tmp_path)

    assert "${" not in (tmp_path / "cy.yaml").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/test_config_tree.py::test_the_pipeline_file_has_nothing_left_to_resolve -v`
Expected: PASS already, if Task 3 is complete — the assertion is what Task 3 achieved and
this test is what pins it. If it fails, a `${` survives: find it in the dumped file and fix
the stage config that emits it before continuing.

- [ ] **Step 3: Rewrite the header the dumped files carry**

In `src/clearml_yolo/config_tree.py`, replace `HEADER`:

```python
HEADER = """# Generated by `cy-init-config`. Edit freely, then run:
#     uv run {command} --config-dir {directory} --config-name {name}
#
# In cy.yaml, the values more than one stage needs — clearml, auto_gpu, ground_truth,
# splits, weights — are named once at the top level and handed to each stage by the run.
# A stage block holds only what that stage alone decides.
"""
```

Update the module docstring's second paragraph if it mentions interpolation; the paragraph
about file naming and schema matching stays as it is.

Also drop the now-stale comment above the `resolve=False` argument in `_composed`
(`config_tree.py:52-53`) and replace it with:

```python
    # resolve=False so a standalone config that does carry an interpolation keeps it, and
    # so dumping never depends on a value being resolvable at dump time.
```

- [ ] **Step 4: Run the config-tree suite**

Run: `uv run pytest tests/test_config_tree.py -v`
Expected: PASS, including `test_dumped_files_explain_how_to_use_them` (the `--config-dir`
line is still in the header) and `test_folder_composes_back_to_the_built_in_defaults`.

- [ ] **Step 5: Full checks and commit**

```bash
uv run pytest && uv run ruff check . && uv run mypy .
git add src/clearml_yolo/config_tree.py tests/test_config_tree.py
git commit -m docs:\ say\ where\ a\ shared\ value\ is\ named\ in\ the\ file\ that\ carries\ it
```

---

### Task 5: The README describes the mechanism the code now uses

**Files:**
- Modify: `README.md`, section «Общие ключи конвейера» (around lines 61-108) and the
  `--config-dir` example around line 450.

**Interfaces:**
- Consumes: the behaviour from Tasks 1-4.
- Produces: nothing.

- [ ] **Step 1: Read the section as it stands**

Read `README.md` lines 61-110. The tables of what reaches which stage stay true — only the
sentences describing *how* the value gets there change.

- [ ] **Step 2: Rewrite the mechanism sentences**

In Russian, per the docs rule. Concretely:

- The opening sentence «Значения, которые нужны нескольким этапам, задаются один раз на
  верхнем уровне, а этапы ссылаются на них интерполяцией» becomes: they are set once at the
  top level and the pipeline passes them to each stage; the stage block holds only what
  that stage alone decides. Keep the following clause about not being able to change one
  and forget another — it is still exactly the point.
- The producer→consumer paragraph («Так же связаны и цепочки…») keeps every pair
  (`metrics.predictions` ← `predict.output`, `report.metrics_dir` ← `metrics.output_dir`,
  `predict.imgsz` ← `train.imgsz`, `predict.model` ← `train.model`, comparison inference ←
  `predict.*`, `compare.iou_threshold`/`matching_strategy` ← `metrics.evaluation.*`) but
  states that the pipeline passes the value on, rather than that the key points at another
  key. Note that `predict.weights` and the other passed keys are no longer settable per
  stage inside the pipeline.
- The baseline paragraph keeps `report.baseline.*` as the single place the prod model is
  named, and states that the comparison is given that task. Add that inside the pipeline
  there is no `compare/baseline_model` group: a baseline checkpoint on disk is a job for
  standalone `cy-compare`.
- The sentence «Единственное, чего интерполяция выразить не может…» loses «интерполяция»:
  the split-choice check is still made before training, for the same reason.

- [ ] **Step 3: Document the new top-level `weights` key**

Add it to the shared-keys table with `skip_train`: unset it means the checkpoint this run's
training writes; set it to run the rest of the pipeline over somebody else's model. Show
the command form:

```
uv run cy skip_train=true weights=runs/detect/prev/weights/best.pt
```

Check whether the README's `skip_*` section elsewhere needs the same pointer.

- [ ] **Step 4: Verify the documented commands actually work**

Run: `uv run cy --cfg job skip_train=true weights=runs/old/best.pt | head -40`
Expected: composes without error and shows `weights: runs/old/best.pt` at the top level.

- [ ] **Step 5: Full checks and commit**

```bash
uv run pytest && uv run ruff check . && uv run mypy . && pre-commit run --all-files
git add README.md
git commit -m docs:\ say\ that\ the\ run\ hands\ each\ stage\ its\ shared\ values
```

---

## Done when

- `cy.yaml` contains no `${`, and `clearml`, `auto_gpu`, `ground_truth`, `splits` and
  `weights` each appear once, at the top level.
- Every guarantee listed in the spec's Testing section passes through `stage_configs()`.
- `uv run pytest`, `uv run ruff check .`, `uv run mypy .` and `uv run lint-imports` are clean.
- The standalone apps are unchanged: `cy-compare` still offers both model groups, and
  `cy-predict` still reads `imgsz` from the checkpoint.
