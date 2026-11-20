# cy-predict

`cy-predict` прогоняет готовые веса (weights) по изображениям из файла разметки ([ground truth](../../GLOSSARY.md#ground-truth)) и записывает предсказания (predictions) в CSV. Команда нужна, когда модель уже обучена и вы хотите отдельно получить предсказания, чтобы затем посчитать по ним метрики командой [`cy-metrics`](cy-metrics.md) или сравнить модели.

## Примеры

```bash
cy-predict weights=weights/best.pt ground_truth=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
```

Предсказания Ultralytics YOLO для всех изображений разметки; CSV пишется в каталог запуска ([run directory](../../GLOSSARY.md#run-directory)).

```bash
cy-predict model=rfdetr/small weights=weights/best.pt ground_truth=data/ground_truth.csv 'splits=[val,test]' model.predict.conf=0.01 fiftyone.enabled=false clearml.project_name=my-project clearml.task_name=my-run
```

Предсказания RF-DETR только для split `val` и `test`, без публикации в FiftyOne.

```bash
cy-predict weights=<task-id> ground_truth=data/ground_truth.csv output=runs/my-run/predict.csv clearml.project_name=my-project clearml.task_name=my-run 'clearml.tags=[my-tag]'
```

Веса берутся из задачи ClearML (task) обучения, CSV пишется по заданному пути.

## Синтаксис и аргументы

```text
cy-predict [--config-dir configs] [ключ=значение ...]
```

Команда — приложение Hydra: она принимает override `ключ=значение` поверх собранной конфигурации. Синтаксис override, `--config-dir`, `--cfg job` и `--multirun` описаны в разделе [Конфигурация](../configuration/README.md).

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `model` | `ultralytics` | Семейство моделей ([detector family](../../GLOSSARY.md#detector-family)) и preset, а для семейств, кроме Ultralytics YOLO, — параметры предсказания `model.predict`. См. [группа `model`](../configuration/model.md). |
| `ultralytics` | см. страницу группы | Параметры обучения Ultralytics. В `cy-predict` нужны только как источник значений, которые `ultralytics_predict` наследует через `${ultralytics.…}`, например `imgsz`. См. [группа `ultralytics`](../configuration/ultralytics.md). |
| `ultralytics_predict` | см. страницу группы | Параметры предсказания Ultralytics YOLO. См. [группа `ultralytics_predict`](../configuration/ultralytics-predict.md). |
| `weights` | `null` | Веса для предсказания: путь к файлу, ID задачи ClearML или ссылка `clearml://<ID модели>`. См. [Как выбираются веса](#как-выбираются-веса). |
| `model_label` | `null` | Подпись модели ([model identity](../../GLOSSARY.md#model-identity)) в результатах, если происхождение модели ([model provenance](../../GLOSSARY.md#model-provenance)) неизвестно. См. [`model_label`](#model_label). |
| `ground_truth` | обязателен | Разметка: путь к CSV или ссылка на датасет ClearML. Формат — [Разметка](../formats/ground-truth.md). |
| `output` | `null` | Путь CSV с предсказаниями. `null` — `predict.csv` в каталоге запуска, см. [Результат](#результат). Путь должен лежать внутри `CY_HOME`. |
| `splits` | `null` | Список split, для изображений которых строятся предсказания, например `splits=[val,test]`. `null` — все изображения разметки. |
| `image_name` | `name` | Что записывается в колонку `image_name`: `name`, `stem` или `path`. См. [Предсказания](../formats/predictions.md). |
| `clearml` | см. страницу группы | Проект, имя, теги задачи ClearML. См. [группа `clearml`](../configuration/clearml.md). |
| `fiftyone` | см. страницу группы | Публикация в FiftyOne; `fiftyone.enabled=false` отключает её. См. [группа `fiftyone`](../configuration/fiftyone.md). |

### Как выбираются веса

Файл весов задаётся одним из двух способов:

- ключом `weights`;
- для Ultralytics YOLO — ключом `ultralytics_predict.model`.

Если заданы оба и они различаются, команда останавливается: `weights conflicts with ultralytics_predict.model` (для других семейств — `weights conflicts with the native prediction model`). Если не задан ни один: `Prediction requires weights=<checkpoint> or ultralytics_predict.model`.

Значение разбирается так:

1. Существующий локальный файл используется как есть.
2. Строка из 32 шестнадцатеричных символов, которой нет на диске, считается ID задачи ClearML. CY скачивает выбранный checkpoint этой задачи и, если в задаче записан его SHA-256, сверяет его с файлом.
3. `clearml://<ID модели>` — модель из реестра моделей ClearML. CY скачивает её и, если в модели записан SHA-256, сверяет его с файлом.
4. Иное значение (например имя `yolo11n.pt`) передаётся Ultralytics, который ищет или скачивает веса сам.

Checkpoint семейств DEIMv2, RF-DETR, Faster R-CNN и FCOS хранит описание модели ([checkpoint descriptor](../../GLOSSARY.md#checkpoint-descriptor)): семейство, preset, классы и предобработку. При `model=` такого семейства checkpoint обязан содержать описание модели, и оно должно совпадать с выбранными семейством и preset (см. [группа `model`](../configuration/model.md)). При `model=ultralytics` checkpoint без такого описания обрабатывается Ultralytics.

### `model_label`

Каждый результат привязывается к происхождению модели. Происхождение известно, если веса взяты из задачи или модели ClearML, или если рядом с локальным файлом лежит `<имя файла>.identity.json`, который CY пишет при публикации весов обучения. В этих случаях `model_label` не используется.

Для любого другого файла `model_label` обязателен, иначе команда останавливается: `Model provenance is unavailable; supply a custom model_label (comparison model references use label)`. Тогда подпись модели — значение `model_label`, а в происхождение модели записывается SHA-256 файла.

### Параметры предсказания по семействам

- Ultralytics YOLO (`model=ultralytics`): параметры берутся из `ultralytics_predict`. Изменённые ключи `model.predict` отклоняются до запуска. `ultralytics_predict.source` задавать нельзя: список изображений строит сама команда из разметки. `imgsz` должен быть задан (иначе `Set imgsz explicitly in ultralytics_predict`); по умолчанию он наследуется из `ultralytics.imgsz`.
- DEIMv2, RF-DETR, Faster R-CNN, FCOS: параметры берутся из `model.predict` (`device`, `batch`, `imgsz`, `conf`, `iou`, `max_det`, `half`). Изменённые ключи `ultralytics_predict` и `ultralytics` отклоняются до запуска. Если `model.predict.imgsz` равен `null`, используется разрешение, записанное в checkpoint.

Ключи `ultralytics_predict.project` и `ultralytics_predict.name` по умолчанию указывают на `<каталог CSV>/native/predict`.

## Как это работает

1. Hydra собирает конфигурацию. До создания задачи ClearML команда проверяет ключи, форму значения `ground_truth`, неактивные группы семейства и пути записи по правилу записи внутри `CY_HOME` ([write containment rule](../../GLOSSARY.md#write-containment-rule)) (см. [Рабочий каталог](../workspace.md#правило-записи-внутри-cy_home)).
2. Создаётся задача ClearML. Если `output` не задан, путь CSV выбирается после этого, по имени и ID задачи.
3. Если `ground_truth` ссылается на датасет ClearML, он скачивается.
4. Веса разрешаются (см. выше) и для них определяется происхождение модели.
5. В задачу записывается таблица разрешения: при каком `imgsz` обучена модель и при каком она оценивается. Для YOLO при расхождении пишется предупреждение.
6. Из разметки выбираются уникальные `image_path`. С `splits` изображения обрабатываются группами по split в указанном порядке; без `splits` — одной группой.
7. Для каждой группы рядом с CSV пишутся список изображений и YAML-файлы настроек, затем модель предсказывает. Если хотя бы одно изображение не удалось прочитать, команда останавливается.
8. Все группы объединяются в один CSV, рядом пишется `.provenance.json`.
9. Разметка и предсказания публикуются в ClearML, затем, если включено, в FiftyOne.

## Результат

В каталоге CSV (по умолчанию каталог запуска `runs/<проект>/<имя задачи>-<ID задачи>/`, см. [Рабочий каталог](../workspace.md)). Имя задачи у `cy-predict` — `<clearml.task_name>/predict`, и `/` в имени каталога кодируется: при `clearml.project_name=my-project clearml.task_name=my-run` CSV по умолчанию — `runs/my-project/my-run%2Fpredict-<task-id>/predict.csv`.

| Файл | Содержимое |
| --- | --- |
| `predict.csv` (или путь `output`) | Предсказания, формат — [Предсказания](../formats/predictions.md). |
| `predict.csv.provenance.json` | Связь предсказаний с весами и режимом `image_name`. |
| `ultralytics_predict.yaml`, `ultralytics_predict_<N>.yaml` | Фактические настройки предсказания для группы 0, 1, … |
| `ultralytics_predict_requested.yaml`, `ultralytics_predict_<N>_requested.yaml` | Запрошенные настройки для той же группы. |
| `prediction_inputs/<N>/images.txt` | Абсолютные пути изображений группы `<N>`. |
| `native/predict/` | Каталог предсказателя, если он что-то сохраняет. |

В конце команда пишет в лог `Wrote <число> predictions to <путь>`.

Что появляется в задаче ClearML (артефакты `gt_csv`, `predicts_csv`, таблица `predict` / `resolution`) и в FiftyOne, описано в разделе [Публикация](../publication.md).

### Коды завершения

| Код | Когда |
| --- | --- |
| `0` | Предсказания записаны и опубликованы. |
| `1` | Любая ошибка: конфигурация, пути, веса, разметка, ClearML, FiftyOne, предсказание. |

## Частые ошибки

```text
omegaconf.errors.MissingMandatoryValue: Missing mandatory value: ground_truth
```

Не задан `ground_truth`. Добавьте `ground_truth=data/ground_truth.csv`.

```text
ValueError: Changed model.predict settings ['conf'] are inactive for ultralytics; use ultralytics_predict instead
```

Для YOLO параметры предсказания задаются в `ultralytics_predict`, например `ultralytics_predict.conf=0.5`.

```text
ValueError: Changed ultralytics_predict settings ['conf'] are inactive for rfdetr/small; use model.predict instead
```

Для других семейств — наоборот: `model.predict.conf=0.5`.

```text
ValueError: Project write destination /elsewhere/x.csv must be contained beneath CY_HOME=/workspace/project; choose a destination inside CY_HOME or select the intended project workspace. External input and library configuration paths remain supported.
```

`output` лежит вне рабочего каталога ([workspace](../../GLOSSARY.md#workspace)). Укажите путь внутри `CY_HOME`.

```text
ValueError: No ground-truth rows for splits ['test']
```

В разметке нет строк с указанным split. Исправьте `splits` или разметку.

```text
ValueError: Model provenance is unavailable; supply a custom model_label (comparison model references use label)
```

Происхождение модели для локального файла весов неизвестно. Добавьте `model_label=my-model`.

```text
ValueError: Native detector weights require a bound checkpoint descriptor; raw comparison weights require explicit ModelRef metadata
```

Выбрано семейство, кроме Ultralytics YOLO, а checkpoint не содержит описания модели. Используйте checkpoint, записанный обучением CY для этого семейства.

```text
ValueError: Explicit model selection disagrees with the checkpoint descriptor
```

Семейство или preset в `model=` не совпадает с записанным в checkpoint. Укажите `model=<семейство>/<preset>` checkpoint.

```text
ValueError: Ultralytics returned no result for 1 of 10 images; they are undecodable or not a recognised image format: ['images/a.jpg']
```

Изображение повреждено или имеет неподдерживаемый формат. Исправьте или уберите его из разметки.

## См. также

- [`cy-metrics`](cy-metrics.md), [`cy-val`](cy-val.md), [`cy`](cy.md)
- [Группа `model`](../configuration/model.md), [`ultralytics_predict`](../configuration/ultralytics-predict.md)
- [Предсказания](../formats/predictions.md), [Разметка](../formats/ground-truth.md)
- [Рабочий каталог](../workspace.md), [Публикация](../publication.md)
- [Сценарии](../scenarios.md)
