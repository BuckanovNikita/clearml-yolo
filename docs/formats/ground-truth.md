# Разметка (ground truth)

Разметка ([ground truth](../../GLOSSARY.md#ground-truth)) — один CSV-файл со всеми рамками (bounding box) датасета, путями к изображениям и split каждого изображения. Он нужен для обучения, предсказаний, метрик, сравнения и проверки экспорта.

## Кто пишет и кто читает

- Пишет: [`cy-ground-truth`](../commands/cy-ground-truth.md) из YOLO-датасета (см. [Датасеты](datasets.md)), или вы сами.
- Читают: [`cy-train`](../commands/cy-train.md) и [`cy`](../commands/cy.md) (полная проверка, описанная ниже), [`cy-export`](../commands/cy-export.md) при проверке модели (та же проверка, но обязателен только проверяемый split), [`cy-predict`](../commands/cy-predict.md) (берёт `image_path` и `split`), [`cy-metrics`](../commands/cy-metrics.md) и [`cy-compare`](../commands/cy-compare.md) (сопоставляют предсказания по `image_name`), [`cy-val`](../commands/cy-val.md) (предсказания и метрики подряд).

Ключ `ground_truth` принимает путь к CSV или ссылку на датасет ClearML. Датасет ClearML должен быть финализирован и содержать только один файл `dataset.csv` в корне; изображения храните вне датасета. CSV из датасета ClearML скачивается в локальный кэш, и относительный `image_path` отсчитывается от каталога этой копии, поэтому в таком CSV указывайте абсолютные пути к изображениям. Для локального пути команда пишет предупреждение `Using local ground-truth CSV ...; prefer a ClearML dataset reference for versioned annotations.`

Ссылка на датасет ClearML записывается так:

```bash
cy-train 'ground_truth={dataset_id:<dataset-id>}'
cy-train 'ground_truth={project_name:my-project,name:my-dataset,version:"1.0.0"}'
```

`dataset_id` нельзя совмещать с `project_name`, `name` и `version`; без `dataset_id` нужны и `project_name`, и `name`. Без `version` ClearML выбирает версию сам, и следующий запуск может получить другую. Какой датасет был выбран (ID, проект, имя, версия и SHA-256 CSV), команда записывает в задачу ClearML как `ground_truth_source`.

## Колонки

Файл в UTF-8 (BOM допускается), первая строка — заголовок. Порядок колонок в файле не важен, лишние колонки не мешают.

| Колонка | Тип | Правила |
| --- | --- | --- |
| `image_name` | строка | Обязательна, не пустая. Должна совпадать с именем файла из `image_path` (последний компонент пути после раскрытия символических ссылок: для ссылки это имя файла, на который она указывает). По ней сопоставляются разметка и [предсказания](predictions.md) |
| `instance_label` | строка | Имя класса. Пусто только в строке изображения без объектов ([image without objects](../../GLOSSARY.md#image-without-objects), см. ниже). Значение `background` зарезервировано: обучение его принимает, а метрики и сравнение отклоняют |
| `bbox_x_tl` | число | Левая граница рамки в пикселях |
| `bbox_y_tl` | число | Верхняя граница рамки в пикселях |
| `bbox_x_br` | число | Правая граница рамки в пикселях, больше `bbox_x_tl` |
| `bbox_y_br` | число | Нижняя граница рамки в пикселях, больше `bbox_y_tl` |
| `image_path` | строка | Обязательна, не пустая. Абсолютный путь или путь относительно каталога, в котором лежит CSV (не текущего каталога). `~` раскрывается |
| `split` | строка | Обязательна: `train`, `val` или `test` |
| `source_row_id` | строка | Необязательна. Если есть, служит идентификатором строки в таблицах результатов метрик; значения должны быть уникальными и не пустыми. Без неё CY нумерует строки сам |

Текстовые колонки читаются буквально: `NA`, `None`, `nan` или `001` остаются строками, а пропуском считается только пустая ячейка.

Координаты — абсолютные пиксели, начало в левом верхнем углу изображения. Рамка должна лежать внутри изображения: `0 <= bbox_x_tl < bbox_x_br <= ширина`, `0 <= bbox_y_tl < bbox_y_br <= высота`.

## Изображение без объектов

Изображение без объектов записывается одной строкой, в которой `instance_label` и все четыре координаты пусты, а `image_name`, `image_path` и `split` заполнены:

```csv
b.jpg,images/train/b.jpg,,,,,,train
```

Такая строка оставляет изображение в датасете: при обучении оно получает пустой файл разметки, при метриках остаётся в числе оцениваемых изображений. `cy-ground-truth` пишет такую строку для каждого изображения, у которого нет файла разметки или он пуст. У одного изображения может быть только одна такая строка, и её нельзя смешивать со строками рамок того же изображения.

## Правила split

- Каждое изображение принадлежит ровно одному split: все строки одного `image_name` и одного пути должны иметь одинаковый `split`.
- Одно `image_name` не может указывать на два разных файла, и один файл не может иметь два разных `image_name`.
- Обучение требует изображений в `train` и `val` (и в других split из ключа `required_splits`, если он задан) и хотя бы одной корректной рамки в `train`.
- Метрики подбирают пороги уверенности (confidence threshold) на `val`, поэтому `val` нужен и для `cy-metrics`. Каждый split из ключа `splits` должен присутствовать в файле.

## Пример

Файл `data/ground_truth.csv`, изображения лежат в `data/images/`:

```csv
image_name,image_path,instance_label,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br,split
a.jpg,images/train/a.jpg,car,240,120,400,360,train
a.jpg,images/train/a.jpg,person,0,0,160,120,train
b.jpg,images/train/b.jpg,,,,,,train
d.jpg,images/val/d.jpg,car,240,120,400,360,val
c.jpg,images/test/c.jpg,car,240,120,400,360,test
```

## Как проверяется файл при обучении

`cy-train`, этап ([stage](../../GLOSSARY.md#stage)) обучения `cy` и проверка модели в `cy-export` проверяют файл целиком до начала работы:

1. Заголовок: нет повторяющихся колонок, есть все колонки, кроме `source_row_id`.
2. Каждая строка: `image_name` и `image_path` не пусты, `split` допустим, `image_name` совпадает с именем файла.
3. Принадлежность изображений split, повторяющиеся пустые строки и смешение пустой строки с рамками.
4. Каждое изображение открывается. Допустимые расширения: `avif`, `bmp`, `dng`, `heic`, `heif`, `jp2`, `jpeg`, `jpg`, `mpo`, `png`, `tif`, `tiff`, `webp`. Обе стороны не меньше 10 пикселей. Для JPEG с поворотом в EXIF (значения 6 и 8) ширина и высота меняются местами.
5. Каждая рамка проверяется по размерам изображения.

Рамка с ошибкой не останавливает обучение: она отбрасывается, а в лог пишется `Invalid bounding boxes dropped: N`. Причины для такой рамки: `missing label` (есть координаты, но пустой `instance_label`), `incomplete coordinates`, `coordinates must be numeric`, `coordinates must be finite`, `box width and height must be positive`, `coordinates are outside image bounds 0..W x 0..H`. Список отброшенных рамок с номерами строк попадает в `preparation.json` (см. [Датасеты](datasets.md)). Если в классе не осталось ни одной рамки в `train`, команда пишет предупреждение `Class 'car' has no valid training examples`.

При обучении подготовленный датасет кэшируется по содержимому CSV (см. [Датасеты](datasets.md)). Пока CSV не изменился, повторный запуск берёт готовый кэш и шаги 1–5 не повторяет; проверяется только наличие изображений в обязательных split.

## Ошибки

Сообщения при обучении начинаются с полного пути к CSV; ниже он заменён на `data/ground_truth.csv`. Номер строки считается вместе с заголовком: первая строка данных — `row 2`.

| Сообщение | Причина |
| --- | --- |
| `data/ground_truth.csv: missing required columns: split` | В заголовке нет колонки |
| `data/ground_truth.csv: Duplicate CSV header(s): split` | Колонка повторяется в заголовке |
| `data/ground_truth.csv: CSV contains no data rows` | В файле только заголовок |
| `data/ground_truth.csv: row 2 has an empty image_name` | Пустая ячейка `image_name` |
| `data/ground_truth.csv: row 2 has an empty image_path` | Пустая ячейка `image_path` |
| `data/ground_truth.csv: row 2 has invalid split 'dev'; expected train, val, or test` | Недопустимый `split` |
| `data/ground_truth.csv: row 2 image_name 'x.jpg' must match resolved path basename 'a.jpg'` | `image_name` не совпадает с именем файла |
| `data/ground_truth.csv: image 'a.jpg' belongs to both split 'train' and 'val' (row 5)` | Одно изображение в двух split |
| `data/ground_truth.csv: image name 'a.jpg' refers to both /workspace/project/data/a.jpg and /workspace/project/data/images/train/a.jpg (row 5)` | Одно имя у двух разных файлов |
| `data/ground_truth.csv: Duplicate background row 5` | Две одинаковые строки изображения без объектов |
| `data/ground_truth.csv: image 'b.jpg' mixes an explicit background row with an annotation row` | У изображения есть и пустая строка, и рамки |
| `data/ground_truth.csv: Duplicate box for image 'a.jpg' at row 5; numerically repeats row 2` | Та же рамка того же класса повторяется (сравниваются числа, `240` и `240.0` совпадают) |
| `data/ground_truth.csv: image 'z.jpg' at /workspace/project/data/images/train/z.jpg cannot be read` | Файл изображения отсутствует или повреждён |
| `data/ground_truth.csv: image 'a.gif' has unsupported extension '.gif'; supported extensions: ...` | Расширение не из списка |
| `data/ground_truth.csv: image 'a.png' decodes as unsupported format 'gif'` | Содержимое файла не соответствует ни одному допустимому формату |
| `data/ground_truth.csv: image 'a.jpg' is 8 x 8 pixels; both dimensions must be at least 10 pixels` | Изображение слишком маленькое |
| `data/ground_truth.csv: required split(s) contain no images: val` | Нет изображений в обязательном split |
| `data/ground_truth.csv: at least one valid training box is required` | В `train` не осталось ни одной корректной рамки |
| `Unsupported required split(s): dev; expected train, val, or test` | В `required_splits` указан недопустимый split |
| `Cached dataset required split(s) contain no images: test` | CSV уже в кэше, но в нём нет изображений split из `required_splits` |

При загрузке разметки из датасета ClearML:

| Сообщение | Причина |
| --- | --- |
| `Ground-truth ClearML dataset must be finalized` | Датасет не финализирован |
| `Ground-truth ClearML dataset requires root dataset.csv` | В корне датасета нет `dataset.csv` |
| `Ground-truth ClearML dataset must contain only root dataset.csv; store images and other files outside the dataset` | Кроме `dataset.csv` в датасете есть другие файлы |

При предсказании, метриках и сравнении:

| Сообщение | Причина |
| --- | --- |
| `Ground truth has no 'image_path' column` | Нет колонки `image_path` (`cy-predict`) |
| `Ground truth contains an empty image_path` | Пустой `image_path` (`cy-predict`) |
| `No images to predict` | В файле нет ни одной строки для предсказания (`cy-predict`) |
| `No ground-truth rows for splits ['test']` | В файле нет строк запрошенного split |
| `No ground-truth rows for calibration split 'val'` | В файле нет `val` (`cy-metrics`) |
| `A logical image cannot belong to both val and test; overlapping image_name(s): ['a.jpg']` | Изображение есть и в `val`, и в `test` |
| `'background' is a reserved class label for unmatched detections.` | Класс называется `background` |
| `Ground-truth unlabeled rows must have fully empty boxes.` | Строка без `instance_label`, но с координатами |
| `Ground-truth boxes must have numeric coordinates.` | Координата не число |
| `Ground-truth boxes must have ordered corners and positive area.` | Правая или нижняя граница не больше левой или верхней |
| `Ground-truth boxes must have complete finite coordinates.` | Координата бесконечна или не задана |
| `source_row_id must be unique and nonmissing` | Повтор или пропуск в `source_row_id` |
| `Ground truth contains no labelled objects to evaluate` | Ни в разметке, ни в предсказаниях нет ни одного класса |

## См. также

- [Предсказания](predictions.md)
- [Датасеты](datasets.md)
- [`cy-ground-truth`](../commands/cy-ground-truth.md)
