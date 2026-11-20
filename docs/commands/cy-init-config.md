# cy-init-config

`cy-init-config` записывает в каталог редактируемое дерево YAML для одной команды CY и одной модели: файл команды, её базовую конфигурацию (configuration) и нужные ей группы конфигурации (config group). Команда нужна, когда вы хотите хранить настройки запуска в файлах, а не передавать их override в командной строке. Она не создаёт задачу ClearML (task) и не загружает модель.

## Примеры

```bash
cy-init-config configs
```

Дерево для `cy` с моделью Ultralytics.

```bash
cy-init-config --command cy-train --model rfdetr/small configs
```

Дерево для `cy-train` с моделью RF-DETR `small`.

```bash
cy-init-config --force configs
```

Перезаписывает уже созданные файлы примеров.

## Синтаксис и аргументы

```text
cy-init-config [-h]
               [--command {cy,cy-train,cy-predict,cy-val,cy-metrics,cy-report,cy-compare,cy-ground-truth,cy-export}]
               [--force] [--model MODEL]
               directory
```

| Аргумент | По умолчанию | Описание |
| --- | --- | --- |
| `directory` | — | Каталог, в который записываются файлы. Должен лежать внутри `CY_HOME` (см. [правило записи внутри `CY_HOME`](../workspace.md#правило-записи-внутри-cy_home) ([write containment rule](../../GLOSSARY.md#write-containment-rule))). |
| `--command` | `cy` | Команда, для которой создаётся дерево: `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`, `cy-compare`, `cy-ground-truth`, `cy-export`. |
| `--model` | `ultralytics`; для `cy-export` — `fasterrcnn/resnet50_fpn` | Модель вида `backend/preset` (см. [Модель](../configuration/model.md)). Другая модель, кроме `ultralytics`, допустима только для команд, которые запускают модель: `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-compare`, `cy-export`. Для `cy-export` — только пресеты Faster R-CNN. |
| `--force` | выключен | Разрешает заменить существующие файлы примеров. |
| `-h`, `--help` | — | Показать справку и выйти. |

## Как это работает

1. Команда проверяет сочетание `--command` и `--model`.
2. Она собирает конфигурацию выбранной команды с выбранной моделью и готовит содержимое файлов.
3. До первой записи она проверяет все пути назначения: каждый родительский путь должен быть обычным каталогом, а не символической ссылкой; существующий файл без `--force` — ошибка; с `--force` заменяются только обычные файлы. Если проверка не прошла, не записывается ни один файл.
4. Команда создаёт каталоги и записывает файлы, печатая `Wrote <путь>` для каждого.

Записываемые файлы:

| Файл | Когда |
| --- | --- |
| `<команда>.yaml` | Всегда. Файл, который вы правите и передаёте в `--config-name`. В начале — комментарии с готовой строкой запуска и подсказками; `???` отмечает обязательные значения. |
| `<конфигурация>.yaml` | Всегда. Базовая конфигурация команды: `pipeline.yaml` для `cy`, `ground_truth.yaml` для `cy-ground-truth`, для остальных имя команды без `cy-` (`train.yaml`, `metrics.yaml` и т. д.). |
| `transforms/default.yaml`, `transforms/albumentations.yaml`, `transform_overrides/<модель>_default.yaml`, `transform_overrides/<модель>_albumentations.yaml` | `cy` и `cy-train` (см. [Аугментации](../configuration/transforms.md)). |
| `model/<модель>.yaml` | Команды, которые запускают модель: `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-compare`, `cy-export`. |
| `ultralytics/_defaults.yaml`, `ultralytics_predict/_defaults.yaml` | `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-compare`. |
| `ultralytics/default.yaml` | Команды, которые запускают модель, при `--model ultralytics` (см. [Ultralytics](../configuration/ultralytics.md)). |
| `ultralytics_predict/default.yaml` | `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-compare` при `--model ultralytics` (см. [Ultralytics: предсказание](../configuration/ultralytics-predict.md)). |

Например, `cy-init-config configs` записывает:

```text
configs/cy.yaml
configs/pipeline.yaml
configs/transforms/default.yaml
configs/transform_overrides/ultralytics_default.yaml
configs/transforms/albumentations.yaml
configs/transform_overrides/ultralytics_albumentations.yaml
configs/model/ultralytics.yaml
configs/ultralytics/_defaults.yaml
configs/ultralytics_predict/_defaults.yaml
configs/ultralytics/default.yaml
configs/ultralytics_predict/default.yaml
```

`cy-init-config --command cy-metrics configs` записывает только `configs/cy-metrics.yaml` и `configs/metrics.yaml`; `--command cy-export` — `cy-export.yaml`, `export.yaml` и `model/fasterrcnn/resnet50_fpn.yaml`. Для модели с `/` в имени файлы модели лежат во вложенных каталогах, например `model/rfdetr/small.yaml` и `transform_overrides/rfdetr/small_default.yaml`.

Запуск по созданному дереву (строка из комментария в начале файла команды):

```bash
cy-train --config-dir /workspace/project/configs --config-name cy-train
```

Как устроено локальное дерево и как его переопределять, описано в [Конфигурации](../configuration/README.md#локальное-дерево-конфигурации).

## Результат

Файлы в каталоге `directory`. Для каждого файла в stderr выводится строка журнала уровня `INFO` с `Wrote <путь>`. При ошибке перед сообщением `cy-init-config: error: ...` выводятся строка журнала уровня `DEBUG` с той же причиной, трассировка и строка `usage`.

### Коды завершения

| Код | Значение |
| --- | --- |
| `0` | Все файлы записаны. |
| `2` | Ошибка аргументов, недопустимое сочетание `--command` и `--model`, неизвестная модель, каталог вне `CY_HOME` или ошибка проверки путей (в этих случаях ни один файл не записан), а также ошибка файловой системы во время записи (файлы, записанные до неё, остаются). |

## Частые ошибки

```text
cy-init-config: error: Cannot initialize configuration directory configs: FileExistsError: configs/cy.yaml already exists. Pass --force to overwrite examples.
```

Файлы уже созданы раньше. Добавьте `--force` или выберите другой каталог.

```text
cy-init-config: error: Cannot initialize configuration directory configs: ValueError: cy-metrics does not execute a model
```

`--model` с моделью, отличной от `ultralytics`, передан команде, которая не запускает модель (`cy-metrics`, `cy-report`, `cy-ground-truth`). Уберите `--model`.

```text
cy-init-config: error: Cannot initialize configuration directory configs: ValueError: cy-export supports only Faster R-CNN presets
```

Для `cy-export` укажите preset `fasterrcnn/...` или не указывайте `--model`.

```text
cy-init-config: error: Cannot initialize configuration directory configs: MissingConfigException: In 'pipeline': Could not find 'model/nope/x'
```

Неизвестная модель. Список `Available options in 'model'` под сообщением показывает только `ultralytics`, а не все модели. Список моделей — на странице [Модель](../configuration/model.md).

```text
cy-init-config: error: Cannot initialize configuration directory ../outside: ValueError: Project write destination ../outside must be contained beneath CY_HOME=/workspace/project; choose a destination inside CY_HOME or select the intended project workspace. External input and library configuration paths remain supported.
```

Каталог лежит вне `CY_HOME`. Выберите каталог внутри рабочего каталога ([workspace](../../GLOSSARY.md#workspace)) или задайте другой `CY_HOME` (см. [Рабочий каталог](../workspace.md)).

`... is not a regular directory` и `... is not a regular file; choose another directory.` означают, что на пути есть символическая ссылка или объект не того типа. Выберите другой каталог.

## См. также

- [Конфигурация](../configuration/README.md)
- [Модель](../configuration/model.md)
- [Рабочий каталог](../workspace.md)
