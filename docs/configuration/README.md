# Конфигурация

Девять команд CY — `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`, `cy-compare`, `cy-ground-truth` и `cy-export` — приложения Hydra. У них нет обычных флагов для параметров: команда собирает конфигурацию (configuration) из встроенных значений по умолчанию, ваших YAML-файлов и override в командной строке. Эта страница описывает, как это устроено; ключи каждой группы конфигурации (config group) описаны на отдельных страницах.

| Группа | Страница |
| --- | --- |
| `model` | [model.md](model.md) |
| `ultralytics` | [ultralytics.md](ultralytics.md) |
| `ultralytics_predict` | [ultralytics-predict.md](ultralytics-predict.md) |
| `transforms` | [transforms.md](transforms.md) |
| `evaluation` | [evaluation.md](evaluation.md) |
| `clearml` | [clearml.md](clearml.md) |
| `fiftyone` | [fiftyone.md](fiftyone.md) |

Остальные ключи команды перечислены на странице этой команды, например [`cy-train`](../commands/cy-train.md).

## Override

Значение задаётся аргументом `key=value`, вложенный ключ — через точку:

```bash
cy-train ground_truth=data/ground_truth.csv ultralytics.epochs=50 clearml.project_name=my-project
```

Префиксы работают так, как их определяет Hydra:

| Запись | Действие |
| --- | --- |
| `key=value` | Изменить существующий ключ |
| `+key=value` | Добавить ключ, которого нет в конфигурации |
| `++key=value` | Добавить ключ или изменить существующий |
| `~key` | Удалить ключ |

CY принимает только ключи, которые есть у команды. Новый ключ верхнего уровня, добавленный через `+`, отклоняется:

```text
ValueError: Unsupported wrapper settings: ['foo']
```

Ключ верхнего уровня, удалённый через `~`, команда берёт со значением по умолчанию. Обязательный ключ удалить нельзя: команда завершается до создания задачи ClearML (task), например `Required setting evaluation is missing`. Hydra не удаляет ключ со значением `null`.

Списки и строки со спецсимволами берите в кавычки оболочки, например `'clearml.tags=[my-tag]'`.

## Выбор варианта группы

Группа `model` выбирается целиком: `model=<backend>/<preset>` для `rfdetr`, `deimv2`, `fasterrcnn` и `fcos`, `model=ultralytics` для Ultralytics (это вариант по умолчанию).

```bash
cy-train model=rfdetr/small ground_truth=data/ground_truth.csv
```

Список доступных вариантов печатает `--help` в разделе `== Configuration groups ==` (строки `model/<backend>: ...`), а описание — страница [model.md](model.md). Профиль ([transforms profile](../../GLOSSARY.md#transforms-profile)) аугментации выбирается так же: `transforms=default` или `transforms=albumentations`, см. [transforms.md](transforms.md).

## Какие ключи действуют для какого backend

Параметры обучения и предсказания задаются в разных местах в зависимости от семейства моделей ([detector family](../../GLOSSARY.md#detector-family)):

| Backend | Обучение | Предсказание |
| --- | --- | --- |
| `ultralytics` | `ultralytics.*` | `ultralytics_predict.*` |
| `rfdetr`, `deimv2`, `fasterrcnn`, `fcos` | `model.train.*` | `model.predict.*` |

Изменённый ключ «чужой» группы — ошибка, а не молчаливый пропуск:

```text
ValueError: Changed ultralytics settings ['epochs'] are inactive for rfdetr/small; use model.train instead
ValueError: Changed model.train settings [...] are inactive for ultralytics; use ultralytics instead
```

Для `ultralytics_predict` сообщение аналогично и советует `model.predict` или `ultralytics_predict`.

Прочие ограничения:

- Группа `transforms` есть только у `cy` и `cy-train`.
- `cy-export` работает только с вариантами `fasterrcnn/*`; другой выбор даёт `cy-export supports only Faster R-CNN presets`.
- В группе `inference` допустимы только `reuse_existing` и `image_name`.

## Локальное дерево конфигурации

Чтобы хранить свои значения в файлах, создайте каталог с YAML (это делает [`cy-init-config`](../commands/cy-init-config.md)) и укажите его через `--config-dir`:

```bash
cy-train --config-dir configs ground_truth=data/ground_truth.csv
```

- Hydra ищет конфигурацию сначала в `--config-dir`, затем во встроенных значениях пакета. Файл в `configs` с тем же именем, что и встроенный (например, `train.yaml` или `ultralytics/_defaults.yaml`), заменяет встроенный; группы и файлы, которых в `configs` нет, берутся из пакета.
- `--config-name` выбирает корневой файл вместо имени команды по умолчанию (`pipeline` для `cy`, `ground_truth` для `cy-ground-truth`, иначе имя команды без `cy-`). Свой файл может наследовать встроенный через `defaults`:

```yaml
# configs/my-train.yaml
defaults:
  - train
  - _self_
clearml:
  project_name: my-project
```

```bash
cy-train --config-dir configs --config-name my-train ground_truth=data/ground_truth.csv
```

Override в командной строке применяются поверх файлов.

[`cy-init-config`](../commands/cy-init-config.md) создаёт в каталоге корневой файл `cy-<команда>.yaml` (например, `cy-train.yaml`) и копии встроенных файлов. Чтобы команда читала именно его, укажите `--config-name`:

```bash
cy-train --config-dir configs --config-name cy-train ground_truth=data/ground_truth.csv
```

Без `--config-name` команда берёт `train.yaml`, а файлы групп, которые подключает только `cy-train.yaml` (например, `ultralytics/default.yaml`), не действуют.

## Просмотр конфигурации

| Аргумент | Что печатает |
| --- | --- |
| `--help` | Группы конфигурации и собранную конфигурацию команды |
| `--hydra-help` | Справку Hydra |
| `--cfg job` | Собранную конфигурацию с учётом override, без запуска |
| `--cfg hydra` | Настройки Hydra, в том числе каталоги вывода |
| `--info` | Пути поиска конфигурации и выбранные значения по умолчанию |

`--cfg` ничего не запускает и не создаёт задачу ClearML (task). Интерполяции вида `${ultralytics.save_txt}` печатаются как есть. Hydra не позволяет сочетать `--cfg` с `-m`.

## Multirun

`-m` (`--multirun`) запускает sweep: значения через запятую дают по одному заданию на каждую комбинацию.

```bash
cy-train -m ground_truth=data/ground_truth.csv ultralytics.epochs=50,100
```

- Значения через запятую без `-m` (или без `hydra.mode=MULTIRUN`) отклоняются: `Use -m or hydra.mode=MULTIRUN to expand a Hydra sweep`.
- До запуска первого задания CY собирает конфигурацию каждого задания и проверяет в ней отклонённые ключи очереди и пути записи. Такая ошибка в любом задании останавливает весь sweep до начала работы; остальные проверки выполняются при запуске каждого задания.
- Задания выполняются последовательно. Поддерживаются только стандартные `BasicSweeper` и `BasicLauncher` Hydra; другой sweeper или launcher даёт `cy supports sequential BasicSweeper/BasicLauncher sweeps; use cy-queue for concurrent execution`.
- Пустой sweep отклоняется: `Hydra sweep must produce at least one job`.
- Все задания одного запуска получают общий тег multirun ([multirun tag](../../GLOSSARY.md#multirun-tag)) вида `multirun-<ГГГГММДД-ЧЧММСС>-<шесть слов через дефис>` (время в UTC). Он добавляется к `clearml.tags`, ваши теги сохраняются.

## Каталоги Hydra

Hydra не меняет текущий каталог (`hydra.job.chdir=false`). Свои файлы она пишет в каталоги Hydra ([Hydra output directory](../../GLOSSARY.md#hydra-output-directory)):

| Режим | Каталог |
| --- | --- |
| Обычный запуск | `CY_HOME/outputs/<ГГГГ-ММ-ДД>/<ЧЧ-ММ-СС>-<host>-<pid>` |
| Sweep | `CY_HOME/multirun/<ГГГГ-ММ-ДД>/<ЧЧ-ММ-СС>-<host>-<pid>/<номер задания>` |

Внутри — `.hydra/config.yaml`, `.hydra/hydra.yaml`, `.hydra/overrides.yaml` и журнал `common.log`; для sweep рядом с заданиями лежит `multirun.yaml`. Каталоги можно переопределить через `hydra.run.dir` и `hydra.sweep.dir`, но они, как и любой путь записи, должны быть внутри рабочего каталога ([workspace](../../GLOSSARY.md#workspace)) `CY_HOME`: так требует [правило записи внутри `CY_HOME`](../workspace.md#правило-записи-внутри-cy_home) ([write containment rule](../../GLOSSARY.md#write-containment-rule)). Результаты команд пишутся не сюда, а в каталог запуска ([run directory](../../GLOSSARY.md#run-directory)) в `runs/`.

## Отклонённые ключи очереди

Ключи `queue`, `autogpu`, `auto_gpu` и выбор `hydra/launcher=cy_queue` удалены из прямых команд. Их наличие в командной строке, в корневом YAML или в файлах, подключённых через `defaults` из `--config-dir`, останавливает команду до запуска:

```text
ValueError: Legacy queue/autogpu controls are removed from direct cy commands. Remove these settings from CLI overrides and saved YAML. Use cy-queue submit for scheduled execution; direct commands preserve native devices.
```

Уберите эти ключи. Запуск через очередь описан на странице [Очередь](../queue.md).

## Интерполяции в файлах конфигурации

Файлы, которые команда публикует в ClearML как конфигурацию (описание датасета `data_yaml`, файл отчёта `report_config_path`), могут содержать интерполяции OmegaConf вида `${clearml.project_name}`. CY разрешает их относительно собранной конфигурации команды; ключ верхнего уровня файла с тем же именем, что у ключа команды, заменяет его целиком. Типы значений, пустые значения и `null` сохраняются. Вычисляемая ссылка вида `${${key}}` и незаполненное значение `???` не допускаются. Любая ошибка разрешения останавливает команду; сообщение не содержит ни значений, ни имени поля:

```text
ValueError: Configuration values could not be resolved: ValueError
```

Проверьте в файле ссылки `${...}`: каждая должна указывать на существующий ключ команды, а ключ верхнего уровня файла не должен затенять ключ команды, на который ссылается другое значение.

Значения, похожие на пароли и токены, в опубликованной копии заменяются заглушкой; для запуска используется файл с исходными значениями.

## Коды завершения

Ошибка проверки конфигурации завершает команду с кодом `1`. Ошибки, найденные до запуска Hydra (ключи очереди, sweep без `-m`, пути записи вне `CY_HOME`), печатаются с полным стеком. Для ошибок, найденных после сборки конфигурации (например, `Unsupported wrapper settings`), Hydra печатает только сообщение; полный стек выводится при `HYDRA_FULL_ERROR=1`.

## См. также

- [Установка и окружение](../installation.md)
- [Рабочий каталог](../workspace.md)
- [Публикация в ClearML и FiftyOne](../publication.md)
