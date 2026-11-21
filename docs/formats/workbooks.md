# Книги Excel

`cy-metrics`, `cy-compare` и `cy-report` записывают результаты в книги Excel (workbook) и кладут рядом CSV- и JSON-файлы с подробными данными. Здесь описано, какие файлы появляются, какие в них листы и как читать подпись модели ([model identity](../../GLOSSARY.md#model-identity)) внизу листа.

Во всех именах `<split>` — имя split, например `test`. Символы, кроме латинских букв, цифр, `-`, `_` и `~`, в нём кодируются как `%XX` по байтам UTF-8 (точка — `%2E`, пробел — `%20`).

## Метрики: `cy-metrics`

[`cy-metrics`](../commands/cy-metrics.md) (и этап ([stage](../../GLOSSARY.md#stage)) метрик [`cy`](../commands/cy.md)) подбирает пороги уверенности (confidence threshold) на `val` и считает метрики для каждого split из ключа `splits`. В каталог результатов он пишет:

| Файл | Содержимое |
| --- | --- |
| `metrics_best_confidences_val.csv` | Подобранные пороги ([selected confidence thresholds](../../GLOSSARY.md#selected-confidence-thresholds)): порог уверенности для каждого класса, подобранный на `val` (при `confidence_optimization=global` в [группе `evaluation`](../configuration/evaluation.md) у всех классов одно значение); колонки `class_name`, `confidence`. Один файл на запуск |
| `full_dashboard_<split>.xlsx` | Дашборд ([dashboard](../../GLOSSARY.md#dashboard)): полная таблица метрик по классам |
| `метрики_дтрк_<split>.xlsx` | Дашборд ДТРК, который строит digital-metrics |
| `matrix_<split>.xlsx` | Матрица ошибок (confusion matrix) |
| `recall_confidence_intervals_<split>.png`, `precision_confidence_intervals_<split>.png`, `perebrak_confidence_intervals_<split>.png`, `nedobrak_confidence_intervals_<split>.png` | Графики доверительных интервалов |
| `metrics_evaluation_<split>.xlsx` | Сводная книга, листы описаны ниже |
| `metrics_evaluation_<split>_ground_truth_matches.csv` | Каждая рамка разметки ([ground truth](../../GLOSSARY.md#ground-truth)) и её сопоставление с предсказаниями |
| `metrics_evaluation_<split>_prediction_matches.csv` | Каждое предсказание и его сопоставление с разметкой |
| `metrics_evaluation_<split>_thresholds.csv` | Пороги, при которых посчитан split: `class_name`, `confidence` |
| `metrics_evaluation_<split>_methodology.csv` | Параметры оценки: колонки `parameter` и `value`, значение записано в JSON |
| `evaluation_<split>.json` | Все данные оценки split в одном файле (см. ниже) |

Числа в CSV-файлах `cy-metrics` записаны с 17 значащими цифрами, чтобы их можно было прочитать без потерь.

Листы `metrics_evaluation_<split>.xlsx`:

| Лист | Содержимое |
| --- | --- |
| `summary` | Сводные метрики split одной строкой |
| `per_class` | Метрики по классам, первая колонка `class_name` |
| `confusion_matrix` | Матрица ошибок |
| `Dataset counts` | Число объектов по классам в каждом split датасета, на котором обучена модель ([см. ниже](#лист-dataset-counts)) |

### `evaluation_<split>.json`

| Поле | Содержимое |
| --- | --- |
| `schema_version` | `1` |
| `split` | Имя split |
| `image_names` | Оценённые изображения |
| `thresholds` | Порог уверенности по классу |
| `ground_truth` | Рамки разметки: `index`, `image_name`, `label`, `box`, `confidence`, `status` (`TP`, `FP`, `FN` или `filtered`) |
| `predictions` | Рамки предсказаний с теми же полями |
| `matches` | Сопоставления: `gt_index`, `pred_index`, `gt_label`, `pred_label`, `confidence`, `iou`, `status` (`TP`, `FP` или `FN`) |
| `methodology` | Параметры оценки |
| `report` | Классы, матрица ошибок, PR-кривые и AP по классам (`ap50`, `ap75`, `ap50_95`) |
| `model_identity` | Модель, к которой относятся результаты |

## Сравнение: `cy-compare`

[`cy-compare`](../commands/cy-compare.md) оценивает две модели на одном split и пишет в каталог результатов:

| Файл | Содержимое |
| --- | --- |
| `full_dashboard_baseline_<split>.xlsx`, `full_dashboard_candidate_<split>.xlsx` | Дашборды каждой модели; рядом такие же `метрики_дтрк_...`, `matrix_...` и графики с суффиксом `baseline_<split>` или `candidate_<split>` |
| `baseline_predictions_<split>_<хэш>.csv`, `candidate_predictions_<split>_<хэш>.csv` | [Предсказания](predictions.md) каждой модели |
| `compare_workbook_<split>.xlsx` | Статистическое сравнение моделей |
| `compare_workbook_<split>_excluded.csv` | Классы, исключённые из сравнения, и причины |
| `compare_workbook_<split>_methodology.csv` | Параметры сравнения: колонки `Параметр` и `Значение` |
| `comparison_manifest.json` | Связь файлов одного сравнения; его читает `cy-report` |

Листы `compare_workbook_<split>.xlsx`: `Сравнение` (по строке на класс, последняя строка `Итого`, вердикты `улучшение`, `деградация`, `не значимо`, пропущенные значения `NA`) и `Dataset counts` с числами объектов для обеих моделей.

Поля `comparison_manifest.json`: `split`, `baseline_dashboard`, `candidate_dashboard`, `baseline_predictions`, `candidate_predictions`, `statistical_workbook` (имена файлов в том же каталоге), `baseline_identity`, `candidate_identity`.

Сравнение пропускается, если [baseline](../../GLOSSARY.md#baseline) задан только тегом `prod` (без task ID, проекта, имени задачи и весов) и в проекте нет завершённой задачи ClearML (task) с этим тегом. Тогда `cy-compare` оценивает только модель-кандидат ([candidate model](../../GLOSSARY.md#candidate-model)): пишет `full_dashboard_candidate_<split>.xlsx` с соседними файлами и `candidate_predictions_<split>_<хэш>.csv`, а вместо `compare_workbook_<split>.xlsx` и `comparison_manifest.json` — книгу кандидата `compare_evaluation_candidate_<split>.xlsx` с листами `Classes`, `Summary` и `Dataset counts`. Рядом лежат `compare_evaluation_candidate_<split>_thresholds.csv` (`class_name`, `confidence`) и `compare_evaluation_candidate_<split>_methodology.csv` с колонками `status` (`skipped`), `reason` и описанием модели-кандидата. Без манифеста сравнения ([comparison manifest](../../GLOSSARY.md#comparison-manifest)) `cy-report` по такому каталогу не запускается.

## Отчёт: `cy-report`

[`cy-report`](../commands/cy-report.md) читает `comparison_manifest.json` из каталога `comparison_dir` и две книги `full_dashboard_...`, на которые он ссылается. Без манифеста команда останавливается: `Comparison directory <каталог> has no comparison_manifest.json; run cy-compare first`. Если книги из манифеста нет в каталоге: `Comparison candidate dashboard does not exist: <путь>` (или `baseline dashboard`). Вместо дашбордов нельзя подать `compare_workbook_<split>.xlsx`: `The candidate input is not a per-model metrics dashboard: ... Use the candidate and baseline dashboards, not the statistical comparison workbook.`

Команда пишет две книги:

| Файл | Листы по умолчанию |
| --- | --- |
| `report_dev_<split>.xlsx` | `Новая модель` (модель-кандидат), `Прод модель` (baseline), `Сравнение`, `Удаленные классы` |
| `report_business_<split>.xlsx` | `Новая модель`, `Прод модель`, `Сравнение`, `Вердикт`, `Удаленные классы` |

Имена листов можно переопределить в разделе `sheet_names` YAML-файла, путь к которому задаёт ключ `report_config_path`.

Классы, у которых в обучающем split меньше `min_train_count` объектов, в отчётные таблицы не попадают: они перечислены на листе `Удаленные классы` с причиной `Мало примеров train (< 20)`. По умолчанию `min_train_count` равен 20; другое целое значение задаётся ключом `min_train_count` в том же YAML-файле.

Если у какого-то класса нет корректного числа обучающих объектов, этот класс исключается из агрегатов, отфильтрованных по этому числу, в обе книги добавляются листы `Unknown training count` и `Report issues`, а команда пишет предупреждение `Reports contain N unavailable training counts; ...`.

### Бизнес-отчёт

На листах `Новая модель`, `Прод модель` и `Сравнение` книги `report_business_<split>.xlsx` показан фиксированный набор колонок в фиксированном порядке:

| Колонка дашборда | Заголовок в отчёте | Формат | Строка `Среднее` |
| --- | --- | --- | --- |
| имя класса | `Класс` | текст | подпись `Среднее` |
| `tp`, `fp`, `fn` | без изменений | `0` | `NA` |
| `confidence` | `Порог` | `0.0000` | `NA` |
| `precision`, `recall`, `f1_score` | без изменений | `0.0000` | среднее |
| `perebrak`, `nedobrak` | `Перебраковка, %`, `Недобраковка, %` | `0.00` | среднее |
| вычисляются по `perebrak` и `nedobrak` | `Перебраковка в целях`, `Недобраковка в целях`, `Перебраковка грубо не в целях`, `Недобраковка грубо не в целях` | `0.00` | среднее |
| `Количество примеров test`, `train`, `val` | `Число примеров test`, `train`, `val` | `0` | сумма |

Колонка из списка, которой нет ни в одном из двух дашбордов, пропускается. Другие колонки дашборда (например, `ap50`, `cohen_kappa` и доверительные интервалы) в бизнес-отчёт не попадают. Если ни в одном дашборде нет чисел примеров по split, вместо трёх колонок показана одна `Количество примеров`. Заголовки оставшихся колонок можно переименовать в разделе `business.column_translations` YAML-файла из `report_config_path`. Во всех ячейках записаны вычисленные значения, формул в книге нет.

Строка `Среднее` на листах моделей считается по классам этой модели, попавшим в таблицу:

- в колонках из списка `excluded_from_mean` того же YAML-файла стоит `NA`; по умолчанию из показанных колонок это `tp`, `fp`, `fn` и `Порог`;
- в колонках числа примеров стоит сумма, каким бы ни был список `excluded_from_mean`;
- в остальных колонках стоит среднее.

На листе `Сравнение` каждая ячейка равна значению модели-кандидата минус значение baseline, включая `tp`, `fp`, `fn`, `Порог`, колонки целей и числа примеров. Если значения нет хотя бы у одной модели, в ячейке стоит `NA`. Строка `Среднее` этого листа считается по классам, общим для обеих моделей: сумма разниц в колонках числа примеров, среднее разниц в остальных, `NA` в колонках из `excluded_from_mean`. Цветом отмечены только разницы `precision`, `recall`, `f1_score`, перебраковки и недобраковки. Под таблицей записана легенда: строка `Легенда:` и четыре строки текста в колонке A, первые две — на окрашенных ячейках.

На листах `Новая модель`, `Прод модель`, `Сравнение` и `Вердикт` через одну пустую строку под содержимым записано примечание о наборах классов — пять строк в колонке A:

```text
Средние и вердикт: собственный набор допустимых классов каждой модели (новая: N, прод: M);
среднее разниц: общих классов K.
Наборы могут различаться;
NA — отсутствующие или отфильтрованные данные.
Причины отсутствия сравнения приведены на листе исключений.
```

[Подпись модели](#подпись-модели) начинается через одну пустую строку после примечания.

Колонок `... coverage` и строк с числом допустимых классов (`Valid class counts`) в бизнес-отчёте нет. В `report_dev_<split>.xlsx` эти строки по-прежнему записаны под таблицами, и сама эта книга не изменилась.

## Лист `Dataset counts`

Лист показывает, сколько объектов каждого класса было в каждом split датасета, на котором обучена модель. Колонки: `Role`, `Model`, `Training task ID`, `Original split`, `Class`, `Annotation count`. Строки для `train`, `val` и `test` есть всегда; если CY не знает чисел для split, в `Class` и `Annotation count` стоит `NA`. Неизвестные имя модели и task ID тоже записаны как `NA`. Лист есть в `full_dashboard_...`, `метрики_дтрк_...`, `matrix_...`, `metrics_evaluation_<split>.xlsx`, `compare_workbook_<split>.xlsx` и `compare_evaluation_candidate_<split>.xlsx`. В книгах `cy-report` его нет.

## Подпись модели

Под таблицами каждого листа CY пишет, к какой модели относятся результаты. В книгах `cy-metrics` роль модели — `model`, в книгах сравнения и отчёта — `baseline` и `candidate`. Для каждой роли выводятся две строки:

```text
candidate: my-run
Training task: open in ClearML
```

- Первая строка — роль и подпись модели. Если модель зарегистрирована в ClearML и ссылка на неё известна, строка — ссылка.
- Вторая строка — ссылка `Training task: open in ClearML` на задачу ClearML обучения, если известны её ID и ссылка. Если ID известен, а ссылки нет, — `Training source: recorded`, если ID неизвестен, — `Training source: unavailable`.

В нижний колонтитул для печати попадает та же подпись в одну строку, роли разделены `|`:

```text
baseline: my-run · Training source: recorded | candidate: my-run · Training source: unavailable
```

Идентификаторы задач и моделей и хэши в видимом тексте не появляются. Если имена классов заменены на читаемые, добавляется строка `Class labels use readable aliases; original values are retained.`

Внутри книги хранится машиночитаемая копия этих данных и контрольная сумма содержимого. Не редактируйте и не пересохраняйте книги, которые потом читает `cy-report`. Книга, изменённая после подписи, отклоняется с ошибкой `Workbook changed after model identity annotation; regenerate the workbook before reading its metrics or identities`. Программа, которая при сохранении отбрасывает служебную часть книги (например, openpyxl), молча удаляет машиночитаемую подпись. Чтобы получить книгу заново, повторите команду, которая её записала.

## См. также

- [Предсказания](predictions.md)
- [Публикация](../publication.md): какие из этих файлов попадают в ClearML
- [Конфигурация `evaluation`](../configuration/evaluation.md)
