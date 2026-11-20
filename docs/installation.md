# Установка и окружение

Эта страница описывает, что устанавливает пакет, какие версии Python он поддерживает, как выбирается рабочий каталог ([workspace](../GLOSSARY.md#workspace), `CY_HOME`) и какие переменные окружения (environment variable) читает CY. Прочитайте её перед первым запуском на новом хосте.

## Пакет

| Что | Значение |
| --- | --- |
| Имя пакета | `clearml-yolo` |
| Python | `>=3.12.13,<3.14` |
| Исходный код | `https://github.com/BuckanovNikita/clearml-yolo` |

Пакет ставит тринадцать консольных команд:

| Команда | Назначение |
| --- | --- |
| `cy` | Пайплайн ([pipeline](../GLOSSARY.md#pipeline)): обучение (training), предсказания (predictions), метрики, отчёт (report) и сравнение (comparison) в одном запуске |
| `cy-train` | Обучение |
| `cy-predict` | Предсказания |
| `cy-val` | Валидация (validation) |
| `cy-metrics` | Метрики |
| `cy-report` | Отчёт |
| `cy-compare` | Сравнение моделей |
| `cy-ground-truth` | Подготовка разметки ([ground truth](../GLOSSARY.md#ground-truth)) |
| `cy-export` | Экспорт (export) |
| `cy-init-config` | Создание локального дерева конфигурации (configuration) |
| `cy-dedup` | Дедупликация файлов кэша (cache) |
| `cy-download-weights` | Заранее скачивает веса (weights) и исходники моделей |
| `cy-batch-estimate` | Оценка batch size |

Первые девять команд — приложения Hydra, они настраиваются через override вида `key=value`; см. [Конфигурация](configuration/README.md). Остальные четыре принимают обычные флаги.

Все семейства моделей ([detector family](../GLOSSARY.md#detector-family)) входят в стандартную установку: PyTorch, Ultralytics, RF-DETR, ONNX и ONNX Runtime — прямые зависимости пакета, отдельных extras нет. Среди зависимостей есть пакеты `digital-metrics` и `report-generator`; они должны быть доступны в индексе пакетов, из которого вы ставите `clearml-yolo`.

### Как установить

В публичном PyPI пакета `clearml-yolo` нет. Установите его по Git-ссылке в окружение с поддерживаемой версией Python, например через `uv`:

```bash
uv venv --python 3.12
uv pip install "clearml-yolo @ git+https://github.com/BuckanovNikita/clearml-yolo"
```

Пакеты `digital-metrics` и `report-generator` установщик берёт из вашего индекса пакетов. Если они лежат архивами в локальном каталоге, добавьте его к команде установки: `--find-links wheels`.

> В публичном PyPI есть посторонний пакет с именем `report-generator`. CY он не подходит. Убедитесь, что установщик берёт `digital-metrics` и `report-generator` из вашего индекса или из локального каталога.

### Установка из исходного кода

В клоне репозитория пакеты `digital-metrics` и `report-generator` собираются из их исходников:

1. Положите исходники нужных ревизий в `external/digital-metrics` и `external/report-generator`. Без них задача останавливается с сообщением `local-deps: missing approved checkouts: ...`.
2. Соберите архивы и настройте `uv`:

   ```bash
   uvx --from go-task-bin task local-deps
   ```

   Задача кладёт архивы обоих пакетов в `external/wheelhouse` и, если файла `uv.toml` в корне клона нет, создаёт его со строкой `find-links = ["external/wheelhouse"]`. Существующий `uv.toml` не перезаписывается.
3. Установите окружение по lock-файлу; команды появятся в `.venv/bin`:

   ```bash
   uv sync --locked
   ```

После установки проверьте, что команды на месте:

```bash
cy-dedup --help
```

Команды CY во время работы ничего не устанавливают. Драйверы GPU и TensorRT (нужен только для [`cy-export`](commands/cy-export.md)) ставятся отдельно.

На Linux CY следит за процессами обучения и других тяжёлых этапов ([stage](../GLOSSARY.md#stage)) через pidfd, поэтому ядро и сборка Python должны поддерживать `os.pidfd_open`, `signal.pidfd_send_signal` и `os.waitid` с `P_PIDFD`. Без этого этап останавливается до начала работы:

```text
RuntimeError: Process supervision unavailable in /usr/bin/python3: os.pidfd_open failed ([Errno 38] Function not implemented); native work has not started
```

## Рабочий каталог `CY_HOME`

Каждая команда работает внутри одного рабочего каталога. Его задаёт переменная `CY_HOME`; если она не задана или пуста, рабочим каталогом становится текущий каталог, из которого вы запускаете команду. При старте команда превращает значение в абсолютный путь (с раскрытием `~`; относительный путь считается от текущего каталога), создаёт каталог, если его нет, и передаёт его дочерним процессам.

```bash
export CY_HOME=/workspace/project
cy-train ground_truth=data/ground_truth.csv
```

Команды Hydra при старте проверяют, что текущий каталог находится внутри рабочей копии Git. Если Git этого не подтверждает (каталог вне репозитория или `git` не установлен), команда печатает предупреждение и продолжает работу:

```text
WARNING | Git working tree could not be verified for launch directory '/workspace/project': Git did not confirm working-tree membership. To version experiment configuration, launch from a Git checkout or deliberately run 'git init' in this directory. Continuing.
```

Все файлы, которые пишет сам CY, должны лежать внутри `CY_HOME`. Что именно там создаётся и что можно удалять, описано на странице [Рабочий каталог](workspace.md).

## Переменные окружения

Переменные, которые вы можете задать сами:

| Переменная | По умолчанию | Описание |
| --- | --- | --- |
| `CY_HOME` | текущий каталог | Рабочий каталог. |
| `CY_RUNTIME_TEMP_ROOT` | `CY_HOME/.tmp` | Каталог для временных каталогов ([runtime scratch directory](../GLOSSARY.md#runtime-scratch-directory)) `cy-runtime-*`. Относительный путь считается от `CY_HOME`; путь вне `CY_HOME` отклоняется ошибкой `Project write destination ... must be contained beneath CY_HOME=...`, и команда завершается с кодом 1. |
| `CY_WEIGHTS_DOWNLOAD_TIMEOUT` | `1800` | Лимит в секундах на одну попытку скачать архив весов проекта. Значение должно быть положительным конечным числом, иначе команда завершается с ошибкой `CY_WEIGHTS_DOWNLOAD_TIMEOUT must be positive finite seconds`. |
| `GHR` | не задана | Корень зеркала весов ([weight mirror](../GLOSSARY.md#weight-mirror)) для файлов GitHub release (например, Files remote в Artifactory). См. [Зеркала весов](#зеркала-весов). |
| `GH` | не задана | Корень VCS-репозитория Artifactory для скачивания исходников DEIMv2. |
| `CY_PROGRESS_FILE` | не задана | Путь к JSON-файлу, в который команда записывает текущий прогресс (например, шаг обучения). Путь должен быть внутри `CY_HOME`. |
| `LOGURU_LEVEL` | `DEBUG` | Наименьший уровень сообщений журнала; например, `INFO` скрывает сообщения `DEBUG`. На любом уровне каждая строка журнала содержит модуль, функцию и номер строки кода, где она записана (формат Loguru по умолчанию). Значение `TRACE` также включает трассировку операций CY: записи `START`, `DONE`, `FAILED` или `INTERRUPTED` для каждой операции, а в stderr — сообщение `TRACE ACTIVE` о текущей операции каждые 30 секунд и снимок стеков `TRACE STACK snapshot` не чаще раза в 60 секунд, если он изменился. Помогает разобрать зависание. |
| `HF_TOKEN`, `HUGGING_FACE_HUB_TOKEN` | не заданы | Токен для запросов к `huggingface.co`. |
| `HF_HOME`, `HF_TOKEN_PATH`, `XDG_CACHE_HOME` | стандарт Hugging Face | Где искать файл токена Hugging Face, если токен не задан переменной: `HF_TOKEN_PATH`, иначе `HF_HOME/token`, иначе `XDG_CACHE_HOME/huggingface/token` (`~/.cache/huggingface/token`). |
| `SSL_CERT_FILE` | системные сертификаты | CA bundle для HTTPS-скачиваний весов. Проверка TLS не отключается. |
| `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE` | не заданы | CA bundle для HTTPS-скачиваний весов, если `SSL_CERT_FILE` не задана. |
| `HYDRA_FULL_ERROR` | не задана | `1` печатает полный стек ошибки команд Hydra. |

Переменные `CY_RUNTIME_ARENA`, `CY_CAPTURE_STDERR_TTY`, `CY_SCALAR_JOURNAL`, `CY_CLEARML_OWNER_PID`, `CY_CLEARML_OWNER_TASK_ID`, `CY_EXECUTION_CHANNEL_FD`, `CY_EXECUTION_OWNER_PID`, `CY_MODEL_PROCESS_OWNER`, `CY_DIRECT_MODEL_PROCESS_OWNER`, `CY_TRAINING_WORKER_OWNER`, `CY_BATCH_CASE_OWNER` и `CY_FIFTYONE_START_GATE` CY выставляет сам для своих дочерних процессов. Не задавайте их вручную. Стандартные переменные распределённого запуска (`WORLD_SIZE`, `RANK`, `LOCAL_RANK`) и `CUDA_VISIBLE_DEVICES` читаются как обычно для PyTorch.

## Учётные данные

CY не хранит учётные данные в своей конфигурации. Он передаёт их получение библиотекам.

### ClearML

ClearML SDK читает адрес сервера и ключи из своего файла `~/clearml.conf` (путь можно изменить переменной `CLEARML_CONFIG_FILE`) или из переменных `CLEARML_API_HOST`, `CLEARML_API_ACCESS_KEY`, `CLEARML_API_SECRET_KEY`. Например:

```bash
export CLEARML_API_HOST=https://clearml.example.com
```

Перед публикацией файла конфигурации в задачу ClearML (task) CY заменяет на заглушку значения ключей, похожих на пароли и токены, а также значения таких переменных окружения, если они встречаются в файле. Параметры проекта и задачи задаются в группе [`clearml`](configuration/clearml.md).

### FiftyOne

FiftyOne берёт адрес базы данных из своей конфигурации или из переменной `FIFTYONE_DATABASE_URI`. Настройки публикации в FiftyOne со стороны CY — в группе [`fiftyone`](configuration/fiftyone.md).

### Зеркала весов

Веса и исходники моделей по умолчанию скачиваются с GitHub и Hugging Face. Если прямой доступ закрыт, задайте зеркало весов:

```bash
export GHR=https://artifactory.example/artifactory/github-files
```

- `GHR` применяется к ссылкам вида `https://github.com/<owner>/<repo>/releases/download/<tag>/<file>`: CY сначала пробует `GHR` с тем же путём `<owner>/<repo>/releases/download/<tag>/<file>`, затем исходную ссылку GitHub.
- `GH` применяется только к исходникам DEIMv2: CY запрашивает архив коммита через `<префикс>/api/vcs/downloadCommit/<ключ репозитория>/<owner>/<repo>/<revision>?ext=tar.gz`, где `<ключ репозитория>` — последний сегмент пути в `GH`. Если в `GH` нет такого сегмента, команда завершается ошибкой `GH must identify an Artifactory VCS repository root`.
- Логин и пароль для зеркала весов берутся из `~/.netrc` (по хосту) или из адреса вида `https://user:password@host/...`. Прокси задаются стандартными `HTTP_PROXY` и `HTTPS_PROXY`.
- Для Hugging Face используется `HF_TOKEN` и переменные из таблицы выше. Адрес зеркала Hugging Face (`HF_ENDPOINT`) читает сама библиотека `huggingface_hub`. Если он отличается от `https://huggingface.co`, CY сначала обращается к зеркалу, а при неудаче — к `https://huggingface.co` без токена.

Подробнее о заранее подготовленных весах — на странице [`cy-download-weights`](commands/cy-download-weights.md).

## См. также

- [Рабочий каталог](workspace.md)
- [Конфигурация](configuration/README.md)
- [Публикация в ClearML и FiftyOne](publication.md)
