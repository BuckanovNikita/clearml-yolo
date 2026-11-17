# ClearML publication

Every execution command (`cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`,
`cy-compare`, `cy-report`, `cy-ground-truth`, `cy-export`) records its experiment in
exactly one ClearML task: the executable configuration, sanitized scientific parameters,
source-code identity, required result artifacts, one verified best Output Model when it
trains, and, for `cy`, a stage-by-stage outcome. A command succeeds only after every
required upload has been confirmed and read back. When a `cy` pipeline has finished
training successfully, a later stage failure is recorded as a warning instead of
discarding the trained model. ClearML is required for these commands; configuration
export, cache maintenance, batch estimation, weight preparation and inspection create no
task.

## Behavior

### Task ownership

- One invocation owns one task, created with `reuse_last_task_id=False`. Pipeline
  stages reuse it; native and DDP worker processes never create tasks or upload. A
  ClearML Agent run joins the task it was submitted for.
- The task is named `clearml.task_name` for `cy` and `<task_name>/<stage>` for a
  standalone stage (for example `yolo-run/train`), in project `clearml.project_name`.
- New local tasks record the module entry point `-m clearml_yolo.entrypoints.<stage>`,
  working directory `.`, and, from a source checkout, the sanitized `origin` URL,
  branch (`HEAD` when detached) and exact commit, verified by fresh readback before
  work starts. No uncommitted diff or raw arguments are uploaded, so the commit does not
  claim to include local edits. An installed package or missing Git warns and leaves
  these fields empty. Agent runs keep their submitted script.
- Credentials never enter published configuration or failure status; a failed task's
  status message says only `<error type>: invocation failed; see local diagnostics for
  details`.

### Experiment names

Task and best-model display names must be unique within the project, counting archived
tasks and models but not the current records. An unused name stays unchanged; on a
collision, task and model get the same readable `-<adjective>-<noun>` suffix, rechecked
after each write, with up to 20 attempts. Output paths, URLs and IDs never change with
the display name, and clones resolve their own names. Requested and effective names are
recorded in the `run` configuration under `display_names`.

### Stable experiment parameters

`General` holds the sanitized scientific training arguments without `device`, `project`,
`name`, `save_dir`, `exist_ok` and the CSV-generated `data`. Training publishes it after
validation and before dataset preparation; native owner callbacks later refresh it with
observed normalization, including DDP and the other detector families. Commands that do
not train publish no `General`. Filtering applies to newly connected values only; clones
keep keys inherited from their source task. Remote YOLO training replay applies
scientific `General` overrides, never redacted values, and a null `batch` still triggers
a fresh capacity lookup.

### Publication inventory

| Name | Contents |
| --- | --- |
| Output Models | One owned best checkpoint with verified association, bytes and metadata |
| Scalars, Plots, Debug Samples | Owner training and validation telemetry and permitted previews, without native validation PR images |
| `gt_csv` | Effective ground truth, once per invocation |
| `predicts_csv` | One combined prediction and evaluation table, including valid empty results |
| `metrics_best_confidences_val` | Full-precision validation thresholds when calibrated |
| `metrics_dashboard_full_<split>`, `metrics_dashboard_dtrk_<split>` | Full and DTRK workbooks per evaluated split |
| `comparison_<role>_dashboard_full_<split>`, `comparison_<role>_dashboard_dtrk_<split>` | Candidate and baseline reinference workbooks |
| `compare_workbook_<split>`, `compare_workbook_<split>_excluded` | Paired workbook and excluded-class CSV |
| `report_dev_<split>`, `report_business_<split>` | Final paired developer and business workbooks |
| `pipeline_outcome` | `cy` only: stage outcomes and artifact references |
| `export_onnx`, `export_engine`, `export_metadata`, `export_verification`, `export_corpus` | [Export](export.md) outputs |
| Configuration Objects | `run`, `run_overrides`, `model_assets`, consumed `dataset`, explicit `report` |

Ground-truth and training commands publish `gt_csv`; training also owns the model and
telemetry. Prediction adds not-evaluated rows; metrics and validation add evaluated
rows, thresholds, dashboards and plots; comparison adds reinference rows, both
dashboards and paired outputs when a baseline exists; report publishes its workbooks;
`cy` publishes the union of its enabled stages with each CSV once. Without an automatic
baseline, candidate outputs and a skip reason are published, never fabricated pairs.
Split names are percent-encoded in artifact names. Prepared datasets, native YAML,
archives, raw metrics, sidecars, receipts and diagnostics stay local, and configuration
copies or duplicate checkpoints are never uploaded. Table contents are defined in
[prediction and validation](prediction-and-validation.md), [comparison](comparison.md)
and [reports](reports.md).

### Upload timing and completion

- Each artifact uploads synchronously as soon as its final file is written: `gt_csv`
  once its validated file is complete, thresholds after calibration, each dashboard
  after its identity annotation and before the next evaluation, each workbook after its
  final annotation, each export file when produced. Existing names are never replaced
  by intermediate uploads.
- Identical table bytes publish once and satisfy every expectation that names them;
  distinct bytes under one name upload as `<name>_2`, `<name>_3` and so on.
  Re-registering identical ground truth is a no-op; conflicting ground truth fails.
- Workflows declare every enabled result producer (`predict`, `metrics`, `compare`)
  before adding rows and complete each after its last change. The last completion
  assembles and uploads the single `predicts_csv`, before later statistics, reports or
  FiftyOne publication. A skipped comparison completes without rows.
- At the end, the owner checks that every declared producer completed and every
  required artifact uploaded, waits for model uploads, requires a confirmed flush,
  re-verifies each Output Model, uploads `pipeline_outcome`, drains the console and
  marks the task completed.

### Output Model registration and verification

- YOLO training's native callback registers the best checkpoint; the other detector
  families register their single descriptor-bound checkpoint directly. A missing or
  second model is an error; no wrapper fallback is created.
- Flush alone is not proof: the owner reloads the task, requires one model associated
  with the task and project, rejects transient or failed upload URLs, force-downloads
  non-empty bytes and compares their SHA-256 with the local checkpoint. It then sets the
  display name, the `best` tag and metadata on the same model and verifies a fresh
  readback, without uploading the weights again.
- Metadata records the checkpoint role, filename and SHA-256, training task ID,
  architecture, input size and channels, requested and effective model names and
  package versions (YOLO adds the input model ID when there is exactly one; the other
  families add backend, preset and checkpoint descriptor); IDs, timestamps and
  production tags are never invented. A
  `<checkpoint>.identity.json` sidecar binds the model name and training task to the
  checkpoint bytes.
- Only the invocation's own verified model receives validation thresholds, and only
  when the prediction checkpoint hash equals the model's:

  | Metadata key | Value | Type |
  | --- | --- | --- |
  | `clearml_yolo_confidence_thresholds` | Exact JSON map of class to threshold | `str` |
  | `clearml_yolo_confidence_threshold/<class>` | `repr(float)` of each threshold | `float` |
  | `clearml_yolo_calibration_split` | `val` | `str` |
  | `clearml_yolo_calibration_checkpoint_sha256` | Prediction checkpoint SHA-256 | `str` |

  The model ID, URL and downloaded hash are rechecked and these values join the final
  verification. Standalone `cy-metrics` never creates or modifies a model.

### Training outcome after a later failure

For `cy`, once training produced a non-empty checkpoint, each later stage (prediction,
metrics, thresholds, comparison, report, visualization, publication) is recorded as
`succeeded`, `completed_with_warnings`, `failed` or `skipped` in `pipeline_outcome.json`
and `pipeline_outcome.txt` in the run directory, written atomically after every stage.
A failed stage is logged, dependent stages are skipped with a reason (all later compute
stages when the post-training resource handoff fails), and the command returns
normally. Missing uploads are listed as missing, never marked uploaded. The
task ends `completed` with a status message starting `completed_with_warnings:`; if
ClearML cannot be reached for that update, the local outcome records it. Interruptions,
training failures and pipelines with `skip_train=true` stay strict and fail.

Publication failures follow the same split. In a standalone command, or before pipeline
training succeeds, a failed required upload, finalization step or final console delivery
marks the task failed. After successful pipeline training it is recorded as a failed
`publication` stage, and the task ends `completed` with
`completed_with_warnings: Training succeeded; publication incomplete; see local outcome`
(or `completed_with_warnings: Training succeeded; console publication incomplete` when
only the final console delivery failed).

### Controller cache identity

External pipeline controllers can reuse completed tasks by normalizing their cache key:

```python
from clearml.automation.job import ClearmlJob
from clearml_yolo.adapters.clearml.cache import normalize_task_hash

ClearmlJob.register_hashing_callback(normalize_task_hash)
```

Register it in the controller, not a worker, before creating cached jobs (with
`cache_executed_step=True`), composing explicitly with any existing callback. Supply
`run` overrides as JSON text:
`configuration_overrides={"run": json.dumps(run, ensure_ascii=False)}`. A dictionary
override is serialized with ASCII escapes and
`Task.set_configuration_object(config_dict=...)` writes HOCON; HOCON is never normalized,
so routing differences then prevent a cache hit. For `clearml_yolo` entry points the key
ignores run names, output and cache destinations and `run_overrides`, and compares
explicit CUDA ordinals by device count (`[0,1]` matches `[2,3]`; CPU, MPS, one and two
GPUs differ). Automatic selectors stay distinct from explicit allocations. Paths under
the recorded `run.prepared_dataset` root compare by its cache identity and relative path;
other paths compare literally. Scientific inputs, and names or paths that select inputs,
stay significant; documents it cannot parse safely stay unnormalized. A hit reuses the
matched task's remote outputs and writes nothing locally; pin task IDs before caching
mutable "latest" lookups.

## Configuration

| Option | Default | Meaning |
| --- | --- | --- |
| `clearml.project_name` | `clearml-yolo` | Project of the task and its models |
| `clearml.task_name` | `yolo-run` | Requested task name; also names the implicit run directory |
| `clearml.task_type` | `training` | ClearML task type |
| `clearml.tags` | `[]` | Task tags; the best model also gets `best` |
| `clearml.output_uri` | `true` | Artifact storage: `true` uses the ClearML settings, a string sets the URI; `false`, `null` and `""` are rejected |

## Failure behavior

- A standalone command, or `cy` before training succeeds, fails when any computation,
  required upload, readback, flush or model verification fails or a declared producer is
  incomplete. The task is marked failed and local outputs are kept; completed uploads
  stay available and an incomplete `predicts_csv` is never uploaded.
- Owner SDK work is bounded per step, not per invocation: the Agent snapshot read, the
  completion barrier, failure cleanup, the warning outcome upload, each status
  update, console finish and the incomplete owner's logging-handler close each get their
  own 600-second main-thread Unix alarm, in direct and queued runs alike. One expired step
  does not prevent the next outcome or status attempt, so the total can exceed ten
  minutes. An expired step is a finalization failure and follows the rules above. A
  cleanup or finalization error never replaces the original computation error.
- Before marking its task failed, the owner releases its own SDK status monitor so the
  SDK does not treat that transition as an external abort; an SDK that cannot confirm the
  release fails finalization. After a failed or expired close, only this owner's task and
  reporter exit callbacks are detached, so interpreter exit does not repeat unbounded
  shutdown work; other SDK owners, handlers and configuration are untouched.
- Uncertain deliveries are not retried automatically.
- If Linux startup fails inside `Task.query_tasks` because `tasks` is `None`, keep the
  failed invocation and its logs; an empty task list alone does not establish this
  failure. The SDK's thread-based reporting can be selected in the ClearML SDK
  configuration file chosen by `CLEARML_CONFIG_FILE` (not a Hydra override):
  `sdk.development.report_use_subprocess = false`. Retry into a fresh output directory;
  the normal publication checks must still pass.
- If task setup or owner shutdown does not confirm closure, the process is quarantined:
  every later invocation in it, including later members of a sequential `cy -m` sweep,
  fails before creating a task with `Previous ClearML owner did not confirm closure;
  start a fresh process before another invocation`. Inspect the original failure and
  relaunch in a fresh process. A normally closed owner permits the next invocation.

## Limits

- Bounded finalization requires a Unix main thread with no other active `ITIMER_REAL`
  alarm; otherwise it fails with `Bounded ClearML finalization requires a Unix main
  thread` or `... conflicts with an existing alarm`. CY never overrides an embedding
  application's timer.
- Top-level `LOCAL_RANK` launches are rejected; start the `cy` command directly.
- Historical tasks are never rewritten or backfilled, and parameter history is not
  cleaned.

## Code and tests

- [`adapters/clearml/session.py`](../../src/clearml_yolo/adapters/clearml/session.py) — task lifecycle, uploads, finalization
- [`adapters/clearml/results.py`](../../src/clearml_yolo/adapters/clearml/results.py) — result producers, `gt_csv`, `predicts_csv`
- [`adapters/clearml/native.py`](../../src/clearml_yolo/adapters/clearml/native.py), [`detectors.py`](../../src/clearml_yolo/adapters/clearml/detectors.py) — Output Model verification
- [`adapters/clearml/naming.py`](../../src/clearml_yolo/adapters/clearml/naming.py), [`parameters.py`](../../src/clearml_yolo/adapters/clearml/parameters.py), [`script.py`](../../src/clearml_yolo/adapters/clearml/script.py), [`cache.py`](../../src/clearml_yolo/adapters/clearml/cache.py), [`deadline.py`](../../src/clearml_yolo/adapters/clearml/deadline.py)
- [`core/pipeline_outcome.py`](../../src/clearml_yolo/core/pipeline_outcome.py), [`core/artifact_names.py`](../../src/clearml_yolo/core/artifact_names.py)
- Tests: [`test_clearml_session.py`](../../tests/test_clearml_session.py),
  [`test_clearml_results.py`](../../tests/test_clearml_results.py),
  [`test_result_lifecycle.py`](../../tests/test_result_lifecycle.py),
  [`test_clearml_native.py`](../../tests/test_clearml_native.py),
  [`test_clearml_models.py`](../../tests/test_clearml_models.py),
  [`test_clearml_naming.py`](../../tests/test_clearml_naming.py),
  [`test_clearml_parameters.py`](../../tests/test_clearml_parameters.py),
  [`test_clearml_script.py`](../../tests/test_clearml_script.py),
  [`test_clearml_cache.py`](../../tests/test_clearml_cache.py),
  [`test_native_tracking_contract.py`](../../tests/test_native_tracking_contract.py),
  [`test_pipeline_outcomes.py`](../../tests/test_pipeline_outcomes.py)
- Unit tests use a ClearML fake; real server publication is established only by the
  live suite.
