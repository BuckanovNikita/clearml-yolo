# Группа `clearml`

Группа конфигурации (config group) `clearml` задаёт задачу ClearML (task), которую создаёт каждый запуск команды: проект, имя, тип, теги и хранилище артефактов. Подключение к серверу ClearML (адрес и ключи доступа) настраивается не здесь, а в файле ClearML или переменных окружения (см. [Установка](../installation.md)).

## Где действует группа

Группа есть у всех девяти Hydra-команд: `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`, `cy-compare`, `cy-ground-truth`, `cy-export`. У каждой из них одни и те же ключи и значения по умолчанию.

Ошибка в группе останавливает команду до обращения к серверу ClearML, и задача не создаётся. Неизвестный ключ отклоняет Hydra при сборке конфигурации (`Could not override 'clearml.<ключ>'`), недопустимый `output_uri` отклоняет проверка конфигурации, недопустимый `task_type` отклоняет SDK ClearML в начале создания задачи.

## Ключи

| Ключ | По умолчанию | Допустимые значения | Описание |
| --- | --- | --- | --- |
| `project_name` | `clearml-yolo` | строка | Проект ClearML, в котором создаётся задача. Также входит в путь каталога запуска ([run directory](../../GLOSSARY.md#run-directory)) под `runs/` в рабочем каталоге ([workspace](../../GLOSSARY.md#workspace)), см. [Рабочий каталог](../workspace.md). Задавайте явно, чтобы разделять эксперименты. |
| `task_name` | `yolo-run` | строка | Имя задачи. `cy` использует его как есть, остальные команды добавляют имя этапа ([stage](../../GLOSSARY.md#stage)): `<task_name>/<этап>`. Полное имя задачи (с этапом) вместе с ID задачи входит в путь каталога запуска. Если имя в проекте уже занято, к нему добавляется суффикс (см. [Публикация](../publication.md#задача-clearml)). |
| `task_type` | `training` | `training`, `testing`, `inference`, `data_processing`, `application`, `monitor`, `controller`, `optimizer`, `service`, `qc`, `custom` | Тип задачи ClearML. Список допустимых значений задаёт установленный SDK ClearML; другое значение даёт ошибку `Task type '<значение>' not supported, options are: ...`. |
| `tags` | `[]` | список строк | Теги задачи. Те же теги вместе с тегом `best` получает выходная модель ([output model](../../GLOSSARY.md#output-model)) обучения. При multirun каждая задача дополнительно получает общий тег multirun ([multirun tag](../../GLOSSARY.md#multirun-tag)), см. [Multirun](README.md#multirun). |
| `output_uri` | `true` | `true` или непустая строка URI | Куда ClearML загружает артефакты и модели. `true` — хранилище по умолчанию из настроек ClearML, строка — указанный URI. `false`, `null` и пустая строка запрещены: команда завершается ошибкой `ClearML output_uri is required for remote artifact storage`. |

Ключи `project_name`, `task_name`, `tags` и `output_uri` не попадают в объект конфигурации ([configuration object](../../GLOSSARY.md#configuration-object)) `run_overrides` задачи, так как определяют, куда пишется запуск, а не что он вычисляет (см. [Публикация](../publication.md#объекты-конфигурации)).

## Пример

```bash
cy-train ground_truth=data/ground_truth.csv \
  clearml.project_name=my-project clearml.task_name=my-run 'clearml.tags=[my-tag]'
```

Задача получит имя `my-run/train` в проекте `my-project` и тег `my-tag`.

Список задаётся в синтаксисе Hydra и заключается в кавычки, чтобы оболочка не разобрала скобки: `'clearml.tags=[my-tag,baseline]'`.

## См. также

- [Публикация в ClearML и FiftyOne](../publication.md)
- [Установка: подключение к ClearML](../installation.md)
- [Как устроена конфигурация](README.md)
