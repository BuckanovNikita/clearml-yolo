# Pipeline stages take their shared values from code, not from interpolations

## Problem

`cy.yaml`, the config `cy-init-config` dumps for a user to edit, is 185 lines and roughly
half of it is plumbing. Every stage carries an eight-line `clearml:` block of
`${clearml.*}` references, and `predict.imgsz`, `compare.inference.*`,
`compare.baseline_model.*`, `metrics.predictions`, `report.metrics_dir` and the rest are
`${...}` pointers at another stage's key. The file's own header exists to warn the reader
not to resolve them by hand.

Those references are how the pipeline keeps one value in step across stages, but they are
not the only mechanism in the codebase for that. `run_pipeline` already calls every stage
as `**{**stage_cfg, "clearml": clearml}` — the five `clearml:` blocks in the dumped file
are already dead at runtime, overridden by code. This design extends the mechanism that
already exists to the remaining shared values and stops emitting the interpolations.

## What changes

Each pipeline stage block declares only what that stage alone decides. Everything more
than one stage needs is passed in by `run_pipeline`.

| stage key | today | after |
|---|---|---|
| `train/predict/metrics/report/compare.clearml` | `${clearml.*}`, 8 lines each | already injected; key removed |
| `train/predict/compare.auto_gpu` | `${auto_gpu}` | top-level `auto_gpu` |
| `predict/metrics/compare.ground_truth` | `${ground_truth}` | top-level `ground_truth` |
| `predict/metrics/report.splits` | `${splits}` | top-level `splits` |
| `train.name` | `${clearml.task_name}` | `clearml.task_name` |
| `predict.weights` | `${train.project}/${train.name}/weights/best.pt` | the trained checkpoint, or built from `train.project` and `clearml.task_name` |
| `predict.imgsz`, `predict.model` | `${train.imgsz}`, `${train.model}` | the train block |
| `metrics.predictions` | `${predict.output}` | `predict.output` |
| `report.metrics_dir` | `${metrics.output_dir}` | `metrics.output_dir` |
| `compare.iou_threshold`, `compare.matching_strategy` | `${metrics.evaluation.*}` | `metrics.evaluation` |
| `compare.inference.{conf,iou,imgsz,batch,model,image_name}` | `${predict.*}` | the predict block |
| `compare.baseline_model` | `${report.baseline.*}` | `report.baseline` |

No `${...}` remains anywhere in `cy.yaml`.

### Guarantees that must survive unchanged

- `clearml.task_name=exp-42` still names the whole run: every stage's task, and the
  training run directory. This is the feature the dumped file's header currently defends.
- `ground_truth=`, `splits=` and `auto_gpu.*=` each still reach every stage that reads
  them, from one name on the command line.
- A stage still reads what the previous one wrote: `predict.output=` reaches metrics,
  `metrics.output_dir=` reaches the report.
- The report and the comparison still resolve the *same* baseline task, including when
  the report's own baseline source is switched to `local` or `none`.
- The comparison still re-infers exactly as the predict stage did, and still resolves its
  own card rather than inheriting one.

### Two keys that need a new home

**`weights`** becomes a top-level pipeline key defaulting to `null`, next to
`ground_truth` and `splits`. Unset, it means the checkpoint this run's training stage
writes — `run_pipeline` builds `{train.project}/{clearml.task_name}/weights/best.pt` when
training is skipped, and uses the trained checkpoint when it is not. It is the key you
set under `skip_train=true`. This is the one interpolation doing work no code path
already does, and the only key this design adds.

`skip_predict` and `skip_metrics` need no new key: they are pointed at existing outputs
through `predict.output=` and `metrics.output_dir=`, which is already how those values
reach downstream.

**`compare.inference`** shrinks to the two fields the comparison owns rather than
inherits: `device` and `reuse_existing`. `device` stays out of the shared set on purpose —
inheriting a card would put a hardware difference inside a comparison meant to isolate the
model. `run_pipeline` merges the predict values onto that block.

### Accepted costs

- **`compare/baseline_model=local` is no longer available inside the pipeline.** The
  comparison's baseline becomes, by definition, the task the report compares against; a
  local-checkpoint baseline means running `cy-compare` standalone. The
  `compare/baseline_model` store group and `PipelineBaselineModelConf` are deleted.
- **Per-stage divergence inside the pipeline becomes impossible** — `predict.imgsz=1280`
  against `train.imgsz=640` can no longer be expressed. `SharedKeys` already documents
  that as the intent, not a limitation.

## Design

### `PIPELINE_FILLED_KEYS` — one constant, two consumers

Interpolation made a stale key impossible for free: a key that points at another key
cannot disagree with it. Code injection has to earn that back, or a stage config and the
code that fills it drift apart silently.

`tasks/pipeline.py` gains `PIPELINE_FILLED_KEYS: dict[str, frozenset[str]]` — per stage,
the keys `run_pipeline` supplies. It lives next to the code that fills them, and it has
two consumers:

- `configs.py` imports it and omits exactly those keys from the pipeline variant of each
  stage config. (`configs.py` already imports from `tasks.*` and `tasks/pipeline.py` does
  not import `configs`, so the direction adds no cycle.)
- `test_every_stage_config_key_is_a_parameter_of_its_task` asserts
  `block keys | filled keys == task signature`, so a key dropped from a config without
  being filled by code, or filled without being dropped, fails the suite. A second
  assertion pins `filled keys` to keys `stage_configs` actually produces — the union alone
  would let a key named in `PIPELINE_FILLED_KEYS` but never filled slip through — except
  `candidate_model`, which `run_compare_stage` fills from the model this run just trained,
  not `stage_configs`.

`FILLED_IN_AT_RUNTIME` in `test_configs.py` is subsumed by it: `compare.candidate_model`
is simply another key the pipeline fills.

### `stage_configs()` — where the values are handed over

One named function in `tasks/pipeline.py` builds all five stages' keyword arguments from
their own blocks plus the run-level values. It is the code half of what `SharedKeys.PIPELINE`
expresses today, and reading it answers "where does this stage's `imgsz` come from?" in one
place.

`run_pipeline` gains `auto_gpu`, `ground_truth`, `splits` and `weights` parameters —
`zen()` passes them from the matching top-level keys — and calls `stage_configs()` in
place of its five `_as_dict` calls. Stage ordering, the skip flags, `_check_split_choices`,
the trained-device threading and the two stage helpers are unchanged; `_check_split_choices`
reads the top-level `splits` instead of `metrics_cfg["splits"]`.

`_as_dict` keeps its job of turning one composed block into plain Python, but its docstring
claim that a stage is called by forwarding its whole block is no longer the whole truth and
is corrected.

The `CHECKPOINT` layout template — `{project}/{name}/weights/best.pt` — is needed by
`configs.py` for the standalone default and now by `tasks/pipeline.py` for the
`skip_train` path, while `configs.py` imports `PIPELINE_FILLED_KEYS` from
`tasks/pipeline.py`. It moves to `tasks/train.py`, which is where the layout is decided
(`save_dir / "weights" / "best.pt"`) and which both modules may import. Naming it twice is
how it would come to disagree with the file training actually writes.

### `configs.py`

`SharedKeys` keeps only what a standalone stage needs — its literal defaults. The
`PIPELINE` instance, `PipelineStageClearMLConf`, `PipelineInferenceConf` and
`PipelineBaselineModelConf` are deleted; the pipeline variant of each stage is the same
factory output with `PIPELINE_FILLED_KEYS[stage]` removed. `PipelineConf` keeps the
top-level `clearml`, `auto_gpu`, `ground_truth`, `splits` and skip flags as the single
source, and gains `weights=None`.

### `config_tree.py`

`_composed` still dumps with `resolve=False` — the standalone configs are unaffected and
nothing is left to resolve in `cy.yaml` anyway. The `HEADER` comment, which currently
explains why `${...}` entries must not be resolved by hand, is rewritten: the shared
values are named once at the top level of the file, and stages read them from there.

## Testing

`test_configs.py`'s `_pipeline_stages` helper composes the pipeline and resolves each
stage with `_as_dict`. After this change, composing proves nothing about what a stage
receives, so the helper composes and then calls `stage_configs()`. Every existing
guarantee is re-pinned through it with its meaning unchanged:
`one_ground_truth_reaches_inference_scoring_and_comparison`,
`one_split_list_reaches_every_stage_that_reads_one`,
`the_gpu_policy_is_named_once_for_all_three_stages`,
`the_run_name_follows_the_experiment_name`,
`each_stage_reads_what_the_previous_one_wrote`,
`the_comparison_re_infers_exactly_as_the_predict_stage_did`,
`inference_runs_at_the_resolution_the_model_was_trained_at`,
`the_model_under_test_is_named_once_for_the_whole_run`,
`the_report_and_the_comparison_resolve_the_same_baseline`,
`promoting_a_different_tag_moves_both_sides_of_the_baseline`,
`the_baseline_can_be_pinned_whichever_report_the_run_asks_for`,
`the_comparison_scores_at_the_iou_its_thresholds_were_calibrated_at`.

`test_clearml_name_reaches_every_pipeline_stage` currently reads `config[stage].clearml`
straight off the composed config; those blocks no longer exist, so it asserts on the
stage kwargs instead.

New tests:

- The dumped `cy.yaml` contains no `${` — the inverse of
  `test_interpolations_are_dumped_unresolved`, which is deleted.
- `PIPELINE_FILLED_KEYS` names no key that the pipeline stage config still declares.
- With `skip_train=true` and no `weights`, predict is handed
  `runs/detect/<task_name>/weights/best.pt`; with `weights=` set, it is handed that path.
- `compare.inference.device` and `reuse_existing` set in config survive the merge of the
  predict values.

`test_config_tree.py`'s round-trip test (dumped folder composes back to the built-in
defaults) is unaffected and must keep passing — it is the check that the dumped file is
still honest.

## Documentation

`README.md` (Russian) section «Общие ключи конвейера» states that stages reference shared
values by interpolation. The tables of what reaches where stay true; the mechanism
sentence, the producer→consumer paragraph, the baseline paragraph and the sentence about
what interpolation cannot express are rewritten to say that the pipeline hands these
values to each stage. The new top-level `weights` key is documented with `skip_train`.
