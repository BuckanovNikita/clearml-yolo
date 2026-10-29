# ONNX и TensorRT: экспорт, сборка и проверка

## Предварительные условия

Экспорт поддерживается для шести зарегистрированных пресетов **Faster R-CNN**.
Другие семейства могут обучаться и оцениваться, но не приобретают поддержку
`cy-export` от одной замены `model=`. Нужен реальный чекпойнт с проверенным
descriptor, словарём классов и preprocessing. ONNX-зависимости входят в CY;
TensorRT и совместимый CUDA runtime устанавливаются отдельно.

Для CPU/FP32 ONNX GPU не нужен. Сборка engine и его проверка требуют GPU,
поддерживаемых библиотек и достаточной памяти. Приведённые команды — интерфейс,
а не свидетельство прохождения всех preset/precision/target проверок.
Совместимость с целевым CUDA 11.8 здесь не подтверждена.

## Пример

### Экспортировать ONNX на CPU

```bash
cy-init-config export-config --command cy-export --model fasterrcnn/resnet50_fpn
cy-export model=fasterrcnn/resnet50_fpn weights=./best.pth \
  export.operation=onnx export.device=cpu export.precision=fp32 \
  output_dir=./exported/onnx clearml.project_name=cy-tutorial \
  clearml.task_name=export-onnx 'clearml.tags=[tutorial,export]'
```

[export.operation](/#field=export.operation) разделяет три операции. При `onnx`
разрешены только `device=cpu` и `precision=fp32`. Настройки confidence, NMS IoU и
max detections из [model.predict](/#field=model.predict) встраиваются в граф;
для их изменения требуется новый экспорт. Исходный native-чекпойнт не изменяется.

### Собрать engine

```bash
cy-export model=fasterrcnn/resnet50_fpn export.operation=build \
  export.onnx=./exported/onnx/model.onnx export.device=0 export.precision=fp32 \
  output_dir=./exported/engine-fp32 clearml.project_name=cy-tutorial \
  clearml.task_name=build-engine 'clearml.tags=[tutorial,export]'
```

Повторите с `export.precision=fp16` и новым output directory для FP16-варианта.
Внешние image/detection tensors остаются float32; FP16 меняет разрешённые внутренние
операции engine. [export.workspace_gib](/#field=export.workspace_gib) управляет
builder workspace, а не верхним пределом памяти инференса. Некоторым backbone
нужен больший workspace; ошибка сборки не означает, что другой режим проверен.

Храните `model.onnx` вместе с `model.onnx.json`, `model.engine` вместе с
`model.engine.json`. [export.metadata](/#field=export.metadata) может указать
явный sidecar. Они связывают хеши, source checkpoint, классы, preprocessing,
профили, runtime и plugin identities. Не редактируйте metadata для обхода mismatch.

### Проверить engine на размеченном наборе

```bash
cy-export model=fasterrcnn/resnet50_fpn export.operation=verify \
  weights=./best.pth export.engine=./exported/engine-fp32/model.engine \
  ground_truth=./tutorial-data/ground_truth.csv export.split=test \
  export.device=0 export.precision=fp32 output_dir=./exported/verification \
  clearml.project_name=cy-tutorial clearml.task_name=verify-engine \
  'clearml.tags=[tutorial,export]'
```

Для meaningful quality acceptance нужен репрезентативный размеченный корпус и
native-модель с ненулевым качеством. Маленький набор из первого урока удобен для
проверки выполнения, но не доказывает допустимую потерю production accuracy.
Проверяйте одинаковые байты checkpoint/corpus, preprocessing и evaluator source.

### Самостоятельный inference runner

Runner может работать в отдельно подготовленном окружении без Torch и ClearML.
Нужны соответствующие версии CY source, NumPy/Pydantic, TensorRT/CUDA и декодер
изображений. Не смешивайте такое узкое deployment-окружение с обычной установкой
для обучения или `cy-export verify`.

```python
from pathlib import Path

import numpy as np
from PIL import Image

from clearml_yolo.adapters.export.metadata import read_metadata
from clearml_yolo.adapters.export.preprocessing import postprocess, preprocess
from clearml_yolo.adapters.export.runtime import TensorRTRunner

metadata = read_metadata(Path("exported/engine-fp32/model.engine.json"))
rgb = np.asarray(Image.open("tutorial-data/images/test-0.png").convert("RGB"))
images, sizes = preprocess(
    [rgb],
    (608, 960),
    mean=metadata.descriptor.preprocessing.mean,
    std=metadata.descriptor.preprocessing.std,
)
runner = TensorRTRunner(Path("exported/engine-fp32/model.engine"), metadata, device=0)
detections, counts = runner(images, sizes)
results = postprocess(
    detections,
    counts,
    [rgb.shape[:2]],
    sizes,
    class_count=len(metadata.descriptor.class_names),
)
print(results)
```

Объект runner используйте последовательно; один execution context не предназначен
для одновременных вызовов. Конструирование загружает TensorRT и создаёт CUDA
resources, поэтому выбирайте разрешённое устройство до этого момента. Сам runner
не создаёт ClearML task и не подменяет engine native-моделью при ошибке.

### Формы и динамические профили

Вход `images` — float32 NCHW; `image_sizes` — int64 `[B,2]` с valid resized H/W.
Выход `detections` — float32 `[B,max_det,6]`, а `counts` задаёт действительное число
строк. Нулевые хвосты исключаются. Внутри engine foreground IDs начинаются с 1;
`postprocess` переводит их в нулевую индексацию словаря.

| Профиль | Минимум NCHW | Оптимум | Максимум |
| --- | --- | --- | --- |
| Полные кадры | `[1,3,608,960]` | `[2,3,608,960]` | `[4,3,736,960]` |
| Полосы | `[1,3,128,1536]` | `[2,3,256,1920]` | `[4,3,256,1920]` |

Форма целиком должна попадать в один профиль, H/W кратны 32. Например,
`[3,3,192,1728]` допустима для полос, а `[1,3,736,1920]` смешивает два профиля
и отклоняется. Не считайте диапазон декларации доказательством динамичности всех
операций: нужны реальные прогоны крайних/внутренних размеров и переходов профилей.

## Ожидаемый результат

ONNX operation создаёт граф и metadata, build — engine и metadata, verify —
измеренные результаты сопоставления с native-моделью. Standalone runner возвращает
детекции в координатах исходных изображений. Версии TensorRT/CUDA и engine identity
должны соответствовать metadata; изменение окружения может потребовать пересборки.

## Частые ошибки

- ONNX запрошен на GPU/FP16: используйте CPU/FP32 и выберите FP16 на этапе build.
- `build` без ONNX или `verify` без weights/engine/ground truth: заполните все входы.
- Sidecar отсутствует/хеш неверен: восстановите исходную пару artifact + metadata.
- Форма пересекает профили: выберите один поддерживаемый canvas/batch.
- Недостаточно workspace или несовместим TensorRT: проверьте действительное
  окружение и builder diagnostics; успешный ONNX не доказывает сборку engine.
- Пустые предсказания: проверьте counts, словарь и качество модели; не удаляйте
  пустые изображения из evaluation population.

## Проверка

Проверьте код каждой операции, реальные файлы и хеши, загрузите опубликованные
артефакты. Выполните native-versus-engine проверку на неизменном размеченном
корпусе и отдельно standalone execution без Torch/ClearML. Для каждого целевого
preset/precision проверьте все нужные batch/shape/profile transitions, пустые и
плотные сцены, rejection cases и accuracy loss. Заявляйте только реально
проверенные устройства и runtime-версии.
