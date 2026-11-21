# Публикация в ClearML и FiftyOne

Эта страница описывает, что запуск команды CY оставляет в ClearML и FiftyOne: задачу ClearML (task), её объекты конфигурации ([configuration object](../GLOSSARY.md#configuration-object)), артефакты, графики, скаляры и модели, датасеты FiftyOne и их поля, а также когда запуск считается успешным. Она нужна, чтобы найти результаты запуска в веб-интерфейсе и понять, почему задача завершилась со статусом ошибки или с предупреждением.

Настройки задачи задаёт группа [`clearml`](configuration/clearml.md), настройки FiftyOne — группа [`fiftyone`](configuration/fiftyone.md). Подключение к серверам описано в разделе [Установка](installation.md). Локальные файлы запуска описаны в разделах [Рабочий каталог](workspace.md) ([workspace](../GLOSSARY.md#workspace)) и [Книги Excel](formats/workbooks.md).

## Задача ClearML

Каждый запуск Hydra-команды создаёт ровно одну задачу ClearML и сам выставляет её итоговый статус. Этапы ([stage](../GLOSSARY.md#stage)) внутри команды (например обучение, предсказание и метрики в `cy` или предсказание и метрики в `cy-val`) пишут в эту же задачу, отдельных задач для этапов нет. Утилиты `cy-init-config`, `cy-dedup`, `cy-download-weights` и `cy-batch-estimate` задач ClearML не создают.

| Параметр | Значение |
| --- | --- |
| Проект | `clearml.project_name` |
| Имя | `clearml.task_name` для `cy`; `<clearml.task_name>/<этап>` для остальных команд |
| Тип | `clearml.task_type` |
| Теги | `clearml.tags`; при multirun ещё тег multirun ([multirun tag](../GLOSSARY.md#multirun-tag)) вида `multirun-<дата>-<время>-<слова>` |
| Хранилище артефактов | `clearml.output_uri` |

Этап в имени задачи по командам:

| Команда | Имя задачи при `clearml.task_name=my-run` |
| --- | --- |
| `cy` | `my-run` |
| `cy-train` | `my-run/train` |
| `cy-predict` | `my-run/predict` |
| `cy-val` | `my-run/val` |
| `cy-metrics` | `my-run/metrics` |
| `cy-report` | `my-run/report` |
| `cy-compare` | `my-run/compare` |
| `cy-ground-truth` | `my-run/ground_truth` |
| `cy-export` | `my-run/export` |

Имя задачи в проекте уникально. Если задача с таким именем в проекте уже есть (в том числе в архиве), CY добавляет к имени случайный суффикс из двух слов, например `my-run/train-swift-otter`, и повторяет проверку. Тот же суффикс получает выходная модель ([output model](../GLOSSARY.md#output-model)) задачи. Если свободное имя не найдено за 20 попыток, команда завершается ошибкой `Cannot resolve project-local experiment/model names after 20 attempts`. Каталог запуска ([run directory](../GLOSSARY.md#run-directory)) при переименовании не меняется: его путь строится из исходного имени.

Сразу после создания задачи команда печатает её ID и ссылку на страницу результатов:

```text
ClearML Task: created new task id=<task-id>
ClearML results page: ...
```

Вывод команды в терминал публикуется во вкладку Console задачи, а скаляры — в её графики. CY отправляет их в ClearML порциями раз в 2 секунды. Перед тем как отметить задачу завершённой, команда до 8 секунд ждёт подтверждения, что весь вывод доставлен; иначе публикация завершается ошибкой `Console publication barrier deadline expired; logs retained`, а локальные журналы сохраняются (см. [Рабочий каталог](workspace.md)).

При локальном запуске команда записывает в раздел Execution задачи: `entry point` = `-m clearml_yolo.entrypoints.<команда>`, `working dir` = `.`, пустой `diff`, а если CY установлен из Git-checkout — ещё адрес `remote.origin.url` без учётных данных, ветку и commit. Аргументы командной строки и незакоммиченные изменения не записываются. Если CY установлен не из checkout или Git недоступен, полей репозитория нет, а в журнал пишется предупреждение (например `No source checkout; ClearML Git identity is unavailable`). После записи команда перечитывает поля с сервера; если какое-то не сохранилось, она завершается ошибкой `ClearML did not retain script metadata field '<поле>'`.

## Объекты конфигурации

| Объект | Когда пишется | Содержимое |
| --- | --- | --- |
| `run` | Каждый запуск | Полная собранная конфигурация команды (JSON). По ходу запуска в неё добавляются сведения о результатах: итоговые имена задачи и модели (`display_names`), выбранные модели, параметры и итоги оценки (`evaluation_result`), сравнения (`comparison`, `comparison_status`), экспорта (`export_result`), публикации в FiftyOne (`fiftyone_result`) и другие. |
| `run_overrides` | Каждый запуск | Только ключи, отличающиеся от встроенных значений по умолчанию команды. Пути вывода (`run_id`, `run_dir`, `output`, `output_dir`, `dataset_cache_dir`), ключи `clearml.project_name`, `clearml.task_name`, `clearml.tags`, `clearml.output_uri` и `project`, `name`, `save_dir` групп `ultralytics` и `ultralytics_predict` сюда не входят. |
| `model_assets` | Когда команда скачивает или находит файлы весов по ссылке модели | Список использованных файлов весов: откуда взяты и где лежат локально. |
| `dataset` | `cy-ground-truth`, обучение в `cy-train` и `cy` | Описание датасета: исходный файл `data_yaml` для `cy-ground-truth`, подготовленное описание датасета для обучения. |
| `report` | `cy-report` и этап отчёта `cy`, если задан `report_config_path` | Файл настроек отчёта. |

Значения, похожие на пароли, токены и ключи доступа, в объектах конфигурации заменяются на `<redacted>`.

При обучении параметры обучения дополнительно записываются в раздел гиперпараметров `General`.

## Артефакты

`<split>` в имени артефакта — имя split, закодированное для имени файла: символы, кроме букв, цифр, `-` и `_`, записываются как `%XX` в UTF-8, точка — как `%2E`. Например `val` остаётся `val`.

| Артефакт | Кто пишет | Содержимое |
| --- | --- | --- |
| `gt_csv` | `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-compare`, `cy-ground-truth` | Разметка ([ground truth](../GLOSSARY.md#ground-truth)), с которой работал запуск. В `cy-train` и при обучении в `cy` — подготовленная для обучения разметка. |
| `predicts_csv` | `cy`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-compare` | Общая таблица строк разметки и предсказаний (predictions); после оценки строки дополнены статусами сопоставления (колонка `evaluation_status`, см. [ниже](#статусы-строк-predicts_csv)). Загружается, когда все этапы запуска, работающие с предсказаниями, закончили. |
| `metrics_best_confidences_val` | `cy-metrics`, `cy-val`, этап метрик `cy` | Подобранные пороги ([selected confidence thresholds](../GLOSSARY.md#selected-confidence-thresholds)) — пороги уверенности (confidence threshold), выбранные на split `val`: столбцы `class_name`, `confidence`. |
| `metrics_dashboard_full_<split>` | `cy-metrics`, `cy-val`, этап метрик `cy` | Полный дашборд ([dashboard](../GLOSSARY.md#dashboard)) метрик по split. |
| `metrics_dashboard_dtrk_<split>` | `cy-metrics`, `cy-val`, этап метрик `cy` | Сокращённый дашборд метрик по split. |
| `comparison_baseline_dashboard_full_<split>`, `comparison_baseline_dashboard_dtrk_<split>` | `cy-compare`, этап сравнения `cy` | Дашборды модели [baseline](../GLOSSARY.md#baseline). |
| `comparison_candidate_dashboard_full_<split>`, `comparison_candidate_dashboard_dtrk_<split>` | `cy-compare`, этап сравнения `cy` | Дашборды модели-кандидата ([candidate model](../GLOSSARY.md#candidate-model)). |
| `compare_workbook_<split>` | `cy-compare`, этап сравнения `cy` | Книга Excel (workbook) сравнения. |
| `compare_workbook_<split>_excluded` | `cy-compare`, этап сравнения `cy` | CSV с классами, исключёнными из сравнения. Если в этом запуске артефакт с таким именем уже загружен с другим содержимым (например, сравнение в `cy` по нескольким split), к имени добавляется `_2`, `_3` и так далее; таблица с тем же содержимым повторно не загружается. |
| `report_dev_<split>`, `report_business_<split>` | `cy-report`, этап отчёта `cy` | Технический и бизнес-отчёт. |
| `export_onnx`, `export_metadata` | `cy-export` при `export.operation=onnx` | Граф ONNX и описание экспорта. |
| `export_engine`, `export_metadata` | `cy-export` при `export.operation=build` | Движок TensorRT ([TensorRT engine](../GLOSSARY.md#tensorrt-engine)) и описание экспорта. |
| `export_corpus`, `export_verification` | `cy-export` при `export.operation=verify` | Набор изображений для проверки и отчёт о проверке движка. |
| `pipeline_outcome` | `cy` | Итог пайплайна ([pipeline outcome](../GLOSSARY.md#pipeline-outcome)): статус и причина для каждого этапа пайплайна ([pipeline](../GLOSSARY.md#pipeline)). Тот же итог лежит в каталоге запуска в `pipeline_outcome.json` и `pipeline_outcome.txt`. |

Содержимое книг и дашбордов описано в разделе [Книги Excel](formats/workbooks.md).

### Статусы строк `predicts_csv`

Колонка `row_type` равна `gt` для строк разметки и `predict` для предсказаний. Колонка `evaluation_status` принимает значения:

| Статус | Значение |
| --- | --- |
| `TP`, `FP`, `FN` | Верное срабатывание, ложное срабатывание, пропущенный объект разметки. |
| `filtered` | Предсказание отброшено порогом уверенности; `exclusion_reason` = `confidence_threshold`. |
| `background` | Строка разметки без класса (изображение без объектов). |
| `excluded` | Строка не участвовала в оценке. Причина в `exclusion_reason`: `invalid_geometry:<причина>` (некорректная рамка), `duplicate_ground_truth` (дубликат рамки разметки), `prediction_preprocessing` (предсказание убрано фильтрами `preprocess_preds_*`), `class_not_evaluated` (для класса нет подобранного порога). |
| `not_evaluated` | Строка не оценивалась, например предсказания `cy-predict` без этапа метрик. Предсказания по изображениям вне выбранных split получают `exclusion_reason` = `outside_selected_splits`. |

Каждый перечисленный артефакт обязателен: команда загружает его синхронно и до завершения проверяет, что все объявленные артефакты загружены. Если хотя бы один не загружен, задача не считается успешной (см. [Успех и ошибка](#успех-и-ошибка)).

## Графики, таблицы и скаляры

| Раздел | Вкладка | Кто пишет | Содержимое |
| --- | --- | --- | --- |
| `metrics`, серия `<split>` | Plots (таблица) | `cy-metrics`, `cy-val`, этап метрик `cy` | Метрики по классам для split. |
| `metrics_<split>` | Scalars | `cy-metrics`, `cy-val`, этап метрик `cy` | Сводные значения метрик split, по одной серии на значение. |
| `predict`, серия `resolution` | Plots (таблица) | `cy-predict`, `cy-val`, этап предсказания `cy` | Разрешение, при котором оценивалась модель. |
| `Confusion matrix` | Plots | `cy-metrics`, `cy-val`, этап метрик `cy`; для модели-кандидата также `cy-compare` и этап сравнения `cy` | Матрица ошибок с переключателем: `Counts`, `Row %`, `Column %`, `Overall %`. Одна серия на модель и split. |
| `Precision-recall` | Plots | Те же команды, только для split `test` | Кривые precision-recall по классам. |
| `<split>/<значение>` | Scalars, сводная таблица одиночных значений | `cy-compare`, этап сравнения `cy` | Итоговые значения сравнения: число проверенных и исключённых классов, число классов, где метрика ухудшилась или улучшилась, общие изменения precision и recall. |
| `train`, `lr`, `Epoch Time` и метрики валидации по эпохам | Scalars | Обучение при `model.backend=ultralytics` | Пишет callback ClearML из Ultralytics. Он же загружает графики обучения в Plots. |
| `Native training` | Scalars | Обучение остальных семейств моделей ([detector family](../GLOSSARY.md#detector-family)) | Метрики обучения по шагам. |

## Модели

**Выходная модель.** Обучение (`cy-train` и этап обучения `cy`) регистрирует лучший checkpoint как выходную модель задачи. Она получает:

- имя обучения; при совпадении имени в проекте — тот же суффикс, что и задача;
- теги задачи и тег `best`;
- список классов и описание архитектуры;
- метаданные `clearml_yolo_*`: роль checkpoint (`best`), имя файла и SHA-256 checkpoint, ID обучающей задачи, архитектуру, размер входа, версию CY, запрошенное и итоговое имя модели.

Перед завершением CY скачивает загруженную модель и сверяет её SHA-256 с локальным checkpoint; при расхождении задача завершается ошибкой.

Если в той же задаче после обучения выполняется этап метрик (`cy`), к выходной модели добавляются подобранные пороги: `clearml_yolo_confidence_thresholds`, `clearml_yolo_confidence_threshold/<класс>`, `clearml_yolo_calibration_split` (`val`) и `clearml_yolo_calibration_checkpoint_sha256`.

**Входные модели.** CY сам не регистрирует используемые веса как входные модели задачи. Какие веса использованы, видно в объектах конфигурации `run` и `model_assets`. Если у задачи обучения ровно одна входная модель, её ID записывается в метаданные выходной модели `clearml_yolo_input_model_id`.

## Что CY читает обратно

| Что читается | Кто читает | Откуда |
| --- | --- | --- |
| Лучший checkpoint модели | Команды, которым модель задана задачей ClearML | Выходная модель с метаданными `clearml_yolo_checkpoint_role=best`; без них — модель с файлом `best.pt` (или `.pth`, `.ckpt`); без него — последняя зарегистрированная выходная модель с предупреждением. Скачанный файл сверяется с SHA-256 из метаданных. |
| Пороги уверенности | `cy-compare`, этап сравнения `cy`, если пороги не заданы явно | Первый найденный артефакт задачи модели: `metrics_best_confidences_val`, затем старые имена `best_confidences_val`, `metrics_best_confidences_test`, `best_confidences_test`, затем дашборды `metrics_dashboard_full_val`, `dashboard_full_val`, `metrics_dashboard_full_test`, `dashboard_full_test` (с предупреждением, что точность может быть округлена). Если ничего нет, команда завершается ошибкой `... has no 'metrics_best_confidences_val' or supported historical threshold/dashboard artifact. Supply thresholds explicitly.` |
| Состав исходного датасета | Сравнение и отчёты, когда модель связана с обучающей задачей | Артефакт `gt_csv` обучающей задачи. Если его нет, пишется предупреждение `Original dataset counts unavailable`, и работа продолжается без этих чисел. |
| Последняя завершённая задача | Выбор модели по проекту, имени и тегам (см. [`cy-compare`](commands/cy-compare.md)) | Самая поздно завершённая задача со статусом `completed` или `published`, кроме текущей, имя которой целиком совпадает с заданным именем (оно читается как регулярное выражение, например `my-run.*`) и у которой есть все заданные теги. |
| Объект `run` | Повторный запуск клона задачи агентом ClearML (см. [Очередь](queue.md)) | Объект конфигурации `run` клона заменяет собранную конфигурацию. |

## Успех и ошибка

Запуск успешен, когда команда отработала без ошибки и затем:

1. все объявленные артефакты загружены;
2. загрузка выходных моделей завершена, и модели прошли проверку;
3. SDK ClearML подтвердил, что все данные отправлены;
4. вывод в Console доставлен.

После этого задача получает статус `completed`.

Если команда или любой из этих шагов завершается ошибкой, задача получает статус `failed` с причиной — именем класса ошибки — и сообщением `<Ошибка>: invocation failed; see local diagnostics for details`. Подробности ошибки в ClearML не пишутся: они остаются в выводе команды и в локальных журналах (см. [Рабочий каталог](workspace.md)). Если процесс останавливается сигналом `SIGTERM`, причиной будет `SIGTERM`. Команда при этом завершается с ненулевым кодом завершения (exit code).

Каждый обмен с сервером ClearML при завершении задачи (загрузка, проверка, закрытие) ограничен 600 секундами. Если сервер не ответил за это время, шаг завершается ошибкой `ClearML task finalization deadline expired`.

Исключение — `cy` после успешного обучения. Если обучение дало непустой checkpoint, а потом ошибся следующий этап или не удалась часть публикации, задача получает статус `completed` с сообщением, которое начинается с `completed_with_warnings:`:

- `completed_with_warnings: Pipeline completed; inspect pipeline_outcome for details` — один из этапов после обучения завершился ошибкой;
- `completed_with_warnings: Training succeeded; publication incomplete; see local outcome` — не удалось завершить публикацию; в итог добавляется список незагруженных артефактов;
- `completed_with_warnings: Training succeeded; console publication incomplete` — не удалось доставить вывод в Console.

Подробности смотрите в артефакте `pipeline_outcome` или в файлах `pipeline_outcome.json` и `pipeline_outcome.txt` каталога запуска. Прерывание (например `SIGTERM` или Ctrl+C) всегда даёт статус `failed`; после `SIGTERM` команда завершается с кодом 143.

Перед выходом — успешным, с ошибкой или после прерывания — команда Hydra останавливает процессы, которые запустила сама (например, процессы обучения на нескольких GPU и загрузчики данных): сначала `SIGTERM`, через 2 секунды `SIGKILL`. Процессы, которые существовали до её запуска, она не трогает. Повторный Ctrl+C во время этой очистки откладывается до её конца; дождитесь выхода команды.

Ошибки FiftyOne никогда не влияют на статус задачи и код завершения.

Если закрыть задачу не удалось (например, ошибка `ClearML owner remained active after close`), процесс больше не создаёт задач. При multirun (см. [Конфигурация](configuration/README.md)) задания идут по очереди в одном процессе, поэтому следующие задания завершаются ошибкой `Previous ClearML owner did not confirm closure; start a fresh process before another invocation`. Запустите оставшиеся задания новой командой.

### Кэш шагов в контроллере ClearML

Если вы запускаете команды CY как шаги своего пайплайна ClearML с кэшированием, зарегистрируйте в контроллере функцию хеширования CY до поиска в кэше:

```python
from clearml.automation.job import ClearmlJob
from clearml_yolo.adapters.clearml.cache import normalize_task_hash

ClearmlJob.register_hashing_callback(normalize_task_hash)
```

Функция меняет только хеш, не запуск, и только для задач с `entry point` `-m clearml_yolo.entrypoints.<команда>`. Она убирает из хеша объект `run_overrides` и ключи, которые не влияют на результат (имена и маршрутизацию), сводит выбор устройств к типу и числу, а пути датасета внутри подготовленного датасета — к его идентичности. Если у контроллера уже есть своя функция хеширования, вызывайте `normalize_task_hash` из неё.

## FiftyOne

Публикация в FiftyOne выполняется в `cy`, `cy-predict` и `cy-metrics`, если `fiftyone.enabled=true` (по умолчанию). Ключи описаны на странице [`fiftyone`](configuration/fiftyone.md).

### Предварительная проверка и таймауты

1. Сразу после создания задачи ClearML команда запускает предварительную проверку ([FiftyOne preflight](../GLOSSARY.md#fiftyone-preflight)) — отдельный процесс, который загружает FiftyOne и запрашивает список датасетов. Процесс не видит GPU. На это отводится `fiftyone.preflight_timeout_seconds`.
2. Если проверка не прошла (FiftyOne не установлен, база недоступна, время вышло), команда пишет предупреждение `FiftyOne visualization setup failed; continuing without visualization` и выполняет всю остальную работу без публикации в FiftyOne.
3. После вычислений публикация выполняется в новом отдельном процессе. Весь процесс, включая загрузку FiftyOne, запись и выход, ограничен `fiftyone.publish_timeout_seconds`; по истечении процесс останавливается.
4. Перед записью процесс берёт блокировку датасета и ждёт её не дольше `fiftyone.lock_timeout_seconds`. Файл блокировки лежит в каталоге `clearml-yolo-locks` внутри каталога базы данных FiftyOne на этой машине.
5. Если публикация завершилась ошибкой или по таймауту, команда пишет предупреждение `FiftyOne visualization publication failed; continuing task` и завершает работу как обычно.

При `fiftyone.enabled=false` команда к FiftyOne не обращается.

### Датасет

Имя датасета: `<fiftyone.dataset_prefix>-v1-<SHA-256 CSV разметки>`. Датасет постоянный (persistent). Запуски с одной и той же разметкой (байт в байт) пишут в один датасет: изображения добавляются один раз, а каждый запуск добавляет свои поля.

Если датасет с таким именем уже есть, но был создан для других путей к изображениям или другого split изображений, публикация завершается ошибкой с советом использовать исходные пути или другой `fiftyone.dataset_prefix`.

Поля образца (sample), общие для всех запусков:

| Поле | Содержимое |
| --- | --- |
| `filepath` | Путь к изображению из столбца `image_path` разметки. |
| `image_name` | Имя изображения из разметки. |
| `split` | Split изображения. |
| `metadata` | Ширина и высота изображения. |
| `ground_truth` | Рамки (bounding box) разметки. |

### Поля запуска

Каждая задача ClearML получает ключ запуска ([run key](../GLOSSARY.md#run-key)) `run_<SHA-256 ID задачи>` и свой набор полей с этим ключом в конце:

| Поле | Содержимое |
| --- | --- |
| `predictions_<ключ>` | Предсказания запуска. |
| `matched_ground_truth_<ключ>` | Рамки разметки со статусом сопоставления. |
| `matched_predictions_<ключ>` | Предсказания со статусом сопоставления, включая отброшенные порогом. |
| `evaluated_predictions_<ключ>` | Предсказания, прошедшие порог, со статусом сопоставления. |
| `predicted_<ключ>` | Было ли изображение в предсказаниях запуска. |
| `evaluated_<ключ>` | Участвовало ли изображение в оценке. |
| `tp_<ключ>`, `fp_<ключ>`, `fn_<ключ>` | Число верных, ложных и пропущенных срабатываний на изображении. |

Рамки в полях сопоставления несут атрибуты `dm_index`, `dm_status`, `dm_gt_indices`, `dm_pred_indices`, `dm_ious` и `dm_matches`.

Для каждого split с результатами оценки создаётся оценка FiftyOne (evaluation) с ключом `eval_<ключ запуска>_<SHA-256 имени split>` и методом `digital_metrics`; сопоставления в ней берутся из оценки CY, FiftyOne их не пересчитывает. При повторной публикации той же задачи её прежние оценки удаляются и пишутся заново.

Сведения о запуске (ID задачи, имена полей, пороги и параметры оценки) хранятся в `info` датасета под `cy_runs`.

### Что остаётся после публикации

Команда записывает квитанцию ([publication receipt](../GLOSSARY.md#publication-receipt)) `fiftyone_publication.json` в свой каталог вывода и добавляет в объект конфигурации `run` задачи раздел `fiftyone_result`: имя датасета, ключ запуска, был ли датасет использован повторно, число образцов, имена полей и ключи оценок.

### Просмотр в FiftyOne App

Откройте датасет из той же базы данных FiftyOne и с той же конфигурацией FiftyOne, что и у команды; пути к изображениям из `image_path` должны читаться на этой машине. Имя датасета — поле `dataset_name` квитанции:

```python
import json

import fiftyone as fo

receipt = json.load(open("runs/my-run/fiftyone_publication.json"))
session = fo.launch_app(fo.load_dataset(receipt["dataset_name"]))
session.wait()
```

Панели оценок CY (`Imported Model Evaluation` и `Imported AP / PR Reports`, плагин `@clearml-yolo/evaluation`) устанавливаются один раз в каталог плагинов FiftyOne (`fo.config.plugins_dir`) того окружения, где работает FiftyOne App:

```python
from clearml_yolo.adapters.fiftyone.panel import install_evaluation_plugin

install_evaluation_plugin()
```

Повторная установка без `overwrite=True` завершается ошибкой `Plugin '@clearml-yolo/evaluation' already exists`. Если App уже запущен, перезапустите его после установки.

## См. также

- [Группа `clearml`](configuration/clearml.md)
- [Группа `fiftyone`](configuration/fiftyone.md)
- [Группа `evaluation`](configuration/evaluation.md)
- [Рабочий каталог](workspace.md)
- [Книги Excel](formats/workbooks.md)
