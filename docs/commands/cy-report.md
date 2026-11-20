# cy-report

`cy-report` строит технический и бизнес-отчёт — две книги Excel (workbook) — по результатам [`cy-compare`](cy-compare.md). Запускайте команду, когда сравнение модели-кандидата ([candidate model](../../GLOSSARY.md#candidate-model)) с моделью [baseline](../../GLOSSARY.md#baseline) уже выполнено и нужен отчёт для команды или заказчика.

## Примеры

Построить отчёты по каталогу сравнения:

```bash
cy-report comparison_dir=runs/my-run/compare clearml.project_name=my-project clearml.task_name=my-run
```

С собственными настройками отчёта и каталогом результатов:

```bash
cy-report comparison_dir=runs/my-run/compare report_config_path=configs/report.yaml output_dir=runs/my-run/report \
  clearml.project_name=my-project clearml.task_name=my-run
```

## Синтаксис и аргументы

```text
cy-report [--config-dir DIR] [--config-name NAME] [--cfg job] [KEY=VALUE ...]
```

Команда — приложение Hydra: параметры задаются override вида `ключ=значение` (см. [Конфигурация](../configuration/README.md)).

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `comparison_dir` | обязателен | Каталог результатов `cy-compare` с файлом `comparison_manifest.json`. |
| `baseline_label` | `null` | Подпись модели ([model identity](../../GLOSSARY.md#model-identity)) baseline. Используется, только если ни книга модели baseline, ни манифест ([comparison manifest](../../GLOSSARY.md#comparison-manifest)) не содержат описания модели. |
| `candidate_label` | `null` | То же для модели-кандидата. |
| `output_dir` | `null` | Каталог результатов. При `null` — `runs/<проект>/<задача>-<ID>/report` (см. [Рабочий каталог](../workspace.md) ([workspace](../../GLOSSARY.md#workspace))). Должен быть внутри `CY_HOME`. |
| `report_config_path` | `null` | YAML с настройками генератора отчётов, например имена листов в разделе `sheet_names`. При `null` — встроенные настройки. |
| `clearml` | см. группу | Задача ClearML (task): [`clearml`](../configuration/clearml.md). |

## Как это работает

1. Команда проверяет, что `output_dir` (если задан) лежит внутри `CY_HOME`, и создаёт задачу ClearML. Обе проверки идут до чтения `comparison_dir`, поэтому при недоступном сервере ClearML вы увидите ошибку ClearML, даже если каталога сравнения нет.
2. Читает `comparison_manifest.json` из `comparison_dir` и проверяет, что обе книги сравнения, на которые ссылается манифест, лежат в этом каталоге. Split отчёта берётся из манифеста. Если задан `report_config_path`, публикует файл как объект конфигурации ([configuration object](../../GLOSSARY.md#configuration-object)) `report`; ссылки `${...}` в нём разрешаются (см. [Интерполяции](../configuration/README.md#интерполяции-в-файлах-конфигурации)).
3. Определяет обе модели: по подписи, сохранённой в книге, иначе по манифесту, иначе по `baseline_label` и `candidate_label`. Если описание в книге не совпадает с манифестом, команда останавливается.
4. Строит `report_dev_<split>.xlsx` и `report_business_<split>.xlsx` в `output_dir`. Классы без корректного числа обучающих объектов исключаются из агрегатов, отфильтрованных по этому числу; в обе книги добавляются листы `Unknown training count` и `Report issues`, в журнал — предупреждение `Reports contain N unavailable training counts; ...` (см. [Отчёт: `cy-report`](../formats/workbooks.md#отчёт-cy-report)).
5. Подписывает книги описанием моделей и загружает их в задачу как артефакты `report_dev_<split>` и `report_business_<split>`.

`cy-report` ничего не пересчитывает: значения берутся из книг сравнения. В FiftyOne команда ничего не публикует.

## Результат

Две книги в `output_dir`: `report_dev_<split>.xlsx` и `report_business_<split>.xlsx`. Листы описаны в [Книги Excel](../formats/workbooks.md#отчёт-cy-report), артефакты — в [Публикация](../publication.md#артефакты). В журнал команда пишет `Split '<split>': report_dev_<split>.xlsx and report_business_<split>.xlsx`.

### Коды завершения

| Код | Значение |
| --- | --- |
| `0` | Обе книги записаны и загружены, задача завершена успешно. |
| `1` | Ошибка конфигурации, входных файлов или ClearML. Задача, если она уже создана, получает статус `failed` (см. [Успех и ошибка](../publication.md#успех-и-ошибка)). |

## Частые ошибки

Ошибки чтения книг сравнения (книга не той формы, книга изменена после подписи) описаны в [Книги Excel](../formats/workbooks.md#отчёт-cy-report).

| Сообщение | Причина и решение |
| --- | --- |
| `Missing mandatory value: comparison_dir` | Не задан `comparison_dir`. |
| `Comparison directory <каталог> has no comparison_manifest.json; run cy-compare first` | В каталоге нет манифеста: сравнение не запускалось или было пропущено. Запустите `cy-compare`. |
| `Comparison candidate dashboard does not exist: <путь>` | Книги из манифеста нет в каталоге (или `baseline dashboard`). Не переносите и не удаляйте файлы каталога сравнения. |
| `baseline dashboard identity does not match comparison manifest` | Книга подменена книгой другой модели (или `candidate`). Повторите `cy-compare`. |
| `Model provenance is unavailable; supply a custom model_label (comparison model references use label)` | Модель нигде не описана. Задайте `baseline_label` или `candidate_label`. |
| `Project write destination ... must be contained beneath CY_HOME=...` | `output_dir` вне рабочего каталога (см. [Правило записи](../workspace.md#правило-записи-внутри-cy_home)). |
| `Unrecognized Authentication Error: ...` | Сервер ClearML недоступен или не настроены учётные данные (см. [Установка](../installation.md#clearml)). |

## См. также

- [`cy-compare`](cy-compare.md), [`cy`](cy.md)
- [Книги Excel](../formats/workbooks.md)
- [Публикация в ClearML и FiftyOne](../publication.md), [Рабочий каталог](../workspace.md)
