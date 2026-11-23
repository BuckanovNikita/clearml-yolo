# cy-metrics

`cy-metrics` считает метрики детекции по готовым предсказаниям (predictions) и разметке ([ground truth](../../GLOSSARY.md#ground-truth)). Пороги уверенности (confidence threshold) подбираются один раз на split `val`, затем каждый split из `splits` оценивается при этих порогах. Запускайте команду после [`cy-predict`](cy-predict.md), когда метрики нужны отдельно от пайплайна ([pipeline](../../GLOSSARY.md#pipeline)) [`cy`](cy.md).

## Примеры

Оценить `train`, `val` и `test`:

```bash
cy-metrics predictions=runs/my-run/predict.csv ground_truth=data/ground_truth.csv \
  clearml.project_name=my-project clearml.task_name=my-run
```

Оценить только `val` и `test` без публикации в FiftyOne:

```bash
cy-metrics predictions=runs/my-run/predict.csv ground_truth=data/ground_truth.csv \
  'splits=[val,test]' fiftyone.enabled=false clearml.project_name=my-project clearml.task_name=my-run
```

Оценить CSV, полученный другим инструментом, с подписью модели ([model identity](../../GLOSSARY.md#model-identity)):

```bash
cy-metrics predictions=runs/my-run/predict.csv ground_truth=data/ground_truth.csv model_label=my-model \
  clearml.project_name=my-project clearml.task_name=my-run
```

## Синтаксис и аргументы

```text
cy-metrics [--config-dir DIR] [--config-name NAME] [--cfg job] [KEY=VALUE ...]
```

Команда — приложение Hydra: параметры задаются override вида `ключ=значение` (см. [Конфигурация](../configuration/README.md)).

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `predictions` | обязателен | CSV предсказаний (см. [Предсказания](../formats/predictions.md)). |
| `model_label` | `null` | Подпись модели. Нужна, только если рядом с CSV предсказаний нет файла `<predictions>.provenance.json` (например, `runs/my-run/predict.csv.provenance.json`, его пишет [`cy-predict`](cy-predict.md)) или в нём не записана модель; если модель записана, `model_label` не используется. |
| `ground_truth` | обязателен | CSV разметки (см. [Разметка](../formats/ground-truth.md)) или ссылка на ClearML Dataset ([ClearML dataset reference](../../GLOSSARY.md#clearml-dataset-reference)): `{dataset_id: ...}` либо `{project_name: ..., name: ..., version: ...}` (`version` необязателен). `dataset_id` не совмещается с остальными полями. |
| `output_dir` | `null` | Каталог результатов. При `null` — `runs/<проект>/<задача>-<ID>/metrics` в каталоге запуска ([run directory](../../GLOSSARY.md#run-directory)). Должен быть внутри рабочего каталога ([workspace](../../GLOSSARY.md#workspace)) `CY_HOME`, см. [Рабочий каталог](../workspace.md). |
| `splits` | `[train,val,test]` | Split, для которых считаются метрики, в этом порядке. Повторы убираются. |
| `calibration_split` | `val` | Split для подбора порогов. Допустимо только `val`. |
| `evaluation` | см. группу | Сопоставление рамок (bounding box) и расчёт метрик: [`evaluation`](../configuration/evaluation.md). |
| `clearml` | см. группу | Задача ClearML (task): [`clearml`](../configuration/clearml.md). |
| `fiftyone` | см. группу | Публикация в FiftyOne: [`fiftyone`](../configuration/fiftyone.md). |

## Как это работает

1. До создания задачи ClearML команда проверяет `calibration_split`, отсутствие `all` в `splits` и значения групп `evaluation` и `fiftyone`. Затем она создаёт задачу ClearML и находит разметку. Локальный CSV используется как есть, с предупреждением `Using local ground-truth CSV ...; prefer a ClearML dataset reference for versioned annotations.`; ссылка на ClearML Dataset разрешается в CSV этого датасета.
2. Если `fiftyone.enabled=true`, выполняет предварительную проверку ([FiftyOne preflight](../../GLOSSARY.md#fiftyone-preflight)) FiftyOne (см. [FiftyOne](../publication.md#fiftyone)).
3. Определяет происхождение модели ([model provenance](../../GLOSSARY.md#model-provenance)): из `<predictions>.provenance.json`, иначе из `model_label`. Если этот файл есть, он должен соответствовать текущему содержимому CSV предсказаний: после правки CSV команда завершается ошибкой.
4. Проверяет правила split:
   - `calibration_split` равен `val`;
   - в `splits` нет `all`;
   - для каждого split из `splits` и для `val` в разметке есть строки;
   - ни одно `image_name` не входит одновременно в `val` и `test`;
   - каждое `image_name` предсказаний есть в разметке.
5. Загружает разметку и предсказания в задачу (артефакты `gt_csv` и `predicts_csv`, см. [Публикация](../publication.md#артефакты)).
6. Готовит данные по ключам группы `evaluation`: отбрасывает предсказания с некорректной геометрией, при `evaluation.preprocess=true` убирает дубликаты рамок разметки, применяет фильтры `preprocess_preds_*`. Список классов — объединение классов разметки и предсказаний.
7. Подбирает пороги уверенности только на `val` и записывает их в `metrics_best_confidences_val.csv`. Этот файл загружается в задачу как артефакт `metrics_best_confidences_val`; его читает [`cy-compare`](cy-compare.md).
8. Для каждого split из `splits` считает метрики при подобранных порогах ([selected confidence thresholds](../../GLOSSARY.md#selected-confidence-thresholds)), записывает книги Excel (workbook) и соседние файлы, публикует таблицу и скаляры в ClearML.
9. Если FiftyOne включён, публикует разметку, предсказания и результаты сопоставления.

Подобранные пороги применяются к `test` без изменений: `test` никогда не влияет на пороги.

### Недоступные значения

Число обучающих объектов по классу CY берёт из задачи ClearML, которая обучила checkpoint. Если число неизвестно (например, предсказания получены не из весов CY или у модели нет записанной задачи обучения), в колонке `Количество примеров train` книг `full_dashboard_<split>.xlsx` и `метрики_дтрк_<split>.xlsx` стоит `NA`, к книгам добавляются листы `Unknown training count` и `Report issues`, а в отчётах [`cy-report`](cy-report.md) такие классы не входят в агрегаты, отфильтрованные по числу обучающих объектов. Лист `Dataset counts` описан в [Книги Excel](../formats/workbooks.md#лист-dataset-counts).

## Результат

В `output_dir` записываются `metrics_best_confidences_val.csv` и для каждого split — `evaluation_<split>.json`, `metrics_evaluation_<split>.xlsx`, дашборды ([dashboard](../../GLOSSARY.md#dashboard)) и графики. Полный список и листы: [Метрики: `cy-metrics`](../formats/workbooks.md#метрики-cy-metrics). Что появляется в ClearML и FiftyOne: [Публикация](../publication.md). После каждого split команда пишет в журнал строку `Split '<split>': <N> classes, mean f1 <значение> -> <путь к дашборду>`.

### Коды завершения

| Код | Значение |
| --- | --- |
| `0` | Все split оценены, задача завершена успешно. Ошибки FiftyOne код не меняют. |
| `1` | Ошибка конфигурации, входных файлов, правил split или ClearML. Задача, если она уже создана, получает статус `failed` (см. [Успех и ошибка](../publication.md#успех-и-ошибка)). |

## Частые ошибки

Ошибки формата CSV описаны в [Разметка](../formats/ground-truth.md#ошибки) и [Предсказания](../formats/predictions.md#ошибки), ошибки ключей `evaluation` — в [`evaluation`](../configuration/evaluation.md).

| Сообщение | Причина и решение |
| --- | --- |
| `Missing mandatory value: predictions` | Не задан `predictions` (так же для `ground_truth`). |
| `Ground truth path must not be empty` | `ground_truth` — пустая строка. |
| `dataset_id cannot be combined with project_name, name or version` | В ссылке на ClearML Dataset заданы и `dataset_id`, и имя. Оставьте что-то одно. |
| `calibration_split must be exactly 'val'; test data must never calibrate thresholds` | `calibration_split` не `val`. Уберите override. |
| `split='all' is unsupported for frozen evaluation; name concrete splits` | В `splits` есть `all`. Перечислите split явно. |
| `No ground-truth rows for splits ['test']` | В разметке нет строк запрошенного split. Уберите его из `splits` или добавьте в разметку. |
| `No ground-truth rows for calibration split 'val'` | В разметке нет `val`. |
| `A logical image cannot belong to both val and test; overlapping image_name(s): [...]` | Одно изображение в `val` и `test`. Исправьте разметку. |
| `Prediction image_name values are outside canonical ground-truth membership: [...]; evaluation requires image_name='name'` | В предсказаниях есть значения `image_name`, которых нет в разметке. Проверьте, что предсказания сделаны по тому же датасету. |
| `Comparison and evaluation require image_name='name'; 'stem' is supported only for raw prediction export` | Предсказания записаны [`cy-predict`](cy-predict.md) с `image_name=stem` или `image_name=path`. Повторите предсказание с `image_name=name`. |
| `Prediction provenance does not match prediction CSV bytes` | CSV предсказаний изменён после записи `<predictions>.provenance.json`. Верните исходный CSV или повторите предсказание. |
| `Model provenance is unavailable; supply a custom model_label (comparison model references use label)` | Рядом с CSV предсказаний нет `<predictions>.provenance.json` или в нём не записана модель. Задайте `model_label`. |
| `Ground truth contains no labelled objects to evaluate` | Ни в разметке, ни в предсказаниях нет ни одного класса. |
| `Reconstructed AP50 for class '<класс>' (...) disagrees with authoritative compute_map AP50 (...)` | Проверка согласованности: AP50 класса, восстановленный CY по PR-кривой, отличается от AP50 библиотеки digital-metrics больше, чем на погрешность округления float32. Классы без объектов разметки не проверяются. Оценка останавливается; это ошибка CY, а не входных данных. |
| `Project write destination ... must be contained beneath CY_HOME=...` | `output_dir` вне рабочего каталога: нарушено правило записи внутри `CY_HOME` ([write containment rule](../../GLOSSARY.md#write-containment-rule)), см. [Рабочий каталог](../workspace.md#правило-записи-внутри-cy_home). |
| `Unrecognized Authentication Error: ...` | Сервер ClearML недоступен или не настроены учётные данные (см. [Установка](../installation.md#clearml)). |

## См. также

- [`evaluation`](../configuration/evaluation.md), [`fiftyone`](../configuration/fiftyone.md), [`clearml`](../configuration/clearml.md)
- [Книги Excel](../formats/workbooks.md), [Разметка](../formats/ground-truth.md), [Предсказания](../formats/predictions.md)
- [`cy-predict`](cy-predict.md), [`cy-val`](cy-val.md), [`cy-compare`](cy-compare.md), [`cy`](cy.md)
- [Публикация в ClearML и FiftyOne](../publication.md), [Рабочий каталог](../workspace.md)
- [Сценарии](../scenarios.md)
