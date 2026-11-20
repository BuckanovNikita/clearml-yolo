# Таблица batch size

Таблица batch size ([batch size table](../../GLOSSARY.md#batch-size-table)) — YAML-файл, в котором для каждой GPU, размера изображения и модели записан batch size на одну GPU. Обучение берёт batch из этой таблицы только тогда, когда вы задали batch равным `null`. Таблицу заполняет `cy-batch-estimate`, и вы можете править её вручную.

## Где лежит

`CY_HOME/.config/clearml-yolo/batch-sizes.yaml` (см. [Рабочий каталог](../workspace.md) ([workspace](../../GLOSSARY.md#workspace))). Если файла нет, таблица считается пустой.

## Кто пишет и кто читает

- Пишет: [`cy-batch-estimate`](../commands/cy-batch-estimate.md) после измерения на GPU, а также вы сами.
- Читают: обучение в [`cy-train`](../commands/cy-train.md) и [`cy`](../commands/cy.md), когда batch равен `null`: ключ `ultralytics.batch` для Ultralytics (см. [Ultralytics](../configuration/ultralytics.md)), `model.train.batch` для остальных семейств (см. [Модель](../configuration/model.md)). По умолчанию оба ключа заданы числом, поэтому таблица не используется, пока вы не передадите, например, `ultralytics.batch=null`. Ещё таблицу читает `cy-batch-estimate --list` для отчёта о покрытии.

Рядом `cy-batch-estimate` хранит `batch-estimates.json` с подробными результатами измерений. Это не таблица для правки: обучение его не читает.

## Структура

Три уровня вложенности: метка GPU, размер изображения, модель.

```yaml
# Batch size на одну GPU
NVIDIA GeForce RTX 4090 [24 GiB]:
  640:
    ultralytics/yolo11n: 64   # подобрано вручную
    ultralytics/yolo11s: 32
  1024:
    ultralytics/yolo11n: 16
```

| Уровень | Правила |
| --- | --- |
| Метка GPU | `Имя GPU [N GiB]`: имя, как его сообщает CUDA, пробел и объём памяти в GiB в квадратных скобках, можно с дробной частью. Другая форма метки — ошибка |
| Размер изображения | Целое положительное число, сторона квадратного изображения (`imgsz`) |
| Модель | Каноническое имя модели вида `семейство/вариант`, например `ultralytics/yolo11n`, `rfdetr/small`, `deimv2/s`. Короткое имя вроде `yolo11n` в таблице — ошибка. Полный список выводит `cy-batch-estimate --list` |
| Значение | Целое положительное число, batch size на одну GPU |

Комментарии и порядок строк сохраняются, когда `cy-batch-estimate` обновляет файл.

## Строка метаданных

`cy-batch-estimate` дописывает в конец файла одну служебную строку комментария:

```yaml
# clearml-yolo-batch-metadata: {"schema_version": 1, "capacities": {...}, "measured": {...}, "failures": [...], "forced": {...}, "sources": {...}}
```

В ней хранятся точный объём памяти GPU в байтах, измеренные значения, отметки измерений с `--force`, источники измерений и случаи, когда модель не поместилась на GPU даже с одним изображением. Не меняйте и не копируйте эту строку: две такие строки или испорченный JSON делают таблицу недействительной.

Запись считается измеренной, пока её значение совпадает с измеренным в метаданных. Если вы измените число вручную, запись становится ручной (`manual` в выводе `cy-batch-estimate --list`).

## Как обучение выбирает batch

Модель берётся из конфигурации: для Ultralytics из `ultralytics.model` (`yolo11n.pt` соответствует `ultralytics/yolo11n`), для остальных семейств из `model.backend` и `model.preset`. Если `device` не задан, обучение использует GPU с индексом 0. Для каждой выбранной GPU обучение ищет запись с тем же размером изображения и той же моделью:

1. Точное совпадение: то же имя GPU и тот же объём памяти. Если таких записей несколько, берётся наименьший batch.
2. Если точной записи нет, а в метаданных записано, что модель не помещается на эту GPU, обучение останавливается: `No training batch table entry: Confirmed no_capacity for ultralytics/yolo11n at 640 on NVIDIA GeForce RTX 4090; remeasure or add an exact entry. Run cy-batch-estimate --imgsz 640 --models ultralytics/yolo11n using the assigned GPUs, or set an explicit training batch.` Ваша ручная точная запись снимает этот запрет.
3. Иначе берётся запись GPU с наибольшим объёмом памяти, не превышающим объём текущей GPU (при равном объёме — с наименьшим batch), и пишется предупреждение `Training batch fallback for ... uses ...: per-GPU batch N. This is a table value from another GPU, not a measurement on the target. ...`.

Если записи нет, обучение останавливается: `No training batch table entry: No batch table entry for ultralytics/yolo11n at 640 on NVIDIA GeForce RTX 4090. Run cy-batch-estimate --imgsz 640 --models ultralytics/yolo11n using the assigned GPUs, or set an explicit training batch.`

Если запись выбрана из измерения с `--force`, обучение пишет предупреждение `Training batch source ... is forced/background-sensitive; ...`.

При нескольких GPU общий batch равен наименьшему batch на одну GPU среди выбранных, умноженному на число GPU. Явный batch нужен при обучении на CPU или MPS (`batch=null requires CUDA estimates; set an explicit batch for CPU/MPS`), при неквадратном `imgsz` (`Non-square training requires an explicit batch`) и для собственной архитектуры Ultralytics, которой нет в списке моделей (`Custom YOLO architectures require an explicit batch`).

## Как править таблицу

1. Откройте `CY_HOME/.config/clearml-yolo/batch-sizes.yaml` в редакторе. Если файла нет, создайте его.
2. Добавьте или измените запись на нужном уровне. Метку GPU пишите так же, как в существующих записях или в выводе `cy-batch-estimate`.
3. Не трогайте строку `# clearml-yolo-batch-metadata:`.
4. Проверьте файл:

```bash
cy-batch-estimate --list --models ultralytics/yolo11n,ultralytics/yolo11s
```

```text
Editable table coverage across recorded GPUs and image sizes; no CUDA required.
MODEL	STATUS	REASON	CONTEXT
ultralytics/yolo11n	covered	Editable table entry	NVIDIA GeForce RTX 4090 [24 GiB]; imgsz=640; per_gpu_batch=64; manual
ultralytics/yolo11n	covered	Editable table entry	NVIDIA GeForce RTX 4090 [24 GiB]; imgsz=1024; per_gpu_batch=16; manual
ultralytics/yolo11s	covered	Editable table entry	NVIDIA GeForce RTX 4090 [24 GiB]; imgsz=640; per_gpu_batch=32; manual
Summary: selected=2	covered=2	missing=0
Results: /workspace/project/.config/clearml-yolo/batch-sizes.yaml
```

Если в файле ошибка (неверная метка GPU, неизвестная модель, не целое или не положительное число, повторяющийся ключ, испорченная строка метаданных), команда и обучение останавливаются, а файл не перезаписывается. `cy-batch-estimate` завершается с кодом 2 и пишет:

```text
cy-batch-estimate: error: Invalid batch size table /workspace/project/.config/clearml-yolo/batch-sizes.yaml; repair it before retrying; file preserved
```

## См. также

- [`cy-batch-estimate`](../commands/cy-batch-estimate.md)
- [Модель](../configuration/model.md)
