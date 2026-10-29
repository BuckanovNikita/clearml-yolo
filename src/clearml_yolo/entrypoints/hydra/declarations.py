"""Documented command declarations projected onto permissive Hydra configurations.

The named dataclasses own defaults and documentation. They deliberately use Any:
Hydra historically allowed composition before runtime request validation. Registering
strict dataclass annotations would change existing YAML and replay compatibility.
"""

# ruff: noqa: RUF001 -- Public configuration documentation is intentionally Russian.

from dataclasses import dataclass, field, fields
from typing import Any

from hydra_zen import builds, make_config
from omegaconf import MISSING

from clearml_yolo.adapters.yolo.config import native_defaults, prediction_defaults, stage_settings
from clearml_yolo.application.contracts import ClearMLConfig, ModelRef
from clearml_yolo.core.evaluation.models import EvaluationConfig
from clearml_yolo.core.export_requests import ExportSettings
from clearml_yolo.core.publication import FiftyOneConfig
from clearml_yolo.entrypoints.hydra.transforms import profile_values


def _metadata(
    description: str,
    shapes: str,
    constraints: str,
    applicability: str,
    example: str,
) -> dict[str, object]:
    return {
        "description": description,
        "shapes": shapes,
        "constraints": constraints,
        "applicability": applicability,
        "examples": (example,),
    }


@dataclass
class CommandDeclaration:
    """Common marker for reflective compatibility projection, without validation."""


def _values(declaration: type[CommandDeclaration]) -> dict[str, Any]:
    instance = declaration()
    # Dataclass reflection intentionally preserves every declared field and its order.
    return {item.name: getattr(instance, item.name) for item in fields(instance)}


@dataclass
class PipelineMetricsConfig(CommandDeclaration):
    evaluation: Any = field(
        default_factory=lambda: builds(EvaluationConfig, populate_full_signature=True),
        metadata=_metadata(
            "Правила сопоставления детекций и вычисления метрик.",
            "mapping EvaluationConfig",
            "Пороговые значения и стратегия должны совпадать при сравнении моделей.",
            "pipeline",
            "evaluation.iou_threshold=0.5",
        ),
    )
    calibration_split: Any = field(
        default_factory=lambda: "val",
        metadata=_metadata(
            "Сплит, на котором подбираются пороги уверенности.",
            "val",
            "Калибровка выполняется на val; не подбирайте пороги на test.",
            "pipeline",
            "calibration_split=val",
        ),
    )


@dataclass
class PipelineCompareConfig(CommandDeclaration):
    baseline_model: Any = field(
        default_factory=lambda: builds(ModelRef, populate_full_signature=True),
        metadata=_metadata(
            "Базовая модель с происхождением checkpoint и калиброванными порогами.",
            "mapping ModelRef",
            (
                "Для source=local обязательны weights и непустые thresholds; backend "
                "и preset задаются вместе."
            ),
            "pipeline",
            "baseline_model.task_id=baseline-task",
        ),
    )
    q: Any = field(
        default_factory=lambda: 0.05,
        metadata=_metadata(
            "Уровень значимости статистического сравнения.",
            "number",
            "Конечное число от 0 до 1 включительно; проверяется validate_q.",
            "pipeline",
            "q=0.05",
        ),
    )
    bootstrap_iterations: Any = field(
        default_factory=lambda: 10000,
        metadata=_metadata(
            "Количество повторных bootstrap-выборок для сравнения.",
            "positive integer",
            "Положительное целое; больше итераций требует больше времени.",
            "pipeline",
            "bootstrap_iterations=10000",
        ),
    )
    seed: Any = field(
        default_factory=lambda: 0,
        metadata=_metadata(
            "Начальное состояние генератора случайных чисел.",
            "nonnegative integer | null",
            (
                "Допустимость null определяется операцией; фиксированное число делает"
                " разбиение/оценку повторяемыми."
            ),
            "pipeline",
            "seed=0",
        ),
    )


@dataclass
class PipelineReportConfig(CommandDeclaration):
    report_config_path: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Путь к пользовательской конфигурации генератора отчётов.",
            "path string | null",
            "null использует встроенное оформление; файл читается только при реальном выполнении.",
            "pipeline",
            "report_config_path=report.yaml",
        ),
    )


@dataclass
class ComparisonInferenceConfig(CommandDeclaration):
    reuse_existing: Any = field(
        default=True,
        metadata=_metadata(
            "Повторно использовать сохранённые предсказания при совпадении происхождения.",
            "boolean",
            "Проверяется совместимость checkpoint, входов и параметров инференса.",
            "compare",
            "inference.reuse_existing=true",
        ),
    )
    image_name: Any = field(
        default="name",
        metadata=_metadata(
            "Идентификатор изображения для сопоставимой оценки.",
            "name",
            "Сравнение поддерживает только полное имя файла name.",
            "compare",
            "inference.image_name=name",
        ),
    )


@dataclass
class ExportConfig(CommandDeclaration):
    model: Any = field(
        default_factory=dict,
        metadata=_metadata(
            "Выбор семейства детектора, архитектуры и параметров нативного адаптера.",
            "mapping; Hydra model=backend/preset",
            (
                "Выбирайте зарегистрированный preset; настройки "
                "model.train/model.predict неактивны для Ultralytics."
            ),
            "export",
            "model=rfdetr/small",
        ),
    )
    export: Any = field(
        default_factory=lambda: ExportSettings().model_dump(mode="json"),
        metadata=_metadata(
            "Настройки экспорта ONNX, сборки TensorRT или проверки качества движка.",
            "mapping ExportSettings",
            "Поддерживается только Faster R-CNN; operation определяет обязательные входы.",
            "export",
            "export.operation=onnx",
        ),
    )
    weights: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Путь к готовому checkpoint для инференса или экспорта.",
            "path string | null",
            (
                "В полном конвейере допустим только при skip_train=true; обучение "
                "выбирает веса в настройках модели."
            ),
            "export",
            "weights=best.pt",
        ),
    )
    ground_truth: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "CSV аннотации или ссылка на неизменяемый набор ClearML Dataset.",
            (
                "path string | {dataset_id: string} | {project_name: string, name: "
                "string, version?: string} | null"
            ),
            (
                "Обязателен там, где значение ???; dataset_id нельзя смешивать с "
                "именованным селектором. null допустим только для операций без "
                "размеченных данных."
            ),
            "export",
            "ground_truth=truth.csv",
        ),
    )
    output_dir: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Каталог результатов текущей команды.",
            "path string | null",
            (
                "null выбирает маршрут, принадлежащий запуску; допустимость пути "
                "проверяется перед записью."
            ),
            "export",
            "output_dir=outputs/evaluation",
        ),
    )
    clearml: Any = field(
        default_factory=lambda: builds(ClearMLConfig, populate_full_signature=True),
        metadata=_metadata(
            "Имя, теги и удалённое хранилище эксперимента ClearML.",
            "mapping ClearMLConfig",
            "Укажите проект, задачу и теги явно; output_uri не может отключать удалённое хранение.",
            "export",
            "clearml.project_name=examples",
        ),
    )


@dataclass
class TrainConfig(CommandDeclaration):
    model: Any = field(
        default_factory=dict,
        metadata=_metadata(
            "Выбор семейства детектора, архитектуры и параметров нативного адаптера.",
            "mapping; Hydra model=backend/preset",
            (
                "Выбирайте зарегистрированный preset; настройки "
                "model.train/model.predict неактивны для Ultralytics."
            ),
            "train",
            "model=rfdetr/small",
        ),
    )
    ultralytics: Any = field(
        default_factory=lambda: stage_settings(native_defaults(), "train"),
        metadata=_metadata(
            "Параметры обучения Ultralytics и встроенной проверки тренера.",
            "mapping",
            (
                "Активны только для model=ultralytics; владелец запуска задаёт "
                "маршруты данных и результатов."
            ),
            "train",
            "ultralytics.epochs=10",
        ),
    )
    ultralytics_predict: Any = field(
        default_factory=prediction_defaults,
        metadata=_metadata(
            (
                "Параметры отдельного предсказания Ultralytics; общие значения могут "
                "наследоваться из обучения."
            ),
            "mapping",
            (
                "Изменения в обучении наследуются только через оставленные выражения "
                "${ultralytics.FIELD}."
            ),
            "train",
            "ultralytics_predict.batch=8",
        ),
    )
    transforms: Any = field(
        default_factory=lambda: profile_values("default"),
        metadata=_metadata(
            "Профиль обучающих аугментаций и файл Albumentations.",
            "mapping TransformConfig",
            "Для albumentations нужен pipeline_file либо готовый snapshot; preview не читает файл.",
            "train",
            "transforms=albumentations",
        ),
    )
    clearml: Any = field(
        default_factory=lambda: builds(ClearMLConfig, populate_full_signature=True),
        metadata=_metadata(
            "Имя, теги и удалённое хранилище эксперимента ClearML.",
            "mapping ClearMLConfig",
            "Укажите проект, задачу и теги явно; output_uri не может отключать удалённое хранение.",
            "train",
            "clearml.project_name=examples",
        ),
    )
    ground_truth: Any = field(
        default_factory=lambda: MISSING,
        metadata=_metadata(
            "CSV аннотации или ссылка на неизменяемый набор ClearML Dataset.",
            (
                "path string | {dataset_id: string} | {project_name: string, name: "
                "string, version?: string} | null"
            ),
            (
                "Обязателен там, где значение ???; dataset_id нельзя смешивать с "
                "именованным селектором. null допустим только для операций без "
                "размеченных данных."
            ),
            "train",
            "ground_truth=truth.csv",
        ),
    )
    dataset_format: Any = field(
        default_factory=lambda: "ndjson",
        metadata=_metadata(
            "Формат подготовленного рабочего набора изображений и разметки.",
            "ndjson | flat | coco",
            "Для YOLO используйте ndjson или flat; нативные не-YOLO адаптеры используют COCO.",
            "train",
            "dataset_format=ndjson",
        ),
    )
    dataset_cache_dir: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Каталог кэша подготовленного рабочего набора.",
            "path string | null",
            (
                "null выбирает CY_HOME/.cache/clearml-yolo/datasets; в конвейере "
                "каталог должен быть вне run_dir."
            ),
            "train",
            "dataset_cache_dir=cache/datasets",
        ),
    )
    required_splits: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Сплиты, наличие которых обязательно при подготовке обучающего набора.",
            "list[string] | null",
            (
                "null оставляет выбор обязательных сплитов текущей операции; "
                "изображения сплитов должны быть раздельны."
            ),
            "train",
            "required_splits=[train,val]",
        ),
    )


@dataclass
class PredictConfig(CommandDeclaration):
    model: Any = field(
        default_factory=dict,
        metadata=_metadata(
            "Выбор семейства детектора, архитектуры и параметров нативного адаптера.",
            "mapping; Hydra model=backend/preset",
            (
                "Выбирайте зарегистрированный preset; настройки "
                "model.train/model.predict неактивны для Ultralytics."
            ),
            "predict",
            "model=rfdetr/small",
        ),
    )
    ultralytics: Any = field(
        default_factory=lambda: stage_settings(native_defaults(), "train"),
        metadata=_metadata(
            "Параметры обучения Ultralytics и встроенной проверки тренера.",
            "mapping",
            (
                "Активны только для model=ultralytics; владелец запуска задаёт "
                "маршруты данных и результатов."
            ),
            "predict",
            "ultralytics.epochs=10",
        ),
    )
    ultralytics_predict: Any = field(
        default_factory=prediction_defaults,
        metadata=_metadata(
            (
                "Параметры отдельного предсказания Ultralytics; общие значения могут "
                "наследоваться из обучения."
            ),
            "mapping",
            (
                "Изменения в обучении наследуются только через оставленные выражения "
                "${ultralytics.FIELD}."
            ),
            "predict",
            "ultralytics_predict.batch=8",
        ),
    )
    weights: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Путь к готовому checkpoint для инференса или экспорта.",
            "path string | null",
            (
                "В полном конвейере допустим только при skip_train=true; обучение "
                "выбирает веса в настройках модели."
            ),
            "predict",
            "weights=best.pt",
        ),
    )
    model_label: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Читаемая подпись модели в результатах и отчётах.",
            "string | null",
            "null использует идентичность checkpoint или текущего запуска.",
            "predict",
            "model_label=candidate",
        ),
    )
    ground_truth: Any = field(
        default_factory=lambda: MISSING,
        metadata=_metadata(
            "CSV аннотации или ссылка на неизменяемый набор ClearML Dataset.",
            (
                "path string | {dataset_id: string} | {project_name: string, name: "
                "string, version?: string} | null"
            ),
            (
                "Обязателен там, где значение ???; dataset_id нельзя смешивать с "
                "именованным селектором. null допустим только для операций без "
                "размеченных данных."
            ),
            "predict",
            "ground_truth=truth.csv",
        ),
    )
    output: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Путь результирующего CSV.",
            "path string | null",
            (
                "null выбирает имя результата текущей команды; существующие входы не "
                "заменяют этим полем."
            ),
            "predict",
            "output=predictions.csv",
        ),
    )
    splits: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Упорядоченный список сплитов для предсказаний или оценки.",
            "list[string] | null",
            (
                "null использует доступные сплиты; калибровочный val и итоговый test "
                "должны оставаться раздельными."
            ),
            "predict",
            "splits=[val,test]",
        ),
    )
    image_name: Any = field(
        default_factory=lambda: "name",
        metadata=_metadata(
            "Способ записи идентификатора изображения в CSV предсказаний.",
            "name | stem | path",
            "Для сопоставимой оценки и сравнения требуется name; проверьте уникальность имён.",
            "predict",
            "image_name=name",
        ),
    )
    clearml: Any = field(
        default_factory=lambda: builds(ClearMLConfig, populate_full_signature=True),
        metadata=_metadata(
            "Имя, теги и удалённое хранилище эксперимента ClearML.",
            "mapping ClearMLConfig",
            "Укажите проект, задачу и теги явно; output_uri не может отключать удалённое хранение.",
            "predict",
            "clearml.project_name=examples",
        ),
    )
    fiftyone: Any = field(
        default_factory=lambda: builds(FiftyOneConfig, populate_full_signature=True),
        metadata=_metadata(
            "Публикация изображений, предсказаний и оценок в FiftyOne.",
            "mapping FiftyOneConfig | null",
            "enabled=false отключает публикацию; таймауты ограничивают отдельные операции.",
            "predict",
            "fiftyone.enabled=false",
        ),
    )


@dataclass
class ValConfig(CommandDeclaration):
    model: Any = field(
        default_factory=dict,
        metadata=_metadata(
            "Выбор семейства детектора, архитектуры и параметров нативного адаптера.",
            "mapping; Hydra model=backend/preset",
            (
                "Выбирайте зарегистрированный preset; настройки "
                "model.train/model.predict неактивны для Ultralytics."
            ),
            "val",
            "model=rfdetr/small",
        ),
    )
    ultralytics: Any = field(
        default_factory=lambda: stage_settings(native_defaults(), "train"),
        metadata=_metadata(
            "Параметры обучения Ultralytics и встроенной проверки тренера.",
            "mapping",
            (
                "Активны только для model=ultralytics; владелец запуска задаёт "
                "маршруты данных и результатов."
            ),
            "val",
            "ultralytics.epochs=10",
        ),
    )
    ultralytics_predict: Any = field(
        default_factory=prediction_defaults,
        metadata=_metadata(
            (
                "Параметры отдельного предсказания Ultralytics; общие значения могут "
                "наследоваться из обучения."
            ),
            "mapping",
            (
                "Изменения в обучении наследуются только через оставленные выражения "
                "${ultralytics.FIELD}."
            ),
            "val",
            "ultralytics_predict.batch=8",
        ),
    )
    weights: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Путь к готовому checkpoint для инференса или экспорта.",
            "path string | null",
            (
                "В полном конвейере допустим только при skip_train=true; обучение "
                "выбирает веса в настройках модели."
            ),
            "val",
            "weights=best.pt",
        ),
    )
    model_label: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Читаемая подпись модели в результатах и отчётах.",
            "string | null",
            "null использует идентичность checkpoint или текущего запуска.",
            "val",
            "model_label=candidate",
        ),
    )
    ground_truth: Any = field(
        default_factory=lambda: MISSING,
        metadata=_metadata(
            "CSV аннотации или ссылка на неизменяемый набор ClearML Dataset.",
            (
                "path string | {dataset_id: string} | {project_name: string, name: "
                "string, version?: string} | null"
            ),
            (
                "Обязателен там, где значение ???; dataset_id нельзя смешивать с "
                "именованным селектором. null допустим только для операций без "
                "размеченных данных."
            ),
            "val",
            "ground_truth=truth.csv",
        ),
    )
    output_dir: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Каталог результатов текущей команды.",
            "path string | null",
            (
                "null выбирает маршрут, принадлежащий запуску; допустимость пути "
                "проверяется перед записью."
            ),
            "val",
            "output_dir=outputs/evaluation",
        ),
    )
    splits: Any = field(
        default_factory=lambda: ["train", "val", "test"],
        metadata=_metadata(
            "Упорядоченный список сплитов для предсказаний или оценки.",
            "list[string] | null",
            (
                "null использует доступные сплиты; калибровочный val и итоговый test "
                "должны оставаться раздельными."
            ),
            "val",
            "splits=[val,test]",
        ),
    )
    evaluation: Any = field(
        default_factory=lambda: builds(EvaluationConfig, populate_full_signature=True),
        metadata=_metadata(
            "Правила сопоставления детекций и вычисления метрик.",
            "mapping EvaluationConfig",
            "Пороговые значения и стратегия должны совпадать при сравнении моделей.",
            "val",
            "evaluation.iou_threshold=0.5",
        ),
    )
    clearml: Any = field(
        default_factory=lambda: builds(ClearMLConfig, populate_full_signature=True),
        metadata=_metadata(
            "Имя, теги и удалённое хранилище эксперимента ClearML.",
            "mapping ClearMLConfig",
            "Укажите проект, задачу и теги явно; output_uri не может отключать удалённое хранение.",
            "val",
            "clearml.project_name=examples",
        ),
    )


@dataclass
class MetricsConfig(CommandDeclaration):
    predictions: Any = field(
        default_factory=lambda: MISSING,
        metadata=_metadata(
            "CSV ранее сохранённых предсказаний.",
            "path string",
            "Обязателен для cy-metrics; должен соответствовать ground_truth и выбранным сплитам.",
            "metrics",
            "predictions=predictions.csv",
        ),
    )
    model_label: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Читаемая подпись модели в результатах и отчётах.",
            "string | null",
            "null использует идентичность checkpoint или текущего запуска.",
            "metrics",
            "model_label=candidate",
        ),
    )
    ground_truth: Any = field(
        default_factory=lambda: MISSING,
        metadata=_metadata(
            "CSV аннотации или ссылка на неизменяемый набор ClearML Dataset.",
            (
                "path string | {dataset_id: string} | {project_name: string, name: "
                "string, version?: string} | null"
            ),
            (
                "Обязателен там, где значение ???; dataset_id нельзя смешивать с "
                "именованным селектором. null допустим только для операций без "
                "размеченных данных."
            ),
            "metrics",
            "ground_truth=truth.csv",
        ),
    )
    output_dir: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Каталог результатов текущей команды.",
            "path string | null",
            (
                "null выбирает маршрут, принадлежащий запуску; допустимость пути "
                "проверяется перед записью."
            ),
            "metrics",
            "output_dir=outputs/evaluation",
        ),
    )
    splits: Any = field(
        default_factory=lambda: ["train", "val", "test"],
        metadata=_metadata(
            "Упорядоченный список сплитов для предсказаний или оценки.",
            "list[string] | null",
            (
                "null использует доступные сплиты; калибровочный val и итоговый test "
                "должны оставаться раздельными."
            ),
            "metrics",
            "splits=[val,test]",
        ),
    )
    calibration_split: Any = field(
        default_factory=lambda: "val",
        metadata=_metadata(
            "Сплит, на котором подбираются пороги уверенности.",
            "val",
            "Калибровка выполняется на val; не подбирайте пороги на test.",
            "metrics",
            "calibration_split=val",
        ),
    )
    evaluation: Any = field(
        default_factory=lambda: builds(EvaluationConfig, populate_full_signature=True),
        metadata=_metadata(
            "Правила сопоставления детекций и вычисления метрик.",
            "mapping EvaluationConfig",
            "Пороговые значения и стратегия должны совпадать при сравнении моделей.",
            "metrics",
            "evaluation.iou_threshold=0.5",
        ),
    )
    clearml: Any = field(
        default_factory=lambda: builds(ClearMLConfig, populate_full_signature=True),
        metadata=_metadata(
            "Имя, теги и удалённое хранилище эксперимента ClearML.",
            "mapping ClearMLConfig",
            "Укажите проект, задачу и теги явно; output_uri не может отключать удалённое хранение.",
            "metrics",
            "clearml.project_name=examples",
        ),
    )
    fiftyone: Any = field(
        default_factory=lambda: builds(FiftyOneConfig, populate_full_signature=True),
        metadata=_metadata(
            "Публикация изображений, предсказаний и оценок в FiftyOne.",
            "mapping FiftyOneConfig | null",
            "enabled=false отключает публикацию; таймауты ограничивают отдельные операции.",
            "metrics",
            "fiftyone.enabled=false",
        ),
    )


@dataclass
class ReportConfig(CommandDeclaration):
    comparison_dir: Any = field(
        default_factory=lambda: MISSING,
        metadata=_metadata(
            "Каталог результатов cy-compare с manifest и таблицами сравнения.",
            "path string",
            "Обязателен для отчёта; нужны результаты завершённого сравнения.",
            "report",
            "comparison_dir=outputs/comparison",
        ),
    )
    baseline_label: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Подпись базовой модели в отчёте.",
            "string | null",
            "null сохраняет подпись из результатов сравнения.",
            "report",
            "baseline_label=production",
        ),
    )
    candidate_label: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Подпись проверяемой модели в отчёте.",
            "string | null",
            "null сохраняет подпись из результатов сравнения.",
            "report",
            "candidate_label=experiment",
        ),
    )
    output_dir: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Каталог результатов текущей команды.",
            "path string | null",
            (
                "null выбирает маршрут, принадлежащий запуску; допустимость пути "
                "проверяется перед записью."
            ),
            "report",
            "output_dir=outputs/evaluation",
        ),
    )
    report_config_path: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Путь к пользовательской конфигурации генератора отчётов.",
            "path string | null",
            "null использует встроенное оформление; файл читается только при реальном выполнении.",
            "report",
            "report_config_path=report.yaml",
        ),
    )
    clearml: Any = field(
        default_factory=lambda: builds(ClearMLConfig, populate_full_signature=True),
        metadata=_metadata(
            "Имя, теги и удалённое хранилище эксперимента ClearML.",
            "mapping ClearMLConfig",
            "Укажите проект, задачу и теги явно; output_uri не может отключать удалённое хранение.",
            "report",
            "clearml.project_name=examples",
        ),
    )


@dataclass
class CompareConfig(CommandDeclaration):
    baseline_model: Any = field(
        default_factory=lambda: builds(ModelRef, populate_full_signature=True),
        metadata=_metadata(
            "Базовая модель с происхождением checkpoint и калиброванными порогами.",
            "mapping ModelRef",
            (
                "Для source=local обязательны weights и непустые thresholds; backend "
                "и preset задаются вместе."
            ),
            "compare",
            "baseline_model.task_id=baseline-task",
        ),
    )
    candidate_model: Any = field(
        default_factory=lambda: builds(ModelRef, populate_full_signature=True),
        metadata=_metadata(
            "Модель-кандидат с checkpoint и собственными калиброванными порогами.",
            "mapping ModelRef",
            (
                "Не переносите пороги базовой модели на кандидата; локальный источник"
                " требует точных thresholds."
            ),
            "compare",
            "candidate_model.task_id=candidate-task",
        ),
    )
    ground_truth: Any = field(
        default_factory=lambda: MISSING,
        metadata=_metadata(
            "CSV аннотации или ссылка на неизменяемый набор ClearML Dataset.",
            (
                "path string | {dataset_id: string} | {project_name: string, name: "
                "string, version?: string} | null"
            ),
            (
                "Обязателен там, где значение ???; dataset_id нельзя смешивать с "
                "именованным селектором. null допустим только для операций без "
                "размеченных данных."
            ),
            "compare",
            "ground_truth=truth.csv",
        ),
    )
    output_dir: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Каталог результатов текущей команды.",
            "path string | null",
            (
                "null выбирает маршрут, принадлежащий запуску; допустимость пути "
                "проверяется перед записью."
            ),
            "compare",
            "output_dir=outputs/evaluation",
        ),
    )
    split: Any = field(
        default_factory=lambda: "test",
        metadata=_metadata(
            "Сплит итогового сравнения моделей.",
            "string",
            "Обычно test; его изображения не участвуют в подборе порогов.",
            "compare",
            "split=test",
        ),
    )
    model: Any = field(
        default_factory=dict,
        metadata=_metadata(
            "Выбор семейства детектора, архитектуры и параметров нативного адаптера.",
            "mapping; Hydra model=backend/preset",
            (
                "Выбирайте зарегистрированный preset; настройки "
                "model.train/model.predict неактивны для Ultralytics."
            ),
            "compare",
            "model=rfdetr/small",
        ),
    )
    ultralytics: Any = field(
        default_factory=lambda: stage_settings(native_defaults(), "train"),
        metadata=_metadata(
            "Параметры обучения Ultralytics и встроенной проверки тренера.",
            "mapping",
            (
                "Активны только для model=ultralytics; владелец запуска задаёт "
                "маршруты данных и результатов."
            ),
            "compare",
            "ultralytics.epochs=10",
        ),
    )
    ultralytics_predict: Any = field(
        default_factory=prediction_defaults,
        metadata=_metadata(
            (
                "Параметры отдельного предсказания Ultralytics; общие значения могут "
                "наследоваться из обучения."
            ),
            "mapping",
            (
                "Изменения в обучении наследуются только через оставленные выражения "
                "${ultralytics.FIELD}."
            ),
            "compare",
            "ultralytics_predict.batch=8",
        ),
    )
    inference: Any = field(
        default_factory=lambda: _values(ComparisonInferenceConfig),
        metadata=_metadata(
            "Управление повторным использованием предсказаний при сравнении.",
            "{reuse_existing: bool, image_name: name}",
            "Параметры модели задаются в model.predict или ultralytics_predict.",
            "compare",
            "inference.reuse_existing=true",
        ),
    )
    q: Any = field(
        default_factory=lambda: 0.05,
        metadata=_metadata(
            "Уровень значимости статистического сравнения.",
            "number",
            "Конечное число от 0 до 1 включительно; проверяется validate_q.",
            "compare",
            "q=0.05",
        ),
    )
    bootstrap_iterations: Any = field(
        default_factory=lambda: 10000,
        metadata=_metadata(
            "Количество повторных bootstrap-выборок для сравнения.",
            "positive integer",
            "Положительное целое; больше итераций требует больше времени.",
            "compare",
            "bootstrap_iterations=10000",
        ),
    )
    seed: Any = field(
        default_factory=lambda: 0,
        metadata=_metadata(
            "Начальное состояние генератора случайных чисел.",
            "nonnegative integer | null",
            (
                "Допустимость null определяется операцией; фиксированное число делает"
                " разбиение/оценку повторяемыми."
            ),
            "compare",
            "seed=0",
        ),
    )
    evaluation: Any = field(
        default_factory=lambda: builds(EvaluationConfig, populate_full_signature=True),
        metadata=_metadata(
            "Правила сопоставления детекций и вычисления метрик.",
            "mapping EvaluationConfig",
            "Пороговые значения и стратегия должны совпадать при сравнении моделей.",
            "compare",
            "evaluation.iou_threshold=0.5",
        ),
    )
    clearml: Any = field(
        default_factory=lambda: builds(ClearMLConfig, populate_full_signature=True),
        metadata=_metadata(
            "Имя, теги и удалённое хранилище эксперимента ClearML.",
            "mapping ClearMLConfig",
            "Укажите проект, задачу и теги явно; output_uri не может отключать удалённое хранение.",
            "compare",
            "clearml.project_name=examples",
        ),
    )


@dataclass
class GroundTruthConfig(CommandDeclaration):
    data_yaml: Any = field(
        default_factory=lambda: MISSING,
        metadata=_metadata(
            "Путь к исходному описанию датасета в формате YOLO YAML.",
            "path string",
            "Обязателен для cy-ground-truth; содержит пути к изображениям и имена классов.",
            "ground_truth",
            "data_yaml=data.yaml",
        ),
    )
    output: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Путь результирующего CSV.",
            "path string | null",
            (
                "null выбирает имя результата текущей команды; существующие входы не "
                "заменяют этим полем."
            ),
            "ground_truth",
            "output=predictions.csv",
        ),
    )
    test_fraction: Any = field(
        default_factory=lambda: 0.5,
        metadata=_metadata(
            "Доля исходного val, выделяемая в независимый test при конвертации.",
            "number",
            "Диапазон [0, 1); разбиение выполняется по изображениям.",
            "ground_truth",
            "test_fraction=0.5",
        ),
    )
    seed: Any = field(
        default_factory=lambda: 0,
        metadata=_metadata(
            "Начальное состояние генератора случайных чисел.",
            "nonnegative integer | null",
            (
                "Допустимость null определяется операцией; фиксированное число делает"
                " разбиение/оценку повторяемыми."
            ),
            "ground_truth",
            "seed=0",
        ),
    )
    clearml: Any = field(
        default_factory=lambda: builds(ClearMLConfig, populate_full_signature=True),
        metadata=_metadata(
            "Имя, теги и удалённое хранилище эксперимента ClearML.",
            "mapping ClearMLConfig",
            "Укажите проект, задачу и теги явно; output_uri не может отключать удалённое хранение.",
            "ground_truth",
            "clearml.project_name=examples",
        ),
    )


@dataclass
class PipelineConfig(CommandDeclaration):
    model: Any = field(
        default_factory=dict,
        metadata=_metadata(
            "Выбор семейства детектора, архитектуры и параметров нативного адаптера.",
            "mapping; Hydra model=backend/preset",
            (
                "Выбирайте зарегистрированный preset; настройки "
                "model.train/model.predict неактивны для Ultralytics."
            ),
            "pipeline",
            "model=rfdetr/small",
        ),
    )
    ultralytics: Any = field(
        default_factory=lambda: stage_settings(native_defaults(), "train"),
        metadata=_metadata(
            "Параметры обучения Ultralytics и встроенной проверки тренера.",
            "mapping",
            (
                "Активны только для model=ultralytics; владелец запуска задаёт "
                "маршруты данных и результатов."
            ),
            "pipeline",
            "ultralytics.epochs=10",
        ),
    )
    ultralytics_predict: Any = field(
        default_factory=prediction_defaults,
        metadata=_metadata(
            (
                "Параметры отдельного предсказания Ultralytics; общие значения могут "
                "наследоваться из обучения."
            ),
            "mapping",
            (
                "Изменения в обучении наследуются только через оставленные выражения "
                "${ultralytics.FIELD}."
            ),
            "pipeline",
            "ultralytics_predict.batch=8",
        ),
    )
    transforms: Any = field(
        default_factory=lambda: profile_values("default"),
        metadata=_metadata(
            "Профиль обучающих аугментаций и файл Albumentations.",
            "mapping TransformConfig",
            "Для albumentations нужен pipeline_file либо готовый snapshot; preview не читает файл.",
            "pipeline",
            "transforms=albumentations",
        ),
    )
    metrics: Any = field(
        default_factory=lambda: make_config(**_values(PipelineMetricsConfig)),
        metadata=_metadata(
            "Настройки стадии метрик полного конвейера.",
            "{evaluation: EvaluationConfig, calibration_split: val}",
            "Пороги подбираются на val; test используется для итоговой оценки.",
            "pipeline",
            "metrics.evaluation.iou_threshold=0.5",
        ),
    )
    compare: Any = field(
        default_factory=lambda: make_config(**_values(PipelineCompareConfig)),
        metadata=_metadata(
            "Настройки сравнения обученной модели с baseline в полном конвейере.",
            (
                "{baseline_model: ModelRef, q: number, bootstrap_iterations: integer,"
                " seed: integer | null}"
            ),
            "Для запуска сравнения baseline должен разрешаться в существующий checkpoint.",
            "pipeline",
            "compare.baseline_model.task_id=baseline-task",
        ),
    )
    report: Any = field(
        default_factory=lambda: make_config(**_values(PipelineReportConfig)),
        metadata=_metadata(
            "Настройки стадии отчёта полного конвейера.",
            "{report_config_path: path string | null}",
            "Отчёт использует результаты предшествующих стадий.",
            "pipeline",
            "report.report_config_path=null",
        ),
    )
    clearml: Any = field(
        default_factory=lambda: builds(ClearMLConfig, populate_full_signature=True),
        metadata=_metadata(
            "Имя, теги и удалённое хранилище эксперимента ClearML.",
            "mapping ClearMLConfig",
            "Укажите проект, задачу и теги явно; output_uri не может отключать удалённое хранение.",
            "pipeline",
            "clearml.project_name=examples",
        ),
    )
    ground_truth: Any = field(
        default_factory=lambda: MISSING,
        metadata=_metadata(
            "CSV аннотации или ссылка на неизменяемый набор ClearML Dataset.",
            (
                "path string | {dataset_id: string} | {project_name: string, name: "
                "string, version?: string} | null"
            ),
            (
                "Обязателен там, где значение ???; dataset_id нельзя смешивать с "
                "именованным селектором. null допустим только для операций без "
                "размеченных данных."
            ),
            "pipeline",
            "ground_truth=truth.csv",
        ),
    )
    splits: Any = field(
        default_factory=lambda: ["train", "val", "test"],
        metadata=_metadata(
            "Упорядоченный список сплитов для предсказаний или оценки.",
            "list[string] | null",
            (
                "null использует доступные сплиты; калибровочный val и итоговый test "
                "должны оставаться раздельными."
            ),
            "pipeline",
            "splits=[val,test]",
        ),
    )
    dataset_format: Any = field(
        default_factory=lambda: "ndjson",
        metadata=_metadata(
            "Формат подготовленного рабочего набора изображений и разметки.",
            "ndjson | flat | coco",
            "Для YOLO используйте ndjson или flat; нативные не-YOLO адаптеры используют COCO.",
            "pipeline",
            "dataset_format=ndjson",
        ),
    )
    dataset_cache_dir: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Каталог кэша подготовленного рабочего набора.",
            "path string | null",
            (
                "null выбирает CY_HOME/.cache/clearml-yolo/datasets; в конвейере "
                "каталог должен быть вне run_dir."
            ),
            "pipeline",
            "dataset_cache_dir=cache/datasets",
        ),
    )
    weights: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Путь к готовому checkpoint для инференса или экспорта.",
            "path string | null",
            (
                "В полном конвейере допустим только при skip_train=true; обучение "
                "выбирает веса в настройках модели."
            ),
            "pipeline",
            "weights=best.pt",
        ),
    )
    model_label: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Читаемая подпись модели в результатах и отчётах.",
            "string | null",
            "null использует идентичность checkpoint или текущего запуска.",
            "pipeline",
            "model_label=candidate",
        ),
    )
    run_id: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Пользовательский идентификатор общего каталога конвейера.",
            "string | null",
            (
                "При отсутствии run_dir задаёт каталог runs/run_id; используйте "
                "уникальный идентификатор."
            ),
            "pipeline",
            "run_id=experiment-01",
        ),
    )
    run_dir: Any = field(
        default_factory=lambda: None,
        metadata=_metadata(
            "Общий каталог всех стадий конвейера.",
            "path string | null",
            (
                "Явный путь имеет приоритет перед run_id; нативные маршруты "
                "результатов должны ему соответствовать."
            ),
            "pipeline",
            "run_dir=runs/experiment-01",
        ),
    )
    skip_train: Any = field(
        default_factory=lambda: False,
        metadata=_metadata(
            "Пропустить стадию train в полном конвейере.",
            "boolean",
            (
                "При пропуске необходимые результаты предыдущего выполнения должны "
                "существовать; проверьте согласованность входов."
            ),
            "pipeline",
            "skip_train=true",
        ),
    )
    skip_predict: Any = field(
        default_factory=lambda: False,
        metadata=_metadata(
            "Пропустить стадию predict в полном конвейере.",
            "boolean",
            (
                "При пропуске необходимые результаты предыдущего выполнения должны "
                "существовать; проверьте согласованность входов."
            ),
            "pipeline",
            "skip_predict=true",
        ),
    )
    skip_metrics: Any = field(
        default_factory=lambda: False,
        metadata=_metadata(
            "Пропустить стадию metrics в полном конвейере.",
            "boolean",
            (
                "При пропуске необходимые результаты предыдущего выполнения должны "
                "существовать; проверьте согласованность входов."
            ),
            "pipeline",
            "skip_metrics=true",
        ),
    )
    skip_report: Any = field(
        default_factory=lambda: False,
        metadata=_metadata(
            "Пропустить стадию report в полном конвейере.",
            "boolean",
            (
                "При пропуске необходимые результаты предыдущего выполнения должны "
                "существовать; проверьте согласованность входов."
            ),
            "pipeline",
            "skip_report=true",
        ),
    )
    skip_compare: Any = field(
        default_factory=lambda: False,
        metadata=_metadata(
            "Пропустить стадию compare в полном конвейере.",
            "boolean",
            (
                "При пропуске необходимые результаты предыдущего выполнения должны "
                "существовать; проверьте согласованность входов."
            ),
            "pipeline",
            "skip_compare=true",
        ),
    )
    fiftyone: Any = field(
        default_factory=lambda: builds(FiftyOneConfig, populate_full_signature=True),
        metadata=_metadata(
            "Публикация изображений, предсказаний и оценок в FiftyOne.",
            "mapping FiftyOneConfig | null",
            "enabled=false отключает публикацию; таймауты ограничивают отдельные операции.",
            "pipeline",
            "fiftyone.enabled=false",
        ),
    )


COMMAND_DECLARATIONS: dict[str, type[CommandDeclaration]] = {
    "export": ExportConfig,
    "train": TrainConfig,
    "predict": PredictConfig,
    "val": ValConfig,
    "metrics": MetricsConfig,
    "report": ReportConfig,
    "compare": CompareConfig,
    "ground_truth": GroundTruthConfig,
    "pipeline": PipelineConfig,
}


def command_values(name: str) -> dict[str, Any]:
    """Return fresh legacy-compatible defaults without narrowing Hydra input types."""
    return _values(COMMAND_DECLARATIONS[name])


NESTED_DECLARATIONS: dict[str, type[CommandDeclaration]] = {
    "metrics": PipelineMetricsConfig,
    "compare": PipelineCompareConfig,
    "report": PipelineReportConfig,
    "inference": ComparisonInferenceConfig,
}
