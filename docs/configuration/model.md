# Группа `model`

Группа конфигурации (config group) `model` выбирает семейство моделей ([detector family](../../GLOSSARY.md#detector-family)) и его архитектуру, а для DEIMv2, RF-DETR, Faster R-CNN и FCOS также задаёт параметры обучения (`model.train`) и предсказания (`model.predict`). Группа есть у `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-compare` и `cy-export`.

## Выбор модели

Модель выбирается одной строкой Hydra `model=<backend>/<preset>`:

```bash
cy-train model=rfdetr/small ground_truth=data/ground_truth.csv
cy-train model=fasterrcnn/resnet50_fpn model.train.epochs=50 model.train.device=0 ground_truth=data/ground_truth.csv
cy-predict model=deimv2/s weights=weights/best.pt
```

Ultralytics YOLO выбирается как `model=ultralytics` (без `/preset`); это значение по умолчанию у всех команд, кроме `cy-export`, где по умолчанию `model=fasterrcnn/resnet50_fpn`. Несуществующий выбор Hydra отклоняет до запуска:

```text
hydra.errors.MissingConfigException: In 'train': Could not find 'model/rfdetr/foo'
```

Посмотреть итоговые значения группы без запуска:

```bash
cy-train --cfg job model=rfdetr/nano
```

## Ключи верхнего уровня

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `backend` | `ultralytics` | Семейство: `ultralytics`, `deimv2`, `rfdetr`, `fasterrcnn`, `fcos`. Задаётся выбором `model=...`. |
| `preset` | `default` | Архитектура внутри семейства, из таблицы ниже. Определяет `model.train.imgsz` по умолчанию. Для `ultralytics` единственный preset — `default`. |
| `source_dir` | `null` | Только DEIMv2: каталог с исходниками DEIMv2 нужной ревизии. `null` — CY сам скачивает и распаковывает утверждённую ревизию. Для других семейств любое значение отклоняется: `source_dir is only supported for DEIMv2`. |
| `train` | см. ниже | Параметры обучения, таблица `model.train`. |
| `predict` | см. ниже | Параметры предсказания, таблица `model.predict`. |

## Список preset

Значение в столбце «`imgsz`» становится `model.train.imgsz` по умолчанию.

| Выбор | `imgsz` | Семейство |
| --- | --- | --- |
| `deimv2/s` | 640 | DEIMv2 |
| `deimv2/m` | 640 | DEIMv2 |
| `deimv2/l` | 640 | DEIMv2 |
| `deimv2/x` | 640 | DEIMv2 |
| `rfdetr/nano` | 384 | RF-DETR |
| `rfdetr/small` | 512 | RF-DETR |
| `rfdetr/medium` | 576 | RF-DETR |
| `rfdetr/large` | 704 | RF-DETR |
| `fasterrcnn/resnet50_fpn` | 800 | Faster R-CNN, backbone ResNet-50 FPN |
| `fasterrcnn/resnet101_fpn` | 800 | Faster R-CNN, backbone ResNet-101 FPN |
| `fasterrcnn/convnext_tiny` | 800 | Faster R-CNN, backbone ConvNeXt-Tiny |
| `fasterrcnn/swin_tiny` | 800 | Faster R-CNN, backbone Swin-Tiny |
| `fasterrcnn/dinov2_small` | 800 | Faster R-CNN, backbone DINOv2-Small |
| `fasterrcnn/dinov3_small` | 800 | Faster R-CNN, backbone DINOv3-Small |
| `fcos/resnet50_fpn` | 800 | FCOS, backbone ResNet-50 FPN |
| `fcos/resnet101_fpn` | 800 | FCOS, backbone ResNet-101 FPN |
| `fcos/convnext_tiny` | 800 | FCOS, backbone ConvNeXt-Tiny |
| `fcos/swin_tiny` | 800 | FCOS, backbone Swin-Tiny |
| `fcos/dinov2_small` | 800 | FCOS, backbone DINOv2-Small |
| `fcos/dinov3_small` | 800 | FCOS, backbone DINOv3-Small |

## Ultralytics YOLO: настройки в других группах

При `model=ultralytics` ключи `model.train` и `model.predict` не действуют. Обучение настраивается в группе [`ultralytics`](ultralytics.md), предсказание — в [`ultralytics_predict`](ultralytics-predict.md). Изменённый ключ не в той группе останавливает команду до запуска:

```text
ValueError: Changed model.train settings ['epochs'] are inactive for ultralytics; use ultralytics instead
```

И наоборот, для других семейств изменения в группах `ultralytics` и `ultralytics_predict` отклоняются:

```text
ValueError: Changed ultralytics settings ['epochs'] are inactive for fcos/swin_tiny; use model.train instead
```

Аналогичное сообщение с `model.predict` / `ultralytics_predict` выдаётся для параметров предсказания.

## `model.train`

Ключи обучения для DEIMv2, RF-DETR, Faster R-CNN и FCOS. Неизвестный ключ отклоняется.

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `device` | `null` | Устройство: `cpu`, строка CUDA (`cuda`, `cuda:0`), один индекс GPU или список индексов. `null` — `cuda`, если GPU доступен, иначе `cpu`. DEIMv2 и RF-DETR в одном процессе принимают только одно устройство: `DEIMv2 multi-device execution is unsupported by this adapter`. |
| `epochs` | `100` | Число эпох, целое больше 0. |
| `batch` | `4` | Глобальный batch size, целое больше 0. `null` — значение берётся из [таблицы batch size](../formats/batch-table.md) ([batch size table](../../GLOSSARY.md#batch-size-table)) для текущего GPU. При обучении на нескольких GPU batch size должен делиться на число устройств. |
| `imgsz` | из preset | Размер входа: целое больше 0 или пара `[высота, ширина]`. RF-DETR: только целое, кратное 32. DEIMv2: обе стороны кратны 32 и не меньше 128, для обучения — квадрат. |
| `workers` | `4` | Число процессов загрузки данных; `0` — загрузка в основном процессе. |
| `lr` | `0.0001` | Начальная скорость обучения, больше 0. |
| `weight_decay` | `0.0001` | Коэффициент регуляризации весов, не меньше 0. |
| `seed` | `0` | Целочисленный seed обучения и аугментации. |
| `pretrained` | `true` | Начинать с предобученных весов (см. «Как выбираются веса»). `false` — обучение с нуля без загрузки весов. |
| `weights` | `null` | Локальный checkpoint для дообучения. Если задан, автоматическая подготовка весов не выполняется. Файл должен существовать. |
| `backbone_weights` | `null` | Локальные веса backbone для DEIMv2, Faster R-CNN и FCOS. RF-DETR их не принимает: `RF-DETR backbone_weights is unsupported; use model.train.weights`. |
| `amp` | `true` | Смешанная точность. У DEIMv2, Faster R-CNN и FCOS включается только на CUDA. |
| `grad_accum_steps` | `1` | Число шагов накопления градиента, больше 0. DEIMv2 принимает только `1`: `DEIMv2 native grad_accum_steps other than 1 is unsupported`. |
| `use_ema` | `true` | Экспоненциальное усреднение весов (EMA). |
| `augmentation` | `null` | Отключаемые встроенные аугментации семейства. Заполняется автоматически при `transforms=albumentations`, см. [группу `transforms`](transforms.md). При профиле ([transforms profile](../../GLOSSARY.md#transforms-profile)) `default` должно быть `null`, иначе: `model.train.augmentation requires transforms=albumentations`. |

## `model.predict`

Ключи предсказания для DEIMv2, RF-DETR, Faster R-CNN и FCOS. Действуют в командах, которые строят предсказания этими семействами.

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `device` | `null` | Устройство предсказания, задаётся независимо от `model.train.device`. `null` — `cuda`, если GPU доступен, иначе `cpu`. Предсказание выполняется на одном устройстве; список из нескольких индексов отклоняется. |
| `batch` | `1` | Число изображений в batch, целое больше 0. |
| `imgsz` | `null` | Размер входа; `null` — размер, записанный в checkpoint при обучении. RF-DETR: целое, кратное 32. DEIMv2: стороны кратны 32 и не меньше 128. |
| `conf` | `0.001` | Порог уверенности (confidence threshold) сохраняемых детекций, от 0 до 1. Низкий порог оставляет запас для последующего выбора порога по метрикам. |
| `iou` | `0.7` | Порог IoU подавления пересекающихся рамок (bounding box), больше 0 и не больше 1. Faster R-CNN и FCOS используют его для NMS. DEIMv2 и RF-DETR принимают только `0.7`. |
| `max_det` | `300` | Максимум детекций на изображение, целое больше 0. |
| `half` | `false` | FP16 при предсказании. Faster R-CNN и FCOS: только на CUDA (`Torchvision half inference requires CUDA`). DEIMv2 и RF-DETR принимают только `false`. |

Для DEIMv2 и RF-DETR другие значения `iou` и `half` останавливают предсказание: `DEIMv2 nondefault iou and half controls are unsupported` (для RF-DETR — `RF-DETR nondefault iou and half controls are unsupported`).

Файл весов для предсказания задаётся не в группе `model`, а ключом `weights` команды, например [`cy-predict`](../commands/cy-predict.md). Checkpoint семейств DEIMv2, RF-DETR, Faster R-CNN и FCOS хранит описание модели ([checkpoint descriptor](../../GLOSSARY.md#checkpoint-descriptor)) с семейством и preset, с которыми он обучен. Выбор `model=` должен им соответствовать, иначе команда останавливается: `Explicit model selection disagrees with the checkpoint descriptor`.

## Как выбираются веса

Веса (weights) для обучения выбираются в таком порядке:

1. Если задан `model.train.weights`, обучение начинается с этого файла. Предобученные веса не загружаются.
2. Иначе, если `model.train.pretrained=false`, обучение идёт с нуля.
3. Иначе CY готовит предобученные веса автоматически:
   - RF-DETR — полный checkpoint preset из реестра RF-DETR; результат подставляется как `model.train.weights`.
   - Faster R-CNN и FCOS — веса backbone (torchvision для ResNet, timm для ConvNeXt, Swin, DINOv2, DINOv3); результат подставляется как `model.train.backbone_weights`. Если `backbone_weights` задан явно, используется он.
   - DEIMv2 `s` и `m` — дистиллированный backbone ViT-Tiny / ViT-Tiny+; `l` и `x` — backbone DINOv3. Для `l` и `x` CY сначала ищет оригинальный файл Meta `.pth` в кэше, а если его нет — скачивает представление весов с Hugging Face и конвертирует его. Если `backbone_weights` задан явно, используется он.

Явно заданные `weights` и `backbone_weights` проверяются перед обучением, уже после создания задачи ClearML (task): `Explicit model weights do not exist: weights/best.pt`.

Для DEIMv2 CY также готовит исходники DEIMv2, если `model.source_dir=null`, и кладёт архив в рабочий каталог ([workspace](../../GLOSSARY.md#workspace)), в `CY_HOME/.cache/clearml-yolo/sources/DEIMv2/` (см. [Рабочий каталог](../workspace.md)).

Подготовка выполняется только для тех весов, которые нужны текущему запуску, и использует уже скачанные файлы из кэшей. Недостающий файл CY скачивает сначала через зеркало весов ([weight mirror](../../GLOSSARY.md#weight-mirror)), если оно задано, затем по исходному адресу; на каждый адрес — две попытки, каждая не дольше 300 секунд и не больше 4 GiB. Адреса зеркал весов и токены Hugging Face описаны в [установке](../installation.md). Заранее скачать веса на GPU-хосте можно командой [`cy-download-weights`](../commands/cy-download-weights.md).

### Если весов нет

Если файл не удалось получить, команда завершается с сообщением, где для каждого недостающего файла указаны исходный адрес, место в кэше и ключ для явного указания пути:

```text
Model asset preparation failed. Copy the original files to the listed destinations and rerun offline; no download receipt is required.
Missing fcos/swin_tiny asset <file>:
  Original URL: <url>
  Local destination: <path>
  Override: model.train.backbone_weights=<path>
  Attempts: <url> (<error>)
```

Скопируйте файл по пути `Local destination` и запустите команду снова, либо передайте путь в ключ из строки `Override`. Для весов DEIMv2 и для `fasterrcnn/dinov3_small` и `fcos/dinov3_small` в сообщении есть строка `Access:` с условиями доступа (лицензия, `HF_TOKEN`, ручная загрузка).

## Особенности семейств

### DEIMv2

- Нужны исходники DEIMv2: `model.source_dir` или автоматическая подготовка.
- Обучение требует квадратный `imgsz`, стороны кратны 32 и не меньше 128.
- `grad_accum_steps` только `1`.
- При `pretrained=true` нужны `weights` или `backbone_weights`; при автоматической подготовке они заполняются сами.
- При предсказании `iou` только `0.7`, `half` только `false`.

### RF-DETR

- `imgsz` (обучение и предсказание) — одно целое, кратное 32: `RF-DETR resolution must be square and divisible by 32`.
- `backbone_weights` не поддерживается; предобученные веса — полный checkpoint в `weights`.
- При предсказании `iou` только `0.7`, `half` только `false`.

### Faster R-CNN

- Веса backbone задаются `backbone_weights` или готовятся автоматически.
- `imgsz` задаёт холст: каждая сторона округляется вверх до кратной 32. Изображение масштабируется с сохранением пропорций, чтобы поместиться в холст, а остаток справа и снизу заполняется.
- Только Faster R-CNN поддерживает [`cy-export`](../commands/cy-export.md): `cy-export supports only Faster R-CNN presets`.
- Для `dinov3_small` репозиторий весов может требовать принятия лицензии на Hugging Face.

### FCOS

- Те же backbone и правила весов, что у Faster R-CNN.

### Ultralytics YOLO

- `model=ultralytics`, preset `default`. Все параметры — в группах [`ultralytics`](ultralytics.md) и [`ultralytics_predict`](ultralytics-predict.md).

## См. также

- [Группа `transforms`](transforms.md)
- [Как устроена конфигурация](README.md)
- [`cy-train`](../commands/cy-train.md), [`cy-predict`](../commands/cy-predict.md)
- [Таблица batch size](../formats/batch-table.md)
- [`cy-batch-estimate`](../commands/cy-batch-estimate.md)
