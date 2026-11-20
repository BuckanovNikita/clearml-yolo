# cy-compare

`cy-compare` заново прогоняет две модели — [baseline](../../GLOSSARY.md#baseline) и модель-кандидат ([candidate model](../../GLOSSARY.md#candidate-model)) — на изображениях одного split текущей разметки ([ground truth](../../GLOSSARY.md#ground-truth)), оценивает обе с их собственными порогами уверенности (confidence threshold) и проверяет по каждому классу, значимо ли изменились precision и recall. Команда нужна, чтобы решить, лучше ли новая модель той, что уже работает.

Сравнение (comparison) внутри полного пайплайна ([pipeline](../../GLOSSARY.md#pipeline)) выполняет этап ([stage](../../GLOSSARY.md#stage)) сравнения [`cy`](cy.md); его ключ `compare.baseline_model` устроен так же, как `baseline_model` на этой странице.

## Примеры

Сравнить модель из задачи ClearML с последней задачей проекта с тегом `prod`:

```bash
cy-compare ground_truth=data/ground_truth.csv candidate_model.task_id=<task-id> clearml.project_name=my-project clearml.task_name=my-run
```

Сравнить две задачи ClearML, указанные явно, на split `val`:

```bash
cy-compare ground_truth=data/ground_truth.csv baseline_model.task_id=<task-id> candidate_model.task_id=<task-id> split=val clearml.project_name=my-project clearml.task_name=my-run
```

Сравнить локальный checkpoint кандидата с моделью из ClearML; для локального файла пороги задаются явно:

```bash
cy-compare ground_truth=data/ground_truth.csv baseline_model.task_id=<task-id> candidate_model.source=local candidate_model.weights=weights/best.pt 'candidate_model.thresholds={defect: 0.35}' clearml.project_name=my-project clearml.task_name=my-run
```

Синтаксис override описан в [конфигурации](../configuration/README.md).

## Синтаксис и аргументы

```text
cy-compare [--config-dir DIR] [--cfg job] [-m] [КЛЮЧ=ЗНАЧЕНИЕ ...]
```

`cy-compare` — приложение Hydra: параметры задаются override `ключ=значение` поверх собранной конфигурации (см. [конфигурацию](../configuration/README.md)). Значения по умолчанию получены командой `cy-compare --cfg job`.

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `baseline_model` | см. [ссылку на модель](#ссылка-на-модель-baseline_model-и-candidate_model) ([model reference](../../GLOSSARY.md#model-reference)) | Модель baseline. |
| `candidate_model` | см. [ссылку на модель](#ссылка-на-модель-baseline_model-и-candidate_model) | Модель-кандидат. |
| `ground_truth` | `???` (обязателен) | Разметка: путь к CSV ([формат](../formats/ground-truth.md)) или ссылка на датасет ClearML. |
| `output_dir` | `null` | Каталог результатов. При `null` — `runs/<проект>/<задача>-<ID>/compare` в рабочем каталоге ([workspace](../../GLOSSARY.md#workspace), см. [рабочий каталог](../workspace.md)). |
| `split` | `test` | Split, на котором сравниваются модели. |
| `model` | `ultralytics` | Семейство моделей ([detector family](../../GLOSSARY.md#detector-family)), которым запускаются обе модели. См. [`model`](../configuration/model.md). |
| `ultralytics` | см. [страницу группы](../configuration/ultralytics.md) | Параметры обучения Ultralytics; `cy-compare` их только проверяет и использует как источник значений `${ultralytics.*}` в `ultralytics_predict`. |
| `ultralytics_predict` | см. [страницу группы](../configuration/ultralytics-predict.md) | Параметры предсказания, общие для обеих моделей. `model`, `project` и `name` должны оставаться `null`. |
| `inference.reuse_existing` | `true` | Использовать сохранённые предсказания (predictions), если они получены теми же весами (weights) с теми же параметрами на тех же изображениях. |
| `inference.image_name` | `name` | Как сопоставлять изображения разметки и предсказаний. Допустимо только `name`. |
| `q` | `0.05` | Уровень значимости после поправки Benjamini-Hochberg; конечное число от 0 до 1. |
| `bootstrap_iterations` | `10000` | Число bootstrap-выборок; положительное целое. |
| `seed` | `0` | Seed генератора bootstrap-выборок. |
| `evaluation` | см. [страницу группы](../configuration/evaluation.md) | Правила сопоставления рамок (bounding box) и вычисления метрик; ключ `evaluation.backend` должен оставаться `null`. |
| `clearml` | см. [страницу группы](../configuration/clearml.md) | Проект, имя и теги задачи ClearML (task) этого запуска. Проект также служит проектом поиска моделей по умолчанию. |

### Ссылка на модель: `baseline_model` и `candidate_model`

У обоих ключей одинаковый набор полей и одни и те же значения по умолчанию.

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `baseline_model.source`, `candidate_model.source` | `clearml` | Откуда берётся checkpoint: `clearml` — из задачи ClearML, `local` — из локального файла. |
| `baseline_model.task_id`, `candidate_model.task_id` | `null` | ID задачи ClearML, из которой берётся модель. Запрещён при `source=local`. |
| `baseline_model.project_name`, `candidate_model.project_name` | `null` | Проект поиска задачи, если `task_id` не задан. При `null` — `clearml.project_name`. |
| `baseline_model.task_name`, `candidate_model.task_name` | `null` | Имя задачи при поиске; читается как регулярное выражение и должно совпасть целиком. |
| `baseline_model.tags`, `candidate_model.tags` | `[prod]` | Теги поиска: у найденной задачи должны быть все перечисленные теги. |
| `baseline_model.weights`, `candidate_model.weights` | `null` | Путь к локальному checkpoint. Обязателен при `source=local`, запрещён при `source=clearml`. |
| `baseline_model.thresholds`, `candidate_model.thresholds` | `null` | Пороги уверенности по именам классов, например `{defect: 0.35}`; каждое значение от 0 до 1. Обязательны и не могут быть пустыми при `source=local`. При `source=clearml` и `null` берутся из задачи модели. |
| `baseline_model.label`, `candidate_model.label` | `null` | Подпись модели ([model identity](../../GLOSSARY.md#model-identity)) в результатах. При `null` используется имя, под которым модель известна. |
| `baseline_model.backend`, `candidate_model.backend` | `null` | Семейство моделей, к которому относится checkpoint. Задаётся только вместе с `preset`. |
| `baseline_model.preset`, `candidate_model.preset` | `null` | Архитектура checkpoint из списка preset выбранного `backend` (см. [`model`](../configuration/model.md)). |
| `baseline_model.source_dir`, `candidate_model.source_dir` | `null` | Каталог исходников DEIMv2. Требует `backend` и `preset` и допустим только для DEIMv2. |
| `baseline_model.class_names`, `candidate_model.class_names` | `null` | Имена классов checkpoint в порядке выходов модели. Требует `backend` и `preset`. |
| `baseline_model.preprocessing`, `candidate_model.preprocessing` | `null` | Подготовка изображений для checkpoint: `{resize: stretch\|letterbox\|shortest_edge, size: <размер>}`. Требует `backend` и `preset`. |

Правила, связывающие поля:

- `backend` и `preset` задаются вместе или не задаются вовсе. `source_dir`, `class_names` и `preprocessing` без них запрещены.
- `source=local`: нужны `weights` и непустые `thresholds`; `task_id` запрещён. Пороги должны покрывать все классы, по которым оценивается модель.
- `source=clearml`: `weights` запрещён.
- `backend` и `preset` проверяют checkpoint, созданный CY: если они расходятся с описанием, сохранённым в checkpoint, команда завершается ошибкой. То же для `class_names` и `preprocessing`, если они заданы.
- Сырой checkpoint семейства, отличного от Ultralytics, без сохранённого CY описания требует `backend`, `preset`, `class_names` и `preprocessing`.
- Не переносите пороги модели baseline на кандидата: у каждой модели свои пороги, подобранные для её checkpoint.

## Как это работает

1. Hydra собирает конфигурацию. Значение `inference.image_name`, отличное от `name`, отклоняется до создания задачи ClearML.
2. Команда создаёт задачу ClearML с именем и тегами из группы `clearml` и проверяет поля `baseline_model`, `candidate_model`, `inference`, `ultralytics_predict`, `q`.
3. Команда читает разметку и проверяет, что каждое изображение относится к одному split.
4. Выбирается модель baseline:
   - `source=local` — файл `weights`; если его нет, команда завершается ошибкой.
   - `source=clearml` с `task_id` — эта задача.
   - `source=clearml` без `task_id` — последняя завершённая задача (статус `completed` или `published`) в проекте `project_name` (или `clearml.project_name`) с заданным именем и тегами, кроме задачи этого запуска. Правило поиска описано в [публикации](../publication.md#что-cy-читает-обратно).

   Из задачи ClearML берётся лучший checkpoint и, если `thresholds` не заданы, пороги, подобранные при её оценке (см. [публикацию](../publication.md#что-cy-читает-обратно)).
5. Если модель baseline задана только значениями по умолчанию (`source=clearml`, тег `prod`, без `task_id`, `project_name`, `task_name` и `weights`) и подходящей задачи нет, сравнение пропускается: команда оценивает только кандидата (см. «Результат»). Если поиск с явно заданными полями ничего не нашёл, команда завершается ошибкой.
6. Тем же способом выбирается модель-кандидат. Значения по умолчанию у неё те же, что у модели baseline, поэтому кандидата нужно задать явно: иначе обе стороны найдут одну и ту же задачу. Если обе модели указывают на один и тот же файл, команда завершается ошибкой.
7. Обе модели запускаются на изображениях split из текущей разметки — не на сохранённых предсказаниях из прежних задач — с одинаковыми параметрами `ultralytics_predict` (или `model.predict` для других семейств). Если модель baseline обучалась с другим `imgsz`, команда пишет предупреждение, но обе модели получают один и тот же запрошенный `imgsz`.
8. Предсказания каждой модели сохраняются в CSV в `output_dir`. Имя файла содержит хэш от пути и содержимого весов, параметров предсказания, утверждений о модели (`backend`, `preset` и другие) и состава split (имена и пути изображений). При `inference.reuse_existing=true` и уже существующем файле с таким именем предсказания читаются из него, а модель не запускается. Перед этим команда сверяет записанные в файле checkpoint и модель с выбранными; при расхождении она завершается ошибкой. Если файла `.metadata.json` рядом нет, он повреждён или нативные результаты прежнего запуска не сохранились в `output_dir/native`, файл игнорируется и модель запускается заново. При `inference.reuse_existing=false` модель запускается всегда.

   Файлы ищутся только в `output_dir` текущего запуска. Каталог по умолчанию содержит ID новой задачи и у каждого запуска свой, поэтому повторно использовать предсказания можно, только если задать один и тот же `output_dir` явно.
9. Каждая модель оценивается со своими порогами по правилам группы `evaluation`; результаты оценки публикуются в задачу.
10. По каждому классу считаются изменения precision и recall (кандидат минус baseline):
    - precision — bootstrap по изображениям: `bootstrap_iterations` выборок с seed `seed`, p-value и доверительный интервал;
    - recall — точный тест Макнемара по рамкам разметки (p-value) и bootstrap (интервал).

    Поправка Benjamini-Hochberg применяется ко всем гипотезам split сразу (precision и recall всех классов). Изменение класса значимо, если скорректированный p-value не больше `q` и изменение не равно нулю: тогда вердикт — улучшение или деградация ([degraded class](../../GLOSSARY.md#degraded-class)) по знаку изменения, иначе — не значимо. Если p-value вычислить нельзя, вердикта нет (`NA` в книге Excel). Строка итога по всем сравниваемым классам в поправку не входит и оценивается по своему p-value.
11. Класс исключается из сравнения, если его не знает хотя бы одна модель, если в split нет его разметки или если ни одна модель его не предсказала. Исключённые классы и причины попадают в отдельную таблицу.
12. Команда пишет книгу Excel (workbook) сравнения, таблицы и манифест ([comparison manifest](../../GLOSSARY.md#comparison-manifest)) и публикует их в ClearML.

## Результат

Все файлы пишутся в `output_dir`. Состав книг Excel и манифеста описан в [форматах книг Excel](../formats/workbooks.md#сравнение-cy-compare):

- `compare_workbook_<split>.xlsx`, `compare_workbook_<split>_excluded.csv`, `compare_workbook_<split>_methodology.csv` — статистическое сравнение, исключённые классы, параметры сравнения;
- `comparison_manifest.json` — связь файлов одного сравнения; его читает [`cy-report`](cy-report.md);
- дашборды ([dashboard](../../GLOSSARY.md#dashboard)) каждой модели;
- `baseline_predictions_<split>_<хэш>.csv` и `candidate_predictions_<split>_<хэш>.csv` с файлами `.metadata.json` рядом — предсказания и их происхождение;
- `ultralytics_predict_<роль>_<split>.yaml` и `ultralytics_predict_<роль>_<split>_requested.yaml` — действующие и запрошенные параметры предсказания;
- `native/` и `native_outputs_<роль>_<split>.zip` — нативные результаты предсказания и их архив.

В `<роль>` стоит `baseline` или `candidate`.

Если сравнение пропущено (шаг 5), команда пишет только файлы кандидата и книгу `compare_evaluation_candidate_<split>.xlsx` вместо `compare_workbook_<split>.xlsx`; рядом лежат `compare_evaluation_candidate_<split>_thresholds.csv` и `compare_evaluation_candidate_<split>_methodology.csv`; манифеста нет (см. [форматы книг Excel](../formats/workbooks.md#сравнение-cy-compare)). В объекте конфигурации ([configuration object](../../GLOSSARY.md#configuration-object)) `run` задачи записывается `comparison_status` со статусом `skipped` и причиной.

Что попадает в ClearML — артефакты, графики, scalars и объект `run` с разделом `comparison`, — описано в [публикации](../publication.md).

Деградация отдельных классов — это результат сравнения, а не ошибка: команда завершается успешно, пишет предупреждение `Split 'test': 2 class(es) significantly degraded` (с вашим split и числом классов), а вердикты видны в книге Excel и в scalars задачи (`degraded_precision`, `degraded_recall`, `improved_precision`, `improved_recall`).

### Коды завершения

| Код | Когда |
| --- | --- |
| `0` | Сравнение выполнено, в том числе если найдены деградации или сравнение пропущено из-за отсутствия модели baseline. |
| `1` | Ошибка конфигурации, недоступный ClearML, не найдена модель или пороги, ошибка предсказания или публикации. |

## Частые ошибки

Hydra печатает трассировку; смысл ошибки — в последней строке перед `Set the environment variable HYDRA_FULL_ERROR=1 for a complete stack trace.`

- `omegaconf.errors.MissingMandatoryValue: Missing mandatory value: ground_truth` — не задан `ground_truth`. Добавьте `ground_truth=data/ground_truth.csv`.
- `ValueError: Comparison and evaluation require image_name='name'; 'path' is supported only for raw prediction export` — задан `inference.image_name=path`. Оставьте `name`.
- `Could not override 'inference.foo'.` — у группы `inference` только ключи `reuse_existing` и `image_name`.
- `Value error, source='local' requires weights` и `Value error, source='local' requires exact thresholds` — для локальной модели задайте `weights` и `thresholds`.
- `Value error, source='local' cannot specify a ClearML task_id` и `Value error, source='clearml' cannot specify local weights` — смешаны поля двух источников; выберите один.
- `Value error, Checkpoint backend and preset must be specified together` и `Value error, Raw checkpoint metadata requires backend and preset` — задайте `backend` и `preset` вместе.
- `Value error, source_dir is only supported for DEIMv2` — `source_dir` задан для другого семейства.
- `No completed ClearML task in project 'my-project' tagged ['my-tag']` — поиск модели ничего не нашёл. Проверьте проект, имя и теги или задайте `task_id`.
- `Both sides resolved to the same checkpoint (...), so there is nothing to compare` — обе модели указывают на один файл; чаще всего кандидат не задан и найден тот же `prod`, что и для baseline.
- `Local checkpoint does not exist: weights/best.pt` — нет файла `weights`.
- `Confidence thresholds are missing required class(es): [...]` — в `thresholds` нет порога для класса, по которому оценивается модель.
- `Prediction ['model'] are owned by comparison; use baseline_model/candidate_model and output_dir` — задан `ultralytics_predict.model` (то же для `project` и `name`). Верните `null`.
- `Cached prediction provenance refers to a different checkpoint` и `Cached prediction source identity does not match the selected model` — сохранённые предсказания получены другой моделью. Удалите файл или запустите с `inference.reuse_existing=false`.
- `Raw detector checkpoints require explicit class_names and preprocessing` — сырой checkpoint без описания CY; задайте `class_names` и `preprocessing`.
- `Model reference disagrees with the checkpoint descriptor` — `backend` или `preset` не совпадают с описанием в checkpoint.
- `q must be a finite probability in [0, 1]` — неверный `q`.
- `Confidence thresholds must be within [0, 1] for class(es): [...]` — порог в `thresholds` вне диапазона от 0 до 1.
- `A native detector reference requires the detector dispatcher` — в `baseline_model.backend` или `candidate_model.backend` задано семейство, отличное от Ultralytics, а `model` осталось `ultralytics`. Выберите то же семейство в `model`.
- `Frozen thresholds require the native digital-metrics backend; backend='...' is unsupported` — задан `evaluation.backend`. Верните `null`.
- `Current comparison image does not exist: <путь>` — изображения из `image_path` разметки нет на диске.

## См. также

- [`cy`](cy.md) — этап сравнения в пайплайне
- [`cy-report`](cy-report.md) — отчёт по каталогу сравнения
- [Конфигурация](../configuration/README.md), [`model`](../configuration/model.md), [`evaluation`](../configuration/evaluation.md), [`ultralytics_predict`](../configuration/ultralytics-predict.md), [`clearml`](../configuration/clearml.md)
- [Формат разметки](../formats/ground-truth.md), [книги Excel](../formats/workbooks.md)
- [Рабочий каталог](../workspace.md), [публикация](../publication.md), [установка](../installation.md)
