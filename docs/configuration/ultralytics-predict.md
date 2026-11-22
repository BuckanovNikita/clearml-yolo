# Группа `ultralytics_predict`

Группа конфигурации (config group) `ultralytics_predict` содержит нативные параметры предсказания Ultralytics YOLO. CY передаёт их в `YOLO.predict()`; эта страница перечисляет каждый ключ, значение по умолчанию, которое собирает CY, и то, что CY меняет, ограничивает или запрещает.

Часть ключей по умолчанию ссылается на группу [`ultralytics`](ultralytics.md) (интерполяция `${ultralytics.<ключ>}`): если изменить ключ в `ultralytics`, то же значение получит и предсказание. Такие ключи помечены в таблице как «из `ultralytics`». Override в `ultralytics_predict` заменяет ссылку своим значением.

## Где действует группа

| Команда | Как используется `ultralytics_predict` |
| --- | --- |
| `cy` | Этапы ([stage](../../GLOSSARY.md#stage)) предсказания и сравнения пайплайна ([pipeline](../../GLOSSARY.md#pipeline)). |
| `cy-predict` | Предсказание. |
| `cy-val` | Предсказание перед расчётом метрик. |
| `cy-compare` | Предсказание обеих моделей. Ключи `model`, `project` и `name` должны оставаться `null` (см. таблицу ниже), `task`, `mode` и `source` задаёт CY. |
| `cy-train` | Группа есть в конфигурации, но не используется: CY только проверяет, что в ней нет неизвестных ключей и `cfg` равен `null`. |

У `cy-metrics`, `cy-report`, `cy-ground-truth` и `cy-export` этой группы нет.

Группа действует только при `model.backend=ultralytics` (по умолчанию). Для другого семейства моделей ([detector family](../../GLOSSARY.md#detector-family)) параметры предсказания задаются в `model.predict.*` (см. [`model`](model.md)). Если при другом backend изменить любой ключ этой группы, команда завершается до запуска задачи ClearML (task):

```text
ValueError: Changed ultralytics_predict settings ['conf'] are inactive for rfdetr/nano; use model.predict instead
```

При `model.backend=ultralytics` изменённые ключи `model.predict.*` отклоняются сообщением `Changed model.predict settings [...] are inactive for ultralytics; use ultralytics_predict instead`.

## Как задавать ключи

Ключи из таблицы меняются обычным override: `ultralytics_predict.batch=8`. Синтаксис override описан на странице [Конфигурация](README.md). Нативный ключ Ultralytics, которого нет в собранной группе, добавляется через `+`. Правила те же, что у группы [`ultralytics`](ultralytics.md#как-задавать-ключи): неизвестный ключ отклоняется (`Unknown Ultralytics parameters: [...]`), `cfg` должен быть `null`, известный ключ, который к предсказанию детектора не относится, молча отбрасывается. `embed` отклоняется: `embed is unsupported for detection records; remove its override`.

Пути `project` и `name` CY проверяет при запуске команды, ещё до задачи ClearML, даже с `--cfg job`: они должны лежать внутри `CY_HOME`, иначе `Project write destination ... must be contained beneath CY_HOME=...` (см. [правило записи внутри `CY_HOME`](../workspace.md#правило-записи-внутри-cy_home) ([write containment rule](../../GLOSSARY.md#write-containment-rule))).

Остальные значения — полноту группы, типы и диапазоны — CY тоже проверяет до создания задачи ClearML. Ошибки имеют вид `ultralytics_predict.conf must be between 0 and 1`.

## Ключи

Значения по умолчанию получены командой `cy --cfg job`; у `cy-train`, `cy-predict`, `cy-val` и `cy-compare` они такие же.

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `task` | из `ultralytics` (`detect`) | Тип задачи. Должен быть `detect` (`ultralytics_predict.task must be detect`). |
| `mode` | `predict` | Режим Ultralytics. Должен быть `predict` (`ultralytics_predict.mode must be predict`). |
| `model` | `null` | Checkpoint для предсказания. В `cy-predict` и `cy-val` его можно задать здесь или аргументом `weights`; если заданы оба и они различаются, команда завершается ошибкой `weights conflicts with ultralytics_predict.model`. Если не задан ни один: `Prediction requires weights=<checkpoint> or ultralytics_predict.model`. В `cy` checkpoint берётся из этапа обучения или из `weights` при `skip_train=true`. В `cy-compare` должен быть `null`: модели задают `baseline_model` и `candidate_model`, иначе `Prediction ['model'] are owned by comparison; use baseline_model/candidate_model and output_dir`. Загруженная модель должна быть детектором. |
| `data` | из `ultralytics` (`null`) | Файл описания датасета; передаётся в Ultralytics как есть. Изображения для предсказания CY берёт из разметки ([ground truth](../../GLOSSARY.md#ground-truth)), а не отсюда. |
| `batch` | `1` | Batch size предсказания. Только положительное целое: `Prediction requires a positive integer ultralytics_predict.batch`. |
| `imgsz` | из `ultralytics` (`960`) | Размер входа: положительное целое или `[h, w]`. Другое значение, в том числе `null`, отклоняется: `ultralytics_predict.imgsz must contain positive integer image dimensions`. Если веса обучены на другом размере, CY пишет предупреждение, но использует заданный `imgsz`. |
| `save` | `false` | Сохранять изображения с результатами. В Ultralytics по умолчанию `true`; CY выключает. |
| `device` | `[-1]` | Устройство: `0`, `[0,1]`, `cpu`, `mps`; `-1` — Ultralytics выбирает свободную GPU. |
| `project` | `null` | Корень нативных результатов предсказания. В `cy-predict` и `cy-val` при `null` это `native` рядом с CSV предсказаний (predictions). Путь должен лежать внутри рабочего каталога ([workspace](../../GLOSSARY.md#workspace)) `CY_HOME` (см. [Рабочий каталог](../workspace.md)). В `cy` без `run_dir` и `run_id` значение должно оставаться `null`: каталог запуска ([run directory](../../GLOSSARY.md#run-directory)) тогда зависит от задачи, и до её создания команда завершается ошибкой `Native pipeline output overrides require an explicit run_dir`. С `run_dir` или `run_id` допустимо только `null` или полный путь `native` внутри каталога запуска; другое значение отклоняется до создания задачи: `project='...' conflicts with pipeline run_dir; expected ...`. В `cy-compare` должен быть `null`, иначе `Prediction ['project'] are owned by comparison; use baseline_model/candidate_model and output_dir`. |
| `name` | `null` | Подкаталог внутри `project`; при `null` — `predict`. В `cy` допустимо только `null` или `predict`. Другое значение отклоняется до создания задачи: без `run_dir` и `run_id` — `Native pipeline output overrides require an explicit run_dir`, с ними — `name='...' conflicts with pipeline run_dir; expected predict`. В `cy-compare` должен быть `null`. |
| `exist_ok` | из `ultralytics` (`false`) | Писать в существующий каталог `project/name`, а не создавать новый с номером. |
| `verbose` | `false` | Подробный лог Ultralytics. CY всегда выключает его при предсказании и показывает собственный прогресс; значение не действует. |
| `rect` | `true` | Прямоугольный letterbox. В Ultralytics по умолчанию `false`; CY включает. |
| `compile` | из `ultralytics` (`true`) | `torch.compile()`: `true`, `false` или строка режима. |
| `channels_last` | из `ultralytics` (`null`) | Формат памяти channels-last; `null` — Ultralytics решает сам. |
| `conf` | `0.001` | Порог уверенности (confidence threshold). От 0 до 1. В Ultralytics по умолчанию для предсказания `0.25`. |
| `iou` | из `ultralytics` (`0.7`) | Порог IoU для NMS. От 0 до 1. |
| `max_det` | из `ultralytics` (`300`) | Максимум детекций на изображение. |
| `quantize` | из `ultralytics` (`null`) | Точность вычислений: `16`/`fp16` — половинная, `32`/`fp32`/`null` — полная. |
| `dnn` | `false` | Использовать OpenCV DNN для ONNX. |
| `nms` | из `ultralytics` (`true`) | `true` или `null` — обычный NMS; `false` — голова без NMS, если модель её поддерживает. |
| `source` | `null` | Источник изображений. Должен оставаться `null`: изображения задаёт разметка, иначе `ultralytics source is owned by ground_truth image membership`. |
| `visualize` | из `ultralytics` (`false`) | Сохранять карты активаций. |
| `augment` | из `ultralytics` (`false`) | Test-time augmentation. |
| `agnostic_nms` | из `ultralytics` (`false`) | NMS без учёта классов. |
| `classes` | из `ultralytics` (`null`) | Фильтр по номерам классов. В `cy`, если обучение не пропущено (`skip_train=false`), CY принудительно ставит `null` и пишет об этом в лог. |
| `show` | `false` | Показывать изображения в окне. |
| `save_txt` | из `ultralytics` (`false`) | Сохранять результаты в `.txt`. |
| `save_conf` | из `ultralytics` (`false`) | Добавлять уверенность в `.txt`. |
| `save_crop` | `false` | Сохранять вырезанные области предсказаний. |
| `show_labels` | из `ultralytics` (`true`) | Подписывать классы на изображениях. |
| `show_conf` | из `ultralytics` (`true`) | Подписывать уверенность на изображениях. |
| `show_boxes` | `true` | Рисовать рамки (bounding box). |
| `line_width` | `null` | Толщина линий рамок; `null` — по размеру изображения. |

## Что записывается

В `cy-predict`, `cy-val` и на этапе предсказания `cy` CY сохраняет рядом с CSV предсказаний `ultralytics_predict.yaml` (действующие параметры) и `ultralytics_predict_requested.yaml` (запрошенные); для каждого split после первого к имени добавляется номер, например `ultralytics_predict_1.yaml` и `ultralytics_predict_1_requested.yaml`. `cy-compare` пишет такие же пары файлов для каждой модели и каждого split, с ролью модели и split в имени.

## См. также

- [`ultralytics`](ultralytics.md) — параметры обучения и источник интерполированных ключей.
- [`model`](model.md) — выбор семейства моделей и параметры других backend.
- [Как устроена конфигурация](README.md) — синтаксис override и `--cfg`.
