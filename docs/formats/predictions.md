# Предсказания

Предсказания — CSV, в котором каждая строка — одна рамка (bounding box), найденная моделью, с классом и уверенностью. По этому файлу `cy-metrics` считает метрики против [разметки](ground-truth.md) ([ground truth](../../GLOSSARY.md#ground-truth)).

## Кто пишет и кто читает

- Пишет: [`cy-predict`](../commands/cy-predict.md) (по умолчанию `predict.csv` в каталоге запуска ([run directory](../../GLOSSARY.md#run-directory)), путь задаёт ключ `output`), этап ([stage](../../GLOSSARY.md#stage)) предсказаний [`cy`](../commands/cy.md), [`cy-val`](../commands/cy-val.md) и [`cy-compare`](../commands/cy-compare.md) для каждой модели.
- Читают: [`cy-metrics`](../commands/cy-metrics.md) и этап метрик `cy`.

Изображение, на котором модель ничего не нашла, не даёт ни одной строки.

## Колонки

`cy-predict` пишет колонки в порядке `image_name`, `instance_label`, `confidence`, `bbox_x_tl`, `bbox_y_tl`, `bbox_x_br`, `bbox_y_br`. При чтении порядок колонок не важен.

| Колонка | Тип | Правила |
| --- | --- | --- |
| `image_name` | строка | Обязательна, не пустая. Для метрик — имя файла изображения, как в колонке `image_name` разметки. Каждое значение должно встречаться в разметке |
| `instance_label` | строка | Обязательна, не пустая. Имя класса из обученной модели. `background` зарезервировано |
| `bbox_x_tl` | число | Левая граница рамки в пикселях исходного изображения |
| `bbox_y_tl` | число | Верхняя граница рамки в пикселях |
| `bbox_x_br` | число | Правая граница рамки в пикселях |
| `bbox_y_br` | число | Нижняя граница рамки в пикселях |
| `confidence` | число | Обязательна, от 0 до 1 включительно |
| `source_row_id` | строка | Необязательна, `cy-predict` её не пишет. Если есть, служит идентификатором строки в таблицах результатов метрик; значения должны быть уникальными и не пустыми |

Рамки с пустыми, нечисловыми или бесконечными координатами, с перевёрнутыми углами (`bbox_x_br < bbox_x_tl` или `bbox_y_br < bbox_y_tl`) или с нулевой площадью не останавливают метрики: они отбрасываются из оценки, а в лог пишется предупреждение вида `Dropped 1 of 2 prediction boxes with invalid geometry: zero_area=1; image sample: ['a.jpg']`. Сам CSV не меняется.

## Значение `image_name`

Ключ `image_name` команды `cy-predict` задаёт, что попадает в колонку:

| Значение | Что пишется |
| --- | --- |
| `name` | Имя файла с расширением: `a.jpg`. Значение по умолчанию |
| `stem` | Имя файла без расширения: `a` |
| `path` | Полный путь к изображению после разрешения `image_path` разметки |

Метрики и сравнение работают только с `name`. Файлы с `stem` и `path` годятся лишь как выгрузка.

## Пример

```csv
image_name,instance_label,confidence,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br
a.jpg,car,0.91,240.5,120.0,400.2,360.8
a.jpg,person,0.47,0.0,0.0,158.3,121.0
d.jpg,car,0.88,238.0,119.5,401.0,359.0
```

## Файл `.provenance.json`

Рядом с CSV `cy-predict` пишет `<имя CSV>.provenance.json`, например `runs/my-run/predict.csv.provenance.json`. Он связывает предсказания с весами (weights), которыми они получены:

| Поле | Значение |
| --- | --- |
| `checkpoint_sha256` | SHA-256 файла checkpoint, или `null`, если веса не локальный файл |
| `model_identity` | Описание модели: `model_name`, `training_task_id` (задача ClearML (task) обучения), `checkpoint_sha256`, `model_id` |
| `prediction_image_name` | Значение ключа `image_name`: `name`, `stem` или `path` |
| `predictions_sha256` | SHA-256 байтов CSV |

`cy-metrics` читает этот файл, чтобы знать, какой моделью получены предсказания и в каком режиме записан `image_name`. Файл необязателен: CSV без него, например полученный другим инструментом, `cy-metrics` принимает без проверки хэша и режима `image_name`. Если вы измените CSV после `cy-predict`, хэш перестанет совпадать, и `cy-metrics` остановится с ошибкой `Prediction provenance does not match prediction CSV bytes`. Чтобы изменить предсказания, запустите `cy-predict` снова.

## Ошибки

| Сообщение | Причина |
| --- | --- |
| `Predictions DataFrame is missing columns: ['confidence']` | Нет обязательной колонки |
| `Predictions 'confidence' column contains 1 NA value(s); every prediction must have a numeric confidence.` | Пустая уверенность |
| `Predictions confidence must be numeric and finite.` | Уверенность не число, бесконечна или вне диапазона от 0 до 1 |
| `Predictions instance_label must not be missing.` | Пустой класс |
| `'background' is a reserved class label for unmatched detections.` | Класс называется `background` |
| `Predictions contains empty canonical image names` | Пустой `image_name` |
| `Prediction image_name values are outside canonical ground-truth membership: ['x.jpg']; evaluation requires image_name='name'` | `image_name` нет в разметке |
| `Comparison and evaluation require image_name='name'; 'stem' is supported only for raw prediction export` | Предсказания записаны с `image_name=stem`; для `path` в сообщении стоит `'path'` |
| `Prediction provenance does not match prediction CSV bytes` | CSV изменён после записи |
| `source_row_id must be unique and nonmissing` | Повтор или пропуск в `source_row_id` |

## См. также

- [Разметка (ground truth)](ground-truth.md)
- [Книги Excel](workbooks.md): что `cy-metrics` пишет по предсказаниям
