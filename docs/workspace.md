# Рабочий каталог

Рабочий каталог ([workspace](../GLOSSARY.md#workspace)) — это каталог `CY_HOME`, в котором CY хранит всё, что пишет на диск: каталоги запусков ([run directory](../GLOSSARY.md#run-directory)), журналы Hydra, кэш (cache) весов и датасетов, временные файлы. Как выбирается `CY_HOME`, описано в разделе [Установка](installation.md#рабочий-каталог-cy_home). Эта страница описывает содержимое каталога и что из него можно удалять.

## Структура

```text
/workspace/project/                       # CY_HOME
├── runs/                                  # каталоги запусков
│   ├── latest -> my-project/my-run-<task-id>
│   └── my-project/my-run-<task-id>/
├── outputs/<дата>/<время>-<host>-<pid>/   # каталог Hydra для обычного запуска
├── multirun/<дата>/<время>-<host>-<pid>/  # каталог Hydra для sweep
├── .cache/clearml-yolo/                   # кэш весов, исходников и датасетов
├── .config/clearml-yolo/                  # таблицы batch size
└── .tmp/cy-runtime-*/                     # временные файлы и журналы каждого запуска
```

### `runs/`

Каталоги запусков с результатами команд.

- Если каталог не задан явно, он называется `runs/<проект ClearML>/<имя задачи>-<ID задачи>`. Имена проекта и задачи кодируются в безопасный для файловой системы вид: все символы, кроме латинских букв, цифр, `-` и `_`, заменяются на `%XX` (байты UTF-8), в том числе `.` и `~`.
- `cy` с ключом `run_dir` пишет в указанный каталог, с ключом `run_id` — в `runs/<run_id>`. Существующий каталог запуска не очищается: файлы прошлого запуска остаются рядом с новыми, поэтому для нового эксперимента берите новый `run_dir` или `run_id`.
- Отдельные команды без явного `output_dir` пишут в `runs/<проект>/<задача>-<ID>/<этап>`, где `<этап>` — `val`, `metrics`, `report`, `compare` или `export`. `cy-predict` и `cy-ground-truth` без явного `output` пишут в файлы `runs/<проект>/<задача>-<ID>/predict.csv` и `runs/<проект>/<задача>-<ID>/ground_truth.csv`. `cy-train` без `ultralytics.project` пишет в каталог обучения ([training directory](../GLOSSARY.md#training-directory)) `runs/<проект>/<задача>-<ID>/detect`.
- `cy` и `cy-train` (если `ultralytics.project` не задан) после создания каталога запуска перенаправляют символическую ссылку `runs/latest` на него. Ссылка ставится только на каталоги внутри рабочего каталога. Если на месте `latest` лежит не ссылка, а обычный каталог или файл, CY переименовывает его в `latest-displaced-<host>-<pid>` с сохранением содержимого и пишет предупреждение. Ошибка обновления ссылки не прерывает запуск.

Что лежит внутри каталога запуска, описано на страницах команд и в разделе [Форматы](formats/README.md).

### `outputs/` и `multirun/`

Каталоги Hydra ([Hydra output directory](../GLOSSARY.md#hydra-output-directory)). Для обычного запуска Hydra пишет в `outputs/<ГГГГ-ММ-ДД>/<ЧЧ-ММ-СС>-<host>-<pid>/`, для sweep — в `multirun/<ГГГГ-ММ-ДД>/<ЧЧ-ММ-СС>-<host>-<pid>/<номер задания>/` и файл `multirun.yaml` рядом. Внутри — `.hydra/` с `config.yaml`, `hydra.yaml`, `overrides.yaml` и журнал Hydra. Подробнее — в разделе [Конфигурация](configuration/README.md#каталоги-hydra).

### `.cache/clearml-yolo/`

| Каталог | Содержимое |
| --- | --- |
| `models/<backend>/<preset>/...` | Скачанные веса моделей |
| `sources/DEIMv2/` | Исходники DEIMv2 |
| `weight-bundles/<sha256>.tar` | Архивы весов из GitHub release проекта (`cy-download-weights`) |
| `datasets/` | Рабочие копии датасетов ([prepared dataset copy](../GLOSSARY.md#prepared-dataset-copy)), если `dataset_cache_dir` не задан |
| `preparation/` | Отметки и блокировки подготовки весов |

Без аргумента `cy-dedup` обрабатывает весь каталог `CY_HOME/.cache`. Файлы, которые CY скачивает с Hugging Face для DEIMv2, хранятся в родном кэше ([native cache](../GLOSSARY.md#native-cache)) библиотеки Hugging Face (`HF_HUB_CACHE`), вне `CY_HOME`; веса, сконвертированные из них, CY кладёт в `models/deimv2/`.

### `.config/clearml-yolo/`

| Файл | Содержимое |
| --- | --- |
| `batch-sizes.yaml` | Редактируемая таблица batch size ([batch size table](../GLOSSARY.md#batch-size-table)), см. [Таблица batch size](formats/batch-table.md) |
| `batch-estimates.json` | Результаты измерений `cy-batch-estimate` |

### `.tmp/cy-runtime-*/`

Каждый запуск команды Hydra, `cy-init-config`, `cy-download-weights` и `cy-batch-estimate` создаёт новый временный каталог ([runtime scratch directory](../GLOSSARY.md#runtime-scratch-directory)) `.tmp/cy-runtime-<случайный суффикс>/`, даже с `--cfg job`. Корень `.tmp` можно перенести переменной `CY_RUNTIME_TEMP_ROOT`; относительный путь отсчитывается от `CY_HOME`. Вспомогательные процессы запуска (обучение, измерение batch size) создают рядом собственные каталоги `cy-runtime-*`. Журналы `logs/` пишут только команды Hydra. Внутри:

| Путь | Содержимое |
| --- | --- |
| `logs/stdout.log`, `logs/stderr.log` | Полный вывод команды. Вывод одновременно дублируется в терминал. |
| `logs/scalars.jsonl` | Скалярные метрики обучения, по одной JSON-записи на строку |
| `logs/mirror-diagnostics.log` | Диагностика процесса, дублирующего вывод в терминал |
| `logs/mirror-<id>/` | Служебные смещения для дублирования вывода |
| `clearml-yolo-config-*/` | Подготовленные копии файлов конфигурации для публикации в ClearML |
| `cy-console-*/` | Журналы вывода, если задача ClearML (task) создаётся вне перехвата вывода команды Hydra |

CY не удаляет каталоги `cy-runtime-*` ни после успешного, ни после неудачного запуска и не чистит старые.

## Правило записи внутри `CY_HOME`

Правило записи внутри `CY_HOME` ([write containment rule](../GLOSSARY.md#write-containment-rule)): любой путь, по которому CY пишет результаты, должен после разрешения символических ссылок лежать внутри `CY_HOME`. Команды Hydra до создания задачи ClearML проверяют `run_dir`, `output_dir`, `output`, `dataset_cache_dir`, `ultralytics.project`, `ultralytics.name`, `ultralytics.save_dir`, те же ключи `ultralytics_predict` и каталоги и журналы Hydra; `CY_RUNTIME_TEMP_ROOT` проверяется при старте любой команды. Остальные пути (например, `comparison_dir`) проверяются в момент записи. Нарушение даёт ошибку:

```text
ValueError: Project write destination /elsewhere/x must be contained beneath CY_HOME=/workspace/project; choose a destination inside CY_HOME or select the intended project workspace. External input and library configuration paths remain supported.
```

В сообщении `CY_HOME` показан после разрешения символических ссылок. Исправление: укажите путь внутри `CY_HOME` или задайте `CY_HOME` так, чтобы он включал нужный каталог. Для `cy` есть ещё одно правило: `dataset_cache_dir` не может лежать внутри каталога запуска (`dataset_cache_dir must be outside run_dir`). Входные файлы (датасеты, разметка ([ground truth](../GLOSSARY.md#ground-truth)), веса) и родные кэши библиотек могут лежать где угодно.

## Что можно удалять

| Путь | Можно ли удалить |
| --- | --- |
| `.tmp/cy-runtime-*` | Да, когда запуск завершён. Это журналы конкретного запуска; удаляйте их, когда они больше не нужны. |
| `outputs/`, `multirun/` | Да. Это журналы и снимки конфигурации Hydra; CY их не читает. |
| `.cache/clearml-yolo/` | Да, когда не идёт ни один запуск. Веса и датасеты будут скачаны или подготовлены заново. |
| `runs/<...>` | Да, если результаты уже не нужны. Удаление каталога, на который указывает `runs/latest`, оставляет ссылку битой до следующего `cy` или `cy-train`. |
| `.config/clearml-yolo/` | Это ваши настройки и измерения batch size; удаление сбрасывает их. |

## См. также

- [Установка и окружение](installation.md)
- [Конфигурация](configuration/README.md)
