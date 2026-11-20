# Группа `transforms`

Группа конфигурации (config group) `transforms` выбирает, какая аугментация (augmentation) применяется при обучении: встроенная аугментация семейства моделей ([detector family](../../GLOSSARY.md#detector-family)) или ваш пайплайн (pipeline) Albumentations из JSON-файла. Группа есть только у команд, которые обучают модель: [`cy`](../commands/cy.md) и [`cy-train`](../commands/cy-train.md). Остальные команды отвергают `transforms=...` ошибкой Hydra `Could not override 'transforms'. No match in the defaults list.`

## Примеры

```bash
# встроенная аугментация семейства (по умолчанию)
cy-train model=rfdetr/small ground_truth=data/ground_truth.csv

# свой пайплайн Albumentations
cy-train model=fcos/resnet50_fpn transforms=albumentations transforms.pipeline_file=augmentation/flip.json ground_truth=data/ground_truth.csv

# посмотреть, что меняет профиль, без запуска
cy-train --cfg job model=deimv2/s transforms=albumentations
```

## Ключи

| Ключ | По умолчанию | Описание |
| --- | --- | --- |
| `mode` | `native` | `native` — встроенная аугментация семейства; `albumentations` — пайплайн из `pipeline_file`. Задаётся выбором профиля ([transforms profile](../../GLOSSARY.md#transforms-profile)). |
| `pipeline_file` | `null` | Путь к JSON-файлу пайплайна ([augmentation pipeline file](../../GLOSSARY.md#augmentation-pipeline-file)). Относительный путь считается от текущего каталога. Допустим только при `mode: albumentations`. Файл читается при запуске, а не при `--cfg job`. |
| `snapshot` | `null` | Заполняет CY: содержимое пайплайна, его SHA-256 и имя исходного файла. Не задавайте вручную. |

## Профили

Профиль выбирается как `transforms=<имя>`.

| Профиль | Что делает |
| --- | --- |
| `default` | `mode: native`. Модель обучается со своей встроенной аугментацией. `pipeline_file` задать нельзя. |
| `albumentations` | `mode: albumentations`. Обучение использует пайплайн из `pipeline_file`, а встроенная аугментация семейства отключается (см. ниже). |

Ошибки выбора:

```text
Value error, Albumentations requires pipeline_file or a resolved snapshot
```

`transforms=albumentations` без `transforms.pipeline_file`.

```text
Value error, Select transforms=albumentations before providing a pipeline
```

`transforms.pipeline_file` задан при профиле `default`.

## Что отключается при `transforms=albumentations`

Чтобы аугментация не применялась дважды, профиль `albumentations` переписывает встроенные настройки выбранного семейства. Значения подставляются автоматически отдельной группой `transform_overrides` (её выбирает CY по `model` и `transforms`; вручную её не задают).

| Семейство | Куда пишется | Значения |
| --- | --- | --- |
| Ultralytics YOLO | группа [`ultralytics`](ultralytics.md) | `hsv_h`, `hsv_s`, `hsv_v`, `degrees`, `translate`, `scale`, `shear`, `perspective`, `flipud`, `fliplr`, `bgr`, `mosaic`, `mixup`, `cutmix`, `copy_paste`, `erasing`, `multi_scale` = `0.0`; `auto_augment: null`; `close_mosaic: 0`; `augmentations: []` |
| DEIMv2 | `model.train.augmentation` | `mosaic_prob: 0.0`, `mixup_prob: 0.0`, `copyblend_prob: 0.0`, `base_size_repeat: null`, `ops: []` |
| RF-DETR | `model.train.augmentation` | `aug_config: {}`, `augmentation_backend: torchvision`, `scale_jitter: false`, `multi_scale: off` |
| Faster R-CNN, FCOS | `model.train.augmentation` | `{}` (встроенной аугментации, которую нужно отключать, нет) |

Если вы задали в этих ключах другое значение, CY при запуске заменяет его и пишет предупреждение. Для Ultralytics YOLO замена идёт по каждому ключу, для остальных семейств `model.train.augmentation` заменяется целиком:

```text
WARNING | Custom transforms override model.train.augmentation: {'mosaic_prob': 0.5, 'mixup_prob': 0.0, ...} -> {'mosaic_prob': 0.0, 'mixup_prob': 0.0, ...}
WARNING | Custom transforms override ultralytics.fliplr: 0.5 -> 0.0
```

При профиле `default` ключ `model.train.augmentation` должен оставаться `null`:

```text
ValueError: model.train.augmentation requires transforms=albumentations
```

## Файл пайплайна

Файл — JSON, который сохраняет `albumentations.save(transform, path)` для `A.Compose`. Готовые примеры лежат в репозитории в `examples/augmentation/` (`flip.json`, `mosaic.json`).

Небольшой рабочий пример:

```json
{
  "__version__": "2.0.8",
  "transform": {
    "__class_fullname__": "Compose",
    "p": 1.0,
    "transforms": [
      {"__class_fullname__": "HorizontalFlip", "p": 0.5},
      {"__class_fullname__": "RandomBrightnessContrast", "p": 0.2}
    ],
    "bbox_params": {"format": "pascal_voc", "label_fields": ["class_labels"]}
  }
}
```

Правила файла:

- На верхнем уровне только `__version__` и `transform`.
- `transform` — корневой `Compose`. Вложенные преобразования описываются в `transforms`.
- Разрешены только встроенные классы Albumentations. Классы из других модулей запрещены.
- Запрещены `Normalize`, `ToTensorV2`, `ToTensor3D`, `ToFloat`, `FromFloat` и `Lambda`: нормализацию и перевод в тензор делает само семейство моделей.
- Каждое преобразование должно работать с изображением, а пространственное — ещё и с рамками (bounding box). `keypoint_params` и `additional_targets` не поддерживаются.
- `num_output_channels`, если задан, должен быть `3`: модели получают RGB.
- Параметры конструктора проверяются: неизвестный параметр или недопустимое значение — ошибка. `p` — от 0 до 1.
- `bbox_params` задаётся только у корневого `Compose`. `format` — `pascal_voc` (по умолчанию), `coco`, `yolo` или `albumentations`. `label_fields` — ровно одно поле меток классов; если не задано, используется `class_labels`. Имена `image`, `bboxes`, `mask`, `keypoints` и другие служебные имена Albumentations для него не подходят.
- `Mosaic` допускается только первым преобразованием верхнего уровня.

Пайплайн проверяется при запуске, до создания задачи ClearML (task), поэтому `--cfg job` ошибок в файле не находит. Ошибки указывают путь к узлу:

```text
ValueError: transform.transforms[0]: Normalize conflicts with backend preprocessing or executable-code restrictions; remove it from the training augmentation pipeline
ValueError: Cannot read augmentation JSON augmentation/flip.json: [Errno 2] No such file or directory: 'augmentation/flip.json'
```

## Снимок пайплайна

При запуске CY читает файл и записывает в `transforms.snapshot` снимок пайплайна ([pipeline snapshot](../../GLOSSARY.md#pipeline-snapshot)): его содержимое (`pipeline`), SHA-256 канонического JSON (`sha256`) и путь к файлу (`source`). Если в конфигурации уже есть `transforms.snapshot`, CY использует его и файл не читает, даже если файла уже нет; при этом `pipeline_file` можно не задавать. Если `pipeline_file` отличается от `source` снимка, снимок отбрасывается и файл читается заново. Снимок с несовпадающим хешем отклоняется:

```text
Value error, Transform snapshot sha256 does not match its pipeline content
```

## См. также

- [Группа `model`](model.md)
- [Группа `ultralytics`](ultralytics.md)
- [Как устроена конфигурация](README.md)
- [`cy-train`](../commands/cy-train.md)
