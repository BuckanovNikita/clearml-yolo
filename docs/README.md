# Документация clearml-yolo

Указатель всех страниц документации. Поддерживаемый интерфейс CY — командная строка: тринадцать консольных команд, описанных ниже. Термины CY собраны в [глоссарии](../GLOSSARY.md).

## Команды

| Страница | Что отвечает |
| --- | --- |
| [`cy`](commands/cy.md) | Как запустить весь пайплайн ([pipeline](../GLOSSARY.md#pipeline)): обучение, предсказания, метрики, сравнение и отчёт в одной задаче ClearML (task) |
| [`cy-train`](commands/cy-train.md) | Как обучить модель отдельной командой |
| [`cy-predict`](commands/cy-predict.md) | Как получить предсказания (predictions) готовыми весами (weights) |
| [`cy-val`](commands/cy-val.md) | Как одним запуском выполнить валидацию (validation) готовых весов |
| [`cy-metrics`](commands/cy-metrics.md) | Как посчитать метрики по готовым предсказаниям и разметке ([ground truth](../GLOSSARY.md#ground-truth)) |
| [`cy-compare`](commands/cy-compare.md) | Как сравнить модель-кандидат ([candidate model](../GLOSSARY.md#candidate-model)) с моделью [baseline](../GLOSSARY.md#baseline) |
| [`cy-report`](commands/cy-report.md) | Как построить технический и бизнес-отчёт по результатам сравнения |
| [`cy-ground-truth`](commands/cy-ground-truth.md) | Как превратить YOLO-датасет в CSV разметки |
| [`cy-export`](commands/cy-export.md) | Как перенести модель Faster R-CNN в ONNX и TensorRT и проверить движок |
| [`cy-init-config`](commands/cy-init-config.md) | Как создать редактируемое дерево YAML для команды и модели |
| [`cy-dedup`](commands/cy-dedup.md) | Как заменить одинаковые изображения в кэше (cache) на reflink-клоны ([reflink clone](../GLOSSARY.md#reflink-clone)) |
| [`cy-download-weights`](commands/cy-download-weights.md) | Как заранее подготовить веса и исходники моделей на хосте |
| [`cy-batch-estimate`](commands/cy-batch-estimate.md) | Как измерить наибольший batch size на GPU и заполнить таблицу batch size ([batch size table](../GLOSSARY.md#batch-size-table)) |

## Конфигурация

| Страница | Что отвечает |
| --- | --- |
| [Конфигурация](configuration/README.md) | Как команды Hydra собирают конфигурацию (configuration): override, свои YAML-файлы, просмотр через `--cfg`, multirun, каталоги Hydra ([Hydra output directory](../GLOSSARY.md#hydra-output-directory)), отклонённые ключи очереди и ключи каждого backend |
| [`model`](configuration/model.md) | Как выбрать семейство моделей ([detector family](../GLOSSARY.md#detector-family)), preset и параметры обучения и предсказания |
| [`ultralytics`](configuration/ultralytics.md) | Какие нативные параметры обучения Ultralytics YOLO есть и что CY в них меняет |
| [`ultralytics_predict`](configuration/ultralytics-predict.md) | Какие нативные параметры предсказания Ultralytics YOLO есть и что CY в них меняет |
| [`transforms`](configuration/transforms.md) | Как выбрать аугментацию (augmentation) при обучении, включая свой пайплайн Albumentations |
| [`evaluation`](configuration/evaluation.md) | Как CY сопоставляет предсказания с разметкой, подбирает пороги уверенности (confidence threshold) и считает метрики |
| [`clearml`](configuration/clearml.md) | Как задать проект, имя, тип и теги задачи ClearML |
| [`fiftyone`](configuration/fiftyone.md) | Как управлять публикацией в FiftyOne |

## Форматы

| Страница | Что отвечает |
| --- | --- |
| [Форматы файлов](formats/README.md) | Какие файлы команды читают и записывают |
| [Разметка](formats/ground-truth.md) | Как устроен CSV разметки |
| [Предсказания](formats/predictions.md) | Как устроен CSV предсказаний |
| [Датасеты](formats/datasets.md) | Какой YOLO-датасет принимает `cy-ground-truth`, какую рабочую копию ([prepared dataset copy](../GLOSSARY.md#prepared-dataset-copy)) датасета CY собирает для обучения и где её кэширует (`dataset_cache_dir`) |
| [Книги Excel](formats/workbooks.md) | Какие книги Excel (workbook) и файлы рядом с ними пишут `cy-metrics`, `cy-compare` и `cy-report` |
| [Таблица batch size](formats/batch-table.md) | Где лежит таблица batch size и как её читать и править |

## Остальное

| Страница | Что отвечает |
| --- | --- |
| [Установка и окружение](installation.md) | Что ставит пакет, какой нужен Python, как задать `CY_HOME`, переменные окружения и учётные данные |
| [Рабочий каталог](workspace.md) ([workspace](../GLOSSARY.md#workspace)) | Что CY хранит в `CY_HOME` и что можно удалять |
| [Публикация в ClearML и FiftyOne](publication.md) | Что запуск оставляет в ClearML и FiftyOne и когда он считается успешным |
| [Сценарии](scenarios.md) | Семь цепочек команд от первого запуска до sweep |
| [Очередь](queue.md) | Почему команды CY не ставят запуски в очередь ClearML и что использовать вместо этого |
| [Глоссарий](../GLOSSARY.md) | Что значат термины CY |
