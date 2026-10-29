# Первый эксперимент: установка и небольшой датасет

Этот урок создаёт воспроизводимый набор изображений и запускает одну эпоху YOLO.
Синтетические квадраты проверяют работоспособность конвейера; качество на них не
характеризует качество модели на производственных данных.

## Предварительные условия

Нужны Python `>=3.12.13,<3.14`, поддерживаемая Linux-среда с `pidfd`, доступ к
ClearML и удалённому хранилищу артефактов. Все поддерживаемые детекторы и ONNX
входят в обычную установку CY. TensorRT и отдельный пакет `cy-queue` имеют свои
предварительные условия. Установка не требует Node.js.

При установке из исходников подготовьте утверждённые копии `digital-metrics` и
`report-generator` в `external/`, следуя инструкции поставляемой версии. Сам
lockfile не скачивает эти деревья. Затем из каталога исходников:

```bash
uv sync --frozen
uv run --frozen --no-sync cy-docs
```

После активации установленного Python-окружения достаточно `cy-docs`. Для запуска
без автоматического открытия браузера используйте `cy-docs --no-browser`; команда
напечатает локальный адрес. `cy-docs --check` проверяет документацию без сервера.
Справочник и предпросмотр работают без интернета. Эксперименты выполняются командами
терминала и требуют своих входов и настроенного ClearML.

Настройте SDK обычным способом, например `clearml-init`, указав свои адреса и
учётные данные. Не записывайте секреты в YAML урока. Должно быть доступно удалённое
хранилище: [clearml.output_uri](/#field=clearml.output_uri) по умолчанию равно `true`;
`null`, `false` и пустая строка не отключают публикацию, а вызывают ошибку.

## Пример

Создайте отдельный рабочий каталог и запускайте последующие команды из него.
`CY_HOME` по умолчанию совпадает с каталогом запуска. Все выходные файлы должны
находиться внутри этого корня; исходные данные могут быть внешними.

Сохраните как `make_dataset.py` и выполните `python make_dataset.py`:

```python
import csv
from pathlib import Path

from PIL import Image, ImageDraw

root = Path("tutorial-data")
images = root / "images"
images.mkdir(parents=True, exist_ok=True)
columns = [
    "image_name",
    "image_path",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
    "split",
]
with (root / "ground_truth.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream)
    writer.writerow(columns)
    for split_index, split in enumerate(("train", "val", "test")):
        for index in range(4):
            name = f"{split}-{index}.png"
            image = Image.new("RGB", (160, 128), (20 + split_index * 10, 30, 40))
            if index == 3:
                annotation = ["", "", "", "", ""]
            else:
                left = 12 + index * 24 + split_index
                box = [left, 30, left + 30, 70]
                ImageDraw.Draw(image).rectangle(box, fill=(230, 170, 70))
                annotation = ["square", *box]
            image.save(images / name)
            writer.writerow([name, f"images/{name}", *annotation, split])
print(root / "ground_truth.csv")
```

Одна строка описывает объект; для нескольких объектов повторите имя изображения.
Строка без класса и координат сохраняет пустое изображение. Не смешивайте её с
объектами того же изображения. `image_name` совпадает с basename файла, координаты
измеряются в пикселях. Изображения разных выборок не должны совпадать. Относительные
пути разрешаются от каталога CSV, а не от каталога запуска. Строковые классы `NA`,
`NULL`, `0001` и Unicode сохраняются буквально.

```bash
cy-train ground_truth=./tutorial-data/ground_truth.csv \
  ultralytics.model=yolo11n.pt ultralytics.epochs=1 ultralytics.imgsz=128 \
  ultralytics.batch=2 ultralytics.device=cpu ultralytics.workers=0 \
  ultralytics.compile=false clearml.project_name=cy-tutorial \
  clearml.task_name=first-training 'clearml.tags=[tutorial,quickstart]'
```

CPU выбран явно и действительно выполняет обучение. Для доступного GPU замените
`ultralytics.device=cpu` на `ultralytics.device=0`. Первый запуск может скачать веса;
варианты подготовки для закрытой сети описаны в [операционном уроке](operations.html).

### Вместо локального CSV — ClearML Dataset

[ground_truth](/#field=ground_truth) также принимает один из двух селекторов:

```yaml
ground_truth:
  dataset_id: YOUR_FINALIZED_DATASET_ID
```

```yaml
ground_truth:
  project_name: annotations
  name: ground-truth
  version: "1.2.0"
```

В паре проект/имя версия необязательна, но явная версия делает выбор стабильнее.
Нельзя совместить ID с проектом/именем/версией. Набор должен быть финализирован и
содержать только корневой `dataset.csv`, без изображений и ссылок. При загрузке
CSV не меняется; его относительные пути считаются от места загруженного CSV.
Для переносимого набора используйте доступные выполняющему процессу абсолютные
пути к изображениям. Предпросмотр не скачивает Dataset и не проверяет эти пути.

Для исходной YOLO-разметки есть конвертер:

```bash
cy-ground-truth data_yaml=./source-data/data.yaml output=./converted/ground_truth.csv \
  test_fraction=0.5 seed=0 clearml.project_name=cy-tutorial \
  clearml.task_name=convert-data 'clearml.tags=[tutorial,conversion]'
```

Если исходный набор не содержит `test`, конвертер выделит её из `val` согласно
[test_fraction](/#field=test_fraction) и [seed](/#field=seed). Проверьте разбиение
перед обучением; `cy-train` сам выборки не создаёт.

## Ожидаемый результат

Генератор создаёт 12 изображений: по четыре в каждой выборке, включая одно пустое.
Обучение создаёт одну задачу ClearML, журнал, скаляры и лучший чекпойнт.
Локальный путь к весам напечатан в журнале; по умолчанию результаты лежат в
`runs/<проект>/<задача>-<task-id>/`. В ClearML лучший чекпойнт находится в
`Output Models`. Численные метрики на этом наборе могут быть низкими.

## Частые ошибки

- `ground_truth=???`: обязательный вход не заполнен. Выберите локальный CSV или Dataset.
- Нет `train`/`val`: обучение требует обе непустые выборки; полный `cy` также
  использует `test` по умолчанию.
- Изображения не найдены: проверьте пути относительно CSV и точное имя файла.
- Ошибка ClearML или загрузки артефактов: проверьте конфигурацию SDK и хранилище;
  успешное создание локальных весов ещё не означает успешное завершение задачи.
- Не хватает памяти: уменьшите batch/разрешение по [уроку обучения](training.html).

## Проверка

Сверьте число изображений и выборок, убедитесь в отсутствии пересечений и наличии
пустых строк. Проверьте код завершения обучения, журнал, `Output Models`, артефакт
`gt_csv` и `Configuration / run` задачи. Скачайте веса и сравните их с локальным
чекпойнтом перед следующим шагом. Сохраните идентификационный sidecar рядом с весами.
Для полного эксперимента перейдите к [конвейеру](pipeline.html).
