# Обучение: семейства моделей, веса и память

## Предварительные условия

Подготовьте CSV и ClearML по [первому уроку](quickstart.html). Для обучения нужны
непустые `train` и `val`; состав классов берётся из CSV. Выберите доступное устройство:
прямая команда не ждёт свободного GPU. Все примеры ниже создают реальные задачи.

## Пример

### Выбор семейства и архитектуры

[model](/#field=model) выбирает зарегистрированное семейство/пресет. Произвольное
имя timm и исходный DEIM не являются допустимыми пресетами CY.

| Семейство | Значения `model=` | Размер по умолчанию |
| --- | --- | --- |
| YOLO | `ultralytics` | 960 |
| DEIMv2 | `deimv2/s`, `deimv2/m`, `deimv2/l`, `deimv2/x` | 640 |
| RF-DETR | `rfdetr/nano`, `rfdetr/small`, `rfdetr/medium`, `rfdetr/large` | 384, 512, 576, 704 |
| Faster R-CNN | `fasterrcnn/resnet50_fpn`, `fasterrcnn/resnet101_fpn`, `fasterrcnn/convnext_tiny`, `fasterrcnn/swin_tiny`, `fasterrcnn/dinov2_small`, `fasterrcnn/dinov3_small` | 800 |
| FCOS | `fcos/resnet50_fpn`, `fcos/resnet101_fpn`, `fcos/convnext_tiny`, `fcos/swin_tiny`, `fcos/dinov2_small`, `fcos/dinov3_small` | 800 |

YOLO задаёт файл архитектуры или веса через
[ultralytics.model](/#field=ultralytics.model). Остальные семейства используют
собственный `model.train`; не переносите туда ключи Ultralytics без проверки справочника.

```bash
cy-train ground_truth=./tutorial-data/ground_truth.csv ultralytics.model=yolo11n.pt \
  ultralytics.epochs=1 ultralytics.batch=2 ultralytics.imgsz=128 ultralytics.device=cpu \
  ultralytics.compile=false clearml.project_name=cy-tutorial \
  clearml.task_name=train-yolo 'clearml.tags=[tutorial,training]'

cy-train model=deimv2/s ground_truth=./tutorial-data/ground_truth.csv \
  model.train.epochs=1 model.train.batch=2 model.train.device=0 \
  clearml.project_name=cy-tutorial clearml.task_name=train-deimv2 'clearml.tags=[tutorial,training]'

cy-train model=rfdetr/nano ground_truth=./tutorial-data/ground_truth.csv \
  model.train.epochs=1 model.train.batch=2 model.train.device=0 \
  clearml.project_name=cy-tutorial clearml.task_name=train-rfdetr 'clearml.tags=[tutorial,training]'

cy-train model=fasterrcnn/resnet50_fpn ground_truth=./tutorial-data/ground_truth.csv \
  model.train.epochs=1 model.train.batch=2 model.train.device=0 \
  clearml.project_name=cy-tutorial clearml.task_name=train-fasterrcnn 'clearml.tags=[tutorial,training]'

cy-train model=fcos/resnet50_fpn ground_truth=./tutorial-data/ground_truth.csv \
  model.train.epochs=1 model.train.batch=2 model.train.device=0 \
  clearml.project_name=cy-tutorial clearml.task_name=train-fcos 'clearml.tags=[tutorial,training]'
```

Для CPU у других семейств используйте `model.train.device=cpu`. При необходимости
задайте поддерживаемую выбранным backend точность. CPU не гарантирует малое время
обучения. RF-DETR требует квадратный размер, кратный 32. Для других backend
ограничения размера и preprocessing смотрите в полях выбранного пресета.

### Дообучение и pretrained

Для нового обучения из собственного YOLO-чекпойнта замените `ultralytics.model`
на путь к `best.pt`. Для других семейств добавьте
[model.train.weights](/#field=model.train.weights):

```bash
cy-train model=fasterrcnn/resnet50_fpn ground_truth=./tutorial-data/ground_truth.csv \
  model.train.weights=./previous/best.pth model.train.epochs=5 model.train.device=0 \
  clearml.project_name=cy-tutorial clearml.task_name=finetune 'clearml.tags=[tutorial,finetune]'
```

Путь должен указывать на фактически полученный чекпойнт выбранной архитектуры.
`resume` в CSV-режиме не поддерживается: это новый запуск с заданными начальными
весами. Не смешивайте веса детектора с весами только backbone.

По умолчанию запрашивается pretrained-инициализация. При недоступных весах команда
ошибается, а не переключается незаметно на случайную модель. FCOS использует
pretrained backbone и новую голову; foreground-метки начинаются с нуля. Внутренний
background-индекс Faster R-CNN не меняет строковые классы CSV. Для DINOv3 могут
понадобиться разрешённый доступ к upstream и подготовленные локальные веса.
DEIMv2 при выполнении готовит исходники утверждённой ревизии, если
[model.source_dir](/#field=model.source_dir) не задан явно.

Для YOLO архитектура YAML и pretrained — разные решения: путь `.yaml` выбирает
архитектуру, а `ultralytics.pretrained` задаёт инициализацию согласно нативному
контракту. Не выводите наличие pretrained-весов из одного имени архитектуры.
Закрытая сеть и подготовка всех поддерживаемых весов разобраны в
[операционном уроке](operations.html).

### Batch и недостаток памяти

Числовой [ultralytics.batch](/#field=ultralytics.batch) или
[model.train.batch](/#field=model.train.batch) задаёт batch обучения.
Явное `null` использует совместимую сохранённую оценку, а не запускает измерение
автоматически. Для подготовки оценки на свободном GPU:

```bash
cy-batch-estimate --imgsz 512 --models rfdetr/small --devices 0
```

Это реальные локальные CUDA-пробы, без задачи ClearML. По умолчанию синтетическая
нагрузка содержит 150 классов и 300 объектов на изображение, бюджет памяти 90%,
предел поиска 1024 изображения **на GPU**, timeout пробы 300 секунд. Настройте
нагрузку под свою задачу; оценка зависит от модели, размера, точности, компиляции,
GPU и версий. Для выбранных нескольких GPU выдаются рекомендации для первых N
устройств; измерение на одном GPU и экстраполяция общего batch — разные виды данных.
Экстраполяция не доказывает работоспособность физического DDP.

Новые поиски начинают с batch 1 и 2, затем выбирают кандидатов по измеренному росту
памяти. При отсутствии положительного роста используется удвоение; после реального
OOM или превышения бюджета граница уточняется бинарным поиском. Каждая проба
по-прежнему выполняет пять прогревочных и десять измеряемых обновлений оптимизатора,
все необходимые пути оптимизаторов и валидацию. Выбранный batch подтверждается
повторной полной пробой в свежем процессе.

Независимые случаи модель/тип GPU выполняются параллельно, по одному полному поиску
на свободном выбранном GPU. Каждый случай закреплён за своим устройством; кандидаты
внутри него проверяются последовательно. `--jobs N` задаёт положительный предел
параллельности, `--jobs 1` включает последовательное выполнение; без параметра
используются доступные выбранные GPU. Одинаковые GPU не дублируют один случай.

```bash
cy-batch-estimate --imgsz 512 --models rfdetr/small,fcos/resnet50_fpn --devices 0,1 \
  --jobs 2 --gpu-counts 1,2 --classes 10 --objects-per-image 50 --memory-budget 0.8
```

Каталог `CY_HOME/.config/clearml-yolo/batch-estimates.json` читается в схемах 1/2/3;
сохранение пишет схему 3 с явной стратегией поиска. Старые записи без стратегии
проверяются по прежнему алгоритму с сохранением ключей; чтение не переписывает файл.
Перед использованием нового каталога обновите старый CY. Совместимая готовая оценка
не требует свободного GPU. `--refresh` делает старую запись непригодной перед новым
запуском; промежуточные результаты остаются `failed` с null batch до независимого
подтверждения, проверки результата владельцем и очистки дочерних процессов.
Отмена затрагивает только собственные процессы и сохраняет завершённые случаи.

Если после успешного кандидата возникает nonfinite, одна полная независимая проверка
последнего успешного batch может дать `numerically_limited`. Причина сохраняется,
максимум памяти не установлен. Другой порядок кандидатов может изменить этот batch;
ошибка повторной проверки оставляет результат непригодным.

После ошибки памяти уменьшите batch и при необходимости размер, проверьте другие
процессы и соответствие точности/компиляции оценке. Не завершайте чужие процессы.
Повторите совместимую оценку либо задайте явный числовой batch; для обновления
измерений служит `--refresh`. DDP и accumulation разобраны в
[уроке конфигурации](configuration.html).

## Ожидаемый результат

Каждая команда обучения создаёт собственную задачу ClearML и один лучший Output
Model. Чекпойнт нативного backend сохраняет описание модели, классы и preprocessing;
идентичность обучающей задачи хранится отдельно. Оценщик batch печатает measured
или extrapolated рекомендации, статус и происхождение измерений.

## Частые ошибки

- `model.train.*` не влияет на YOLO: используйте активную группу `ultralytics.*`.
- Несовместимые checkpoint/пресет: выберите соответствующую архитектуру и сохраните
  descriptor/sidecar. Совпадающее расширение файла недостаточно.
- RF-DETR отвергает размер: используйте квадрат, кратный 32.
- `batch=null` без совместимой оценки: измерьте нужную конфигурацию или задайте число.
- Ошибка pretrained: проверьте доступ и локальный путь; не подменяйте модель.

## Проверка

Сравните выбранные модель, веса, batch, устройство и размер с `Configuration / run`
и нативными параметрами. Убедитесь в завершении эпох и наличии лучшего чекпойнта;
затем выполните [отдельную валидацию](evaluation.html). Поддержка пресета в
справочнике не заменяет его реальный запуск на вашем устройстве; ограничения
физического multi-GPU и deployment-проверок остаются отдельными.
