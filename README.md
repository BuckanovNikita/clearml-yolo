# clearml-yolo

clearml-yolo (CY) — набор консольных команд для обучения (training) детекторов объектов, предсказаний (predictions), метрик, сравнения (comparison) моделей, отчётов (report) и экспорта (export). Каждый запуск команды Hydra выполняется в задаче ClearML (task); команды `cy`, `cy-predict` и `cy-metrics` также публикуют разметку ([ground truth](GLOSSARY.md#ground-truth)) и предсказания в FiftyOne, а ошибка FiftyOne не влияет на код завершения (см. [Публикация в ClearML и FiftyOne](docs/publication.md)). Поддерживаются семейства моделей ([detector family](GLOSSARY.md#detector-family)) Ultralytics YOLO, DEIMv2, RF-DETR, Faster R-CNN и FCOS.

## Команды

| Команда | Назначение |
| --- | --- |
| [`cy`](docs/commands/cy.md) | Весь пайплайн ([pipeline](GLOSSARY.md#pipeline)): обучение, предсказания, метрики, сравнение и отчёт в одном запуске |
| [`cy-train`](docs/commands/cy-train.md) | Обучение |
| [`cy-predict`](docs/commands/cy-predict.md) | Предсказания готовыми весами (weights) |
| [`cy-val`](docs/commands/cy-val.md) | Валидация (validation) готовых весов |
| [`cy-metrics`](docs/commands/cy-metrics.md) | Метрики по готовым предсказаниям |
| [`cy-compare`](docs/commands/cy-compare.md) | Сравнение модели-кандидата ([candidate model](GLOSSARY.md#candidate-model)) с [baseline](GLOSSARY.md#baseline) |
| [`cy-report`](docs/commands/cy-report.md) | Отчёты по результатам сравнения |
| [`cy-ground-truth`](docs/commands/cy-ground-truth.md) | CSV разметки из YOLO-датасета |
| [`cy-export`](docs/commands/cy-export.md) | Экспорт Faster R-CNN в ONNX и TensorRT |
| [`cy-init-config`](docs/commands/cy-init-config.md) | Локальное дерево конфигурации (configuration) |
| [`cy-dedup`](docs/commands/cy-dedup.md) | Дедупликация файлов кэша (cache) |
| [`cy-download-weights`](docs/commands/cy-download-weights.md) | Заранее скачивает веса и исходники моделей |
| [`cy-batch-estimate`](docs/commands/cy-batch-estimate.md) | Оценка batch size на GPU |

Первые девять команд настраиваются override вида `key=value`, см. [Конфигурация](docs/configuration/README.md). Остальные четыре принимают обычные флаги.

## Установка

Пакет называется `clearml-yolo` и требует Python `>=3.12.13,<3.14`. Все семейства моделей входят в стандартную установку. Зависимости `digital-metrics>=0.7.0` и `report-generator` должны быть доступны в индексе пакетов, из которого вы ставите `clearml-yolo`. В публичном PyPI пакета нет, он ставится по Git-ссылке:

```bash
uv venv --python 3.12
uv pip install "clearml-yolo @ git+https://github.com/BuckanovNikita/clearml-yolo"
```

Рабочий каталог ([workspace](GLOSSARY.md#workspace), `CY_HOME`), переменные окружения (environment variable) и учётные данные ClearML и FiftyOne описаны в разделе [Установка и окружение](docs/installation.md).

## Первый запуск

Нужны YOLO-датасет, описанный файлом `data/dataset.yaml`, и доступ к серверу ClearML: ключи доступа задаются в `~/clearml.conf` или переменными окружения, см. [Установка и окружение](docs/installation.md#учётные-данные).

```bash
export CY_HOME=/workspace/project CLEARML_API_HOST=https://clearml.example.com
cy-init-config configs
cy-ground-truth data_yaml=data/dataset.yaml output=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
cy --config-dir configs --config-name cy ground_truth=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
```

Команды создают локальное дерево конфигурации, строят CSV разметки из YOLO-датасета и запускают весь пайплайн. Что делает каждый шаг и что он оставляет, описано в разделе [Сценарии](docs/scenarios.md#1-первый-запуск).

## Лицензии весов

Предобученные веса распространяются под лицензиями своих авторов: Ultralytics YOLO — AGPL-3.0, DEIMv2 — только некоммерческое использование, DINOv3 — отдельное соглашение Meta. Подробнее — в разделе [Лицензии весов](docs/configuration/model.md#лицензии-весов).

**Built with DINOv3.**

## Документация

- [Указатель документации](docs/README.md)
- [Глоссарий](GLOSSARY.md)
