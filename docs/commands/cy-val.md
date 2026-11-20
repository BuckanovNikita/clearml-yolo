# cy-val

`cy-val` выполняет валидацию (validation) готовых весов (weights): получает предсказания (predictions) для изображений разметки ([ground truth](../../GLOSSARY.md#ground-truth)), подбирает пороги уверенности (confidence threshold) на split `val` и считает метрики для выбранных split. Всё это происходит в одной задаче ClearML (task). Команда нужна, чтобы одним запуском оценить уже обученную модель.

## Примеры

```bash
cy-val weights=weights/best.pt model_label=my-model ground_truth=data/ground_truth.csv clearml.project_name=my-project clearml.task_name=my-run
```

Валидация локальных весов YOLO на `train`, `val` и `test`.

```bash
cy-val weights=<task-id> ground_truth=data/ground_truth.csv splits=[val,test] clearml.project_name=my-project clearml.task_name=my-run clearml.tags=[my-tag]
```

Валидация весов задачи обучения ClearML только на `val` и `test`.

```bash
cy-val model=deimv2/s weights=weights/best.pt model_label=my-model ground_truth=data/ground_truth.csv model.predict.batch=8 evaluation.iou_threshold=0.5 clearml.project_name=my-project clearml.task_name=my-run
```

Валидация DEIMv2 с другим batch size предсказания и порогом IoU.

## Синтаксис и аргументы

```text
cy-val [--config-dir configs] [ключ=значение ...]
```

Команда — приложение Hydra, см. [Конфигурация](../configuration/README.md).

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `model` | `ultralytics` | Семейство моделей ([detector family](../../GLOSSARY.md#detector-family)), preset и `model.predict`. См. [группа `model`](../configuration/model.md). |
| `ultralytics` | см. страницу группы | Источник значений, которые наследует `ultralytics_predict`. См. [группа `ultralytics`](../configuration/ultralytics.md). |
| `ultralytics_predict` | см. страницу группы | Параметры предсказания Ultralytics YOLO. См. [группа `ultralytics_predict`](../configuration/ultralytics-predict.md). |
| `weights` | `null` | Веса: путь, ID задачи ClearML или `clearml://<ID модели>`. Выбираются так же, как в [`cy-predict`](cy-predict.md#как-выбираются-веса). |
| `model_label` | `null` | Имя модели, если происхождение весов неизвестно, см. [`cy-predict`](cy-predict.md#model_label). |
| `ground_truth` | обязателен | Разметка, см. [Разметка](../formats/ground-truth.md). |
| `output_dir` | `null` | Каталог результатов. `null` — подкаталог `val` каталога запуска ([run directory](../../GLOSSARY.md#run-directory)) задачи: `runs/<проект>/<имя задачи>-<ID задачи>/val`, где имя задачи — `<clearml.task_name>/val` (см. [Рабочий каталог](../workspace.md#runs) ([workspace](../../GLOSSARY.md#workspace)) и [Публикация](../publication.md#задача-clearml)). Должен лежать внутри `CY_HOME`. |
| `splits` | `[train,val,test]` | Split, для которых считаются метрики. Каждый должен быть в разметке. |
| `evaluation` | см. страницу группы | Правила сопоставления и метрик. См. [группа `evaluation`](../configuration/evaluation.md). |
| `clearml` | см. страницу группы | Задача ClearML. См. [группа `clearml`](../configuration/clearml.md). |

У `cy-val` нет ключей `output`, `image_name`, `calibration_split` и группы `fiftyone`: предсказания всегда пишутся в `<output_dir>/predictions.csv` с `image_name=name`, публикации в FiftyOne нет. Параметры предсказания по семействам те же, что у [`cy-predict`](cy-predict.md#параметры-предсказания-по-семействам).

## Как это работает

1. Hydra собирает конфигурацию, команда проверяет ключи и пути записи, затем создаёт задачу ClearML. Если `output_dir` не задан, он выбирается по имени и ID задачи.
2. Если `ground_truth` ссылается на датасет ClearML, он скачивается.
3. Выполняется предсказание как в [`cy-predict`](cy-predict.md#как-это-работает) для split `val` и всех split из `splits` (повторы убираются, `val` идёт первым). Результат — `<output_dir>/predictions.csv`.
4. Пороги уверенности подбираются на `val` и с ними считаются метрики для каждого split из `splits`, как в [`cy-metrics`](cy-metrics.md). Результаты пишутся в `<output_dir>/metrics/`.

### Чем `cy-val` отличается от `cy-predict` + `cy-metrics`

| | `cy-val` | `cy-predict`, затем `cy-metrics` |
| --- | --- | --- |
| Задачи ClearML | Одна | Две |
| Split предсказания | `val` и `splits` | `splits` `cy-predict` (по умолчанию все изображения) |
| `image_name` | Всегда `name` | Задаётся в `cy-predict` |
| FiftyOne | Не публикуется | Публикуется, если `fiftyone.enabled=true` |
| Пути | `<output_dir>/predictions.csv`, `<output_dir>/metrics/` | `output` и `output_dir` задаются отдельно |

Split калибровки в обоих случаях — `val`.

## Результат

| Путь | Содержимое |
| --- | --- |
| `<output_dir>/predictions.csv` и файлы рядом | Предсказания и файлы, перечисленные на странице [`cy-predict`](cy-predict.md#результат). |
| `<output_dir>/metrics/` | Книги Excel (workbook) и файлы метрик, см. [Книги Excel](../formats/workbooks.md). |

Артефакты и графики задачи ClearML (`gt_csv`, `predicts_csv`, `metrics_best_confidences_val`, дашборды ([dashboard](../../GLOSSARY.md#dashboard)), `predict` / `resolution`, метрики по split) описаны в разделе [Публикация](../publication.md).

### Коды завершения

| Код | Когда |
| --- | --- |
| `0` | Предсказания и метрики записаны и опубликованы. |
| `1` | Любая ошибка. |

## Частые ошибки

```text
omegaconf.errors.MissingMandatoryValue: Missing mandatory value: ground_truth
```

Не задан `ground_truth`.

```text
ValueError: No ground-truth rows for splits ['test']
```

По умолчанию `splits=[train,val,test]`. Если в разметке нет какого-то split, перечислите только имеющиеся, например `splits=[val]`. Split `val` нужен всегда.

```text
hydra.errors.ConfigCompositionException: Could not override 'fiftyone.enabled'.
```

У `cy-val` нет группы `fiftyone` и ключей `image_name`, `output`, `calibration_split`; так же Hydra отвечает на любой другой неизвестный ключ. Уберите его из команды.

```text
ValueError: Project write destination /elsewhere/val must be contained beneath CY_HOME=/workspace/project; choose a destination inside CY_HOME or select the intended project workspace. External input and library configuration paths remain supported.
```

`output_dir` лежит вне `CY_HOME`.

```text
ValueError: Model provenance is unavailable; supply a custom model_label (comparison model references use label)
```

Добавьте `model_label=my-model`.

## См. также

- [`cy-predict`](cy-predict.md), [`cy-metrics`](cy-metrics.md), [`cy`](cy.md)
- [Группа `evaluation`](../configuration/evaluation.md), [группа `model`](../configuration/model.md)
- [Книги Excel](../formats/workbooks.md), [Публикация](../publication.md), [Рабочий каталог](../workspace.md)
