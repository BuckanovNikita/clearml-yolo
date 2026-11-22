# Группа `evaluation`

Группа конфигурации (config group) `evaluation` задаёт, как CY сопоставляет предсказания с разметкой ([ground truth](../../GLOSSARY.md#ground-truth)), подбирает пороги уверенности (confidence threshold) и считает метрики. Расчёт выполняет библиотека `digital-metrics`; эта страница описывает каждый ключ, его значение по умолчанию и ограничения, которые добавляет CY.

## Где действует группа

| Команда | Как задаётся | Что делает |
| --- | --- | --- |
| `cy-metrics` | `evaluation.*` | Подбор порогов на split `val` и метрики по каждому split. |
| `cy-val` | `evaluation.*` | То же, после предсказания по checkpoint. |
| `cy-compare` | `evaluation.*` | Сопоставление и метрики модели baseline ([baseline](../../GLOSSARY.md#baseline)) и модели-кандидата ([candidate model](../../GLOSSARY.md#candidate-model)) при уже известных порогах. |
| `cy` | `metrics.evaluation.*` | Этап ([stage](../../GLOSSARY.md#stage)) метрик и этап сравнения пайплайна ([pipeline](../../GLOSSARY.md#pipeline)). |

У остальных команд этой группы нет. Override `evaluation.<ключ>` для команды, у которой нет группы, или неизвестный ключ завершается ошибкой Hydra ещё до запуска, например `Could not override 'evaluation.foo'`.

В выводе `--cfg job` группа содержит строку `_target_: clearml_yolo.core.evaluation.models.EvaluationConfig`. Это не ключ настройки, оставьте его без изменений.

Hydra не проверяет значения ключей: `--cfg job` принимает, например, `evaluation.matching_strategy=bad`. Значения проверяются при запуске команды, до создания задачи ClearML (task): недопустимое значение даёт ошибку, и задача не создаётся.

## Ключи

| Ключ | По умолчанию | Допустимые значения | Описание |
| --- | --- | --- | --- |
| `iou_threshold` | `0.5` | число от `0` до `1` включительно | Минимальный IoU, при котором рамка (bounding box) предсказания может совпасть с рамкой разметки. Действует и при подборе порогов, и при расчёте метрик. |
| `matching_strategy` | `iou_prior` | `greedy`, `hungarian`, `iou_prior` | Способ сопоставления рамок: `greedy` перебирает предсказания по убыванию уверенности (как в Ultralytics), `iou_prior` перебирает пары по убыванию IoU с учётом класса, `hungarian` ищет глобально оптимальное назначение. При любом способе рамка предсказания сопоставляется только с рамкой разметки того же класса. |
| `ap_method` | `interp` | `interp`, `continuous` | Способ расчёта AP: `interp` — интерполяция по 101 точке (как в COCO и Ultralytics), `continuous` — площадь под ступенчатой кривой (VOC 2010+). |
| `confidence_optimization` | `per_class` | `per_class`, `global` | Как подбираются пороги уверенности на split `val`: `per_class` — отдельный порог для каждого класса, `global` — один порог для всех классов. Действует только там, где пороги подбираются: в `cy-metrics`, `cy-val` и на этапе метрик `cy`. Другое значение даёт ошибку `confidence_optimization must be 'per_class' or 'global', got '<значение>'`. |
| `skip_cohen_kappa` | `true` | только `true` | Каппа Коэна не вычисляется. Значение `false` даёт ошибку `Fixed evaluation currently requires skip_cohen_kappa=True`. |
| `preprocess` | `false` | `true`, `false` | При `true` до сопоставления из разметки каждого изображения удаляются дубликаты: из двух рамок с IoU больше `0.99` остаётся первая по порядку в файле, класс при этом не учитывается. На предсказания этот ключ не влияет. |
| `preprocess_preds_conf_threshold` | `null` | `null` или число от `0` до `1` | Предсказания с уверенностью ниже значения удаляются до сопоставления. `null` отключает фильтр. Действует при любом значении `preprocess`. |
| `preprocess_preds_nms_containment_threshold` | `null` | `null` или число от `0` до `1` | NMS внутри одного класса по вложенности: из двух рамок удаляется менее уверенная, если площадь пересечения, делённая на площадь меньшей рамки, не меньше значения. `null` отключает. Действует при любом значении `preprocess`. |
| `preprocess_preds_nms_iou_threshold` | `null` | `null` или число от `0` до `1` | NMS между разными классами: из двух рамок разных классов удаляется менее уверенная, если их IoU не меньше значения. `null` отключает. Действует при любом значении `preprocess`. |
| `backend` | `null` | только `null` | Должен оставаться `null`. В `cy-metrics`, `cy-val` и на этапе метрик `cy` любое другое значение даёт ошибку `Frozen thresholds require the native digital-metrics backend; backend='<значение>' is unsupported`. `cy-compare` этот ключ не читает. |

Перед расчётом CY всегда отбрасывает предсказания с некорректной геометрией (пустые, нечисловые или бесконечные координаты, перевёрнутые углы, нулевая площадь) и пишет в журнал предупреждение `Dropped N of M prediction boxes with invalid geometry: ...`. Этим поведением ключи группы не управляют.

## Пороги уверенности

Подобранные пороги ([selected confidence thresholds](../../GLOSSARY.md#selected-confidence-thresholds)) определяются один раз, только на split `val`, и затем применяются без изменений ко всем запрошенным split. Split для подбора задаёт ключ `calibration_split` рядом с группой (`calibration_split` в `cy-metrics`, `metrics.calibration_split` в `cy`); любое значение, кроме `val`, даёт ошибку. Пороги подбираются по разметке и предсказаниям после предварительной обработки: ключи `preprocess` и `preprocess_preds_*` меняют и пороги, и метрики. `cy-compare` пороги не подбирает: он берёт их у каждой модели (см. [`cy-compare`](../commands/cy-compare.md)), поэтому `confidence_optimization` там не действует.

Значения ключей группы записываются в конфигурацию задачи ClearML и в книгу Excel (workbook) с метриками (см. [Книги Excel](../formats/workbooks.md)).

## Пример

```bash
cy-metrics predictions=runs/my-run/predict.csv ground_truth=data/ground_truth.csv \
  evaluation.iou_threshold=0.7 evaluation.confidence_optimization=global \
  clearml.project_name=my-project clearml.task_name=my-run
```

В `cy` те же ключи задаются с префиксом `metrics.`, например `metrics.evaluation.matching_strategy=greedy`.

## См. также

- [`cy-metrics`](../commands/cy-metrics.md), [`cy-val`](../commands/cy-val.md), [`cy-compare`](../commands/cy-compare.md), [`cy`](../commands/cy.md)
- [Публикация в ClearML и FiftyOne](../publication.md)
- [Как устроена конфигурация](README.md)
