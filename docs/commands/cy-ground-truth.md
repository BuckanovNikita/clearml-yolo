# cy-ground-truth

`cy-ground-truth` превращает YOLO-датасет, описанный YAML-файлом, в CSV разметки ([ground truth](../../GLOSSARY.md#ground-truth)), с которым работают остальные команды CY. Запускайте её один раз для нового датасета, перед обучением и метриками.

## Примеры

Построить CSV разметки в каталоге запуска ([run directory](../../GLOSSARY.md#run-directory)) по умолчанию:

```bash
cy-ground-truth data_yaml=data/dataset.yaml clearml.project_name=my-project clearml.task_name=my-run
```

Записать CSV по своему пути и отдать в split `test` треть изображений `val`:

```bash
cy-ground-truth data_yaml=data/dataset.yaml output=data/ground_truth.csv test_fraction=0.3 seed=42 \
  clearml.project_name=my-project clearml.task_name=my-run
```

## Синтаксис и аргументы

```text
cy-ground-truth [--config-dir DIR] [--config-name NAME] [--cfg job] [KEY=VALUE ...]
```

Команда — приложение Hydra: параметры задаются override вида `ключ=значение` (см. [Конфигурация](../configuration/README.md)). Корневая конфигурация называется `ground_truth`.

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `data_yaml` | обязателен | Путь к YAML-описанию YOLO-датасета. Что в нём допускается, описано в [Датасеты](../formats/datasets.md#вход-cy-ground-truth-yaml-yolo-датасета). |
| `output` | `null` | Путь CSV. При `null` — `ground_truth.csv` в каталоге запуска. Путь должен быть внутри рабочего каталога ([workspace](../../GLOSSARY.md#workspace)) `CY_HOME`, см. [Рабочий каталог](../workspace.md). |
| `test_fraction` | `0.5` | Доля изображений `val`, которая переносится в `test`, если в датасете нет split `test` или он пуст. Допустимо от `0` включительно до `1` не включая. |
| `seed` | `0` | Seed для выбора изображений, переносимых в `test`. Одинаковый seed даёт одинаковое разбиение. |
| `clearml` | см. группу | Проект, имя и теги задачи ClearML (task): [`clearml`](../configuration/clearml.md). Без override задача попадает в проект `clearml-yolo` с именем `yolo-run`, поэтому задавайте `clearml.project_name` и `clearml.task_name` явно. |

## Как это работает

1. Команда проверяет конфигурацию до обращения к ClearML: задан ли `data_yaml`, лежит ли `output`, если он задан, внутри `CY_HOME`, и лежит ли `test_fraction` в диапазоне от `0` включительно до `1` не включая.
2. Создаёт задачу ClearML.
3. Публикует файл `data_yaml` в задаче как объект конфигурации ([configuration object](../../GLOSSARY.md#configuration-object)) `dataset`. Ссылки `${...}` в файле разрешаются относительно конфигурации команды (см. [Интерполяции](../configuration/README.md#интерполяции-в-файлах-конфигурации)); дальше используется файл с разрешёнными значениями.
4. Читает датасет и строит CSV по шагам, описанным в [Как `cy-ground-truth` строит CSV](../formats/datasets.md#как-cy-ground-truth-строит-csv): собирает split, при необходимости выделяет `test` из `val` по `test_fraction` и `seed`, переводит рамки (bounding box) в пиксели.
   Сам файл `data_yaml` проверяется на этом шаге, когда задача уже создана. Если в `names` есть класс `background`, команда останавливается до записи CSV, даже если в разметке нет объектов этого класса.
5. Записывает CSV в `output`.
6. Копирует CSV в `result_publication/gt_csv.csv` рядом с ним и загружает копию в задачу как артефакт `gt_csv` (см. [Публикация](../publication.md#артефакты)).

## Результат

Один CSV в формате [Разметка (ground truth)](../formats/ground-truth.md). Без `output` он лежит в `runs/<проект>/<задача>-<ID>/ground_truth.csv`. Рядом с CSV команда создаёт каталог `result_publication/` с копией, которая уходит в ClearML. В ClearML остаются задача с объектом конфигурации `dataset` и артефактом `gt_csv`. В FiftyOne команда ничего не публикует.

### Коды завершения

| Код | Значение |
| --- | --- |
| `0` | CSV записан, задача завершена успешно. |
| `1` | Ошибка конфигурации, датасета или ClearML. Задача, если она уже создана, получает статус `failed` (см. [Успех и ошибка](../publication.md#успех-и-ошибка)). |

## Частые ошибки

Ошибки в самом датасете перечислены в [Ошибки `cy-ground-truth`](../formats/datasets.md#ошибки-cy-ground-truth).

| Сообщение | Причина и решение |
| --- | --- |
| `Missing mandatory value: data_yaml` | Не задан `data_yaml`. Добавьте `data_yaml=data/dataset.yaml`. |
| `Project write destination /etc/ground_truth.csv must be contained beneath CY_HOME=/workspace/project; choose a destination inside CY_HOME or select the intended project workspace.` | `output` вне рабочего каталога: нарушено правило записи внутри `CY_HOME` ([write containment rule](../../GLOSSARY.md#write-containment-rule)), см. [Рабочий каталог](../workspace.md#правило-записи-внутри-cy_home). Укажите путь внутри `CY_HOME`. |
| `Unrecognized Authentication Error: ...` | Сервер ClearML недоступен или не настроены учётные данные (см. [Установка](../installation.md#clearml)). |

## См. также

- [Датасеты](../formats/datasets.md) и [Разметка (ground truth)](../formats/ground-truth.md)
- [`cy-train`](cy-train.md), [`cy-metrics`](cy-metrics.md)
- [Рабочий каталог](../workspace.md), [Публикация в ClearML и FiftyOne](../publication.md)
- [Сценарии](../scenarios.md)
