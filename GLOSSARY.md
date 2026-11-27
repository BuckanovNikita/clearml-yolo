# Glossary

Use these definitions and Russian wordings when describing clearml-yolo (CY). In Russian prose, keep checkpoint, batch size, split, baseline, preset, backend, IoU, override, multirun, sweep, seed, GPU, CPU, ONNX, TensorRT, YAML, JSON and CSV in English. Preserve command, flag, configuration key, file, column and environment variable names as written.

| Workflow | Start with these terms |
| --- | --- |
| Build and deploy a detector | [Ground truth](#ground-truth), [prepared dataset copy](#prepared-dataset-copy), [detector family](#detector-family), [checkpoint descriptor](#checkpoint-descriptor), [TensorRT engine](#tensorrt-engine) |
| Evaluate checkpoints and compare models | [Prediction provenance](#prediction-provenance), [threshold calibration](#threshold-calibration), [candidate model](#candidate-model), [baseline](#baseline), [comparison manifest](#comparison-manifest) |
| Operate experiments | [Workspace](#workspace), [pipeline](#pipeline), [ClearML task](#clearml-task), [configuration object](#configuration-object), [publication receipt](#publication-receipt) |

## Workspace and runs

<a id="workspace"></a>
**Workspace**:
The directory named by `CY_HOME` (the current directory when it is unset). Every file CY writes for a run lives under it.
_Russian_: рабочий каталог
_Avoid_: домашний каталог, корень проекта

<a id="write-containment-rule"></a>
**Write containment rule**:
Every project write, including outputs, caches and runtime scratch, must resolve inside the workspace. Input files may live elsewhere.
_Russian_: правило записи внутри `CY_HOME`
_Avoid_: песочница, ограничение путей

<a id="run-directory"></a>
**Run directory**:
The directory of one ClearML task under `CY_HOME/runs/<project>/<task name>-<task ID>/`, or the one given by `run_dir` or `run_id` in `cy`. A stage writes its outputs inside it.
_Russian_: каталог запуска
_Avoid_: папка эксперимента, output-каталог

<a id="training-directory"></a>
**Training directory**:
The project directory containing a trainer’s outputs and best checkpoint. By default, it is `detect/` inside the run directory.
_Russian_: каталог обучения
_Avoid_: каталог весов

<a id="hydra-output-directory"></a>
**Hydra output directory**:
The directory Hydra creates for each launch of a Hydra command, under `CY_HOME/outputs/` for a single run and `CY_HOME/multirun/` for a sweep. It holds the composed configuration and the Hydra log.
_Russian_: каталог Hydra
_Avoid_: каталог запуска (that is the run directory)

<a id="runtime-scratch-directory"></a>
**Runtime scratch directory**:
The invocation’s `cy-runtime-*` directory for temporary files and captured Hydra-command logs, under `CY_RUNTIME_TEMP_ROOT` or the workspace’s `.tmp/`. CY retains the directory after the invocation.
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
The chain of training, prediction, metrics, comparison and reporting stages that `cy` runs inside one [ClearML task](#clearml-task).
_Russian_: пайплайн
_Avoid_: конвейер, workflow

<a id="stage"></a>
**Stage**:
One of the pipeline’s operations, such as training or comparison. Each of the five main stages also has a standalone command.
_Russian_: этап
_Avoid_: шаг, фаза

<a id="pipeline-outcome"></a>
**Pipeline outcome**:
The per-stage and overall status that `cy` records in `pipeline_outcome.json` and `pipeline_outcome.txt`. A downstream failure after successful training can produce `completed_with_warnings`. An interrupted run fails.
_Russian_: итог пайплайна
_Avoid_: результат пайплайна, статус запуска

## Models and weights

<a id="detector-family"></a>
**Detector family**:
A group of detectors with a common backend, presets and settings. CY supports Ultralytics YOLO, DEIMv2, RF-DETR, Faster R-CNN and FCOS.
_Russian_: семейство моделей
_Avoid_: фреймворк, тип модели, семейство детекторов

<a id="model-provenance"></a>
**Model provenance**:
Information connecting a checkpoint to its training source, for example a ClearML task or an identity file next to local weights. A user-supplied model label identifies the model when its provenance is unknown.
_Russian_: происхождение модели
_Avoid_: источник весов

<a id="checkpoint-descriptor"></a>
**Checkpoint descriptor**:
The detector family, preset, class names and preprocessing embedded in a DEIMv2, RF-DETR, Faster R-CNN or FCOS checkpoint. Training also writes the descriptor and the checkpoint's SHA-256 to `<checkpoint>.model.json`. A reader can use the embedded descriptor alone and checks the companion file when present.
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
The directory a model library uses to look up downloaded weights, such as the Ultralytics weights directory or the Hugging Face cache.
_Russian_: родной кэш
_Avoid_: системный кэш

<a id="batch-size-table"></a>
**Batch size table**:
The editable `batch-sizes.yaml` table that maps a GPU profile, image size and model to a per-GPU training batch size. Training looks up this value when `batch` is `null`.
_Russian_: таблица batch size
_Avoid_: таблица батчей

## Data

<a id="ground-truth"></a>
**Ground truth**:
The reference labels and split membership supplied as a CSV or a [ClearML dataset reference](#clearml-dataset-reference). The CSV has one row per object box and a membership row for each image without objects.
_Russian_: разметка (ground truth)
_Avoid_: аннотации, лейблы

<a id="image-without-objects"></a>
**Image without objects**:
An image represented in ground truth by a membership row with an empty `instance_label` and empty box coordinates. The word `background` is reserved as a class name.
_Russian_: изображение без объектов
_Avoid_: фоновая строка, пустая строка

<a id="clearml-dataset-reference"></a>
**ClearML dataset reference**:
A `ground_truth` value written as a mapping (`{dataset_id: ...}` or `{project_name: ..., name: ..., version: ...}`) instead of a path. CY downloads the dataset and reads its root `dataset.csv`.
_Russian_: ссылка на ClearML Dataset
_Avoid_: ID датасета

<a id="prepared-dataset-copy"></a>
**Prepared dataset copy**:
The ground truth and images arranged in the native training layout (`ndjson`, `flat` or `coco`). CY can reuse a prepared copy based on the ground truth CSV bytes, ordered image references, format and preparation version. Changing image bytes at the same paths leaves that cache key unchanged.
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

<a id="prediction-provenance"></a>
**Prediction provenance**:
The record accompanying a prediction CSV that identifies its bytes, the image naming mode and the available model or checkpoint identity. It lets evaluation check that the predictions being scored are the ones that were written.
_Russian_: файл `.provenance.json`

<a id="candidate-model"></a>
**Candidate model**:
The model whose results are compared with the baseline. In `cy-compare` it is selected by `candidate_model`. In `cy` it is the checkpoint being evaluated, including when training was skipped.
_Russian_: модель-кандидат
_Avoid_: новая модель

<a id="baseline"></a>
**Baseline**:
The model used as the reference for a comparison. The automatic baseline comes from the latest completed `prod` task in the run’s ClearML project, excluding the current task.
_Russian_: baseline (модель baseline)
_Avoid_: базовая модель, прод-модель

<a id="degraded-class"></a>
**Degraded class**:
A class with a metric (precision or recall) that is significantly worse for the candidate than for the baseline after the Benjamini-Hochberg correction over every class and metric of the split; the comparison verdict `degraded`.
_Russian_: деградация
_Avoid_: ухудшение, регрессия

<a id="threshold-calibration"></a>
**Threshold calibration**:
Selection of confidence thresholds using ground truth and predictions on `val`. Evaluation applies the selected thresholds to the requested splits. In a comparison, each model uses its own thresholds.
_Russian_: подбор порогов уверенности

<a id="selected-confidence-thresholds"></a>
**Selected confidence thresholds**:
The values produced by [threshold calibration](#threshold-calibration), either one per class or one value shared by all classes. CY writes them to `metrics_best_confidences_val.csv` and can attach them to the matching [output model](#output-model) owned by the run.
_Russian_: подобранные пороги
_Avoid_: оптимальные пороги, лучшие пороги

<a id="comparison-manifest"></a>
**Comparison manifest**:
The `comparison_manifest.json` file binding the compared split and the two model roles to their result files. `cy-report` uses it to locate each model’s dashboard.
_Russian_: манифест сравнения
_Avoid_: индекс сравнения

<a id="dashboard"></a>
**Dashboard**:
The metrics workbooks `full_dashboard_*` and `метрики_дтрк_*` that the metrics and comparison stages write and publish as `*_dashboard_full_*` and `*_dashboard_dtrk_*` artifacts.
_Russian_: дашборд
_Avoid_: панель

<a id="training-example-count"></a>
**Training example count**:
The number of annotated objects of a class in the evaluated checkpoint's own training split. Reports use this count to determine whether a class qualifies for that model's aggregates. An unknown count stays unavailable.
_Russian_: число примеров train

## Publication

<a id="clearml-task"></a>
**ClearML task**:
The ClearML record for one experiment invocation. All stages of a `cy` pipeline share one task. Running a stage as a standalone experiment creates its own task.
_Russian_: задача ClearML

<a id="configuration-object"></a>
**Configuration object**:
A named ClearML task configuration entry that CY publishes (`run`, `run_overrides`, `model_assets`, `dataset`, `report`). Results such as `source_model` and `export_result` are sections inside `run`, not objects of their own.
_Russian_: объект конфигурации
_Avoid_: гиперпараметры

<a id="fiftyone-preflight"></a>
**FiftyOne preflight**:
The check of FiftyOne availability before CY publishes a run. If preflight fails, CY skips the optional publication and records a warning.
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
An independent file whose data blocks are initially shared with another file. `cy-dedup` uses this copy-on-write representation for identical cached images.
_Russian_: reflink-клон
_Avoid_: жёсткая ссылка
