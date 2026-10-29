# Свои аугментации и программная композиция

## Предварительные условия

Нужны установленный CY, реальные входы и ClearML из [первого урока](quickstart.html).
Для аугментаций используйте установленную совместимую версию Albumentations.
Программные workflows создают реальные файлы и задачи; вызывающая программа
владеет полным временем жизни ресурсов и публикации.

## Пример

### Сохранить Albumentations JSON

Сохраните этот код как `make_augmentation.py` и выполните его в рабочем каталоге:

```python
from pathlib import Path

import albumentations as A

pipeline = A.Compose(
    [A.HorizontalFlip(p=0.5), A.RandomBrightnessContrast(p=0.2)],
    bbox_params=A.BboxParams(format="pascal_voc", label_fields=["class_labels"]),
)
A.save(pipeline, Path("augmentation.json"), data_format="json")
```

```bash
cy-train model=rfdetr/nano ground_truth=./tutorial-data/ground_truth.csv \
  transforms=albumentations transforms.pipeline_file=./augmentation.json \
  model.train.epochs=1 model.train.batch=2 model.train.device=0 \
  clearml.project_name=cy-tutorial clearml.task_name=custom-augmentation \
  'clearml.tags=[tutorial,augmentation]'
```

[transforms](/#field=transforms) выбирает профиль, а
[transforms.pipeline_file](/#field=transforms.pipeline_file) — редактируемый вход.
`transforms=default` оставляет нативный рецепт. При `albumentations` случайные
аугментации backend отключаются, включая native Mosaic; конфликты заменяются
с диагностикой. Backend всё равно владеет окончательным resize, тензорами и
нормализацией. Не добавляйте `Normalize`, `ToFloat` и `ToTensorV2` в JSON.

### Добавить Mosaic

```python
from pathlib import Path

import albumentations as A

pipeline = A.Compose(
    [
        A.Mosaic(
            grid_yx=(2, 2),
            target_size=(512, 512),
            cell_shape=(512, 512),
            p=0.5,
        ),
        A.HorizontalFlip(p=0.5),
    ],
    bbox_params=A.BboxParams(format="pascal_voc", label_fields=["class_labels"]),
)
A.save(pipeline, Path("mosaic.json"), data_format="json")
```

Поставьте единственный Mosaic первым в корневом `Compose`; вспомогательные
изображения выбираются только из training population. Замените путь в команде
на `mosaic.json`. Размер Mosaic не подменяет размер входа выбранной модели.
При runtime содержимое JSON проверяется, снимок и digest сохраняются для replay
без исходного файла. `snapshot` — сгенерированное происхождение, а не поле для
ручного заполнения. Предпросмотр конфигурации файл JSON не загружает.

### Вставить свою обработку между этапами

Отдельные CLI позволяют встроить анализ в обычный shell-конвейер:

```bash
cy-predict weights=./best.pt ground_truth=./tutorial-data/ground_truth.csv \
  'splits=[val,test]' output=./prediction/predictions.csv model_label=tutorial-yolo \
  ultralytics_predict.device=cpu fiftyone.enabled=false clearml.project_name=cy-tutorial \
  clearml.task_name=predict-for-analysis 'clearml.tags=[tutorial,custom]'
python inspect_predictions.py
cy-metrics ground_truth=./tutorial-data/ground_truth.csv \
  predictions=./prediction/predictions.csv 'splits=[val,test]' \
  output_dir=./metrics-after-inspection model_label=tutorial-yolo fiftyone.enabled=false \
  clearml.project_name=cy-tutorial clearml.task_name=score-after-analysis \
  'clearml.tags=[tutorial,custom]'
```

Например, `inspect_predictions.py` читает результат и пишет отдельный сводный файл:

```python
from pathlib import Path

import pandas as pd

frame = pd.read_csv(
    "prediction/predictions.csv",
    keep_default_na=False,
    dtype={"image_name": str, "instance_label": str},
    float_precision="round_trip",
)
summary = frame.groupby("instance_label", dropna=False).size()
Path("analysis").mkdir(exist_ok=True)
summary.to_csv("analysis/prediction-counts.csv", header=["detections"])
```

Это анализ сырых детекций, не замена метрик. Не перезаписывайте подписанный CSV
и его provenance: изменение байтов делает прежний digest недействительным.
Для преобразования данных создавайте новый вход и явно учитывайте его происхождение.
Каждая standalone-команда имеет собственную задачу ClearML.

### Заменить типизированную зависимость через Python

Workflows принимают `WorkflowDependencies`, объявленный в `application.ports`.
`build_dependencies()` создаёт независимый bundle для одного вызова;
`dataclasses.replace` подменяет выбранный port без глобального service locator.
Ниже полный metrics-вызов с опциональной реализацией `EvaluationEngine`:

```python
from dataclasses import replace
from pathlib import Path
from typing import Any

from clearml_yolo.application.contracts import MetricsResult
from clearml_yolo.application.ports import EvaluationEngine


def run_metrics(engine: EvaluationEngine | None = None) -> MetricsResult:
    from clearml_yolo.adapters.runtime.bootstrap import runtime_environment

    with runtime_environment():
        from clearml_yolo.adapters.clearml.session import invocation
        from clearml_yolo.application.contracts import ClearMLConfig
        from clearml_yolo.application.use_cases.metrics import compute_metrics
        from clearml_yolo.core.evaluation.models import EvaluationConfig
        from clearml_yolo.core.publication import FiftyOneConfig
        from clearml_yolo.entrypoints.composition import build_dependencies

        tracking = ClearMLConfig(
            project_name="cy-tutorial", task_name="python-metrics", tags=["tutorial", "python"]
        )
        evaluation = EvaluationConfig()
        publication = FiftyOneConfig(enabled=False)
        deps = build_dependencies()
        if engine is not None:
            deps = replace(deps, evaluation=engine)
        inputs: dict[str, Any] = {
            "ground_truth": "tutorial-data/ground_truth.csv",
            "predictions": "prediction/predictions.csv",
            "output_dir": "python-metrics",
            "splits": ["val", "test"],
            "calibration_split": "val",
            "model_label": "tutorial-yolo",
            "evaluation": evaluation.model_dump(mode="json"),
            "clearml": tracking.model_dump(mode="json"),
            "fiftyone": publication.model_dump(mode="json"),
        }
        with invocation(tracking, "metrics", resolved_config=inputs):
            return compute_metrics(
                predictions=Path(inputs["predictions"]),
                ground_truth=Path(inputs["ground_truth"]),
                output_dir=Path(inputs["output_dir"]),
                clearml=tracking,
                evaluation=evaluation,
                splits=["val", "test"],
                calibration_split="val",
                fiftyone=publication,
                model_label="tutorial-yolo",
                deps=deps,
            )


if __name__ == "__main__":
    run_metrics()
```

`run_metrics()` использует штатный движок. Интеграция передаёт свой объект как
`run_metrics(my_engine)`, реализовав **все** методы `EvaluationEngine` с теми же
типами и инвариантами. За научную сопоставимость иной реализации отвечает её
проверка; вызов `replace` сам её не доказывает. Полный `resolved_config` нужен для
воспроизводимости: прямой use-case не собирает снимок за вызывающую программу.

Этот пример владеет scratch и ClearML invocation и не запускает модель/FiftyOne.
При программном training/inference дополнительно требуются native runtime,
process supervision и cleanup, соответствующие выбранному backend; их образец —
`entrypoints.hydra.common.execute_owned`. Для обычной композиции этапов используйте
CLI выше. Произвольные pipeline stages нельзя заменить строками `_target_`
в Hydra: bundle создаётся entrypoint, а не пользовательским YAML.

## Ожидаемый результат

Аугментации изменяют только training pipeline; финальная подготовка входов остаётся
у backend. Снимок JSON позволяет повторить запуск без исходного файла. Анализ
между CLI оставляет исходные predictions/provenance нетронутыми. Python-пример
создаёт один metrics invocation, сохраняет полный снимок входов и завершает
публикацию до выхода из контекстов.

## Частые ошибки

- Задан JSON при `transforms=default`: выберите профиль albumentations.
- Normalize/ToTensor в JSON: удалите их, чтобы не дублировать backend preprocessing.
- Mosaic не первый или вложен несколько раз: оставьте один root-first оператор.
- Изменены подписанные predictions: получите новый корректный результат и provenance.
- Прямой вызов use-case без владельца invocation: используйте полный lifecycle.
- Подмена `_target_` вместо port: используйте Python `WorkflowDependencies`.

## Проверка

Сверьте training configuration, diagnostics конфликтов и сохранённый digest JSON.
Убедитесь, что source dataset неизменен и val/test не получают training аугментации.
Для Python-интеграции проверьте типы port, реальные результаты, закрытие задачи,
обязательные uploads и содержимое `Configuration / run`. Тестирование preview
не проверяет JSON операторов, произвольную реализацию port или native обучение.
