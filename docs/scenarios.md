# Сценарии

Семь типичных цепочек команд CY от начала до конца. Каждый шаг — одна команда, которую можно скопировать, и то, что она оставляет. Подробности каждой команды — на её странице.

Во всех примерах рабочий каталог ([workspace](../GLOSSARY.md#workspace)) — `/workspace/project`, команды запускаются из него. `<task-id>` замените на ID задачи ClearML (task) из предыдущего шага.

## 1. Первый запуск

1. Задайте рабочий каталог и адрес сервера ClearML (ключи доступа и FiftyOne — в [Установке](installation.md#учётные-данные)):

   ```bash
   export CY_HOME=/workspace/project CLEARML_API_HOST=https://clearml.example.com
   ```

   Результаты CY пишет только внутри `CY_HOME` — это правило записи внутри `CY_HOME` ([write containment rule](../GLOSSARY.md#write-containment-rule)), см. [Рабочий каталог](workspace.md#правило-записи-внутри-cy_home).

2. Создайте локальное дерево конфигурации для `cy` ([`cy-init-config`](commands/cy-init-config.md)):

   ```bash
   cy-init-config configs
   ```

   В `configs` появляются корневой файл `cy.yaml` и копии встроенных файлов групп конфигурации (config group). Свои значения правьте в `cy.yaml`.

3. Постройте CSV разметки ([ground truth](../GLOSSARY.md#ground-truth)) из YAML YOLO-датасета ([`cy-ground-truth`](commands/cy-ground-truth.md)):

   ```bash
   cy-ground-truth data_yaml=data/dataset.yaml output=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
   ```

   Результат — `data/ground_truth.csv` в формате [Разметки](formats/ground-truth.md). Если в датасете нет split `test`, команда переносит в него долю изображений `val` (`test_fraction`).

4. Запустите полный пайплайн ([pipeline](../GLOSSARY.md#pipeline)) со своим деревом конфигурации ([`cy`](commands/cy.md)):

   ```bash
   cy --config-dir configs --config-name cy ground_truth=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
   ```

   Команда обучает модель Ultralytics YOLO по умолчанию, строит предсказания (predictions), метрики, сравнение (comparison) и отчёт (report) в каталоге запуска ([run directory](../GLOSSARY.md#run-directory)) `runs/my-project/my-run-<task-id>/`. Итог пайплайна ([pipeline outcome](../GLOSSARY.md#pipeline-outcome)) по этапам ([stage](../GLOSSARY.md#stage)) — в `pipeline_outcome.txt` того же каталога. Если в проекте нет завершённой задачи с тегом `prod`, сравнение и отчёт пропускаются, а команда продолжается.

## 2. Этап за этапом

Этапы `cy` отдельными командами и валидация (validation) в конце. Каждая команда создаёт свою задачу ClearML.

1. Обучите модель ([`cy-train`](commands/cy-train.md)):

   ```bash
   cy-train ground_truth=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
   ```

   Checkpoint лежит в каталоге обучения ([training directory](../GLOSSARY.md#training-directory)): `runs/my-project/my-run%2Ftrain-<task-id>/detect/my-run%2Ftrain/weights/best.pt`. Задача `cy-train` называется `my-run/train`, и `/` в путях записывается как `%2F`. ID этой задачи нужен на следующих шагах.

2. Постройте предсказания весами (weights) задачи обучения ([`cy-predict`](commands/cy-predict.md)):

   ```bash
   cy-predict weights=<task-id> ground_truth=data/ground_truth.csv output=runs/my-run/predict.csv clearml.project_name=my-project clearml.task_name=my-run
   ```

   Результат — `runs/my-run/predict.csv` ([формат](formats/predictions.md)) и рядом `runs/my-run/predict.csv.provenance.json`.

3. Посчитайте метрики ([`cy-metrics`](commands/cy-metrics.md)):

   ```bash
   cy-metrics predictions=runs/my-run/predict.csv ground_truth=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
   ```

   В каталог `metrics` каталога запуска (ключ `output_dir`) записываются `metrics_best_confidences_val.csv` с подобранными порогами ([selected confidence thresholds](../GLOSSARY.md#selected-confidence-thresholds)) и книги Excel (workbook) по каждому split, см. [Книги Excel](formats/workbooks.md#метрики-cy-metrics).

4. Отчёт строится по результату сравнения, поэтому сначала сравните обученную модель с [baseline](../GLOSSARY.md#baseline) ([`cy-compare`](commands/cy-compare.md)). Пороги уверенности (confidence threshold) локального checkpoint задаются явно, по одному на каждый класс, по которому оценивается модель; возьмите их из `metrics_best_confidences_val.csv`:

   ```bash
   cy-compare ground_truth=data/ground_truth.csv candidate_model.source=local candidate_model.weights=runs/my-project/my-run%2Ftrain-<task-id>/detect/my-run%2Ftrain/weights/best.pt 'candidate_model.thresholds={defect: 0.35}' output_dir=runs/my-run/compare clearml.project_name=my-project clearml.task_name=my-run
   ```

   Baseline по умолчанию — последняя завершённая задача проекта с тегом `prod`. В `runs/my-run/compare/` появляются книга сравнения и `comparison_manifest.json`. Если baseline не найден, сравнение пропускается и манифеста сравнения ([comparison manifest](../GLOSSARY.md#comparison-manifest)) нет; тогда следующий шаг завершается ошибкой `Comparison directory <каталог> has no comparison_manifest.json; run cy-compare first`.

5. Постройте отчёты ([`cy-report`](commands/cy-report.md)):

   ```bash
   cy-report comparison_dir=runs/my-run/compare clearml.project_name=my-project clearml.task_name=my-run
   ```

   Результат — `report_dev_test.xlsx` и `report_business_test.xlsx` в каталоге `report` каталога запуска.

6. Проверьте веса валидацией на `val` и `test` ([`cy-val`](commands/cy-val.md)):

   ```bash
   cy-val weights=<task-id> ground_truth=data/ground_truth.csv 'splits=[val,test]' clearml.project_name=my-project clearml.task_name=my-run
   ```

   В `runs/my-project/my-run%2Fval-<task-id>/val/` (здесь `<task-id>` — новая задача `cy-val`) записываются `predictions.csv` и каталог `metrics/` с книгами Excel.

## 3. Сравнение с baseline

1. Сравните две модели из задач ClearML на split `test` ([`cy-compare`](commands/cy-compare.md)):

   ```bash
   cy-compare ground_truth=data/ground_truth.csv baseline_model.task_id=<task-id> candidate_model.task_id=<task-id> clearml.project_name=my-project clearml.task_name=my-run
   ```

   Первый `<task-id>` — задача baseline, второй — модели-кандидата ([candidate model](../GLOSSARY.md#candidate-model)). Пороги каждой модели берутся из её задачи. Результат — книга `compare_workbook_test.xlsx`, предсказания обеих моделей и `comparison_manifest.json` в `runs/my-project/my-run%2Fcompare-<task-id>/compare/`, где `<task-id>` — задача самого сравнения ([Книги Excel](formats/workbooks.md#сравнение-cy-compare)). Деградация ([degraded class](../GLOSSARY.md#degraded-class)) классов — результат, а не ошибка: код завершения `0`.

2. Постройте отчёты по этому сравнению; `<task-id>` в пути — задача шага 1 ([`cy-report`](commands/cy-report.md)):

   ```bash
   cy-report comparison_dir=runs/my-project/my-run%2Fcompare-<task-id>/compare clearml.project_name=my-project clearml.task_name=my-run
   ```

3. Чтобы сравнение шло внутри пайплайна с выбранным baseline, задайте его в `compare.baseline_model` ([`cy`](commands/cy.md)):

   ```bash
   cy ground_truth=data/ground_truth.csv compare.baseline_model.task_id=<task-id> clearml.project_name=my-project clearml.task_name=my-run
   ```

   Модель-кандидат — модель, обученная в этом запуске. Сравнение пишется в `comparison/`, отчёт — в `reports/` каталога запуска. Если явно заданный baseline не найден, этап сравнения завершается ошибкой.

## 4. Другое семейство моделей и свой пайплайн аугментаций

1. Сохраните файл пайплайна ([augmentation pipeline file](../GLOSSARY.md#augmentation-pipeline-file)) Albumentations в `augmentation/flip.json` (правила файла — в [`transforms`](configuration/transforms.md#файл-пайплайна)):

   ```json
   {
     "__version__": "2.0.8",
     "transform": {
       "__class_fullname__": "Compose",
       "p": 1.0,
       "transforms": [
         {"__class_fullname__": "HorizontalFlip", "p": 0.5},
         {"__class_fullname__": "RandomBrightnessContrast", "p": 0.2}
       ],
       "bbox_params": {"format": "pascal_voc", "label_fields": ["class_labels"]}
     }
   }
   ```

2. Посмотрите собранную конфигурацию без запуска:

   ```bash
   cy-train --cfg job model=fcos/resnet50_fpn transforms=albumentations transforms.pipeline_file=augmentation/flip.json ground_truth=data/ground_truth.csv
   ```

   Команда печатает конфигурацию и ничего не запускает. Сам файл пайплайна при `--cfg job` не читается и не проверяется.

3. Обучите FCOS со своим файлом пайплайна ([`cy-train`](commands/cy-train.md)):

   ```bash
   cy-train model=fcos/resnet50_fpn transforms=albumentations transforms.pipeline_file=augmentation/flip.json ground_truth=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
   ```

   Файл проверяется при запуске, до создания задачи ClearML. Параметры обучения этого семейства задаются в `model.train.*`, а не в `ultralytics.*` ([`model`](configuration/model.md)).

4. Постройте предсказания тем же семейством моделей ([detector family](../GLOSSARY.md#detector-family)), командой [`cy-predict`](commands/cy-predict.md):

   ```bash
   cy-predict model=fcos/resnet50_fpn weights=<task-id> ground_truth=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
   ```

   Параметры предсказания задаются в `model.predict.*`. Результат — `predict.csv` в каталоге запуска `runs/my-project/my-run%2Fpredict-<task-id>/`.

## 5. Подготовка GPU-хоста

1. Если прямого доступа к GitHub нет, задайте зеркало весов ([weight mirror](../GLOSSARY.md#weight-mirror)), см. [Зеркала весов](installation.md#зеркала-весов):

   ```bash
   export GHR=https://artifactory.example/artifactory/github-files
   ```

2. Заранее скачайте веса всех моделей ([`cy-download-weights`](commands/cy-download-weights.md)):

   ```bash
   cy-download-weights
   ```

   Команда готовит веса именованных моделей и исходники DEIMv2 в их кэшах (cache) и печатает итог.

3. Посмотрите, для каких моделей уже есть batch size ([`cy-batch-estimate`](commands/cy-batch-estimate.md)):

   ```bash
   cy-batch-estimate --list
   ```

4. Заполните пропуски таблицы batch size ([batch size table](../GLOSSARY.md#batch-size-table)) для GPU-хоста:

   ```bash
   cy-batch-estimate --imgsz 640 --devices 0,1 --gpu-counts 1,2
   ```

   Команда измеряет модели на GPU 0 и 1 и печатает рекомендации для одной и двух GPU. Таблица описана в [Таблице batch size](formats/batch-table.md).

5. Посмотрите, сколько дубликатов в кэше, ничего не меняя ([`cy-dedup`](commands/cy-dedup.md)):

   ```bash
   cy-dedup --dry-run
   ```

6. Замените дубликаты в `CY_HOME/.cache` на reflink-клоны ([reflink clone](../GLOSSARY.md#reflink-clone)):

   ```bash
   cy-dedup
   ```

## 6. Экспорт в ONNX и TensorRT

`cy-export` работает только с моделями `fasterrcnn/*`.

1. Экспортируйте checkpoint в ONNX на CPU ([`cy-export`](commands/cy-export.md)):

   ```bash
   cy-export model=fasterrcnn/resnet50_fpn weights=weights/best.pt clearml.project_name=my-project clearml.task_name=my-run
   ```

   Граф и метаданные экспорта ([export metadata](../GLOSSARY.md#export-metadata)) пишутся в `runs/my-project/my-run%2Fexport-<task-id>/export/`: `model.onnx` и `model.onnx.json`.

2. Соберите движок TensorRT ([TensorRT engine](../GLOSSARY.md#tensorrt-engine)) FP16 на GPU 0 из этого графа:

   ```bash
   cy-export model=fasterrcnn/resnet50_fpn export.operation=build export.device=0 export.precision=fp16 export.onnx=runs/my-project/my-run%2Fexport-<task-id>/export/model.onnx clearml.project_name=my-project clearml.task_name=my-run
   ```

   `<task-id>` в пути — задача шага 1. Результат — `model.engine` и `model.engine.json` в каталоге `export` каталога запуска новой задачи.

3. Проверьте движок на split `test` разметки:

   ```bash
   cy-export model=fasterrcnn/resnet50_fpn export.operation=verify export.device=0 export.precision=fp16 export.engine=runs/my-project/my-run%2Fexport-<task-id>/export/model.engine weights=weights/best.pt ground_truth=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
   ```

   `<task-id>` в пути — задача шага 2. `export.precision` должна совпадать с точностью движка. Результат — `corpus.json` и `verification.json`; если проверка не пройдена, команда завершается ошибкой.

## 7. Sweep Hydra (multirun)

1. Проверьте конфигурацию одного задания без запуска (`--cfg` нельзя сочетать с `-m`):

   ```bash
   cy-train --cfg job ground_truth=data/ground_truth.csv ultralytics.epochs=50 clearml.project_name=my-project clearml.task_name=my-run
   ```

2. Запустите sweep: по одному обучению на каждое значение `ultralytics.epochs` ([Multirun](configuration/README.md#multirun)):

   ```bash
   cy-train -m ground_truth=data/ground_truth.csv ultralytics.epochs=50,100 clearml.project_name=my-project clearml.task_name=my-run
   ```

   Задания выполняются последовательно, каждое — отдельная задача ClearML. Все они получают общий тег multirun ([multirun tag](../GLOSSARY.md#multirun-tag)) `multirun-<ГГГГММДД-ЧЧММСС>-<шесть слов через дефис>`. Каталоги Hydra ([Hydra output directory](../GLOSSARY.md#hydra-output-directory)) создаются в `CY_HOME/multirun/`, результаты обучения — в каталоги запуска в `runs/`. Параллельный запуск через очередь описан в [Очереди](queue.md).

## См. также

- [Конфигурация](configuration/README.md)
- [Рабочий каталог](workspace.md)
- [Публикация в ClearML и FiftyOne](publication.md)
