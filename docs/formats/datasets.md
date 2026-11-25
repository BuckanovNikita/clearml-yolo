# Датасеты

На этой странице описано, какой датасет принимает `cy-ground-truth` и какую рабочую копию датасета ([prepared dataset copy](../../GLOSSARY.md#prepared-dataset-copy)) CY собирает для обучения. Обучение читает не YOLO-датасет, а CSV [разметки](ground-truth.md) ([ground truth](../../GLOSSARY.md#ground-truth)); из этого CSV CY сам строит датасет в формате, который нужен семейству моделей ([detector family](../../GLOSSARY.md#detector-family)).

## Вход `cy-ground-truth`: YAML YOLO-датасета

[`cy-ground-truth`](../commands/cy-ground-truth.md) принимает в ключе `data_yaml` YAML-описание детекционного датасета в формате Ultralytics и пишет из него CSV разметки. Файл читает сам Ultralytics, поэтому правила путей те же, что при обучении Ultralytics с `data=`. NDJSON и COCO как вход `cy-ground-truth` не принимает.

| Ключ | Правила |
| --- | --- |
| `path` | Корень датасета. Если ключа нет, корень — каталог YAML-файла. Относительный путь, который не существует относительно текущего каталога, Ultralytics ищет в своём каталоге датасетов |
| `train` | Обязателен. Каталог изображений, файл `.txt` со списком изображений или список таких значений, относительно корня |
| `val` | Обязателен. Тот же формат |
| `test` | Необязателен. Тот же формат |
| `names` | Имена классов: словарь `индекс: имя` или список. Можно вместо него задать `nc` (тогда классы называются `class_0`, `class_1`, ...). Имена вроде `yes`, `off` или `1e3` пишите в кавычках (`"yes"`): без кавычек разные версии Ultralytics читают их по-разному (`True` или `yes`, `1e3` или `1000.0`), и CY отклоняет такой файл, если установленная версия читает их не так, как YAML 1.1 (Ultralytics 8.4.184) |

Файл `.txt` со списком содержит по одному пути на строку; относительные пути отсчитываются от каталога этого файла, пустые строки пропускаются. Из каталога берутся все изображения во вложенных каталогах с расширениями, которые знает Ultralytics.

Файл разметки изображения Ultralytics ищет по своему правилу: `images` в пути заменяется на `labels`, расширение — на `.txt`. Каждая строка файла — одна рамка: `класс cx cy w h`, координаты нормированы на размер изображения. Сегментационные метки не поддерживаются.

```yaml
# data/dataset.yaml: изображения в data/images/{train,val}, метки в data/labels/{train,val}
train: images/train
val: images/val
names:
  0: car
  1: person
```

### Как `cy-ground-truth` строит CSV

1. Собирает изображения split `train`, `val` и `test`.
2. Если split `test` нет или он пуст, переносит часть изображений `val` в `test`. Долю задаёт ключ `test_fraction` (по умолчанию `0.5`), выбор детерминирован ключом `seed` (по умолчанию `0`). Изображение переносится целиком, со всеми рамками. В `val` остаётся хотя бы одно изображение.
3. Отклоняет датасет, если одно имя файла встречается у двух разных изображений: CY сопоставляет предсказания с разметкой только по имени файла.
4. Переводит рамки в пиксели и обрезает их по границам изображения. Размер изображения учитывает поворот из EXIF.
5. Для изображения без файла разметки или с пустым файлом пишет строку изображения без объектов ([image without objects](../../GLOSSARY.md#image-without-objects)).
6. Записывает CSV с колонками `image_name`, `image_path`, `instance_label`, `bbox_x_tl`, `bbox_y_tl`, `bbox_x_br`, `bbox_y_br`, `split`. В `image_path` попадает абсолютный путь.

### Ошибки `cy-ground-truth`

Пути в сообщениях заменены на `data/...`.

| Сообщение | Причина |
| --- | --- |
| `data/dataset.yaml 'val:' key missing ❌.` | В YAML нет `train` или `val` (сообщение Ultralytics) |
| `Dataset 'data/dataset.yaml' images not found, missing path 'data/images/val'` | Путь `val` не существует (сообщение Ultralytics) |
| `test_fraction must be within [0.0, 1.0), got 1.0` | Недопустимое `test_fraction` |
| `data/dataset.yaml resolved to no images at all; nothing to convert` | Ни в одном split нет изображений |
| `Split 'train' points at '...', which is neither an existing image directory nor a .txt image list` | Путь split не каталог и не список |
| `data/train.txt: listed image 'x.jpg' does not exist` | Строка списка указывает на несуществующий файл |
| `data/labels/train/a.txt:1 has 4 fields, expected 5 (class cx cy w h); segment labels are not supported` | Строка метки не из пяти полей |
| `data/labels/train/a.txt:1 is not a YOLO label: '...'` | Поля не числа |
| `data/labels/train/a.txt:1 has a non-positive box size (0.0 x 0.2); such a box has no top-left/bottom-right corner` | Нулевая или отрицательная ширина или высота |
| `data/labels/train/a.txt:1 has nonfinite or out-of-bounds normalized coordinates` | Координата вне диапазона от -0.01 до 1.01 |
| `data/labels/train/a.txt:1 references class 5, but the dataset defines classes 0..1` | Индекс класса не из `names` |
| `Ultralytics reads class names in data/dataset.yaml unlike YAML 1.1: 0 'yes' (YAML 1.1: 'True'); write these names in quotes so every Ultralytics version reads the same text` | Установленная версия Ultralytics читает имя класса без кавычек иначе, чем YAML 1.1. Запишите имена из сообщения в кавычках |
| `data/dataset.yaml is not YAML 1.1, so CY cannot confirm that its class names read the same under every Ultralytics version` | Установленная версия Ultralytics прочла файл, а YAML 1.1 (PyYAML) — нет, поэтому CY не может сравнить имена классов. Исправьте синтаксис YAML |
| `1 image name(s) refer to more than one file, which digital-metrics cannot tell apart: a.jpg (data/images/train/a.jpg and data/images/val/a.jpg)` | Одно имя файла у двух изображений |
| `Cannot read the pixel size of data/images/train/a.jpg` | Изображение с рамками не читается. Если файл не декодируется как изображение, Ultralytics сначала пытается установить пакет `pi-heif`; без доступа к сети вместо этого сообщения вы получите `No module named 'pi_heif'` |

## Рабочая копия датасета для обучения

`cy-train` и этап ([stage](../../GLOSSARY.md#stage)) обучения [`cy`](../commands/cy.md) проверяют CSV разметки (см. [Разметка](ground-truth.md#как-проверяется-файл-при-обучении)) и собирают из него рабочую копию датасета. Исходные изображения копируются и не изменяются.

### `dataset_format`

| Значение | Что получает обучение |
| --- | --- |
| `ndjson` | По умолчанию. Каталоги `images/<split>/` и `labels/<split>/` с исходными именами файлов, `data.yaml` и `dataset.ndjson` |
| `flat` | Те же каталоги, но файлы названы по порядку: `00000001.jpg`, `00000002.jpg`, ... |
| `coco` | Каталоги `train/`, `valid/` (для split `val`), `test/` с нумерованными изображениями и `_annotations.coco.json` в каждом, плюс `data.yaml` |

Для [семейства моделей](../configuration/model.md) `ultralytics` допустимы `ndjson` и `flat`; `coco` вызывает ошибку `Ultralytics training requires ndjson or flat dataset_format`. Остальные семейства всегда получают `coco`, какое бы значение вы ни задали. Другое значение вызывает ошибку `dataset_format must be one of: ndjson, flat, coco` (в `cy` — `Invalid pipeline setting dataset_format: ...`). `cy-train` и `cy` проверяют значение до создания задачи ClearML (task), `cy` — и при `skip_train=true`.

В формате `ndjson` два изображения одного split не могут иметь одинаковое имя без расширения без учёта регистра: `NDJSON label stem collision in split 'train': 'a.jpg' and 'A.png' share stem 'a'`. Используйте `flat` или переименуйте файлы.

Индексы классов присваиваются заново: имена классов из всех непустых `instance_label` CSV сортируются как строки (заглавные буквы раньше строчных) и нумеруются с 0. Индексы из `names` исходного YAML не сохраняются: при `names: {0: person, 1: car}` обучение получит `0: car`, `1: person`.

Изображения рабочей копии упорядочены по `image_name`; в `flat` и `coco` номер файла — позиция изображения в этом порядке по всем split, расширение пишется строчными буквами.

### Файлы рабочей копии

| Файл | Содержимое |
| --- | --- |
| `data.yaml` | Описание датасета для обучения: абсолютный `path`, `names` и split, в которых есть изображения. Имена классов в `names` записаны в двойных кавычках, чтобы любая версия Ultralytics прочла имя вроде `1e3` как строку, а не как число |
| `ground_truth.csv` | Разметка после проверки: только корректные рамки, абсолютные пути, по одной строке на изображение без объектов |
| `preparation.json` | Источник, `input_sha256` (SHA-256 исходного CSV), `dataset_format`, `class_names`, `counts` (`input_boxes`, `valid_boxes`, `invalid_boxes`), число изображений по split, список `invalid_boxes` (номер строки, `image_name`, причина) и список изображений с размерами, числом рамок и `generated_path` |
| `labels.zip` | Архив файлов разметки (`labels/**/*.txt` или `*/_annotations.coco.json`) |
| `dataset.ndjson` | Только для `ndjson`: первая строка описывает датасет, далее по строке на изображение с рамками `[класс, cx, cy, w, h]` |
| `completion.json` | Отметка о том, что копия собрана целиком |

### `dataset_cache_dir`

Рабочие копии хранятся в кэше. По умолчанию это `CY_HOME/.cache/clearml-yolo/datasets` (см. [Рабочий каталог](../workspace.md) ([workspace](../../GLOSSARY.md#workspace))); ключ `dataset_cache_dir` задаёт другой каталог. В `cy` он должен лежать вне каталога запуска ([run directory](../../GLOSSARY.md#run-directory)), иначе ошибка `dataset_cache_dir must be outside run_dir`. В `cy-train` он должен лежать вне каталога проекта обучения Ultralytics (`ultralytics.project`), иначе ошибка `dataset_cache_dir must be outside the run-owned training project`.

Каждая копия лежит в подкаталоге, имя которого — хэш от байтов CSV, списка разрешённых путей к изображениям, `dataset_format` и версии формата подготовки в CY. Если CSV, пути и `dataset_format` не изменились, следующий запуск берёт готовую копию; после обновления CY с новой версией подготовки копия собирается заново в новом подкаталоге. Содержимое изображений при этом не проверяется: если вы заменили файл изображения под тем же путём, измените CSV или удалите подкаталог копии. Готовую копию, среди классов которой есть `background`, CY не использует: команда отклоняет файл тем же сообщением, что и при первом чтении CSV (см. [Разметка](ground-truth.md#как-проверяется-файл-при-обучении)), а копию не удаляет.

Пока обучение использует копию, CY держит блокировку в `.locks/` внутри каталога кэша, поэтому параллельные запуски с той же копией (тот же CSV и `dataset_format`) ждут друг друга. Повреждённую копию CY не удаляет и не пересобирает, а останавливается с ошибкой `Dataset cache entry is invalid and has been preserved: <каталог>. Inspect it and explicitly repair or remove it while the cache is idle.` Удалите этот подкаталог, когда никакое обучение его не использует.

### Что CY задаёт обучению Ultralytics

При обучении из CSV CY сам задаёт ключи Ultralytics и пишет в лог каждое изменение вида `CSV dataset owns <ключ>: <ваше значение> -> <значение CY>`:

| Ключ | Значение |
| --- | --- |
| `task` | `detect`; другое значение вызывает ошибку `CSV ground-truth training supports task=detect only` |
| `classes` | `null` |
| `data` | `data.yaml` рабочей копии |
| `single_cls` | `false` |
| `fraction` | `1.0` |
| `cls_remap` | `false` |
| `split` | `val` |

`resume` вместе с разметкой не поддерживается: `resume is unsupported with ground_truth; use model weights to fine-tune`.

## См. также

- [Разметка (ground truth)](ground-truth.md)
- [`cy-ground-truth`](../commands/cy-ground-truth.md), [`cy-train`](../commands/cy-train.md)
- [Ключи `ultralytics`](../configuration/ultralytics.md)
