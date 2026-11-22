# cy

`cy` запускает весь пайплайн ([pipeline](../../GLOSSARY.md#pipeline)) в одной задаче ClearML (task): обучение, предсказания, метрики, сравнение с [baseline](../../GLOSSARY.md#baseline) и отчёт. Используйте его, когда нужно получить обученную модель и её оценку за один запуск; отдельные этапы ([stage](../../GLOSSARY.md#stage)) выполняют команды [`cy-train`](cy-train.md), [`cy-predict`](cy-predict.md), [`cy-metrics`](cy-metrics.md), [`cy-compare`](cy-compare.md) и [`cy-report`](cy-report.md).

## Примеры

```bash
cy ground_truth=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
```

Полный пайплайн с моделью Ultralytics YOLO по умолчанию; результаты пишутся в `runs/my-project/my-run-<task-id>/`.

```bash
cy ground_truth=data/ground_truth.csv model=deimv2/s model.train.epochs=50 run_id=my-run
```

Другое семейство моделей ([detector family](../../GLOSSARY.md#detector-family)); каталог запуска ([run directory](../../GLOSSARY.md#run-directory)) — `runs/my-run`.

```bash
cy ground_truth=data/ground_truth.csv run_id=my-run skip_train=true
```

Повторяет предсказания, метрики, сравнение и отчёт для checkpoint `runs/my-run/detect/train/weights/best.pt`, обученного ранее.

```bash
cy ground_truth=data/ground_truth.csv skip_train=true weights=weights/best.pt model_label=my-model skip_compare=true skip_report=true
```

Оценивает готовые веса (weights) без обучения, сравнения и отчёта. Без `skip_report=true` этап отчёта при `skip_train=true skip_compare=true` ищет `comparison/` прошлого запуска и в новом каталоге запуска завершается ошибкой.

## Синтаксис и аргументы

```text
cy [--config-dir configs] [--cfg job] [-m] key=value ...
```

`cy` — приложение Hydra: аргументы — это override ключей конфигурации `pipeline`. Синтаксис override, локальные YAML, `--cfg` и `--multirun` описаны в [Конфигурации](../configuration/README.md). Обязателен только `ground_truth`.

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `ground_truth` | обязателен | Разметка ([ground truth](../../GLOSSARY.md#ground-truth)): путь к CSV или ссылка на датасет ClearML, см. [Разметка](../formats/ground-truth.md) |
| `model` | `ultralytics` | Семейство моделей и preset, группа [`model`](../configuration/model.md) |
| `ultralytics` | группа | Параметры обучения Ultralytics, группа [`ultralytics`](../configuration/ultralytics.md) |
| `ultralytics_predict` | группа | Параметры предсказания Ultralytics, группа [`ultralytics_predict`](../configuration/ultralytics-predict.md) |
| `transforms` | `default` | Аугментация (augmentation) обучения, группа [`transforms`](../configuration/transforms.md) |
| `clearml` | группа | Проект, имя, тип и теги задачи ClearML, группа [`clearml`](../configuration/clearml.md) |
| `fiftyone` | группа | Публикация в FiftyOne, группа [`fiftyone`](../configuration/fiftyone.md) |
| `splits` | `[train, val, test]` | Split, на которых считаются метрики. Предсказания строятся для `val` и всех перечисленных split. Повторы удаляются |
| `dataset_format` | `ndjson` | Формат рабочей копии ([prepared dataset copy](../../GLOSSARY.md#prepared-dataset-copy)) датасета для обучения, см. [Датасеты](../formats/datasets.md#dataset_format) |
| `dataset_cache_dir` | `null` | Каталог кэша рабочих копий датасета, см. [Датасеты](../formats/datasets.md#dataset_cache_dir). Должен лежать вне каталога запуска |
| `run_id` | `null` | Имя каталога запуска: `runs/<run_id>` в рабочем каталоге ([workspace](../../GLOSSARY.md#workspace)) |
| `run_dir` | `null` | Путь к каталогу запуска внутри `CY_HOME`. Имеет приоритет над `run_id` |
| `weights` | `null` | Checkpoint для этапов после обучения. Допустим только вместе с `skip_train=true` |
| `model_label` | `null` | Подпись модели ([model identity](../../GLOSSARY.md#model-identity)) для предсказаний и метрик, когда происхождение модели ([model provenance](../../GLOSSARY.md#model-provenance)) неизвестно (например, файла `weights`, обученного вне CY) |
| `skip_train` | `false` | Пропустить обучение |
| `skip_predict` | `false` | Пропустить предсказания |
| `skip_metrics` | `false` | Пропустить метрики |
| `skip_compare` | `false` | Пропустить сравнение |
| `skip_report` | `false` | Пропустить отчёт |
| `metrics.evaluation` | группа | Настройки метрик, группа [`evaluation`](../configuration/evaluation.md) |
| `metrics.calibration_split` | `val` | Split, на котором подбираются пороги уверенности (confidence threshold). Допустимо только `val` |
| `compare.baseline_model` | последняя завершённая задача с тегом `prod` | Модель baseline для сравнения. Ключи те же, что у `baseline_model` в [`cy-compare`](cy-compare.md) |
| `compare.q` | `0.05` | Уровень значимости сравнения, см. [`cy-compare`](cy-compare.md) |
| `compare.bootstrap_iterations` | `10000` | Число итераций bootstrap, целое больше 0 |
| `compare.seed` | `0` | Seed для bootstrap, см. [`cy-compare`](cy-compare.md) |
| `report.report_config_path` | `null` | Путь к YAML настроек отчёта, см. [`cy-report`](cy-report.md) |

## Как это работает

1. CY проверяет override и конфигурацию: неизвестные ключи, ключи неактивного семейства моделей, правило записи внутри `CY_HOME` ([write containment rule](../../GLOSSARY.md#write-containment-rule)) (см. [Рабочий каталог](../workspace.md#правило-записи-внутри-cy_home)). Здесь же CY проверяет значения всех этапов, для которых не нужны файлы и задача: для YOLO — группы `ultralytics` и `ultralytics_predict` (полнота, типы и диапазоны, пустой `ultralytics.model`, `ultralytics.resume`), а также `dataset_format`, `weights` без `skip_train=true`, группы `metrics`, `compare`, `report`, `clearml` и `fiftyone`. Значение отклоняется, даже если его этап пропущен (`skip_*`) или идёт после обучения. Без `run_dir` и `run_id` ключи `project` и `ultralytics.save_dir` должны быть `null`, а `name` — `null` или имя этапа: `train` в `ultralytics`, `predict` в `ultralytics_predict`. С `run_dir` или `run_id` CY проверяет, что `dataset_cache_dir` лежит вне каталога запуска, и ключи `project`, `name` и `ultralytics.save_dir`. Как и на этапе предсказаний, CY отбрасывает ключ `ultralytics_predict.save_dir`, а при обучении сам задаёт `ultralytics_predict.task=detect`. Для других семейств моделей CY проверяет вместо групп Ultralytics `model.train` и `model.predict`, ключей путей в них нет, а `dataset_format` всегда `coco`. CY принимает и такие формы: флаг `skip_*` числом (`skip_compare=1`); ключ, удалённый через `~` или отсутствующий в сохранённой конфигурации, — он получает значение по умолчанию (обязательный ключ удалить нельзя: `Required setting <ключ> is missing`); для других семейств моделей — группу `ultralytics` или `ultralytics_predict`, удалённую целиком; `_target_` группы, который указывает на тот же класс под другим путём импорта; служебные ключи Hydra `_convert_`, `_recursive_`, `_args_` и `_partial_` в группах; `run_id` любого типа при заданном `run_dir`. Ошибка на этом шаге останавливает команду до создания задачи ClearML.
2. CY создаёт задачу ClearML и публикует в неё конфигурацию (см. [Публикация](../publication.md)).
3. CY готовит предобученные веса всех моделей из своего списка в кэше рабочего каталога. Перед этим CY записывает абсолютный путь каталога весов Ultralytics (`weights_dir`) в настройки Ultralytics, если там был относительный путь. Попытка запоминается в `.cache/clearml-yolo/preparation/`, и следующие запуски её не повторяют. Ошибка подготовки не останавливает запуск: CY пишет предупреждение `Model preparation <модель>: <сообщение>`. Повторить подготовку можно командой [`cy-download-weights`](cy-download-weights.md). Затем CY готовит веса выбранной модели, как описано в [Как выбираются веса](../configuration/model.md#как-выбираются-веса); здесь ошибка останавливает команду.
4. CY выбирает каталог запуска:
   - `run_dir` — этот путь;
   - иначе `run_id` — `runs/<run_id>`;
   - иначе `runs/<проект ClearML>/<имя задачи>-<ID задачи>` (правило кодирования имён — в [Рабочем каталоге](../workspace.md#runs)).

   Если каталог запуска задаёт задача (нет `run_dir` и `run_id`), здесь же, уже после создания задачи ClearML, CY проверяет, что `dataset_cache_dir` лежит вне него. Затем каталог создаётся, и ссылка `runs/latest` переводится на него, если каталог лежит в рабочем каталоге.
5. **Обучение** (если не `skip_train`). Разметка проверяется и собирается в рабочую копию датасета (см. [Датасеты](../formats/datasets.md)). Обучение требует изображений в split `train` и `val`; если включены предсказания или метрики — ещё во всех split из `splits`; если включено сравнение — ещё в `test`. Результат пишется в `<каталог запуска>/detect/train/`. Имя лучшего checkpoint зависит от семейства моделей (см. [`cy-train`](cy-train.md#результат)); для YOLO это `detect/train/weights/best.pt`. Если файла нет или он пустой, команда завершается ошибкой.
6. **Предсказания** (если не `skip_predict`) для split `val` и всех split из `splits` пишутся в `<каталог запуска>/predictions.csv` (формат — [Предсказания](../formats/predictions.md)). Используется checkpoint из шага 5, а при `skip_train=true` — `weights` или, без него, `detect/train/weights/best.pt` каталога запуска.
7. **Метрики** (если не `skip_metrics`) по `predictions.csv` пишутся в `<каталог запуска>/metrics/`. Пороги уверенности подбираются на `val` (см. [`evaluation`](../configuration/evaluation.md#пороги-уверенности)), и подобранные пороги ([selected confidence thresholds](../../GLOSSARY.md#selected-confidence-thresholds)) сохраняются в `metrics/frozen_thresholds.json`.
8. **Сравнение** (если не `skip_compare`) на split `test` пишется в `<каталог запуска>/comparison/`. Модель-кандидат ([candidate model](../../GLOSSARY.md#candidate-model)) — эта задача ClearML, если обучение было в этом запуске, иначе локальный checkpoint с порогами из шага 7 (или из `metrics/frozen_thresholds.json` при `skip_metrics=true`). Предсказания сравнения строятся с `conf`, `iou`, `imgsz`, `batch` и `device` из настроек предсказания. Baseline:
   - по умолчанию — последняя завершённая задача ClearML с тегом `prod` в проекте `clearml.project_name`, кроме текущей. Если такой нет, сравнение пропускается: модель-кандидат оценивается на `test` одна, отчёт не строится, команда продолжается;
   - если `compare.baseline_model` задан иначе и модель не найдена, этап сравнения завершается ошибкой `No completed ClearML task in project 'my-project' tagged ['my-tag']`.
9. **Отчёт** (если не `skip_report`) строится по `comparison/` и пишется в `<каталог запуска>/reports/` (см. [Книги Excel](../formats/workbooks.md)). Он требует успешного сравнения в этом же запуске; исключение — `skip_train=true skip_compare=true`: тогда отчёт строится по `comparison/`, оставшемуся в каталоге запуска от прошлого запуска.
10. **Визуализация**: если предсказания доступны, CY публикует разметку, предсказания и оценки в FiftyOne (см. [Публикация](../publication.md#fiftyone)).
11. После каждого этапа CY обновляет итог пайплайна ([pipeline outcome](../../GLOSSARY.md#pipeline-outcome)) в `pipeline_outcome.json` и `pipeline_outcome.txt` и в задаче ClearML.

Этап, которому нечего читать, пропускается с причиной в итоге, а не завершается ошибкой:

| Условие | Что пропускается |
| --- | --- |
| Обучение было, `skip_predict=true` | Метрики, сравнение, отчёт, визуализация: файлу `predictions.csv` от прошлого запуска CY не доверяет |
| Обучение было, `skip_metrics=true` | Сравнение и отчёт: нет порогов |
| `skip_compare=true` при обучении | Отчёт |
| Предсказания или метрики завершились ошибкой после успешного обучения | Этапы, которые читают их результат |

### Сочетания `skip_*`

| Сочетание | Что происходит |
| --- | --- |
| Без `skip_*` | Все этапы |
| `skip_train=true` | Этапы 6–10 для `weights` или для `detect/train/weights/best.pt` из каталога запуска, заданного `run_id` или `run_dir` |
| `skip_train=true skip_predict=true` | Метрики и далее по `predictions.csv` из каталога запуска |
| `skip_train=true skip_predict=true skip_metrics=true` | Сравнение с порогами из `metrics/frozen_thresholds.json` и отчёт |
| `skip_train=true skip_predict=true skip_metrics=true skip_compare=true` | Отчёт по `comparison/` из каталога запуска |
| `skip_compare=true` | Обучение, предсказания и метрики, без сравнения и отчёта |
| `skip_train=true skip_compare=true` | Предсказания, метрики и отчёт по `comparison/` из каталога запуска; если `comparison/` там нет, этап отчёта завершается ошибкой, поэтому для новых весов добавляйте `skip_report=true` |
| `skip_report=true` | Всё, кроме отчёта |

При `skip_train=true` без `weights` нужен `run_id` или `run_dir` прошлого запуска: в новом каталоге checkpoint нет, и этап предсказания завершается ошибкой.

### Семейства моделей

При `model.backend=ultralytics` (по умолчанию) обучение и предсказание берут параметры из групп `ultralytics` и `ultralytics_predict`, а `dataset_format` может быть `ndjson` или `flat`. Для других семейств (`deimv2`, `rfdetr`, `fasterrcnn`, `fcos`) параметры берутся из `model.train` и `model.predict`, изменённые ключи `ultralytics*` отклоняются, а рабочая копия датасета всегда собирается в формате `coco`. В задачу ClearML группы `ultralytics` и `ultralytics_predict` в этом случае не публикуются. Подробности — в [`model`](../configuration/model.md#особенности-семейств).

Ключи `project`, `name` и `save_dir` в `ultralytics` и `ultralytics_predict` задаёт сам `cy`: обучение пишет в `<каталог запуска>/detect/train`, предсказание Ultralytics — в `<каталог запуска>/native/predict`. Другое значение `project` или `name` и любой `ultralytics.save_dir` вызывают ошибку (см. «Частые ошибки»).

### Устройства

`ultralytics.device` и `ultralytics_predict.device` передаются в Ultralytics как заданы (исключение — `ultralytics.batch=null`, см. [`ultralytics`](../configuration/ultralytics.md)). Для других семейств устройства задают `model.train.device` и `model.predict.device`; при нескольких GPU в `model.train.device` CY запускает по одному процессу обучения на GPU и делит batch size между ними; batch size должен делиться на число GPU (`Global training batch must be positive and divisible by GPU count`). Предсказание этих семейств идёт на одном устройстве. Правила и ограничения — в [`model`](../configuration/model.md#modeltrain).

## Результат

Каталог запуска:

| Путь | Содержимое |
| --- | --- |
| `detect/train/` | Результат обучения; лучший checkpoint — см. [`cy-train`](cy-train.md#результат) (для YOLO `detect/train/weights/best.pt`) |
| `native/predict/` | Выход предсказания Ultralytics |
| `predictions.csv` | Предсказания, см. [Предсказания](../formats/predictions.md) |
| `metrics/` | Метрики и `frozen_thresholds.json`, см. [Книги Excel](../formats/workbooks.md) |
| `comparison/` | Сравнение с baseline, см. [Книги Excel](../formats/workbooks.md) |
| `reports/` | Отчёты, см. [Книги Excel](../formats/workbooks.md) |
| `pipeline_outcome.json`, `pipeline_outcome.txt` | Итог пайплайна |

Итог пайплайна перечисляет этапы со статусом `succeeded`, `completed_with_warnings`, `failed` или `skipped`, причину и файлы этапа. Его же команда пишет в лог в конце. Пример `pipeline_outcome.txt`:

```text
Pipeline outcome: completed_with_warnings
training: succeeded
  Artifact: /workspace/project/runs/my-run/detect/train/weights/best.pt
training_resources: succeeded
training_metadata: succeeded
prediction: succeeded
  Artifact: /workspace/project/runs/my-run/predictions.csv
metrics: succeeded
thresholds: succeeded
threshold_publication: succeeded
comparison: skipped — Automatic baseline unavailable
report: skipped — No successful comparison producer in this attempt
visualization: failed — <сообщение ошибки>
```

Общий статус:

- `failed` — прерывание, либо ошибка этапа, когда обучение в этом запуске не прошло или не выполнялось;
- `completed_with_warnings` — обучение прошло, но какой-то этап после него завершился ошибкой, или отчёт нашёл проблемы в числе объектов обучения (лист Issues);
- `succeeded` — иначе; пропущенные этапы на статус не влияют.

Итог пайплайна впервые записывается после успешного обучения или после пропуска обучения при `skip_train=true`. Если обучение завершилось ошибкой, `pipeline_outcome.json` и `pipeline_outcome.txt` не создаются.

Как итог отражается в статусе задачи ClearML, описано в [Публикации](../publication.md#успех-и-ошибка).

### Коды завершения

| Код | Когда |
| --- | --- |
| `0` | Пайплайн завершился со статусом `succeeded` или `completed_with_warnings`. После успешного обучения ошибки следующих этапов не меняют код |
| `1` | Ошибка конфигурации, ошибка до конца обучения или во время него, либо ошибка любого этапа при `skip_train=true` |

## Частые ошибки

Ошибки из таблицы до `Native pipeline output overrides require an explicit run_dir` включительно выводятся до создания задачи ClearML. Исключение — `dataset_cache_dir must be outside run_dir` без `run_dir` и `run_id`: тогда каталог запуска зависит от задачи, и ошибка выводится после её создания. Остальные ошибки выводятся после создания задачи, поэтому без доступного сервера ClearML вы увидите сначала ошибку подключения.

| Сообщение | Причина и решение |
| --- | --- |
| `Missing mandatory value: ground_truth` | Не задан `ground_truth` |
| `Unsupported wrapper settings: ['foo']` | Ключа нет в конфигурации `cy`; проверьте имя |
| `Legacy queue/autogpu controls are removed from direct cy commands. ...` | Заданы `queue`, `autogpu` или `auto_gpu`. Уберите их; постановка в очередь описана в [Очереди](../queue.md) |
| `Project write destination /etc/x must be contained beneath CY_HOME=/workspace/project; ...` | `run_dir`, `dataset_cache_dir` или каталог Ultralytics вне рабочего каталога |
| `Changed ultralytics settings ['epochs'] are inactive for deimv2/s; use model.train instead` | Для семейства, отличного от Ultralytics, изменён ключ `ultralytics`; задайте его в `model.train` |
| `Invalid pipeline setting run_id: ...` | `run_id` задан числом без `run_dir`, например `run_id=123`. Задайте строку: `run_id="'123'"` |
| `Required setting compare.baseline_model is missing` | В сохранённой конфигурации нет обязательного ключа. Пропуск этапа (`skip_*`) ключ не заменяет: верните его |
| `weights is only valid with skip_train=true; training chooses its model` | `weights` без `skip_train=true`. Модель для обучения задаёт `ultralytics.model` или `model` |
| `dataset_cache_dir must be outside run_dir` | `dataset_cache_dir` внутри каталога запуска |
| `project='other' conflicts with pipeline run_dir; expected /workspace/project/runs/my-run/detect` | Задан `ultralytics.project` или `ultralytics_predict.project` (аналогично `name`). Уберите ключ; путь задаёт `run_dir` |
| `save_dir conflicts with pipeline run_dir; use run_dir to route outputs` | Задан `ultralytics.save_dir` |
| `Native pipeline output overrides require an explicit run_dir` | В группе Ultralytics задан `project`, `ultralytics.save_dir` или `name`, отличный от имени этапа (`train` в `ultralytics`, `predict` в `ultralytics_predict`), а `run_dir` и `run_id` не заданы. Уберите ключ; путь задаёт `run_dir` |
| `<путь>: required split(s) contain no images: test` | В разметке нет изображений split, который нужен включённым этапам (см. шаг 5). Добавьте split в разметку, уберите его из `splits` или отключите этап, например `skip_compare=true` для `test` |
| `Training did not produce a usable checkpoint: <путь>` | Обучение не оставило `best.pt` или он пустой |
| `Model provenance is unavailable; supply a custom model_label (comparison model references use label)` | Происхождение модели неизвестно; задайте `model_label` |
| `No completed ClearML task in project 'my-project' tagged ['my-tag']` | Явно заданный `compare.baseline_model` не найден |

## См. также

- [`cy-train`](cy-train.md) — только обучение
- [Конфигурация](../configuration/README.md)
- [Рабочий каталог](../workspace.md)
- [Публикация в ClearML и FiftyOne](../publication.md)
- [Сценарии](../scenarios.md)
