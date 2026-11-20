# Glossary

Terms that `clearml-yolo` (CY) defines or narrows. Each entry gives the Russian wording the user documentation uses. Terms that the documentation keeps in English (split, preset, backend, baseline, multirun and the others listed in the documentation rules) appear here only when CY gives them a narrower meaning.

## Workspace and runs

<a id="workspace"></a>
**Workspace**:
The directory named by `CY_HOME` (the current directory when it is unset). Every file CY writes for a run lives under it.
_Russian_: рабочий каталог
_Avoid_: домашний каталог, корень проекта

<a id="write-containment-rule"></a>
**Write containment rule**:
The rule that every destination a run writes to (run directory, output paths, caches, Hydra directories, `CY_RUNTIME_TEMP_ROOT`) must resolve inside the workspace; a path outside it stops the command with `Project write destination ... must be contained beneath CY_HOME=...`. Input files may live anywhere.
_Russian_: правило записи внутри `CY_HOME`
_Avoid_: песочница, ограничение путей

<a id="run-directory"></a>
**Run directory**:
The directory of one ClearML task under `CY_HOME/runs/<project>/<task name>-<task ID>/`, or the one given by `run_dir` or `run_id` in `cy`. A stage writes its outputs inside it.
_Russian_: каталог запуска
_Avoid_: папка эксперимента, output-каталог

<a id="training-directory"></a>
**Training directory**:
The Ultralytics project directory where `cy-train` and the training stage of `cy` write checkpoints; `detect/` inside the run directory unless `ultralytics.project` is set.
_Russian_: каталог обучения
_Avoid_: каталог весов

<a id="hydra-output-directory"></a>
**Hydra output directory**:
The directory Hydra creates for each launch of a Hydra command, under `CY_HOME/outputs/` for a single run and `CY_HOME/multirun/` for a sweep. It holds the composed configuration and the Hydra log; CY does not read it back.
_Russian_: каталог Hydra
_Avoid_: каталог запуска (that is the run directory)

<a id="runtime-scratch-directory"></a>
**Runtime scratch directory**:
The `.tmp/cy-runtime-*` directory each command process creates under the workspace (under `CY_RUNTIME_TEMP_ROOT` when it is set) for temporary files and, for Hydra commands, the captured logs. CY never deletes it.
_Russian_: временный каталог (`.tmp/cy-runtime-*`)
_Avoid_: кэш

<a id="multirun-tag"></a>
**Multirun tag**:
The ClearML tag `multirun-<UTC stamp>-<six words>` that CY appends to `clearml.tags` of every job of one Hydra sweep.
_Russian_: тег multirun
_Avoid_: тег sweep, тег запуска

## Pipeline

<a id="pipeline"></a>
**Pipeline**:
The chain of stages that the `cy` command runs inside one ClearML task: training, prediction, metrics, comparison, report.
_Russian_: пайплайн
_Avoid_: конвейер, workflow

<a id="stage"></a>
**Stage**:
One step of the pipeline. Each stage can also be run alone by its own command (`cy-train`, `cy-predict`, `cy-metrics`, `cy-compare`, `cy-report`).
_Russian_: этап
_Avoid_: шаг, фаза

<a id="pipeline-outcome"></a>
**Pipeline outcome**:
The status `cy` records for every stage (`succeeded`, `completed_with_warnings`, `failed`, `skipped`) and for the run as a whole (`succeeded`, `completed_with_warnings`, `failed`) in `pipeline_outcome.json` and `pipeline_outcome.txt`. A failed stage after successful training gives `completed_with_warnings`.
_Russian_: итог пайплайна
_Avoid_: результат пайплайна, статус запуска

## Models and weights

<a id="detector-family"></a>
**Detector family**:
A model library CY can train and run, selected by `model.backend`: `ultralytics`, `deimv2`, `rfdetr`, `fasterrcnn`, `fcos`. Each family has its own presets, settings and checkpoint format.
_Russian_: семейство моделей
_Avoid_: фреймворк, тип модели, семейство детекторов

<a id="model-provenance"></a>
**Model provenance**:
What CY knows about where a checkpoint came from: the ClearML task or model it was taken from, or the `.identity.json` file next to a local checkpoint. When provenance is unknown, the command needs `model_label`.
_Russian_: происхождение модели
_Avoid_: источник весов

<a id="checkpoint-descriptor"></a>
**Checkpoint descriptor**:
The detector family, preset, class names and preprocessing that training embeds in a DEIMv2, RF-DETR, Faster R-CNN or FCOS checkpoint, and writes with the checkpoint's SHA-256 to `<checkpoint>.model.json` beside it. Commands that read such a checkpoint require it and check the `model` selection against it.
_Russian_: описание модели
_Avoid_: дескриптор, метаданные checkpoint

<a id="model-identity"></a>
**Model identity**:
The label of a model and its training source that CY writes into the footer and the hidden metadata of a workbook, and reads back to check that the workbook was not changed.
_Russian_: подпись модели
_Avoid_: метка модели, имя модели

<a id="model-reference"></a>
**Model reference**:
The `baseline_model` or `candidate_model` group of `cy-compare` (also `compare.baseline_model` in `cy`): either a ClearML lookup (`source=clearml`) or local weights with explicit thresholds (`source=local`).
_Russian_: ссылка на модель
_Avoid_: дескриптор модели

<a id="output-model"></a>
**Output model**:
The best checkpoint that training registers as a ClearML model of the task, with CY metadata such as its SHA-256 and, after the metrics stage of `cy`, the confidence thresholds.
_Russian_: выходная модель
_Avoid_: опубликованная модель

<a id="weight-mirror"></a>
**Weight mirror**:
An HTTP proxy for GitHub release files (`GHR`) or GitHub sources (`GH`) that CY tries before the original URL when it downloads weights.
_Russian_: зеркало весов
_Avoid_: прокси, artifactory

<a id="native-cache"></a>
**Native cache**:
The directory where a model library keeps its own downloaded weights (for example the Ultralytics weights directory or the Hugging Face cache), as opposed to CY's caches under `.cache/clearml-yolo`.
_Russian_: родной кэш
_Avoid_: системный кэш

<a id="batch-size-table"></a>
**Batch size table**:
The editable file `.config/clearml-yolo/batch-sizes.yaml` that maps a GPU, image size and model to a batch size. `cy-batch-estimate` writes it; training reads it when `batch` is `null`.
_Russian_: таблица batch size
_Avoid_: таблица батчей

## Data

<a id="ground-truth"></a>
**Ground truth**:
In CY, a CSV file with one row per bounding box (or per image without objects) and a `split` column, or a ClearML dataset that holds such a file. It is the only label format the commands read; `cy-ground-truth` builds it from a YOLO dataset.
_Russian_: разметка (ground truth)
_Avoid_: аннотации, лейблы

<a id="image-without-objects"></a>
**Image without objects**:
A ground truth row with an empty `instance_label` and empty box columns. It keeps an image that has no objects in its split.
_Russian_: изображение без объектов
_Avoid_: фоновая строка, пустая строка

<a id="clearml-dataset-reference"></a>
**ClearML dataset reference**:
A `ground_truth` value written as a mapping (`{dataset_id: ...}` or `{project_name: ..., name: ..., version: ...}`) instead of a path. CY downloads the dataset and reads its root `dataset.csv`.
_Russian_: ссылка на ClearML Dataset
_Avoid_: ID датасета

<a id="prepared-dataset-copy"></a>
**Prepared dataset copy**:
The copy of the ground truth and images in the layout a detector family trains from (`ndjson`, `flat` or `coco`), which CY builds once under `dataset_cache_dir` and reuses while the inputs are unchanged.
_Russian_: рабочая копия датасета
_Avoid_: кэш датасета, экспорт датасета

## Augmentation

<a id="transforms-profile"></a>
**Transforms profile**:
A choice in the `transforms` group: `default` keeps each family's built-in augmentation (`transforms.mode=native`), `albumentations` replaces it with a pipeline file (`transforms.mode=albumentations`).
_Russian_: профиль
_Avoid_: режим аугментации

<a id="augmentation-pipeline-file"></a>
**Augmentation pipeline file**:
The Albumentations JSON file named by `transforms.pipeline_file`.
_Russian_: файл пайплайна
_Avoid_: конфиг аугментаций

<a id="pipeline-snapshot"></a>
**Pipeline snapshot**:
The content, SHA-256 and source path of the augmentation pipeline file that CY stores in `transforms.snapshot`, so the run can be repeated without the original file.
_Russian_: снимок пайплайна
_Avoid_: копия пайплайна

## Evaluation, comparison and reports

<a id="candidate-model"></a>
**Candidate model**:
The model `cy-compare` tests against the baseline (`candidate_model`); in `cy`, the model trained by the run.
_Russian_: модель-кандидат
_Avoid_: новая модель

<a id="baseline"></a>
**Baseline**:
The model the candidate is compared with (`baseline_model`). By default, the latest completed ClearML task tagged `prod` in the run's own ClearML project.
_Russian_: baseline (модель baseline)
_Avoid_: базовая модель, прод-модель

<a id="degraded-class"></a>
**Degraded class**:
A class with a metric (precision or recall) that is significantly worse for the candidate than for the baseline after the Benjamini-Hochberg correction over every class and metric of the split; the comparison verdict `degraded`.
_Russian_: деградация
_Avoid_: ухудшение, регрессия

<a id="selected-confidence-thresholds"></a>
**Selected confidence thresholds**:
The confidence thresholds the metrics stage selects once on the `val` split (`calibration_split` accepts only `val`), per class or global by `evaluation.confidence_optimization`, and then applies unchanged to every split. They are written to `metrics_best_confidences_val.csv` and, in `cy`, attached to the output model.
_Russian_: подобранные пороги
_Avoid_: оптимальные пороги, лучшие пороги

<a id="comparison-manifest"></a>
**Comparison manifest**:
The `comparison_manifest.json` file `cy-compare` writes into its output directory; `cy-report` reads it to find the comparison workbooks.
_Russian_: манифест сравнения
_Avoid_: индекс сравнения

<a id="dashboard"></a>
**Dashboard**:
The metrics workbooks `full_dashboard_*` and `метрики_дтрк_*` that the metrics and comparison stages write and publish as `*_dashboard_full_*` and `*_dashboard_dtrk_*` artifacts.
_Russian_: дашборд
_Avoid_: панель

## Publication

<a id="configuration-object"></a>
**Configuration object**:
A named ClearML task configuration entry that CY publishes (`run`, `run_overrides`, `model_assets`, `dataset`, `report`). Results such as `source_model` and `export_result` are sections inside `run`, not objects of their own.
_Russian_: объект конфигурации
_Avoid_: гиперпараметры

<a id="fiftyone-preflight"></a>
**FiftyOne preflight**:
The check CY runs in a separate process without a GPU before it publishes to FiftyOne; a failure turns publication off for the run with a warning.
_Russian_: предварительная проверка
_Avoid_: health check

<a id="run-key"></a>
**Run key**:
`run_<SHA-256 of the task ID>`, the suffix of the per-run fields CY adds to a FiftyOne dataset.
_Russian_: ключ запуска
_Avoid_: ID запуска

<a id="publication-receipt"></a>
**Publication receipt**:
The `fiftyone_publication.json` file CY writes next to the outputs after it publishes to FiftyOne.
_Russian_: квитанция
_Avoid_: отчёт о публикации

## Export

<a id="tensorrt-engine"></a>
**TensorRT engine**:
The `model.engine` file that `cy-export export.operation=build` builds from the ONNX graph on one GPU.
_Russian_: движок TensorRT
_Avoid_: engine-файл

<a id="export-metadata"></a>
**Export metadata**:
The JSON file next to an exported graph or engine (`model.onnx.json`, `model.engine.json`) with the model description, hashes, thresholds, optimization profiles and library versions. `build` and `verify` check their inputs against it.
_Russian_: метаданные экспорта
_Avoid_: манифест экспорта

<a id="optimization-profile"></a>
**Optimization profile**:
A range of batch and image sizes that a TensorRT engine accepts, recorded in the export metadata.
_Russian_: профиль размеров
_Avoid_: профиль оптимизации

## Cache maintenance

<a id="reflink-clone"></a>
**Reflink clone**:
A copy-on-write file copy that shares disk blocks with its source. `cy-dedup` replaces duplicate images with reflink clones and never with hard links or copies.
_Russian_: reflink-клон
_Avoid_: жёсткая ссылка
