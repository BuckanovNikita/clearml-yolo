# Группа `ultralytics`

Группа конфигурации (config group) `ultralytics` содержит нативные параметры обучения Ultralytics YOLO. CY передаёт их в `YOLO.train()` почти без изменений; эта страница перечисляет каждый ключ, значение по умолчанию, которое собирает CY, и то, что CY меняет, ограничивает или запрещает.

Параметры предсказания задаются в отдельной группе [`ultralytics_predict`](ultralytics-predict.md).

## Где действует группа

| Команда | Как используется `ultralytics` |
| --- | --- |
| `cy` | Этап ([stage](../../GLOSSARY.md#stage)) обучения пайплайна ([pipeline](../../GLOSSARY.md#pipeline)); ключи, которые [`ultralytics_predict`](ultralytics-predict.md) интерполирует из этой группы, действуют и на этапе предсказания. |
| `cy-train` | Обучение. |
| `cy-predict`, `cy-val`, `cy-compare` | Обучения нет. CY проверяет, что в группе нет неизвестных ключей и `cfg` равен `null`; значения действуют только через ключи `ultralytics_predict`, интерполированные из этой группы (например `imgsz`, `compile`). |

У `cy-metrics`, `cy-report`, `cy-ground-truth` и `cy-export` этой группы нет; override вида `ultralytics.epochs=1` завершается ошибкой Hydra `Could not override 'ultralytics.epochs'`.

Группа действует только при `model.backend=ultralytics` (по умолчанию). Для другого семейства моделей ([detector family](../../GLOSSARY.md#detector-family)) параметры обучения задаются в `model.train.*` (см. [`model`](model.md)). Если при другом backend изменить любой ключ этой группы, команда завершается до запуска задачи ClearML (task):

```text
ValueError: Changed ultralytics settings ['epochs'] are inactive for deimv2/s; use model.train instead
```

И наоборот, при `model.backend=ultralytics` изменённые ключи `model.train.*` отклоняются:

```text
ValueError: Changed model.train settings ['epochs'] are inactive for ultralytics; use ultralytics instead
```

## Как задавать ключи

Ключи из таблицы ниже меняются обычным override: `ultralytics.epochs=50`. Нативный ключ Ultralytics, которого нет в собранной группе, добавляется через `+` (например `+ultralytics.dropout=0.1`). CY знает все ключи `default.yaml` установленной версии Ultralytics, а также `augmentations` и `save_dir`:

- ключ, которого Ultralytics не знает, отклоняется: `ValueError: Unknown Ultralytics parameters: ['foo']`;
- `cfg` должен оставаться `null`: `ValueError: Native cfg must be null`;
- известный ключ, который к обучению детектора не относится (например `source`, `dropout`, `format`), принимается и молча отбрасывается;
- `save_dir` в `cy` отклоняется ошибкой `save_dir conflicts with pipeline run_dir; use run_dir to route outputs`: с `run_dir` или `run_id` — до создания задачи ClearML (task), без них — после её создания, потому что каталог запуска тогда зависит от задачи. В `cy-train` `save_dir` отбрасывается; в обоих случаях путь сначала проверяется на нахождение внутри `CY_HOME`;
- `augmentations` (список преобразований Albumentations для нативного загрузчика) передаётся в Ultralytics как есть. Собственный пайплайн аугментаций CY настраивается в группе [`transforms`](transforms.md); профиль ([transforms profile](../../GLOSSARY.md#transforms-profile)) `transforms=albumentations` сам обнуляет встроенные аугментации Ultralytics (`hsv_*`, `degrees`, `translate`, `scale`, `shear`, `perspective`, `flipud`, `fliplr`, `bgr`, `mosaic` и другие).

При запуске `cy-train` и `cy` (в `cy` — и при `skip_train=true`), до создания задачи ClearML (task), CY проверяет полную группу: все ключи обучения должны присутствовать, типы и диапазоны должны совпадать с ожиданиями Ultralytics. Ошибки имеют вид `ultralytics.epochs must be an integer`, `ultralytics.lr0 must be between 0 and 1`, `ultralytics.epochs must be at least 1`, `ultralytics.amp must not be null`.

## Ключи

Значения по умолчанию получены командой `cy --cfg job`; у `cy-train`, `cy-predict`, `cy-val` и `cy-compare` они такие же. Описание нативного смысла взято из Ultralytics; колонка «Описание» отдельно говорит, что делает CY.

### Задача, модель и данные

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `task` | `detect` | Тип задачи Ultralytics. CY поддерживает только `detect`; другое значение отклоняется (`ultralytics.task must be detect`). |
| `mode` | `train` | Режим Ultralytics. Должен быть `train` (`ultralytics.mode must be train`). |
| `model` | `yolo11n.pt` | Модель для обучения: имя предобученных весов (weights), путь к `.pt` или к `.yaml` архитектуры. В Ultralytics по умолчанию пусто; CY подставляет `yolo11n.pt`. Пустое значение отклоняется до создания задачи ClearML (task), в `cy` — и при `skip_train=true`: `Set ultralytics.model explicitly; no training model fallback is provided`. Загруженная модель должна быть детектором. |
| `data` | `null` | Файл описания датасета. CY всегда подменяет его рабочей копией датасета ([prepared dataset copy](../../GLOSSARY.md#prepared-dataset-copy)), подготовленной из разметки ([ground truth](../../GLOSSARY.md#ground-truth)) `ground_truth` (см. [форматы датасетов](../formats/datasets.md)); собственное значение не используется. |
| `epochs` | `100` | Число эпох обучения. Целое, не меньше 1. |
| `time` | `null` | Максимальная длительность обучения в часах; если задано, заменяет `epochs`. |
| `patience` | `100` | Ранняя остановка после стольких эпох без улучшения на валидации. Целое, не меньше 0. |
| `batch` | `16` | Batch size: целое число, `-1` для AutoBatch Ultralytics или дробь в (0, 1) как доля памяти GPU. CY дополнительно принимает `null`: тогда batch size берётся из [таблицы batch size](../formats/batch-table.md) ([batch size table](../../GLOSSARY.md#batch-size-table)) для модели, `imgsz` и выбранных GPU, а `device` заменяется списком этих GPU. Для `null` нужны CUDA, квадратный `imgsz` и модель из списка CY. |
| `imgsz` | `960` | Размер входа для обучения и валидации. В Ultralytics по умолчанию `640`; CY использует `960`. Положительное целое (или список положительных целых). |
| `save` | `true` | Сохранять checkpoint обучения. |
| `save_period` | `-1` | Сохранять checkpoint каждые N эпох; меньше 1 — отключено. |
| `cache` | `false` | Кэш изображений: `true`/`ram` — в памяти, `disk` — на диске, `false` — без кэша. |
| `device` | `null` | Устройство: `0`, `[0,1]`, `cpu`, `mps`, `-1` или `[-1,-1]` для автоматического выбора свободных GPU. Передаётся в Ultralytics как есть (исключение — `batch: null`, см. выше). |
| `workers` | `8` | Число процессов загрузчика данных (на каждый процесс при DDP). |

### Выходные каталоги

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `project` | `null` | Корень результатов обучения. В `cy-train` при `null` это `detect` внутри каталога запуска ([run directory](../../GLOSSARY.md#run-directory)) задачи в рабочем каталоге ([workspace](../../GLOSSARY.md#workspace)) под `CY_HOME/runs` (см. [Рабочий каталог](../workspace.md)). Заданный путь должен лежать внутри `CY_HOME`, иначе команда завершается ошибкой `Project write destination ... must be contained beneath CY_HOME=...`. В `cy` допустимо только `null` или полный путь `<каталог запуска>/detect`; другое значение отклоняется ошибкой `project=... conflicts with pipeline run_dir; expected ...`: с `run_dir` или `run_id` — до создания задачи, без них — после её создания, потому что каталог запуска тогда зависит от задачи. |
| `name` | `null` | Имя подкаталога внутри `project`. В `cy-train` при `null` — имя задачи ClearML, приведённое к безопасному виду. В `cy` допустимо только `null` или `train`. Другое значение отклоняется ошибкой `name=... conflicts with pipeline run_dir; expected train`: с `run_dir` или `run_id` — до создания задачи, без них — после её создания. |
| `exist_ok` | `false` | Писать в существующий каталог `project/name`, а не создавать новый с номером. Передаётся как есть. |

### Обучение

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `pretrained` | `true` | Начинать с предобученных весов (`true`/`false`) или загрузить веса из указанного пути. |
| `cls_remap` | `true` | При дообучении на другом датасете сопоставлять строки классификационной головы по именам классов. При обучении на разметке CY принудительно ставит `false`. |
| `optimizer` | `auto` | Оптимизатор: `SGD`, `MuSGD`, `Adam`, `Adamax`, `AdamW`, `NAdam`, `RAdam`, `RMSProp` или `auto`. |
| `verbose` | `true` | Подробный лог Ultralytics. |
| `seed` | `0` | Seed для воспроизводимости. Целое, не меньше 0. |
| `deterministic` | `true` | Детерминированные операции: воспроизводимо, но может быть медленнее. |
| `single_cls` | `false` | Считать все классы одним. При обучении на разметке CY принудительно ставит `false`. |
| `rect` | `false` | Прямоугольные batch при обучении. |
| `cos_lr` | `false` | Косинусный планировщик learning rate. |
| `close_mosaic` | `10` | Отключить mosaic на последних N эпохах (`0` — не отключать). |
| `resume` | `false` | Продолжить обучение с последнего checkpoint. CY не поддерживает: при `true` `cy-train` и `cy` (в `cy` — и при `skip_train=true`) завершаются до создания задачи ClearML (task) ошибкой `resume is unsupported with ground_truth; use model weights to fine-tune`. Чтобы дообучить модель, укажите её веса в `model`. |
| `amp` | `true` | Точность обучения: `true`/`fp16` (AMP), `bf16`, `false`/`fp32`. `null` отклоняется. |
| `fraction` | `1.0` | Доля или число обучающих изображений. При обучении на разметке CY принудительно ставит `1.0`: состав split задаёт CSV. |
| `profile` | `false` | Профилировать скорость ONNX/TensorRT во время обучения для логгеров. |
| `freeze` | `null` | Заморозить первые N слоёв (целое) или перечисленные слои (список индексов или имён модулей). |
| `multi_scale` | `0.0` | Диапазон multi-scale обучения как доля `imgsz`; значение от 0 до 1. |
| `compile` | `true` | `torch.compile()`: `true`, `false` или строка режима (`default`, `reduce-overhead`, `max-autotune-no-cudagraphs`). В Ultralytics по умолчанию `false`; CY включает. |
| `channels_last` | `null` | Формат памяти channels-last; `null` — Ultralytics решает сам. |

### Валидация во время обучения и постобработка

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `val` | `true` | Запускать валидацию во время обучения. |
| `split` | `val` | Split для валидации. При обучении на разметке CY принудительно ставит `val`. |
| `save_json` | `false` | Сохранять результаты валидации в COCO JSON. |
| `conf` | `null` | Порог уверенности (confidence threshold) для валидации внутри обучения; `null` — значение Ultralytics. От 0 до 1. |
| `iou` | `0.7` | Порог IoU для NMS. От 0 до 1. |
| `max_det` | `300` | Максимум детекций на изображение. Целое, не меньше 1. |
| `quantize` | `null` | Точность. При обучении `8`/`int8` включает quantization-aware training. Допустимы `8`, `16`, `32`, `int8`, `fp16`, `fp32`, `w8a8`, `w16a16`, `w32a32`, `w8a16`, `w8a32`. |
| `plots` | `true` | Сохранять графики и изображения обучения и валидации. |
| `nms` | `true` | По описанию Ultralytics: `null` — внешний NMS, `true` — встроить NMS при экспорте, `false` — голова без NMS, если модель её поддерживает. В Ultralytics по умолчанию `null`; CY ставит `true`. |
| `visualize` | `false` | Сохранять визуализацию TP/FP/FN при валидации. |
| `augment` | `false` | Test-time augmentation. |
| `agnostic_nms` | `false` | NMS без учёта классов. |
| `classes` | `null` | Фильтр по номерам классов. При обучении на разметке CY принудительно ставит `null`. |
| `save_txt` | `false` | Сохранять результаты в `.txt`. |
| `save_conf` | `false` | Добавлять уверенность в `.txt`. |
| `show_labels` | `true` | Подписывать классы на изображениях. |
| `show_conf` | `true` | Подписывать уверенность на изображениях. |

### Гиперпараметры

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `lr0` | `0.01` | Начальный learning rate. От 0 до 1. |
| `lrf` | `0.01` | Доля конечного learning rate: конечный = `lr0 * lrf`. От 0 до 1. |
| `momentum` | `0.937` | Momentum SGD или beta1 Adam. От 0 до 1. |
| `weight_decay` | `0.0005` | Weight decay (L2). От 0 до 1. |
| `warmup_epochs` | `3.0` | Эпохи warmup (допустимы дробные). |
| `warmup_momentum` | `0.8` | Начальный momentum во время warmup. От 0 до 1. |
| `warmup_bias_lr` | `0.1` | Learning rate bias во время warmup. От 0 до 1. |
| `distill_model` | `null` | Путь к модели-учителю для дистилляции. |
| `dis` | `6.0` | Вес потерь дистилляции. |
| `box` | `7.5` | Вес потерь рамки (bounding box). |
| `cls` | `0.5` | Вес потерь классификации. |
| `cls_pw` | `0.0` | Степень весов классов при дисбалансе: `0.0` — выключено, `1.0` — полная обратная частота. От 0 до 1. |
| `dfl` | `1.5` | Вес потерь DFL. |
| `nbs` | `64` | Номинальный batch size: градиенты накапливаются за `round(nbs / batch)` batch. Целое, не меньше 1. |

### Аугментации Ultralytics

Все ключи этого раздела — вероятности или доли от 0 до 1, кроме `degrees` и `shear` (в градусах) и `scale` (доля от 0 до 1 или пара `[min, max]`). Профиль `transforms=albumentations` обнуляет их (см. [`transforms`](transforms.md)).

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `hsv_h` | `0.015` | Сдвиг оттенка HSV. |
| `hsv_s` | `0.7` | Сдвиг насыщенности HSV. |
| `hsv_v` | `0.4` | Сдвиг яркости HSV. |
| `degrees` | `0.0` | Поворот, ± градусы. |
| `translate` | `0.1` | Сдвиг, ± доля. |
| `scale` | `0.5` | Масштаб, ± доля или `[min, max]`. |
| `shear` | `0.0` | Сдвиг-скос, ± градусы. |
| `perspective` | `0.0` | Перспектива, доля. |
| `flipud` | `0.0` | Вероятность вертикального отражения. |
| `fliplr` | `0.5` | Вероятность горизонтального отражения. |
| `bgr` | `0.0` | Вероятность перестановки каналов RGB↔BGR. |
| `mosaic` | `1.0` | Вероятность mosaic. |
| `mixup` | `0.0` | Вероятность MixUp. |
| `cutmix` | `0.0` | Вероятность CutMix. |

## Что CY меняет при обучении на разметке

Обучение в `cy-train` и `cy` всегда идёт на рабочей копии датасета, которую CY готовит из CSV разметки. Перед вызовом Ultralytics CY ставит `task=detect`, `classes=null`, `data=<подготовленный датасет>`, `single_cls=false`, `fraction=1.0`, `cls_remap=false`, `split=val` и пишет в лог каждое изменённое значение (`CSV dataset owns ...`). Запрошенные и действующие значения записываются в задачу ClearML (см. [публикация](../publication.md)).

Рядом с результатами обучения CY сохраняет `ultralytics_requested.yaml` (в `<project>/.configs/<name>/`) и `ultralytics.yaml` (в каталоге обучения ([training directory](../../GLOSSARY.md#training-directory))) с запрошенными и действующими параметрами.

## См. также

- [`ultralytics_predict`](ultralytics-predict.md) — параметры предсказания.
- [`model`](model.md) — выбор семейства моделей и параметры других backend.
- [`transforms`](transforms.md) — пайплайн аугментаций.
- [Как устроена конфигурация](README.md) — синтаксис override и `--cfg`.
