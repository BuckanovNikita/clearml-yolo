# clearml-yolo reference

Behavior and contracts that the code does not make obvious. Usage is in [README.md](README.md) and [docs/](docs/README.md);
rules for changing the code are in [AGENTS.md](AGENTS.md).

## Architecture and data flow

- Layers `entrypoints -> adapters -> application (ports, contracts) -> core`; imports point inward only. `.importlinter` is exhaustive (an unclassified package fails) and is the only table of cross-adapter and SDK-owner edges (exact `ignore_imports`); a new SDK import needs an owner module and a contract entry.
- Adapters use application ports and contracts, never `application.use_cases`, `application.evaluation`, `application.ground_truth` or entrypoints. `augmentation` and `observability` import no other adapter; `assets`, `clearml`, `integrations`, `reporting`, `yolo` may import `storage` and `observability`; every other adapter imports only `observability`.
- Use cases compose inward: `pipeline` above `val` and `report`, above `metrics`, above single-stage commands, above `publication`. Command entrypoints are independent. Evaluation never imports reporting or tracking; FiftyOne publication never imports tracking or model execution.
- Core has no filesystem, network, process or environment access and imports only stdlib, NumPy, pandas, SciPy, Pydantic, Pandera. Application performs effects only through typed ports in `WorkflowDependencies`. Neither imports Loguru, Matplotlib, Pillow, OpenPyXL, requests or filelock.
- `entrypoints.composition` builds one dependency bundle per invocation; use cases never construct or look up adapters. Importing a package has no runtime effect; the `clearml_yolo` root imports nothing. Hydra, hydra-zen, OmegaConf belong to `entrypoints.hydra`.
- Heavy SDK imports are plain function-local imports; computed imports only for DEIM namespace loading (`src/ruff.toml` bans `importlib.import_module` and `builtins.__import__`; bare `__import__` needs review).
- Pinned `digital-metrics` algorithms (matching, AP, confidence ordering) run only in evaluation adapters; results are copied into core records. Only reporting writes workbooks and plots.
- `cy` flow: train, predict, metrics (val calibration + evaluation), compare on `test` vs baseline, report, optional FiftyOne publication. `skip_<stage>=true` disables a stage. With `skip_train=true skip_compare=true` the report reads the `comparison/` already in the run directory; when `comparison_manifest.json` is absent there, the report stage is recorded as skipped with reason `No comparison exists in the run directory; set skip_report=true to disable the report stage`, not failed.

## Static analysis

- Ruff selects `ALL` with lint preview (`ruff.toml`, `src/ruff.toml`); each exclusion's rationale is the comment beside it in `ruff.toml`, `src/ruff.toml` or `pyproject.toml`. Review changed diagnostics and exclusion reasons on every Ruff upgrade.
- mypy is strict with extra error codes (`pyproject.toml`); package-level `ignore_missing_imports` also hides missing submodules, so keep that list narrow.
- Vulture runs at `min_confidence = 80` over `src`, `scripts`, `tests`; dynamic framework members (60%) are an advisory audit only. A clean run does not prove reachability.
- import-linter checks layers including function-local and type-only imports; standalone pytest module names are listed by hand.

## Commands and configuration

- Commands -> Hydra configs: `cy`->`pipeline`, `cy-train`->`train`, `cy-predict`->`predict`, `cy-val`->`val`, `cy-metrics`->`metrics`, `cy-compare`->`compare`, `cy-report`->`report`, `cy-ground-truth`->`ground_truth`, `cy-export`->`export`. No-task tools: `cy-init-config`, `cy-dedup`, `cy-download-weights`, `cy-batch-estimate`.
- `cy-init-config DIR [--command NAME] [--model PRESET] [--force]` writes an editable tree; run it with `<command> --config-dir DIR --config-name <command>` (Python `dump_config_tree(directory, *, command="cy", model=None, overwrite=False)`).
- Help: `<command> --help` is a custom `hydra.help` set per launch (`configs.register_command_help`). The banner is the public command name. `== Configuration groups ==` lists only groups the command's packaged defaults let the user select (`model/<backend>`, `transforms`); `_cy_schemas`, `defaults` and `transform_overrides` are not shown. `--hydra-help` is unchanged.
- Composition: packaged defaults, then `--config-dir`, then CLI overrides; `hydra.job.chdir=false`; logs `CY_HOME/outputs/<date>/<time>-<host>-<pid>`, sweeps `CY_HOME/multirun/...`; all routes are containment-checked before the first job.
- Required `???` inputs: `ground_truth` (cy, train, predict, val, metrics, compare), `predictions` (metrics), `comparison_dir` (report), `data_yaml` (ground-truth). Unknown top-level keys fail `Unsupported wrapper settings: [...]`.
- Rejected everywhere (CLI, saved YAML, defaults lists, replay): `queue.*`, `autogpu.*`, `auto_gpu.*`, `hydra/launcher=cy_queue`, `clearml.enabled`. Sweeps need `-m`/`hydra.mode=MULTIRUN` and run sequentially (BasicLauncher); each MULTIRUN adds tag `multirun-YYYYMMDD-HHMMSS-<six-word-phrase>` (UTC).
- Validation order (`execute_owned`): wrapper keys and write routes, then `validate_command_configuration(config, function)`, then the invocation creates the one ClearML task; the same checks run again on the configuration restored by Agent replay, before `run` is published. The preflight decides from the composed configuration alone and has no effect: no directory creation, writes, network, or SDK or adapter call with side effects. Rule: in `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-compare`, `cy-report`, `cy-export` and `cy-ground-truth` the preflight rejects before the task every setting value that a validator of the run or of cy-queue admission rejects, with that validator's message, also for a stage the user skipped (`skip_*`) and, in `cy`, for the stages after training. Before it validates, it applies the run's pure transformations: a detector's `model.train` and `model.predict` replace the Ultralytics groups and a given `dataset_format` becomes `coco` (as in `_execute_direct`); records are taken as Hydra instantiates them; keys bind to the use-case call as the call binds them, so a removed key takes the signature default; in `cy`, skip flags are read by truthiness, `run_id` is ignored next to `run_dir`, and the prediction group goes through the CSV dataset policy (when training) and the backend's prediction projection. It keeps accepting these loose but valid forms: integer skip flags (`skip_compare=1`); optional keys removed with `~key` or missing from a saved YAML or a replayed `run` (signature default); with a detector backend, a missing inactive `ultralytics` or `ultralytics_predict` group; a record `_target_` that Hydra locates to the supported class (locating it imports its module, as instantiation does); Hydra's reserved keys `_convert_`, `_recursive_`, `_args_` and `_partial_` in records; a `run_id` of any type, numeric included, next to an explicit `run_dir`. Accepted exceptions, rejected although a run could get further: `fiftyone=null`, which a run would publish with defaults (message `fiftyone=null is not supported; use fiftyone.enabled=false to turn FiftyOne publication off`); a required key missing from a saved or replayed configuration, which fails before the task with the message of Python's signature binding, `missing a required argument: '<name>'`; a record whose `_target_` names a different class (`Submission requires the supported configuration target <target>`), only for the records a command's preflight validates: in `cy` `clearml`, `fiftyone`, `evaluation`, `baseline_model` and `candidate_model`; in the standalone commands `fiftyone` (`cy-predict`, `cy-metrics`), `evaluation` (`cy-val`, `cy-metrics`, `cy-compare`), `baseline_model` and `candidate_model` (`cy-compare`). No standalone command validates `clearml`: Hydra instantiates it as written. `cy` calls `validate_pipeline_configuration(config, direct=True)`: cy-queue admission's checks plus the run's `split='all'`, evaluation-backend, training-model, `resume` and Ultralytics `dataset_format` (not `coco`) rules and the native routes. With `run_dir` or `run_id` the routes and `dataset_cache_dir` resolve as `run_pipeline` resolves them (`routed_native`, `reject_cache_inside_run_dir`). Without them the run directory needs the task id: a non-null `ultralytics.project`, `ultralytics_predict.project` or `ultralytics.save_dir` fails with cy-queue admission's `Native pipeline output overrides require an explicit run_dir`, and a null `ultralytics.save_dir` key or a native `name` other than the stage's (`train`, `predict`) fails with `routed_native`'s own message (`reject_fixed_native_routes`); a `name` equal to the stage's and a prediction `save_dir`, which the prediction projection drops, pass. cy-queue admission calls `validate_wrapper_keys`, `validate_project_destinations` and `validate_pipeline_configuration(config)` with one argument; these keep cy-queue's admission rules (strict types, every key present, the canonical `_target_`, no reserved keys, `fiftyone: null` rejected by both `validate_wrapper_keys` and `validate_pipeline_configuration` with the same message, the literal `run_dir`, the cache rule only for an explicit `dataset_cache_dir`, and no native output key without a run directory), except that the default-candidate check of `cy-compare` moved from `validate_wrapper_keys` to the preflight; cy-queue passes only `run_pipeline` or `train` there, so its admission is unchanged. `validate_pipeline_configuration`'s name, positional signature and one-argument behavior are a compatibility boundary. The other commands check, after the same transformations, YOLO `ultralytics`/`ultralytics_predict` values, the training model and `resume`, the `dataset_format` value (and, for YOLO, not `coco`) of `cy-train`, the prediction model from the backend's prediction projection, `evaluation` and its backend, `fiftyone`, `calibration_split`, `split='all'`, in `cy-compare` the comparison rule cy-queue applies to `cy`'s `compare` group (`baseline_model`, `q`, `bootstrap_iterations`, `seed`), model refs, the default candidate and owned prediction keys, in `cy-report` the `report_config_path` type rule of `cy`'s `report` group, export input presence and `test_fraction`. Few checks stay after the task because they need it, files or downloads: in `cy` without `run_dir` and `run_id`, the cache rule against the run directory named after the task id; file contents (ground truth, splits, `data_yaml`, comparison dir, `report_config_path` file, weights) and model downloads or ClearML lookups. Two value checks also stay after the task although the composed configuration decides them: `cy-train` with an explicit `ultralytics.project` rejects `dataset_cache_dir must be outside the run-owned training project` and `CSV training output directory must be inside its project` only in the use case (`train.py`); `cy-compare` validates its `inference` values (for example `inference.reuse_existing`) only when the use case builds its settings. In a multirun the value preflight runs per job, when that job starts (only destinations are checked for every member before the first job), so the earlier members of a sweep create tasks and run before an invalid later member fails. The use cases keep their checks for Python API callers. Detector `cy-predict` and `cy-val` require `weights`: `model.predict` has no model field.
- `splits` default `[train, val, test]`. With `skip_train=true`, `weights` defaults to `detect/train/weights/best.pt` in the run dir; `weights` without `skip_train=true` fails.
- Run routing: pipeline task `clearml.task_name`, standalone `<task_name>/<stage>`; outputs `CY_HOME/runs/<project>/<task>-<task-id>/` (percent-encoded); `run_dir` beats `run_id` (`CY_HOME/runs/<run_id>`); run dirs are reused, never cleared; `runs/latest` symlink (non-symlink moved to `latest-displaced-<host>-<pid>`).
- Each experiment command warns once, never fails, when `git rev-parse --is-inside-work-tree` (no inherited `GIT_*`, 5 s timeout) is not `true`.

## Datasets and ground truth

- Ground truth CSV columns: `image_name`, `image_path`, `instance_label`, `bbox_x_tl`, `bbox_y_tl`, `bbox_x_br`, `bbox_y_br`, `split` (train/val/test); absolute pixel corners; `image_path` relative to the CSV dir; identity columns literal text; background rows have empty label and coordinates.
- `ground_truth` is a path or a ClearML dataset selector (`{dataset_id}` or `{project_name, name[, version]}`) whose finalized dataset holds exactly root `dataset.csv`; unversioned resolves to latest; recorded under `run.ground_truth_source`; local paths warn.
- Training drops invalid boxes (`Invalid bounding boxes dropped: N`), forces native `task`, `classes`, `data`, `single_cls`, `fraction`, `cls_remap`, `split` (recorded as `training_data_overrides`); YOLO uses `dataset_format=ndjson` (default) or `flat`, other families COCO; images below 10x10 fail.
- Prepared datasets: `dataset_cache_dir` (default `CY_HOME/.cache/clearml-yolo/datasets`), keyed by CSV bytes, ordered resolved image refs, format and preparation version; locks in `.locks/`; never deletes entries; changed image bytes at unchanged paths are not detected.
- `cy-ground-truth data_yaml=...` converts YOLO labels (5 fields, values in `[-0.01, 1.01]`); without `test` images, `test_fraction` (default 0.5, `[0,1)`) of `val` by name with `seed` (default 0) become `test`.

## Training

- YOLO defaults `model=yolo11n.pt`, `imgsz=960`, `compile=true`, `nms=true`. Native `model.train` defaults: `epochs=100`, `batch=4` (global, divisible by GPU count; `null` reads the batch table), `workers=4`, `lr=0.0001`, `weight_decay=0.0001`, `seed=0`, `pretrained=true`, `amp=true`, `use_ema=true`, `grad_accum_steps=1` (DEIMv2 only 1); unknown keys rejected.
- `model.train.device`: `null`, `cpu`, `cuda`, `cuda:N`, index, list or comma string (logical inside `CUDA_VISIBLE_DEVICES`). 2+ devices start one supervised process per GPU (DEIMv2 NCCL DDP, RF-DETR Lightning DDP, Faster R-CNN/FCOS distributed sampling); NCCL init timeout 120 s, supervision deadline 30 days. Prediction is single-device.
- Best checkpoints: YOLO `weights/best.pt`; DEIMv2 `best_stg2.pth` else `best_stg1.pth`; RF-DETR `checkpoint_best_total.pth`; Faster R-CNN/FCOS `best.pth` by `val/map50_95`. Missing best checkpoint fails.
- Never retries with a smaller batch, no automatic precision/compiler fallback, never substitutes non-finite values (`Native scalar must be finite:`, `Torchvision training produced a nonfinite loss: ...`), never resumes (optimizer/scheduler state never restored).
- In `cy`, once a non-empty checkpoint exists, later stage/publication failures go to `pipeline_outcome.json`/`.txt` and the task completes with `completed_with_warnings: ...`. Standalone commands, pre-training failures, interruptions and `skip_train=true` stay strict.

## Detector families

- Presets (group `model`): `ultralytics` (default, imgsz 960); `deimv2/{s,m,l,x}` (640); `rfdetr/{nano,small,medium,large}` (384/512/576/704); `fasterrcnn/` and `fcos/` `{resnet50_fpn,resnet101_fpn,convnext_tiny,swin_tiny,dinov2_small,dinov3_small}` (800).
- YOLO settings live in `ultralytics`/`ultralytics_predict` (inherits `${ultralytics.<key>}`); other families use typed `model.train`/`model.predict`; changed settings in the inactive group are rejected. `model.source_dir` is DEIMv2-only.
- Geometry: RF-DETR square, divisible by 32; DEIMv2 >=128, divisible by 32, square for training; Faster R-CNN/FCOS accept `[height,width]`, round up to multiples of 32 keeping aspect, pad right/bottom. MPS unsupported.
- Faster R-CNN/FCOS train with AdamW, gradient accumulation, EMA. Non-YOLO checkpoints embed a descriptor (backend, preset, classes, preprocessing, versions, source revision); `<checkpoint>.model.json` (with SHA-256) and `<checkpoint>.identity.json` must agree and travel with it.
- Init: `pretrained=true` without weights prepares the backbone (RF-DETR: full detector); explicit `weights`/`backbone_weights` win even with `pretrained=false`; both null and `pretrained=false` is random init; RF-DETR rejects `backbone_weights`; Faster R-CNN/FCOS load full weights strictly.
- `model.predict` (non-YOLO): `device null`, `batch 1`, `imgsz null` (checkpoint size), `conf 0.001`, `iou 0.7`, `max_det 300`, `half false`; DEIMv2/RF-DETR reject nondefault `iou` and `half=true` (no NMS).

## Augmentation

- `transforms=default` keeps native augmentation. `transforms=albumentations transforms.pipeline_file=FILE` applies an `A.save` JSON (root Compose; `bbox_params` only on root, default `pascal_voc` with `class_labels`) to training only, disables optional native augmentation and keeps final resize/tensor/normalization; overrides in `model.train.augmentation`.
- Rejected: `Normalize`, `ToFloat`, `FromFloat`, `ToTensorV2`, `ToTensor3D`, `Lambda`, `additional_targets`, `keypoint_params`, non-box spatial transforms, non-RGB outputs, unknown classes/args; `A.Mosaic` only once as first root transform (donors from the current training population).
- The validated pipeline is frozen as `transforms.snapshot` with a SHA-256 of canonical JSON; DDP ranks and replay use the snapshot; editing the file does not change it.

## Prediction and validation

- YOLO predict defaults `conf=0.001`, `batch=1`, `rect=true`, `save=false`, `verbose=false`, `device=[-1]`; `batch=-1` rejected. Requested/effective settings in `ultralytics_predict_requested.yaml`/`ultralytics_predict.yaml`.
- `weights`: local file, 32-char ClearML task ID (best model) or `clearml://<model id>` (SHA-256 must match). Without provenance a `model_label` is required. A checkpoint changing mid-prediction fails.
- Prediction CSV columns exactly `image_name, instance_label, confidence, bbox_x_tl, bbox_y_tl, bbox_x_br, bbox_y_br` (original pixels); every requested image must yield a result. `image_name` modes `name` (default; unique basenames required), `stem`, `path`; only `name` can be evaluated.
- `<predictions>.csv.provenance.json` binds bytes SHA-256, checkpoint SHA-256 and naming mode; stale or contradictory sidecars fail; a missing one is accepted only if all names are canonical GT basenames.
- `cy-val` predicts val plus requested splits into `<output_dir>/predictions.csv`, calibrates on val, scores under `<output_dir>/metrics`, one task, never trains, no FiftyOne.

## Evaluation and metrics

- Thresholds calibrate only on `val` (`calibration_split` must be `val`; `evaluation.confidence_optimization` `per_class|global`) and are frozen for every split; val and test must not share an image; `evaluation.backend` stays `null`, `evaluation.skip_cohen_kappa` stays `true`.
- Defaults: `evaluation.iou_threshold 0.5`, `matching_strategy iou_prior` (`greedy|hungarian|iou_prior`), `ap_method interp` (`interp|continuous`), `preprocess false`, `preprocess_preds_*` null.
- Order: read CSVs, assign `source_row_id`/`object_id`; validate splits and names; dedupe GT only with `preprocess=true`; geometry filter in memory (reasons `missing`, `nonnumeric`, `nonfinite`, `reversed_corners`, `zero_area`); optional pred preprocessing. Prediction-only classes count as FP.
- Fixed-threshold TP/FP/FN/confusion use prepared predictions; AP and PR use geometry-valid predictions before preprocessing.
- Reconstructed AP50 per class must equal the library's AP50 or evaluation fails. Unavailable values stay NA, never zero. Thresholds are written to `metrics_best_confidences_val.csv` (17 significant digits).
- Per split: `full_dashboard_<split>.xlsx`, `метрики_дтрк_<split>.xlsx`, `matrix_<split>.xlsx`, four CI plots, `evaluation_<split>.json`, `metrics_evaluation_<split>.xlsx` plus sibling CSVs. Row statuses `TP`, `FP`, `FN`, `background`, `filtered`, `excluded`, `not_evaluated`.
- Computation errors fail standalone commands but become a warning completion inside a pipeline whose training succeeded; invalid geometry alone never fails.

## Comparison

- `cy-compare` takes `baseline_model` and `candidate_model` refs (`source` clearml|local, `task_id`, `project_name`, `task_name` regex, `tags` default `[prod]`, `weights`, `thresholds`, `label`, `backend`/`preset`, `class_names`, `preprocessing`, `source_dir`). Automatic baseline: latest completed `prod` task except the current one; only it may be absent. A `candidate_model` that holds only default values is rejected with a `ValueError` naming the keys to set (`task_id`, `project_name`/`task_name`/`tags`, or `source=local` with `weights` and `thresholds`); the check runs in the command preflight, which also validates the `candidate_model` fields, and in `compare()`, both before the ClearML task is created. A candidate that differs from the defaults only in `thresholds`, `label`, `backend`/`preset`, `source_dir`, `class_names` or `preprocessing` passes and resolves like the automatic baseline; `candidate_model.project_name=<project>` selects the latest `prod` task of a project explicitly. `cy` builds its candidate in code and is not affected.
- Both checkpoints are re-inferred with shared predict settings (cache `<role>_predictions_<split>_<digest>.csv`, `inference.reuse_existing=true`); precision by image-level bootstrap, recall by exact McNemar, Benjamini-Hochberg over split hypotheses (`q=0.05`, `bootstrap_iterations=10000`, `seed=0`); output `compare_workbook_<split>.xlsx`.
- Model recovery: unique `best`-tagged Output Model, else unique `best.pt|.pth|.ckpt`, else last registered (warning). Threshold artifacts searched `metrics_best_confidences_val`, `best_confidences_val`, `metrics_best_confidences_test`, `best_confidences_test`, then dashboards; checkpoint SHA-256 must match.
- No baseline: candidate-only `compare_evaluation_candidate_<split>.xlsx`, `comparison_status` skipped, and `cy` skips report.

## Reports

- `cy-report` reads `comparison_manifest.json` from `comparison_dir`, uses per-model full dashboards, writes `report_dev_<split>.xlsx` and `report_business_<split>.xlsx`; deltas are candidate - baseline.
- Eligibility: training count >= `min_train_count` (20; changeable via `report_config_path`); others go to `Удаленные классы`. Training counts come from the evaluated checkpoint's own training population (verified by SHA-256), never from evaluation data.
- Unknown training counts go to `Unknown training count` and `Report issues` sheets, are excluded from aggregates and give a warning outcome, never a failure.
- Business workbook (the single report-generator business layout): the model and comparison sheets show only `Класс`, `tp`, `fp`, `fn`, `Порог`, `precision`, `recall`, `f1_score`, `Перебраковка, %`, `Недобраковка, %`, the four goal columns and `Число примеров test`/`train`/`val`, in that order. A listed column absent from both dashboards is omitted, except `Число примеров train`, which is always present (a dashboard without a training count has only unknown-count rows); no other dashboard column appears, including the unsplit `Количество примеров`; `business.column_translations` renames the remaining headers. Cells are computed values, never formulas.
- Business `Среднее`: `NA` for columns in `excluded_from_mean` (of the shown columns `tp`, `fp`, `fn`, `Порог` by default), the sum over the model's own eligible classes for example counts whatever that list says, the mean for the rest. Business `Сравнение`: candidate - baseline for every column, `NA` when either operand is missing; its `Среднее` aggregates the differences over shared classes (sum for example counts); only `precision`, `recall`, `f1_score` and the two percentage columns are coloured; the legend is `Легенда:` plus four text lines in column A.
- The business population note is five rows in column A on the model, comparison and verdict sheets, one empty row below the content; the identity footer starts one empty row below it. The business workbook has no `... coverage` columns and no `Valid class counts` rows. The developer workbook shows its availability rows below each table.
- Visible cells show names and roles, never IDs or digests; identities and the exact original workbook live in hidden metadata; an annotated workbook edited afterwards fails ingestion; historical workbooks are never rewritten.

## ClearML publication

- Each experiment command owns exactly one task (`reuse_last_task_id=False`); workers and DDP ranks never create tasks or upload. Success requires every upload confirmed and read back; Output Models are re-downloaded and SHA-256 compared; uncertain deliveries are never retried.
- Defaults `clearml.project_name=clearml-yolo`, `task_name=yolo-run`, `task_type=training`, `tags=[]`, `output_uri=true` (`null`, `false`, `""` rejected); best model tagged `best`. Display names are unique per project with `-<adjective>-<noun>` suffixes (20 attempts), recorded in `run.display_names`.
- The `run` Configuration Object is the only replay/cache input; `run_overrides`, `model_assets`, `export_result` are provenance only. Agent replay reads one remote snapshot, applies `run`, and for YOLO applies `General` overrides unless `batch=null`; explicit outputs must stay in the Agent's `CY_HOME`.
- Local tasks record entry `-m clearml_yolo.entrypoints.<stage>`, working dir `.`, sanitized origin, branch, commit, no diff.
- Artifacts: `gt_csv`, `predicts_csv`, `metrics_best_confidences_val`, `metrics_dashboard_full_<split>`/`_dtrk_<split>`, `comparison_<role>_dashboard_full|dtrk_<split>`, `compare_workbook_<split>[_excluded]`, `report_dev_<split>`, `report_business_<split>`, `pipeline_outcome`, `export_*`; repeated names get `_2`, `_3`.
- Thresholds go only onto the invocation's own verified model as metadata `clearml_yolo_confidence_thresholds`, `clearml_yolo_confidence_threshold/<class>`, `clearml_yolo_calibration_split=val`, `clearml_yolo_calibration_checkpoint_sha256`.
- Each finalization SDK step has its own 600 s main-thread `ITIMER_REAL` alarm. An owner that does not confirm closure quarantines the process (`Previous ClearML owner did not confirm closure; ...`). Workaround for Linux `Task.query_tasks` `tasks is None`: `sdk.development.report_use_subprocess = false`.
- Controller caching: register `ClearmlJob.register_hashing_callback(normalize_task_hash)` from `clearml_yolo.adapters.clearml.cache` and pass `configuration_overrides={"run": json.dumps(run, ensure_ascii=False)}`.
- Credentials never enter configuration, failure status (`<error type>: invocation failed; see local diagnostics for details`) or logs; raw native stdout/stderr is not redacted.

## FiftyOne publication

- For `cy`, `cy-predict`, `cy-metrics`; `fiftyone.enabled` (default true), `preflight_timeout_seconds 60`, `publish_timeout_seconds 900`, `lock_timeout_seconds 30`, `dataset_prefix clearml-yolo`. Runs in a bounded worker without GPU, queue or task ownership; failures only warn; cancellation propagates. `fiftyone=null` is rejected by the direct commands before the task is created and by cy-queue admission, with a hint to use `fiftyone.enabled=false`; the Python API default `fiftyone=None` and a removed group (`~fiftyone`) still mean defaults. A saved configuration with `fiftyone: null` (a replayed `run` or a saved YAML) fails with the same message; replace it with `fiftyone.enabled=false`.
- Dataset `<dataset_prefix>-v1-<GT SHA-256>`; run fields `run_<sha256(task id)>`; one native evaluation per split (method `digital_metrics`) from CY's matches. Receipt `fiftyone_publication.json` in the output dir, not uploaded. `FIFTYONE_DATABASE_DIR` holds publication locks.
- App extension `@clearml-yolo/evaluation` installs only via `clearml_yolo.adapters.fiftyone.panel.install_evaluation_plugin()`, into the environment that runs the FiftyOne server; restart the App afterwards.
- Open a published dataset with the same database (bundled MongoDB or `FIFTYONE_DATABASE_URI`, shared `FIFTYONE_DATABASE_DIR`) and SDK config, with media paths readable: `fo.launch_app(fo.load_dataset(<"dataset_name" from fiftyone_publication.json>))`.

## Model assets

- `cy-download-weights` and the automatic pass before `cy` restore assets only from the pinned `weights-*` GitHub Release in `src/clearml_yolo/adapters/assets/weights-manifest.json` (via `GHR`, then public GitHub); DEIMv2 `l`/`x` excluded from bulk; completion records in `CY_HOME/.cache/clearml-yolo/preparation/`; automatic failures only warn.
- Selected models: local/cached files, then proxies (`GHR` Artifactory Files remote, `GH` VCS remote, `HF_ENDPOINT`), then original URL; two attempts per route. Explicit `model.train.weights`, `backbone_weights`, `model.source_dir` are authoritative. DEIMv2 source revision `1d2ca42171570c713e78fc6a766ec5104b7f4724` with clean `engine/` and `configs/`.
- Limits: `CY_WEIGHTS_DOWNLOAD_TIMEOUT` (default 1800 s per archive attempt), inactivity 10/30 s, selected-model downloads 300 s and 4 GiB. Credentials per host in `~/.netrc` (0600); private CAs via `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`. Never disable checksum, size or TLS checks.
- DEIMv2 `l`/`x` without a local Meta backbone convert the pinned HF snapshot (`facebook/dinov3-vits16-pretrain-lvd1689m` / `...vits16plus...`) into `hf-dinov3-to-deim-v1.pth`. Resolved assets are published as `model_assets`; `run` keeps the selectors.
- Only preparation passes and YOLO batch-estimator setup persist Ultralytics `weights_dir` (locked, read back); imports, help and config inspection never touch Ultralytics settings.

## Batch estimation

- `batch=null` reads `CY_HOME/.config/clearml-yolo/batch-sizes.yaml` keyed by GPU `Name [N GiB]`, square imgsz and canonical model (`ultralytics/yolo11n`): exact entry, else largest smaller-or-equal memory GPU; global batch = GPU count x smallest per-GPU batch. Keep the `# clearml-yolo-batch-metadata:` comment. CPU/MPS, non-square and custom YOLO need explicit batch.
- `cy-batch-estimate --imgsz N`: strategy `memory_guided_small_batches_v1`; defaults `--objects-per-image 300`, `--memory-budget 0.9`, `--search-limit 1024`, `--trial-timeout 300`; statuses `validated`, `ceiling_limited`, `numerically_limited`, `no_capacity`, `failed`; exit 1 unusable, 2 invalid args; evidence `batch-estimates.json` (schema 3), never read by training.

## Export

- `cy-export` (Faster R-CNN only) runs one `export.operation`: `onnx` (CPU fp32, opset 17, bakes `conf`/`iou`/`max_det`), `build` (one GPU, fp32/fp16, `ROIAlign_TRT` v2, `export.workspace_gib=4`), `verify` (mAP50-95 loss <= 0.001 FP32 / 0.005 FP16 on `export.split=test`). Sidecars `<artifact>.json`; never rewrite them; no Output Model.
- TensorRT profiles: full frames min `(1,3,608,960)` opt `(2,3,608,960)` max `(4,3,736,960)`; strips min `(1,3,128,1536)` opt `(2,3,256,1920)` max `(4,3,256,1920)`; H, W divisible by 32. `TensorRTRunner` needs TensorRT 10.13.0 and `ROIAlign_TRT:2`, no Torch/ClearML.

## Process ownership

- Linux only: child subreaper, PID+start-time identity and pidfds. Every command terminates what it launched (SIGTERM, SIGKILL after 2 s, two clean scans, 10 s bound); never signals unproven processes; cleanup failure is raised together with the workflow error. SIGTERM exits 143.
- Multi-GPU ranks and batch trials run in their own sessions; any rank failure or deadline terminates peers. Probe: `python -c 'from clearml_yolo.adapters.runtime.process_tree import require_process_supervision; require_process_supervision()'`.

## Queue

- `cy-queue` is a separate package depending on CY; CY never imports it, Textual or NVML. `cy-queue submit` needs exactly one of `--gpus N`/`--devices LIST`, freezes a snapshot, one job per sweep combination; GPUs admissible below `queue.max_used_memory_gib` (2.0); after training a pipeline shrinks to the first GPU.
- Config TOML `$XDG_CONFIG_HOME/clearml-yolo/queue.toml` (override `CY_QUEUE_CONFIG`) with `[queue] name`, `root`, `coordination_root`. Logs `<project>/.cy/queue-logs/JOB_ID.log`, progress `<project>/.cy/queue-status/JOB_ID.json`. Install: `uv pip install --python .venv/bin/python -e . -e ../cy-queue`. Queue internals are documented in the cy-queue repository.
- Administrator rules: `name`, `root` (job metadata) and `coordination_root` (locks, reservations, workers) are required absolute paths identical for every user of a queue, never under `CY_HOME`; `max_used_memory_gib` positive finite, applied on worker restart. `cy-queue config [--json]` validates without creating anything.
- One coordination root is bound per host (under `/tmp/clearml-yolo-queue`); moving it is an offline procedure. `root` may be on NFS with consistent UIDs; `coordination_root` must be host-local with `flock` or NFS mounted `hard`, `local_lock=flock|all`, shared cache. Each host needs a distinct machine identity; participants on a host share its mount, PID namespace and bootstrap.

## Diagnostics

- Every Hydra command redirects fds 1/2 to append-only `<arena>/logs/stdout.log`, `stderr.log`, `scalars.jsonl`; a mirror renders readable identifiers; a publisher sends console/scalars about every 2 s (8 s barrier).
- `LOGURU_LEVEL=TRACE` adds `START`/`DONE`/`FAILED`/`INTERRUPTED` records and a watchdog (`TRACE ACTIVE` 30 s, `TRACE STACK snapshot` 60 s) on stderr. `CY_PROGRESS_FILE` (inside `CY_HOME`) holds `progress`, `iteration`, `task_url`.

## Filesystem and cache deduplication

- `CY_HOME` (default launch dir) is frozen absolute before composition; every project write must resolve beneath it (`Project write destination <path> must be contained beneath CY_HOME=<root>`). CY never changes HOME, XDG, TMP or library cache selectors.
- Layout: `runs/`, `outputs/`, `multirun/`, `.cache/clearml-yolo/{datasets,models,sources,preparation}/`, `.config/clearml-yolo/{batch-sizes.yaml,batch-estimates.json}`, `.tmp/cy-runtime-*` (arenas under `CY_RUNTIME_TEMP_ROOT`, never cleaned automatically), `.cy/queue-*`.
- `cy-dedup [DIRECTORY] [--dry-run]` (default `CY_HOME/.cache`) reflinks (FICLONE) identical image files with equal name, size, SHA-256 and bytes; no fallback; exit 0 ok, 1 failure, 2 usage; outside `CY_HOME` only with `--dry-run`.

## Installation and dependencies

- Python `>=3.12.13,<3.14`, Linux with pidfd APIs; ClearML server with remote storage is required; no extras; not on PyPI. Commands never install packages at run time.
- `digital-metrics` (`6e801be1564dce458294eb23592cc1aa0939c4d9`, github.com/Wasilkas/digital-metrics) and `report-generator` (`4fd58628670da7f98a896d41eb149e7bf6a9b110`, github.com/Wasilkas/report-generator) are ignored copies under `external/`. `pyproject.toml` declares them by version; `uv.lock` records `source = { registry = "external/wheelhouse" }` and does not enforce revisions. Git-link installs resolve both from the user's index.
- `task local-deps` builds sdists into `external/wheelhouse` and creates `uv.toml` with `find-links = ["external/wheelhouse"]`; it never overwrites `uv.toml` and fails if the entry is missing. When a checkout is missing it names the `external/` paths and the rerun command.
- Changing a dependency floor: test an isolated `lowest-direct` resolution on each supported minor, separate from `uv.lock`.

## Release

- `.github/workflows/release.yml` runs on `pull_request_target` `closed` for PRs merged into `master` and runs `python -m scripts.release`: `semantic-release version --no-push --no-vcs-release`, build command `python -m scripts.release_metadata` (root version in `uv.lock`, `project.version`, `CHANGELOG.md`), validation of one `chore(release): <version>` commit (`scripts/release_lock_guard.py`) and annotated `v<version>` tag, then `git push --atomic --no-follow-tags`.
- Recovery: inspect `git ls-remote origin refs/heads/master 'refs/tags/v*'`, then `gh run rerun <run-id>` (published releases rerun as no-op). Never overwrite, move or delete tags; investigate conflicting tags.
- Weight releases (only on explicit request): `uv run --frozen --no-sync python scripts/package_weights.py --output ./weight-release --tag weights-YYYY-MM-DD --notices ./weight-notices` (empty output dir; `--max-archive-bytes` default 1,900,000,000) writes `weights-NNN.tar`, `deim-noncommercial-NNN.tar`, `manifest.json`, `SHA256SUMS`. Publish under a new tag marked Latest, never replace bytes, then update `weights-manifest.json` in a code PR. Notices: every upstream licence, AGPL source directions, DEIMv2 non-commercial restriction, DINOv3 agreements and model card, "Built with DINOv3" in notes.
- `task paired-check` installs CY and cy-queue (`CY_QUEUE_DIR`, default `../cy-queue`, clean and containing its latest remote default branch) into a temporary venv under `.tmp/`, runs `uv pip check`, `scripts/paired_metadata.py check`, the queue's Ruff, mypy, `lint-imports`, pytest and `cy-queue --help`, and refuses if sources changed.

## Live test environment

- `tests/integration/lifecycle.py` creates a namespace `cy-it-<6 hex>` on the `docker-desktop` Kubernetes context with ClearML and FiftyOne via loopback port-forwards (no web UI, no Agent). `infra-check` exits 0 available, 3 unavailable, 1 error. Ownership record: `tests/integration/.run-tag`; `INTEGRATION_KEEP_DATA=1` keeps it (48-hour lifetime).
- Severstal suite: `--run-severstal-gpu`, `--severstal-dataset` (from `scripts/severstal.py`, seed-0 160/40/40 subset), `--severstal-artifacts`, `--severstal-clearml-project`, `--severstal-tags`, `--severstal-device`, `--severstal-free-vram-mib`, `--severstal-timeout` (1800 s). Each scenario trains two FP32 epochs with the largest valid batch (cap 160) and checks execution, reload, predictions and ClearML records, not accuracy.
- Not automated, check by hand when affected: native CPU/GPU and queued runs, publication readback with forced downloads, `cy-batch-estimate --imgsz 640 --models <model> --devices <index> --search-limit 3` with an isolated `CY_HOME`, chart HTML, FiftyOne App views, detector-family and export matrices.

## Glossary

- Canonical run: complete frozen executable inputs, the replay input. Provenance: origin evidence and hashes supplementing it. Scientific result: prediction, metric, comparison or report tied to its sources.
- Invocation owner: the execution owning one task, its publications and descendant cleanup. Identity footer: readable model identity after a report's data.
- Change acceptance = `task acceptance`; release acceptance = `task release-acceptance`. Paired release check: CY and cy-queue proposed versions pass together (avoid "release check").
- Decisions have no ADR or decision ids; they live in the Linear issue that made them and in this file.

## History

The full pre-compression documents are in git at commit `4c5a9d5`; read one with
`git show 4c5a9d5:<path>` (for example `git show 4c5a9d5:docs/development.md`). Removed
top-level paths: `CLAUDE.md`, `GLOSSARY.md`, `docs/` (`docs/feature/*.md`,
`docs/development.md`, `docs/architecture.md`, `docs/agents/`), `.agents/skills/`,
`.claude/skills`, `.pre-commit-config.yaml`, `scripts/git-hook.sh`, `scripts/install-hooks.sh`.
The current `GLOSSARY.md` and `docs/` are the user glossary and user documentation written after
that commit, not the removed files.
