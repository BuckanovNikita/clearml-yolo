# cy-batch-estimate

`cy-batch-estimate` измеряет на GPU, какой наибольший batch size помещается в память при обучении (training) каждой модели на одной GPU, и записывает результат в [таблицу batch size](../formats/batch-table.md) ([batch size table](../../GLOSSARY.md#batch-size-table)). Обучение берёт batch из этой таблицы, когда batch задан как `null`. Запускайте команду на GPU-хосте один раз для каждого размера изображения, с которым будете обучать. Режим `--list` показывает покрытие таблицы и не требует GPU.

## Примеры

```bash
cy-batch-estimate --list
```

Показывает, для каких моделей в таблице уже есть записи.

```bash
cy-batch-estimate --imgsz 640 --models yolo11n,rfdetr/small
```

Заново измеряет две модели на всех видимых GPU для размера 640.

```bash
cy-batch-estimate --imgsz 640 --devices 0,1 --gpu-counts 1,2
```

Заполняет пропуски таблицы для всех моделей на GPU 0 и 1 и печатает рекомендации для одной и двух GPU.

## Синтаксис и аргументы

```text
cy-batch-estimate [-h] [--list] [--imgsz IMGSZ] [--objects-per-image OBJECTS_PER_IMAGE]
                  [--models MODELS] [--devices DEVICES] [--gpu-counts GPU_COUNTS]
                  [--jobs JOBS] [--force] [--refresh] [--memory-budget MEMORY_BUDGET]
                  [--search-limit SEARCH_LIMIT] [--trial-timeout TRIAL_TIMEOUT]
```

| Аргумент | По умолчанию | Описание |
| --- | --- | --- |
| `--list` | выключен | Показать покрытие таблицы и известные неудачи, не измеряя. Совместим только с `--models`. |
| `--imgsz` | — | Сторона квадратного изображения для измерения, целое больше 0. Обязателен без `--list`. |
| `--models` | все модели | Модели через запятую: `backend/preset` или для Ultralytics короткое имя (`yolo11n`, `yolo11n.pt`, `ultralytics/yolo11n`). С этим флагом выбранные модели измеряются заново, даже если запись есть. Без него заполняются только пропуски таблицы. |
| `--devices` | все видимые GPU | Логические индексы видимых CUDA-устройств через запятую, уникальные и неотрицательные. Порядок задаёт «первые N GPU» для `--gpu-counts`. |
| `--gpu-counts` | от 1 до числа выбранных GPU | Для каких количеств первых выбранных GPU печатать рекомендацию. Каждое значение от 1 до числа выбранных GPU. Отдельных измерений не запускает. |
| `--jobs` | число выбранных GPU | Сколько измерений идёт одновременно, целое больше 0. Значение больше числа выбранных GPU уменьшается до этого числа. |
| `--force` | выключен | Разрешить измерение на GPU с ненулевой загрузкой, у которой нет чужих вычислительных процессов. Такие записи помечаются `forced/background-sensitive`. |
| `--refresh` | выключен | Измерить заново все выбранные сочетания, игнорируя таблицу и прежние результаты. |
| `--memory-budget` | `0.9` | Доля полной памяти GPU, которую может занять измерение: больше 0 и не больше 1. |
| `--search-limit` | `1024` | Наибольший batch size на одну GPU, который пробует поиск, целое больше 0. Рекомендации для нескольких GPU могут его превышать. |
| `--trial-timeout` | `300` | Лимит в секундах на одну пробу, больше 0. |
| `--objects-per-image` | `300` | Число синтетических объектов на изображение, целое больше 0. |
| `-h`, `--help` | — | Показать справку и выйти. |

## Как это работает

### `--list`

1. Команда читает таблицу `CY_HOME/.config/clearml-yolo/batch-sizes.yaml` и результаты прежних измерений `CY_HOME/.config/clearml-yolo/batch-estimates.json` (см. [Рабочий каталог](../workspace.md) ([workspace](../../GLOSSARY.md#workspace))). Отсутствующий файл считается пустым.
2. Для каждой выбранной модели она печатает записи таблицы, подтверждённые случаи «не помещается», неудачные измерения или `not_attempted`.

GPU, CUDA и `nvidia-smi` не нужны.

### Измерение

1. Команда находит видимые GPU и их загрузку через `nvidia-smi`. Без `nvidia-smi` или для GPU в режиме MIG она останавливается.
2. Для каждой модели и каждой выбранной GPU она решает, нужно ли измерение. Без `--refresh` и `--models` сочетание пропускается, если в таблице уже есть точная запись для этой GPU, размера и модели; сохранённый удачный результат с теми же параметрами переносится в таблицу без нового измерения. Если в таблице записано подтверждённое «не помещается» для этой GPU, размера и модели, сохранённый результат не используется и сочетание измеряется заново. Одинаковые GPU (то же имя и объём памяти) измеряются один раз.
3. Каждое измерение идёт в отдельном процессе на одной GPU. Перед запуском GPU должна быть свободна: без чужих вычислительных процессов и, без `--force`, без загрузки. Занятая GPU не ждёт, если её не освободит собственное измерение команды: случай записывается как неудачный.
4. Процесс обучает модель на синтетических данных размера `--imgsz` с `--objects-per-image` объектами на изображение и ищет наибольший batch size, при котором обучение укладывается в `--memory-budget` и проходит без ошибок. Поиск увеличивает batch, пока не встретит нехватку памяти или `--search-limit`, затем сужает интервал, и в конце проверяет найденное значение отдельным свежим запуском.
5. Каждый результат сразу записывается в `batch-estimates.json`, а удачный — ещё и в таблицу. Журнал и файлы процесса лежат в `batch-cases/<идентификатор>/` внутри временного каталога ([runtime scratch directory](../../GLOSSARY.md#runtime-scratch-directory)) `CY_HOME/.tmp/cy-runtime-*/` (см. [Рабочий каталог](../workspace.md)).
6. Для каждой модели и каждого значения из `--gpu-counts` команда берёт из таблицы batch size на одну GPU для первых N выбранных GPU, выбирает наименьший и печатает его вместе с глобальным batch `N × batch`.

## Результат

Файлы: [таблица batch size](../formats/batch-table.md) `batch-sizes.yaml` и `batch-estimates.json` в `CY_HOME/.config/clearml-yolo/`.

Вывод `--list` (поля через табуляцию):

```text
Editable table coverage across recorded GPUs and image sizes; no CUDA required.
MODEL	STATUS	REASON	CONTEXT
ultralytics/yolo11n	not_attempted	No table entry or known capacity failure	-
rfdetr/small	not_attempted	No table entry or known capacity failure	-
Summary: selected=2	covered=0	missing=2
Results: /workspace/project/.config/clearml-yolo/batch-sizes.yaml
```

| `STATUS` | Значение |
| --- | --- |
| `covered` | В таблице есть запись; `CONTEXT` — GPU, `imgsz`, `per_gpu_batch` и происхождение записи. |
| `no_capacity` | Подтверждено, что модель не помещается на эту GPU даже с batch 1. |
| `failed` | Измерение не удалось; `REASON` — причина. |
| `not_attempted` | Ни записи, ни известной неудачи. |

Вывод измерения (поля через табуляцию):

```text
ultralytics/yolo11n	gpus=2	global_batch=128	per_gpu_batch=64	table	digest=<хэш>	sources=<GPU>: 64 (measured)
Results: /workspace/project/.config/clearml-yolo/batch-sizes.yaml; evidence: /workspace/project/.config/clearml-yolo/batch-estimates.json
```

К строке рекомендации добавляется `cached`, если новых измерений для неё не было, и `forced/background-sensitive`, если запись получена с `--force`. Неудачное измерение печатается строкой `<модель>	gpus=1	<статус>	<причина>`; результат, который ограничен численной ошибкой, а не памятью, — строкой `Measurement: <модель>	numerically_limited	<причина>`. Если для GPU используется запись другой GPU, в stderr выводится `Warning: <GPU> uses fallback from <GPU>; run cy-batch-estimate --imgsz <N> --models <модель> --devices <current-device> to measure this GPU.`

### Коды завершения

| Код | Значение |
| --- | --- |
| `0` | `--list` выполнен или все измерения удачны и рекомендации получены. |
| `1` | Хотя бы одно измерение не удалось или для какой-то рекомендации нет записи (`unavailable`). |
| `2` | Ошибка аргументов, нет GPU-телеметрии, недопустимые `--devices` или `--gpu-counts`, испорченный файл таблицы или результатов. |

## Частые ошибки

```text
cy-batch-estimate: error: --imgsz is required unless --list is used
```

Добавьте `--imgsz` или `--list`.

```text
cy-batch-estimate: error: --imgsz cannot be used with --list
```

С `--list` допустим только `--models`. Та же ошибка для любого флага измерения, даже со значением по умолчанию.

```text
cy-batch-estimate: error: Unknown estimator model 'bogus'
cy-batch-estimate: error: Model selection contains duplicate 'ultralytics/yolo11n'
```

Имя модели не из списка `--list` или одна модель указана дважды (например, `yolo11n` и `ultralytics/yolo11n`).

```text
cy-batch-estimate: error: argument --devices: Use comma-separated integer values
cy-batch-estimate: error: argument --devices: Values must be unique nonnegative integers
```

Те же сообщения выдаёт `--gpu-counts`.

```text
cy-batch-estimate: error: 1 validation error for _Options
imgsz
  Input should be greater than 0 [type=greater_than, input_value=0, input_type=int]
```

Число вне допустимого диапазона. Вместо `imgsz` может стоять `jobs`. Для `--memory-budget`, `--search-limit`, `--trial-timeout` и `--objects-per-image` первая строка называет другую внутреннюю модель проверки, а поле — `memory_fraction`, `max_global_batch`, `trial_timeout_seconds` или `objects_per_image` соответственно.

```text
cy-batch-estimate: error: Batch estimation requires nvidia-smi GPU telemetry
```

На хосте нет `nvidia-smi`. Измерение возможно только на GPU-хосте с драйвером NVIDIA.

```text
cy-batch-estimate: error: No visible CUDA GPUs; batch estimation requires idle GPUs
```

На хосте нет видимых GPU (например, пустой `CUDA_VISIBLE_DEVICES`).

```text
cy-batch-estimate: error: --devices must select GPUs inside the inherited CUDA visibility
cy-batch-estimate: error: --gpu-counts must be between 1 and the selected device count
```

Индекс GPU не входит в видимые (учитывается `CUDA_VISIBLE_DEVICES`) или количество GPU больше выбранного.

```text
cy-batch-estimate: error: Visible CUDA device lacks whole-GPU telemetry (MIG unsupported)
```

GPU в режиме MIG не поддерживаются.

`No idle selected GPU for <GPU>: GPU <N> is busy or its telemetry is unavailable` в строке неудачного измерения означает, что GPU занята. Дождитесь освобождения или, если загрузка не связана с чужими процессами, добавьте `--force`.

`Invalid batch size table <путь>; repair it before retrying; file preserved` и `Invalid batch estimate catalogue <путь>; preserve or repair this file before retrying. Existing evidence has not been overwritten.` означают, что файл испорчен. Исправьте таблицу по описанию [формата](../formats/batch-table.md).

## См. также

- [Таблица batch size](../formats/batch-table.md)
- [Рабочий каталог](../workspace.md)
- [Ultralytics](../configuration/ultralytics.md) и [Модель](../configuration/model.md): ключи batch при обучении
- [Сценарии](../scenarios.md)
