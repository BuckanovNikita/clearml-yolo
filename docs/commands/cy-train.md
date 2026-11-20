# cy-train

`cy-train` обучает модель по CSV разметки ([ground truth](../../GLOSSARY.md#ground-truth)) в отдельной задаче ClearML (task) и ничего больше не делает: предсказания, метрики и сравнение не запускаются. Используйте его, когда этапы ([stage](../../GLOSSARY.md#stage)) нужно выполнять по отдельности; весь пайплайн ([pipeline](../../GLOSSARY.md#pipeline)) запускает [`cy`](cy.md).

## Примеры

```bash
cy-train ground_truth=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
```

Обучение Ultralytics YOLO с параметрами по умолчанию.

```bash
cy-train ground_truth=data/ground_truth.csv ultralytics.model=yolo11s.pt ultralytics.epochs=50 ultralytics.device=0
```

Другая модель YOLO, число эпох и GPU.

```bash
cy-train ground_truth=data/ground_truth.csv model=fasterrcnn/resnet50_fpn model.train.epochs=50 required_splits=[train,val,test]
```

Другое семейство моделей ([detector family](../../GLOSSARY.md#detector-family)); обучение требует изображений и в split `test`.

## Синтаксис и аргументы

```text
cy-train [--config-dir configs] [--cfg job] [-m] key=value ...
```

`cy-train` — приложение Hydra: аргументы — это override ключей конфигурации `train`. Синтаксис override, локальные YAML, `--cfg` и `--multirun` описаны в [Конфигурации](../configuration/README.md). Обязателен только `ground_truth`.

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `ground_truth` | обязателен | Разметка: путь к CSV или ссылка на датасет ClearML, см. [Разметка](../formats/ground-truth.md) |
| `model` | `ultralytics` | Семейство моделей и preset, группа [`model`](../configuration/model.md) |
| `ultralytics` | группа | Параметры обучения Ultralytics, группа [`ultralytics`](../configuration/ultralytics.md) |
| `ultralytics_predict` | группа | Группа [`ultralytics_predict`](../configuration/ultralytics-predict.md). `cy-train` только проверяет её ключи и не предсказывает |
| `transforms` | `default` | Аугментация (augmentation), группа [`transforms`](../configuration/transforms.md) |
| `clearml` | группа | Проект, имя, тип и теги задачи ClearML, группа [`clearml`](../configuration/clearml.md) |
| `dataset_format` | `ndjson` | Формат рабочей копии ([prepared dataset copy](../../GLOSSARY.md#prepared-dataset-copy)) датасета, см. [Датасеты](../formats/datasets.md#dataset_format) |
| `dataset_cache_dir` | `null` | Каталог кэша рабочих копий датасета, см. [Датасеты](../formats/datasets.md#dataset_cache_dir). Должен лежать вне `ultralytics.project` |
| `required_splits` | `null` | Split, в которых должны быть изображения. `train` и `val` требуются всегда; `null` — только они |

## Как это работает

1. CY проверяет override и конфигурацию: неизвестные ключи, ключи неактивного семейства моделей, пути `dataset_cache_dir`, `ultralytics.project`, `ultralytics.name` и `ultralytics.save_dir` внутри `CY_HOME` (см. [Рабочий каталог](../workspace.md#правило-записи-внутри-cy_home) ([workspace](../../GLOSSARY.md#workspace))). Ошибка на этом шаге останавливает команду до создания задачи ClearML. Пустой `ultralytics.model`, `ultralytics.resume` и список `required_splits` проверяются позже, уже после создания задачи.
2. CY создаёт задачу ClearML, публикует в неё конфигурацию (см. [Публикация](../publication.md)) и готовит веса (weights) выбранной модели, как описано в [Как выбираются веса](../configuration/model.md#как-выбираются-веса). В отличие от `cy`, остальные модели из списка CY не готовятся.
3. CY выбирает каталог обучения ([training directory](../../GLOSSARY.md#training-directory)):
   - если задан `ultralytics.project` — этот каталог;
   - иначе `runs/<проект ClearML>/<имя задачи>-<ID задачи>/detect` (правило кодирования имён — в [Рабочем каталоге](../workspace.md#runs)); каталог запуска ([run directory](../../GLOSSARY.md#run-directory)) создаётся, и ссылка `runs/latest` переводится на него.

   Подкаталог — `ultralytics.name`, а без него — имя задачи ClearML в том же кодировании.
4. Разметка проверяется и собирается в рабочую копию датасета в кэше (см. [Датасеты](../formats/datasets.md)); проверяется наличие изображений в `train`, `val` и split из `required_splits`.
5. Обучение пишет результат в `<каталог обучения>/<подкаталог>/`. Для семейства Ultralytics параметры берутся из группы `ultralytics`, для остальных — из `model.train`, а рабочая копия датасета всегда собирается в формате `coco` (см. [`model`](../configuration/model.md#особенности-семейств)).

### Устройства

`ultralytics.device` передаётся в Ultralytics как задан (исключение — `ultralytics.batch=null`, см. [`ultralytics`](../configuration/ultralytics.md)). Для других семейств устройство задаёт `model.train.device`; при нескольких GPU CY запускает по одному процессу обучения на GPU и делит batch size между ними поровну, поэтому batch size должен делиться на число GPU (см. [`model`](../configuration/model.md#modeltrain)).

## Результат

Каталог `<каталог обучения>/<подкаталог>/` с результатом обучения. Лучший checkpoint в нём зависит от семейства моделей, и его путь команда пишет в журнал:

| Семейство | Лучший checkpoint |
| --- | --- |
| Ultralytics YOLO | `weights/best.pt` |
| DEIMv2 | `best_stg2.pth`, а если его нет — `best_stg1.pth` |
| RF-DETR | `checkpoint_best_total.pth` |
| Faster R-CNN, FCOS | `best.pth` |

Без `ultralytics.project` и `ultralytics.name` для YOLO это `runs/my-project/my-run-<task-id>/detect/my-run/weights/best.pt`. Если обучение не оставило этого файла, команда завершается ошибкой.

В checkpoint DEIMv2, RF-DETR, Faster R-CNN и FCOS CY встраивает описание модели: семейство, preset, классы и параметры предобработки. Рядом CY пишет `<имя checkpoint>.model.json` с тем же описанием и SHA-256 файла. Если этот файл лежит рядом, он должен совпадать с checkpoint, иначе команда, которая читает веса, останавливается: `Checkpoint hash disagrees with its stored descriptor`. Изменив checkpoint, удалите старый `.model.json`.

Что публикуется в ClearML, описано в [Публикации](../publication.md).

### Коды завершения

| Код | Когда |
| --- | --- |
| `0` | Обучение завершилось |
| `1` | Ошибка конфигурации, подготовки данных или весов, либо обучения |

## Частые ошибки

| Сообщение | Причина и решение |
| --- | --- |
| `Missing mandatory value: ground_truth` | Не задан `ground_truth` |
| `Changed ultralytics settings ['epochs'] are inactive for deimv2/s; use model.train instead` | Для семейства, отличного от Ultralytics, изменён ключ `ultralytics`; задайте его в `model.train` |
| `Legacy queue/autogpu controls are removed from direct cy commands. ...` | Заданы `queue`, `autogpu` или `auto_gpu`. Уберите их; постановка в очередь описана в [Очереди](../queue.md) |
| `Project write destination /etc/x must be contained beneath CY_HOME=/workspace/project; ...` | `ultralytics.project`, `dataset_cache_dir` или другой путь записи вне рабочего каталога |
| `dataset_cache_dir must be outside the run-owned training project` | Кэш датасета внутри каталога обучения |
| `Changed model.train settings ['epochs'] are inactive for ultralytics; use ultralytics instead` | Для семейства Ultralytics изменён ключ `model.train`; задайте его в группе `ultralytics` |
| `Global training batch must be positive and divisible by GPU count` | Для семейства, отличного от Ultralytics, batch size в `model.train.batch` не делится на число GPU в `model.train.device` |
| `Unsupported required split(s): foo; expected train, val, or test` | В `required_splits` указан неизвестный split |
| `Set ultralytics.model explicitly; no training model fallback is provided` | `ultralytics.model` пустой |
| `resume is unsupported with ground_truth; use model weights to fine-tune` | Задан `ultralytics.resume`; для дообучения укажите веса в `ultralytics.model` |
| `data/ground_truth.csv: required split(s) contain no images: val` | Нет изображений в обязательном split, см. [Разметка](../formats/ground-truth.md). Если рабочая копия уже есть в кэше, сообщение начинается с `Cached dataset required split(s) contain no images:` |

## См. также

- [`cy`](cy.md) — весь пайплайн
- [`cy-predict`](cy-predict.md) — предсказания по обученным весам
- [Конфигурация](../configuration/README.md)
- [Датасеты](../formats/datasets.md)
- [Рабочий каталог](../workspace.md)
