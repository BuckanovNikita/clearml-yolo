# Очередь

Команды CY запускают работу сразу, на устройствах, которые заданы в конфигурации. Ставить запуски в очередь они не умеют: для этого есть отдельный инструмент `cy-queue`. Его документация — в репозитории https://github.com/BuckanovNikita/cy-queue.

## Что отклоняют команды CY

Девять команд Hydra (`cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`, `cy-compare`, `cy-ground-truth`, `cy-export`) отклоняют настройки очереди:

| Настройка | Где проверяется |
| --- | --- |
| `queue` | Ключ верхнего уровня в override (в том числе с префиксами `+`, `++`, `~`), в собранной конфигурации, в YAML из `--config-dir` |
| `autogpu` | То же |
| `auto_gpu` | То же |
| `hydra/launcher=cy_queue` | Override и `defaults` в YAML из `--config-dir` |

Группа конфигурации (config group) с именем `queue`, `autogpu` или `auto_gpu` в `defaults` локального YAML тоже отклоняется. Проверка идёт до создания задачи ClearML (task), а при `-m` — для каждого задания sweep до начала работы. Команда печатает traceback Python, завершается с кодом 1 и последней строкой выводит:

```text
ValueError: Legacy queue/autogpu controls are removed from direct cy commands. Remove these settings from CLI overrides and saved YAML. Use cy-queue submit for scheduled execution; direct commands preserve native devices.
```

Уберите эти настройки из командной строки и из своих YAML-файлов. Как устроены локальные файлы, описано в [Конфигурации](configuration/README.md#локальное-дерево-конфигурации), там же — [список отклонённых ключей](configuration/README.md#отклонённые-ключи-очереди).

## Sweep

Sweep (`-m`) CY выполняет только последовательно, стандартными `BasicSweeper` и `BasicLauncher` Hydra. Другой sweeper или launcher даёт ошибку:

```text
cy supports sequential BasicSweeper/BasicLauncher sweeps; use cy-queue for concurrent execution
```

Подробнее — в [Multirun](configuration/README.md#multirun).

## Задача, запущенная агентом ClearML

Когда агент ClearML выполняет клон задачи CY, команда берёт конфигурацию из объекта конфигурации ([configuration object](../GLOSSARY.md#configuration-object)) `run` этой задачи вместо собранной, см. [Что CY читает обратно](publication.md#что-cy-читает-обратно).

## См. также

- [Конфигурация](configuration/README.md)
- [Публикация в ClearML и FiftyOne](publication.md)
- [Сценарии](scenarios.md)
