# cy-export

`cy-export` переносит обученную модель Faster R-CNN в TensorRT в три шага: экспортирует checkpoint в граф ONNX, собирает из графа движок TensorRT ([TensorRT engine](../../GLOSSARY.md#tensorrt-engine)) и проверяет качество движка на размеченных изображениях по сравнению с исходным checkpoint. Один запуск выполняет одну операцию, её выбирает `export.operation`.

## Примеры

Экспортировать checkpoint в ONNX (на CPU):

```bash
cy-export model=fasterrcnn/resnet50_fpn weights=weights/best.pt clearml.project_name=my-project clearml.task_name=my-run
```

Собрать движок TensorRT FP16 на GPU 0 из графа предыдущего шага:

```bash
cy-export model=fasterrcnn/resnet50_fpn export.operation=build export.device=0 export.precision=fp16 export.onnx=runs/my-project/my-run-<task-id>/export/model.onnx clearml.project_name=my-project clearml.task_name=my-run
```

Проверить движок на split `test` разметки ([ground truth](../../GLOSSARY.md#ground-truth)):

```bash
cy-export model=fasterrcnn/resnet50_fpn export.operation=verify export.device=0 export.precision=fp16 export.engine=runs/my-project/my-run-<task-id>/export/model.engine weights=weights/best.pt ground_truth=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
```

Пути `runs/...` в примерах — каталог по умолчанию предыдущего запуска; подставьте свой.

## Синтаксис и аргументы

```bash
cy-export [ключ=значение ...]
```

`cy-export` — приложение Hydra: параметры задаются override вида `ключ=значение`. Синтаксис override, `--cfg`, `--config-dir` и `--multirun` описаны в [конфигурации](../configuration/README.md). Полную собранную конфигурацию без запуска печатает `cy-export --cfg job`.

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `model` | `fasterrcnn/resnet50_fpn` | Семейство моделей ([detector family](../../GLOSSARY.md#detector-family)) и preset, см. [`model`](../configuration/model.md). Допустимы только варианты `fasterrcnn/*`. Из группы используются `model.predict.conf`, `model.predict.iou` и `model.predict.max_det`: при `export.operation=onnx` они встраиваются в граф. |
| `export.operation` | `onnx` | Операция: `onnx`, `build` или `verify`, см. [Как это работает](#как-это-работает). |
| `export.device` | `cpu` | Устройство. Для `onnx` — только `cpu`. Для `build` и `verify` — ровно один GPU: `0`, `cuda:0`, `cuda` или `-1` (последние два означают GPU 0), список из одного элемента (`[0]`). |
| `export.precision` | `fp32` | `fp32` или `fp16`. Для `onnx` — только `fp32`. Для `build` — точность движка. Для `verify` должна совпадать с точностью, записанной в метаданных движка. |
| `export.onnx` | `null` | Путь к графу ONNX. Обязателен для `build`. |
| `export.engine` | `null` | Путь к движку TensorRT. Обязателен для `verify`. |
| `export.metadata` | `null` | Путь к файлу метаданных экспорта ([export metadata](../../GLOSSARY.md#export-metadata)) для `build` и `verify`. `null` — файл рядом с источником: `<export.onnx>.json` для `build`, `<export.engine>.json` для `verify`. При `onnx` не используется. |
| `export.workspace_gib` | `4.0` | Объём рабочей памяти TensorRT при сборке, GiB. Должен быть больше нуля. Используется только при `build`. |
| `export.split` | `test` | Split разметки, на котором `verify` проверяет качество: `train`, `val` или `test`. |
| `weights` | `null` | Веса модели: путь к checkpoint, ID задачи ClearML (task) с обученной моделью или `clearml://<model-id>`. Обязательны для `onnx` и `verify`, для `build` не нужны. |
| `ground_truth` | `null` | Разметка: CSV или ссылка на датасет ClearML, формат — в [разметке](../formats/ground-truth.md). Обязательна для `verify`, для `onnx` и `build` не нужна. |
| `output_dir` | `null` | Каталог результатов. `null` — каталог запуска ([run directory](../../GLOSSARY.md#run-directory)) `runs/<проект>/<задача>-<ID>/export`, см. [рабочий каталог](../workspace.md) ([workspace](../../GLOSSARY.md#workspace)). |
| `clearml` | см. страницу группы | Проект, имя и теги задачи ClearML, см. [`clearml`](../configuration/clearml.md). |

Других ключей в группе `export` нет: override вида `export.foo=1` Hydra отклоняет (`Could not override 'export.foo'`).

## Как это работает

До создания задачи ClearML команда проверяет конфигурацию:

1. Выбран ли вариант `fasterrcnn/*` (иначе `cy-export supports only Faster R-CNN presets`).
2. Допустимы ли значения `export.*` и их сочетание: `onnx` — только `cpu` и `fp32`; `build` и `verify` — ровно один GPU; `export.workspace_gib` больше нуля; `export.split` из списка.
3. Если задан `ground_truth`, корректна ли форма ссылки на разметку.

Затем команда создаёт задачу ClearML и проверяет, что для операции заданы нужные входы: `onnx` — `weights`; `build` — `export.onnx`; `verify` — `export.engine`, `weights` и `ground_truth`. Ссылку на разметку в ClearML команда разрешает в локальный файл, `weights` — в локальный checkpoint. Сведения об источнике весов (модель ClearML, задача обучения или SHA-256 файла) записываются в конфигурацию задачи как `source_model`.

### `export.operation=onnx`

1. Читает checkpoint и описание модели, сохранённое при обучении. Выбор `model=` должен совпадать с семейством и preset checkpoint.
2. Строит детектор на CPU, загружает веса и экспортирует его в `model.onnx` (opset 17). Предобработку изображения (letterbox до холста, нормализация) граф не содержит. RPN, ROIAlign, декодирование рамок (bounding box), порог уверенности (confidence threshold) `model.predict.conf`, NMS с порогом `model.predict.iou` и предел `model.predict.max_det` встроены в граф.
3. Записывает рядом `model.onnx.json` — метаданные экспорта: описание модели (preset, классы, предобработка), SHA-256 графа, встроенные пороги, профили размеров ([optimization profile](../../GLOSSARY.md#optimization-profile)) для TensorRT, версии `torch`, `torchvision`, `timm`, `onnx`.

Граф принимает `images` (float32, NCHW, RGB, нормализованные и дополненные нулями холсты; высота и ширина кратны 32) и `image_sizes` (int64, `[batch, 2]` — размеры изображений внутри холста после масштабирования) и возвращает `detections` и `counts`. Номера классов в `detections` начинаются с 1. Batch, высота и ширина в графе динамические.

### `export.operation=build`

Нужен TensorRT 10.13.0: он не входит в зависимости пакета, установите его отдельно. Без него или с другой версией сборка останавливается.

1. Читает метаданные (`export.metadata` или `<export.onnx>.json`). Preset в них должен совпадать с выбором `model=`, SHA-256 файла `export.onnx` — с записанным в метаданных.
2. Собирает движок `model.engine` на выбранном GPU с точностью `export.precision` и рабочей памятью `export.workspace_gib`. Профили размеров берутся из метаданных; по умолчанию их два: холсты от 608×960 до 736×960 и от 128×1536 до 256×1920, batch от 1 до 4. Движок принимает только такие входы.
3. Записывает `model.engine.json`: метаданные графа, дополненные SHA-256 движка, точностью, версиями TensorRT и CUDA runtime и списком плагинов.

### `export.operation=verify`

1. Читает метаданные (`export.metadata` или `<export.engine>.json`). Preset должен совпадать с `model=`, `export.precision` — с точностью движка, описание модели в checkpoint `weights` — с описанием в метаданных.
2. Проверяет разметку так же, как обучение, но обязателен только split `export.split`. Берёт изображения этого split; среди них должно быть хотя бы одно с объектами. Записывает список изображений с их SHA-256 в `corpus.json` и сразу выгружает его артефактом `export_corpus`.
3. Загружает движок на выбранный GPU. Для этого тоже нужен TensorRT 10.13.0. Движок должен совпадать с метаданными по SHA-256, версии TensorRT и версии CUDA runtime, а его входы, выходы и профили размеров — с записанными в метаданных.
4. Запускает на выбранном GPU исходную модель (FP32, TF32 выключен) и движок на одних и тех же изображениях в 22 сочетаниях batch и размера холста внутри профилей. Неполный последний batch дополняется повтором изображений; повторы в метрики не входят.
5. Для каждого сочетания считает COCO mAP, mAP50 и recall исходной модели и движка (pycocotools), сопоставляет их детекции и сравнивает предобработку движка с предобработкой исходной модели.
6. Проверяет, что движок отклоняет входы вне профилей (batch 5, холст между профилями, холст меньше минимального).
7. Проверяет, что разметка и изображения не изменились за время проверки.
8. Записывает отчёт `verification.json`. Отчёт обновляется после каждого сочетания и записывается также при ошибке, с полем `failure`. Артефактом `export_verification` он выгружается только после того, как все сочетания выполнены: если проверка прервалась ошибкой, отчёт остаётся только в `output_dir`.

Проверка пройдена (`passed: true`), если в каждом сочетании:

- предобработка совпадает с исходной (абсолютный допуск 0.0001, относительный 0.00001);
- исходная модель нашла хотя бы один объект и её mAP больше нуля;
- метрики движка не все равны нулю;
- mAP движка ниже mAP исходной модели не более чем на 0.001 при `fp32` или 0.005 при `fp16`;

и все три входа вне профилей отклонены. Сопоставление детекций (по классу, IoU не ниже 0.99) записывается в отчёт, но на результат не влияет.

## Результат

Файлы пишутся в `output_dir`:

| Операция | Файлы | Артефакты ClearML |
| --- | --- | --- |
| `onnx` | `model.onnx`, `model.onnx.json` | `export_onnx`, `export_metadata` |
| `build` | `model.engine`, `model.engine.json` | `export_engine`, `export_metadata` |
| `verify` | `corpus.json`, `verification.json` | `export_corpus`, `export_verification` |

Каждый файл выгружается артефактом сразу после записи. Итог операции (метаданные или отчёт проверки) записывается в конфигурацию задачи как `export_result`. Что ещё остаётся в ClearML, описано в [публикации](../publication.md).

Если `verify` выполнилась, но проверка не пройдена, оба артефакта выгружаются, а команда завершается ошибкой `Export verification failed; inspect the retained verification report`.

### Коды завершения

| Код | Когда |
| --- | --- |
| `0` | Операция выполнена; для `verify` — проверка пройдена. |
| `1` | Ошибка конфигурации, входов, экспорта, сборки или непройденная проверка. |

## Частые ошибки

| Сообщение | Причина и решение |
| --- | --- |
| `cy-export supports only Faster R-CNN presets` | Выбрано другое семейство моделей. Укажите `model=fasterrcnn/<preset>`. |
| `ONNX export requires device=cpu precision=fp32; select GPU/FP16 during engine build` | При `onnx` задан GPU или `fp16`. Экспортируйте граф с умолчаниями, а GPU и `fp16` задайте при `build`. |
| `Export requires one explicit GPU device` | При `build` или `verify` не задан GPU (например, осталось `export.device=cpu`). Укажите `export.device=0`. |
| `Export requires exactly one device` | В `export.device` передан список из нескольких устройств. |
| `ONNX export requires weights` | Не задан `weights` при `onnx`. |
| `Engine build requires an ONNX graph and its metadata` | Не задан `export.onnx` при `build`. |
| `Verification requires engine, weights and labeled ground_truth` | При `verify` не задан один из `export.engine`, `weights`, `ground_truth`. |
| `Selected preset disagrees with export metadata` | `model=` не совпадает с preset, из которого экспортирован граф. Выберите тот же preset. |
| `ONNX graph hash disagrees with export metadata` | Граф изменён или метаданные от другого графа. Используйте пару файлов из одного запуска `onnx`. |
| `Requested verification precision disagrees with engine metadata` | `export.precision` при `verify` не совпадает с точностью сборки. |
| `Verification checkpoint disagrees with export source descriptor` | `weights` при `verify` — не тот checkpoint, из которого экспортирован граф. |
| `ONNX export requires a checkpoint with a validated descriptor` | В checkpoint нет описания модели, которое CY записывает при обучении. Экспортируйте checkpoint, полученный `cy-train` или `cy`. |
| `Explicit model selection disagrees with the checkpoint descriptor` | `model=` не совпадает с семейством или preset checkpoint, см. [`model`](../configuration/model.md). |
| `TensorRT 10.13.0 is required, got <версия>` | Установлена другая версия TensorRT. |
| `Engine SHA256 does not match export metadata` | Движок изменён или метаданные от другого движка. |
| `Export quality corpus requires images with labeled foreground objects` | В split `export.split` нет изображений с объектами. Выберите другой split или дополните разметку. |
| `Export quality corpus contains invalid boxes; correct them before verification` | В разметке есть некорректные рамки, см. [разметку](../formats/ground-truth.md). |
| `Export verification failed; inspect the retained verification report` | Проверка не пройдена. Откройте `verification.json`: в каждом элементе `cases` есть `quality_passed`, `preprocessing_passed` и `mAP_loss`, в `rejections` — результат проверки входов вне профилей. |

Ошибки конфигурации печатаются через pydantic, например:

```text
pydantic_core._pydantic_core.ValidationError: 1 validation error for ExportSettings
  Value error, Export requires one explicit GPU device [type=value_error, ...]
```

## См. также

- [Конфигурация](../configuration/README.md), [`model`](../configuration/model.md), [`clearml`](../configuration/clearml.md)
- [Разметка](../formats/ground-truth.md)
- [Рабочий каталог](../workspace.md)
- [Публикация](../publication.md)
- [Установка](../installation.md)
