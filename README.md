# clearml-yolo

Набор переиспользуемых hydra-zen приложений: обучение YOLO с DDP и ClearML, инференс,
подсчёт метрик по всем сплитам через [digital-metrics](https://github.com/Wasilkas/digital-metrics)
и сравнение с предыдущей моделью через [report-generator](https://github.com/Wasilkas/report-generator).

## Установка

```bash
uv sync
```

Перед первым запуском нужно настроить ClearML (файла `~/clearml.conf` в системе может не быть):

```bash
uv run clearml-init
```

Либо через переменные окружения: `CLEARML_API_HOST`, `CLEARML_WEB_HOST`,
`CLEARML_FILES_HOST`, `CLEARML_API_ACCESS_KEY`, `CLEARML_API_SECRET_KEY`.

## Приложения

Каждый этап запускается самостоятельно, либо все сразу через `cy`.

| Команда | Что делает |
|---|---|
| `cy-train` | обучение YOLO (DDP, авто-выбор GPU, кастомные аугментации) |
| `cy-predict` | инференс, CSV предсказаний в схеме digital-metrics |
| `cy-metrics` | метрики по каждому сплиту, дашборды в xlsx |
| `cy-report` | сравнение с базовой моделью, dev и business отчёты |
| `cy` | весь конвейер одним экспериментом ClearML |

Посмотреть итоговый конфиг без запуска: `uv run cy-train --cfg job`.

## Быстрый старт

```bash
# весь конвейер
uv run cy \
    clearml.project_name=detection \
    clearml.task_name=yolo11n-v3 \
    train.data=data.yaml \
    train.epochs=300 \
    predict.ground_truth=ground_truth.csv \
    metrics.ground_truth=ground_truth.csv

# только метрики по готовым предсказаниям
uv run cy-metrics predictions=runs/predictions.csv ground_truth=ground_truth.csv
```

Обратите внимание: у отдельных приложений ключи задаются без префикса
(`cy-train epochs=1`), а в конвейере — с префиксом этапа (`cy train.epochs=1`).

## Именование эксперимента

`clearml.project_name` и `clearml.task_name` задаются один раз на верхнем уровне и
попадают во все четыре этапа — конвейер создаёт один эксперимент, к которому
подключаются все стадии. При самостоятельном запуске этап добавляет свой суффикс
(`yolo11n-v3/metrics`).

Отключить трекинг целиком: `clearml.enabled=false`.

## Авто-выбор GPU

По умолчанию `auto_gpu.enabled=true`: NVML опрашивает все карты, отбрасывает занятые
чужими процессами и заполненные, а затем масштабирует батч под самую слабую из
выбранных карт.

```bash
uv run cy-train auto_gpu.batch_per_gpu=16 auto_gpu.reference_vram_gb=24
```

`batch_per_gpu` — ваш оптимальный батч на одну карту при `reference_vram_gb` видеопамяти.
Итоговый `batch` = батч на карту × число карт, всегда кратен числу устройств
(ultralytics делит общий батч между рангами без проверки кратности).

Ручной режим:

```bash
uv run cy-train auto_gpu.enabled=false device=[0,1] batch=32
```

`batch=-1` (автоподбор ultralytics) работает только на одной карте — на нескольких
приложение сообщит об ошибке сразу, а не в середине обучения.

## Кастомные аугментации

Пайплайн albumentations передаётся файлом JSON:

```python
import albumentations as A

pipeline = A.Compose(
    [A.HorizontalFlip(p=0.5), A.Rotate(limit=15, p=0.3)],
    bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"]),
)
A.save(pipeline, "augmentations.json", data_format="json")
```

```bash
uv run cy-train augmentations.path=augmentations.json
```

Требуется ultralytics ≥ 8.4: только с этой версии трансформы переживают передачу в
DDP-подпроцессы. `A.Lambda` и собственные классы трансформов не сериализуются.

## Данные

Для обучения нужен обычный `data.yaml`. Для метрик — CSV разметки со столбцами
`image_name, instance_label, bbox_x_tl, bbox_y_tl, bbox_x_br, bbox_y_br, split`
(абсолютные пиксели, углы рамки; классы именами, не индексами). Для `cy-predict`
дополнительно нужен `image_path`.

Изображение должно принадлежать ровно одному сплиту: digital-metrics отклоняет
пересечения, потому что калибровка порогов утекала бы в оценку.

## Метрики и артефакты

Метрики считаются отдельно для каждого сплита (`splits=[train,val,test]`), пороги
калибруются на `calibration_split=val`. Для самого `val` пороги подбираются по нему же,
так как калибровать сплит по себе нельзя.

В ClearML загружаются: `predictions`, а для каждого сплита — `dashboard_full_*`,
`dashboard_dtrk_*`, `matches_gt_*`, `matches_preds_*`, `metrics_summary_*`,
`metrics_raw_*`, `best_confidences_*`, плюс средние значения как скаляры.

## Сравнение с предыдущей моделью

```bash
# базовая модель из прошлой задачи ClearML (по умолчанию — последняя завершённая)
uv run cy-report baseline=clearml baseline.project_name=detection

# из локальной папки
uv run cy-report baseline=local baseline.directory=runs/previous/metrics

# без сравнения
uv run cy-report baseline=none
```

Внутри конвейера группа называется `report/baseline`:
`uv run cy report/baseline=local report.baseline.directory=...`

На каждый сплит создаётся два файла: `report_dev_{split}.xlsx` (4 листа) и
`report_business_{split}.xlsx` (5 листов, включая вердикт «К выкатке» / «Не к выкатке»).
Сравнение считается как новая модель минус прод.

Классы с числом train-примеров ≤ `min_train_count` (по умолчанию 20) исключаются из
сравнения и попадают на лист «Удаленные классы». Порог меняется своим конфигом:

```bash
uv run cy-report report_config_path=my_report_config.yaml
```

## Разработка

```bash
uv run pytest
uv run ruff check .
uv run mypy src/
```
