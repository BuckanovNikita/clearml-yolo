# clearml-yolo

Обучает детекторы по CSV с разметкой. Веса, метрики и отчёты сохраняются в ClearML.
Можно запустить только обучение или весь эксперимент: обучение, инференс, подбор порогов,
оценку и сравнение с прежней моделью.

Поддерживаются YOLO (Ultralytics), DEIMv2, RF-DETR, Faster R-CNN и FCOS.

## Установка

Что нужно:

- Linux с поддержкой pidfd, Python `>=3.12.13,<3.14` и установленный `uv`;
- настроенный доступ к ClearML с хранилищем артефактов: без ClearML команды
  обучения и оценки не работают;
- для установки из исходников — исходники `digital-metrics` и `report-generator`
  утверждённых ревизий. Ревизии перечислены
  в [DOCS.md](DOCS.md#installation-and-dependencies).

В PyPI пакета нет. Ниже — установка из исходников. Про установку по Git-ссылке см.
[DOCS.md](DOCS.md#installation-and-dependencies). Скопируйте обе зависимости
в `external/digital-metrics` и `external/report-generator`. Затем выполните в корне
репозитория:

```bash
uvx --from go-task-bin task local-deps   # собирает external/wheelhouse и создаёт uv.toml
uv sync --locked --dev
uv run --locked cy --help
source .venv/bin/activate
```

Зависимости всех моделей и ONNX-экспорта ставятся сразу, extras нет. Очередь заданий —
отдельный пакет `cy-queue` (см. раздел «Очередь»). Требования к окружению — в разделе
«Совместимость и зависимости».

## Первое обучение

Подготовьте CSV с разметкой: одна строка — один объект, координаты углов bbox
в пикселях.

```csv
image_name,image_path,instance_label,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br,split
train.jpg,images/train.jpg,helmet,10,20,100,120,train
val.jpg,images/val.jpg,helmet,10,20,100,120,val
test.jpg,images/test.jpg,helmet,10,20,100,120,test
```

Запустите обучение. Проект, имя Task и теги ClearML укажите явно:

```bash
cy-train ground_truth=./ground_truth.csv ultralytics.model=yolo11n.pt ultralytics.device=0 \
  clearml.project_name=detection clearml.task_name=yolo11n-train 'clearml.tags=[yolo,training]'
```

Для остальных семейств модель выбирается через `model=`, а параметры обучения
начинаются с `model.train.`:

```bash
cy-train model=rfdetr/small ground_truth=./ground_truth.csv model.train.device=0 \
  clearml.project_name=detection clearml.task_name=rfdetr-small-train 'clearml.tags=[rfdetr,training]'
```

Команда стартует сразу и не ждёт, пока освободится GPU. Для CPU замените `0` на `cpu`:
`ultralytics.device=cpu` или `model.train.device=cpu`.

Ход обучения смотрите в ClearML Task на вкладках `Console`, `Scalars` и `Plots`.
Лучшие веса — в `Output Models`. Локальные файлы лежат
в `runs/<проект>/<задача>-<task-id>/`. Имя файла лучших весов зависит от семейства.
Для YOLO это `weights/best.pt`, и его точный путь пишется в лог.

## Команды и конфигурация

`cy` запускает весь pipeline:

- обучение;
- инференс;
- подбор порогов на `val`;
- метрики;
- сравнение с baseline на `test`;
- отчёты и публикацию в FiftyOne.

Отдельные шаги запускают `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-compare`,
`cy-report`, `cy-ground-truth` и `cy-export`. Каждая команда собирает конфиг из
встроенных значений, необязательного каталога с YAML и параметров командной строки.
Конфиг проверяется до начала работы и записывается в ClearML Task команды. По нему
ClearML Agent может повторить запуск.

```bash
cy ground_truth=./ground_truth.csv ultralytics.model=yolo11n.pt \
  ultralytics.epochs=50 ultralytics.device=0 ultralytics_predict.device=0 \
  run_dir=./runs/experiment-01 clearml.project_name=detection \
  clearml.task_name=yolo11n-experiment 'clearml.tags=[yolo,experiment]'
```

Устройства для обучения и инференса задаются отдельно. У остальных семейств это
`model.train.device` и `model.predict.device`. Отдельный шаг `cy` можно выключить
параметром `skip_<шаг>=true`, например `skip_compare=true`.

Для каждого эксперимента берите новый `run_dir`. Существующий каталог не очищается,
и файлы прошлого запуска остаются рядом с новыми.

Когда параметров много, сохраните их в файлы: `cy-init-config cy-config`. Команда
создаст:

- `cy-config/cy.yaml` с общими настройками (список `defaults` в нём не трогайте);
- файлы с параметрами обучения и инференса, например
  `cy-config/ultralytics/default.yaml` — без обёртки `ultralytics:`.

Впишите в `cy-config/cy.yaml` путь `ground_truth`, а также проект, имя Task и теги
ClearML (пример — в разделе «Публикация в ClearML»). Без `ground_truth` команда
не запустится.

Запуск: `cy --config-dir cy-config --config-name cy`. Параметры командной строки
переопределяют файлы. `--cfg job --resolve` показывает итоговый конфиг. Для другой
команды или семейства добавьте `--command` и `--model` (пример — в разделе «Семейства
моделей»). `cy-init-config` не перезаписывает существующие файлы, если не указан
`--force`.

Sweep — запуск нескольких вариантов параметров — включается флагом `-m`, например
`cy --config-dir cy-config --config-name cy -m ultralytics.epochs=10,20`. Варианты
выполняются по очереди. Каждый Task из одного sweep получает общий тег с датой
и случайной фразой — по нему их легко найти в ClearML.

Task можно выполнить через ClearML Agent. Настройки берутся из конфига `run`,
сохранённого в Task, так что повторять аргументы командной строки не нужно. Зависимости
ставит ваше окружение Agent, GPU он выбирает через `CUDA_VISIBLE_DEVICES`.

Запускайте команды из Git-репозитория. Вне репозитория команда работает,
но предупреждает об этом.

Если команда пишет про неизвестный параметр, проверьте префикс группы
(`ultralytics.`, `model.train.`) и сверьтесь со свежим YAML из `cy-init-config`.

Подробнее:
[DOCS.md](DOCS.md#commands-and-configuration).

## Данные и разметка

Разметка для всех команд — один CSV. В нём строка на каждый объект. Изображение без
объектов — одна строка с пустыми классом и координатами. В каждой строке есть имя и путь
изображения, класс, углы bbox в пикселях и split.

`ground_truth` принимает путь к CSV или ссылку на финализированный ClearML Dataset.
`cy-ground-truth` переводит в такой CSV разметку YOLO. Перед обучением CSV проверяется.
Подготовленная копия данных кэшируется и переиспользуется, пока не меняются CSV и пути
к изображениям.

```bash
cy-train 'ground_truth={dataset_id:DATASET_ID}' ultralytics.model=yolo11n.pt ultralytics.device=0 \
  clearml.project_name=detection clearml.task_name=dataset-train 'clearml.tags=[training]'

cy-train 'ground_truth={project_name:annotations,name:ground-truth,version:"1.2.0"}' \
  ultralytics.model=yolo11n.pt ultralytics.device=0 \
  clearml.project_name=detection clearml.task_name=versioned-train 'clearml.tags=[training]'
```

В ClearML Dataset должен лежать один файл `dataset.csv`. Изображения в Dataset не входят:
пути из CSV должны быть доступны на машине, где идёт обучение. Без `version` каждый
новый запуск берёт версию, которую выберет ClearML, и она может оказаться другой.

Правила для CSV:

- Несколько объектов на изображении — несколько строк с одним и тем же изображением.
  Изображение без объектов — одна строка с пустыми классом и координатами.
- `image_name` совпадает с именем файла. Относительный `image_path` считается
  от каталога, где лежит CSV.
- Какой split у каждого изображения — `train`, `val` или `test`, — решаете вы.
  `cy-train` нужны `train` и `val`, полному `cy` — ещё и `test`.
- Имена классов читаются буквально: `NA`, `None`, `nan` и числа остаются именами
  классов, а не пропусками.
- Некорректные bbox отбрасываются с сообщением. Если в `train` не осталось ни одного
  bbox, обучение не начнётся.

Разметку YOLO (`data.yaml` и изображения) переводит в CSV `cy-ground-truth`, например
`cy-ground-truth data_yaml=./dataset/data.yaml output=./converted/ground_truth.csv
test_fraction=0.5 seed=0 clearml.project_name=detection
clearml.task_name=convert-ground-truth 'clearml.tags=[conversion]'`. Если в исходной
разметке нет `test`, под него уходит часть `val` (`test_fraction`, `seed`). Проверьте,
как разбились данные, перед обучением.

Если не найдены изображения или split, проверьте пути относительно CSV и наличие
`train` и `val`, а для `cy` — ещё и `test`.

Подробнее:
[DOCS.md](DOCS.md#datasets-and-ground-truth).

## Обучение

Обучение превращает проверенный CSV в лучший чекпойнт выбранного семейства. `cy-train`
запускает только обучение, `cy` — обучение как первый шаг pipeline. Команда сама:

- готовит данные;
- при необходимости берёт batch size из таблицы;
- запускает процессы обучения на указанных устройствах и следит за ними;
- сохраняет лучший чекпойнт для инференса и публикации.

```bash
cy --config-dir cy-config --config-name cy 'ultralytics.device=[0,1]' ultralytics_predict.device=0
```

Параметры YOLO начинаются с `ultralytics.`, остальных семейств — с `model.train.`.
Например, `ultralytics.epochs=50` или `model.train.epochs=50`. Так же задаются `batch`,
`imgsz` и `device`. Начальные веса: `ultralytics.model=./best.pt`
или `model.train.weights=./best.pth`. Это всегда начало нового обучения: продолжить
прерванное (`resume`) нельзя.

Для multi-GPU обучения перечислите устройства, как в примере. Инференс идёт на одной GPU.
У остальных семейств это `'model.train.device=[0,1]'`, и `model.train.batch` должен
делиться на число GPU.

Подробнее: [DOCS.md](DOCS.md#training).

## Семейства моделей

Все пять семейств — Ultralytics YOLO, DEIMv2, RF-DETR, Faster R-CNN и FCOS — работают
с одним форматом CSV, метрик и публикации. Семейство и пресет выбирает `model=` в `cy`,
`cy-train`, `cy-predict`, `cy-val` и `cy-compare`. `cy-export` принимает только
Faster R-CNN.

У каждого семейства свой формат чекпойнтов и свои правила обучения. В каждый чекпойнт
не-YOLO моделей, обученный CY, встроено описание модели. По нему чекпойнт можно
опознать после любого копирования.

```bash
cy-init-config train-config --command cy-train --model rfdetr/small
cy-train --config-dir train-config --config-name cy-train ground_truth=./ground_truth.csv
```

Для YOLO оставьте `model=ultralytics` (по умолчанию) и задайте модель через
`ultralytics.model`. Для остальных семейств укажите пресет, например `deimv2/s`,
`rfdetr/small`, `fasterrcnn/resnet50_fpn` или `fcos/resnet50_fpn`. Полный список
пресетов — в файле ниже.

По умолчанию обучение стартует с предобученных весов. Если их не удалось получить или
они не подходят модели, команда падает с ошибкой и не берёт случайные веса. Для
RF-DETR и DEIMv2 размер изображения должен быть квадратным и кратным 32, для DEIMv2 —
ещё и не меньше 128. Исходники и веса DEIMv2 скачиваются при первом запуске. Что делать
без доступа к GitHub — в разделе «Веса моделей».

Подробнее: [DOCS.md](DOCS.md#detector-families).

## Аугментации

Аугментации для обучения выбирает группа `transforms` в `cy-train` и `cy`. По умолчанию
каждое семейство использует свои встроенные аугментации. `transforms=albumentations`
заменяет их одним pipeline Albumentations из JSON, и он одинаково работает для всех
семейств.

Pipeline проверяется до начала обучения и сохраняется в конфиге запуска, поэтому для
повтора исходный файл не нужен. Инференс, валидация и экспорт аугментации
не используют.

```bash
cy-train model=rfdetr/nano ground_truth=./ground_truth.csv \
  transforms=albumentations transforms.pipeline_file=./augmentation.json \
  model.train.device=0 model.train.epochs=20 \
  clearml.project_name=detection clearml.task_name=rfdetr-custom \
  'clearml.tags=[rfdetr,custom-augmentation]'
```

Что стоит знать:

- JSON сохраняется из Python вызовом `A.save(pipeline, path)`. Корнем должен быть
  `A.Compose`.
- Без `bbox_params` bbox считаются в формате `pascal_voc` с полем `class_labels`.
- Свой pipeline заменяет встроенные случайные аугментации модели.
- Resize и нормализацию модель делает сама, поэтому `Normalize`, `ToFloat`
  и `ToTensorV2` в JSON отклоняются.
- Для Mosaic поставьте `A.Mosaic(...)` первым в `A.Compose`.
- Готовые примеры: `examples/augmentation/flip.json`
  и `examples/augmentation/mosaic.json`.

Подробнее: [DOCS.md](DOCS.md#augmentation).

## Предсказания и валидация

`cy-predict` прогоняет обученный чекпойнт по изображениям из CSV и сохраняет CSV
с предсказаниями для последующей оценки. `cy-val` делает инференс на каждом выбранном
split и на `val` и сразу считает метрики так же, как `cy-metrics`. Каждый CSV
с предсказаниями привязан к чекпойнту, который его создал. Поэтому его нельзя по ошибке
оценить как результат другой модели.

```bash
cy-predict weights=./best.pt ground_truth=./ground_truth.csv 'splits=[val,test]' \
  model_label=local-yolo ultralytics_predict.device=0 output=./predictions/predictions.csv \
  clearml.project_name=detection clearml.task_name=yolo-predict 'clearml.tags=[prediction]'

cy-val weights=./best.pt ground_truth=./ground_truth.csv 'splits=[val,test]' \
  model_label=local-yolo ultralytics_predict.device=0 output_dir=./validation \
  clearml.project_name=detection clearml.task_name=yolo-val 'clearml.tags=[validation]'
```

Каждая команда создаёт свой ClearML Task. В примерах — чекпойнт YOLO. Для других
семейств добавьте `model=...` и замените `ultralytics_predict.device`
на `model.predict.device`.

Что стоит знать:

- `conf` и `iou` в параметрах инференса фильтруют сами предсказания. Пороги
  для итоговой оценки подбираются отдельно.
- `model_label` — подпись модели в таблицах и отчётах. Она нужна, когда у весов или
  предсказаний нет сведений о том, откуда они взялись.
- Эти сведения лежат рядом с файлами: `<checkpoint>.identity.json` у весов
  и `<predictions.csv>.provenance.json` у предсказаний. Переносите их вместе с файлами.

Если команда требует подпись модели, передайте `model_label` или положите файлы
`.identity.json` и `.provenance.json` рядом с весами и предсказаниями.

Подробнее:
[DOCS.md](DOCS.md#prediction-and-validation).

## Метрики

Предсказания сравниваются с разметкой при порогах confidence. Пороги один раз
подбираются на `val` и дальше не меняются.

- `cy-metrics` оценивает готовый CSV с предсказаниями, без запуска модели.
- `cy-val` и `cy` делают ту же оценку после своего инференса.
- `cy-compare` оценивает так обе модели, каждую при её собственных порогах.

Для каждого split получаются метрики по классам, таблицы XLSX и построчные результаты.
В них каждый объект и каждое предсказание можно найти в исходной строке.

```bash
cy-metrics ground_truth=./ground_truth.csv predictions=./predictions/predictions.csv \
  'splits=[val,test]' model_label=local-yolo output_dir=./metrics \
  clearml.project_name=detection clearml.task_name=yolo-metrics 'clearml.tags=[metrics]'
```

`cy-val` и `cy-metrics` подбирают пороги на `val`, даже если оценивается только `test`.

Подробнее: [DOCS.md](DOCS.md#evaluation-and-metrics).

## Сравнение с baseline

Сравнение показывает, лучше ли новая модель, чем baseline. Обе модели заново делают
инференс на одних и тех же текущих изображениях. Каждая оценивается при своих порогах
с `val`.

`cy-compare` сравнивает две модели на одном split (по умолчанию `test`). `cy` сравнивает
свою модель с baseline — по умолчанию с последней моделью с тегом `prod`
(`compare.baseline_model`). Прошлые метрики и предсказания не переиспользуются.
Результат — таблица со статистическим сравнением, из которой `cy-report` делает отчёты.

```bash
cy-compare ground_truth=./ground_truth.csv baseline_model.task_id=BASELINE_TASK_ID \
  candidate_model.task_id=CANDIDATE_TASK_ID ultralytics_predict.device=0 \
  output_dir=./comparison clearml.project_name=detection \
  clearml.task_name=paired-comparison 'clearml.tags=[comparison]'
```

Что стоит знать:

- Baseline — последний завершённый Task с тегом `prod` в том же проекте ClearML.
  В `cy` его можно указать явно: `compare.baseline_model.task_id=BASELINE_TASK_ID`.
  Если baseline нет, новая модель всё равно оценивается на `test`, но парного
  сравнения и отчётов не будет.
- `cy-compare` пороги не подбирает, а берёт сохранённые у каждой модели.
- `cy-compare` может взять модели не из ClearML, а из локальных весов: `source=local`,
  `weights` и `thresholds` у каждой ссылки. Пороги нужны по всем классам.

Если нет сравнения и отчётов, проверьте, есть ли завершённый Task с тегом `prod`
и верна ли явная ссылка на baseline.

Подробнее: [DOCS.md](DOCS.md#comparison).

## Отчёты

`cy-report` делает из результата `cy-compare` два отчёта Excel: для разработчиков
и для бизнеса. `cy` делает этот шаг сам после успешного сравнения. Отчёты не меняют
ни одного значения метрик.

Внизу каждого листа указано, какая модель оценивалась и в каком Task она обучалась.
Если число обучающих примеров неизвестно, это отмечено явным предупреждением.

```bash
cy-report comparison_dir=./comparison output_dir=./reports \
  clearml.project_name=detection clearml.task_name=paired-reports 'clearml.tags=[reports]'
```

`cy-report` работает только с каталогом, который создал `cy-compare`.

Подробнее: [DOCS.md](DOCS.md#reports).

## Публикация в ClearML

Каждая команда эксперимента записывает запуск в один ClearML Task: конфиг, параметры,
версию кода, результаты и, если команда обучает модель, лучшие веса. Без ClearML эти
команды не работают. Команда завершается успешно, только если все обязательные загрузки
подтверждены.

Если в `cy` обучение уже прошло успешно, сбой следующего шага записывается как
предупреждение. Обученная модель при этом не теряется.

Проект, имя Task и теги можно задать в `cy-config/cy.yaml`:

```yaml
ground_truth: ./ground_truth.csv
clearml:
  project_name: detection
  task_name: yolo11n-configured
  tags: [configured, experiment]
```

Где искать результаты:

- настройки, лог и ход обучения — вкладки `Configuration`, `Console`, `Scalars`
  и `Plots` в Task;
- лучшие веса — `Output Models`; для YOLO локальный путь также есть в логе;
- разметка и предсказания — Artifacts `gt_csv` и `predicts_csv`;
- пороги, метрики и графики — Artifacts и `Plots`;
- сравнение и отчёты — XLSX-файлы, если сравнение состоялось;
- файлы запуска — `run_dir` или `runs/<проект>/<задача>-<task-id>/`.

Что бывает при сбоях:

- Обучение прошло, проверенные веса сохранены, а один из следующих шагов упал
  (в том числе загрузка в ClearML). Тогда `cy` завершается с предупреждением
  и записывает, что случилось, в `pipeline_outcome.json` и итоговую сводку.
- Успешный код возврата с предупреждениями не значит, что готовы все отчёты.
- В отдельных командах сбой загрузки — это ошибка.
- Локальные файлы остаются в обоих случаях: и при предупреждении в `cy`, и при
  ошибке в отдельной команде.
- Прерывание запуска, ошибка обучения и ошибки при `skip_train=true` завершают команду
  с ненулевым кодом возврата.

При ошибке ClearML или загрузки проверьте доступ к серверу и хранилищу, локальный лог
и `pipeline_outcome.json`.

Подробнее: [DOCS.md](DOCS.md#clearml-publication).

## Просмотр в FiftyOne

После `cy`, `cy-predict` и `cy-metrics` изображения, разметка, предсказания и результаты
оценки публикуются в постоянный датасет FiftyOne. В нём удобно искать пропуски
и ложные срабатывания (FN и FP). Публикация включена по умолчанию и идёт в отдельном
процессе с ограничением по времени. Если она упадёт, будет только предупреждение:
результат и ClearML Task не пострадают.

```bash
cy --config-dir cy-config --config-name cy fiftyone.publish_timeout_seconds=1800
cy --config-dir cy-config --config-name cy fiftyone.enabled=false   # без FiftyOne
```

Первая команда даёт публикации больше времени, вторая выключает её. Имя датасета
записано в `fiftyone_publication.json` в выходном каталоге команды. Как открыть датасет
в FiftyOne App, описано в разделе ниже.

Подробнее: [DOCS.md](DOCS.md#fiftyone-publication).

## Веса моделей

Перед обучением семействам нужны предобученные веса, а DEIMv2 — ещё и исходники
утверждённой ревизии. `cy-download-weights` заранее кладёт их в кэши, которые читают
сами библиотеки. `cy` пытается сделать то же автоматически. Отдельные команды
скачивают только то, что нужно выбранной модели. Подготовка ничего не устанавливает,
не обучает модели и не создаёт ClearML Task.

```bash
cy-download-weights
```

Команда готовит веса YOLO, RF-DETR, backbone для Faster R-CNN и FCOS, а также DEIMv2
`s` и `m` вместе с исходниками. Файлы берутся из релиза весов этого проекта на GitHub
и проверяются по контрольным суммам. Повторный запуск докачивает только недостающее.
Если что-то скачать не удалось, код возврата ненулевой.

DEIMv2 `l` и `x` в общую подготовку не входят. Они скачиваются, когда вы выбираете эту
модель: исходники — с GitHub, backbone DINOv3 — с Hugging Face. Для этого примите
лицензию на Hugging Face и задайте переменную `HF_TOKEN`. Прокси для этих загрузок
задают переменные `GH` и `HF_ENDPOINT`.

При первом запуске `cy` та же подготовка выполняется сама. Если она прошла не
полностью, `cy` предупредит и продолжит работу с выбранной моделью. Отдельные команды
вроде `cy-train` общую подготовку не запускают.

Если GitHub недоступен напрямую, задайте `GHR` — корень Generic-репозитория
Artifactory, который проксирует `https://github.com`, например
`export GHR="https://artifactory.example/artifactory/github-files"`.

Ещё о загрузке:

- необязательная переменная `CY_WEIGHTS_DOWNLOAD_TIMEOUT` задаёт число секунд на один
  архив, по умолчанию 1800;
- авторизация настраивается через `.netrc`, свой сертификат — через
  `SSL_CERT_FILE` или `REQUESTS_CA_BUNDLE`;
- ответ 401 значит, что не прошла авторизация, 403 — нет прав, 404 — неверен путь или
  файла нет в источнике.

Лицензии у весов разные: YOLO — AGPL-3.0, DEIMv2 — только некоммерческое использование,
DINOv3 — отдельное соглашение Meta с ограничениями. Тексты лицензий лежат в архивах.

**Built with DINOv3.** Backbone DINOv3 распространяется в неизменённом формате
конвертации timm, с исходной конфигурацией и метаданными ревизии.

Если модель не загружается:

- проверьте семейство, пресет и совместимость весов;
- если нет ни сети, ни прокси, разложите файлы вручную: сообщение об ошибке перечисляет
  недостающие файлы, их исходные адреса и пути, куда их положить.

Подробнее: [DOCS.md](DOCS.md#model-assets).

## Подбор batch size

`cy-batch-estimate` измеряет, какой batch size на одну GPU помещается при обучении
на вашем железе. Результат пишется в редактируемую таблицу
`CY_HOME/.config/clearml-yolo/batch-sizes.yaml`. Обучение читает её, только если batch
size явно не задан: `ultralytics.batch=null` или `model.train.batch=null`. Измерение идёт
локально на синтетических данных и не создаёт ClearML Task.

```bash
cy-batch-estimate --imgsz 960
cy-batch-estimate --imgsz 960 --models rfdetr/small,fcos/resnet50_fpn --devices 0,1
cy-batch-estimate --list
```

Что стоит знать:

- В таблице для каждой GPU, размера изображения и модели записан batch size на одну GPU,
  например `rfdetr/small: 3` под `"NVIDIA GeForce RTX 4090 [24 GiB]"` и размером
  `960`. Таблицу можно заполнить и вручную.
- Измеряйте на свободных GPU: GPU, занятая чужим процессом, не измеряется.
- Если для вашей GPU записи нет, берётся запись GPU с памятью не больше вашей.
  Команда об этом предупреждает.
- При multi-GPU общий batch size равен числу GPU, умноженному на наименьшее значение
  среди них.
- Значение из таблицы — рекомендация. При нехватке памяти обучение упадёт и само
  с меньшим batch size не перезапустится.
- Для CPU и неквадратных изображений batch size задаётся числом.

Если записи нет, добавьте её в `batch-sizes.yaml`, запустите `cy-batch-estimate` или
задайте batch size числом.

Подробнее: [DOCS.md](DOCS.md#batch-estimation).

## Экспорт в ONNX и TensorRT

`cy-export` превращает обученный чекпойнт Faster R-CNN в TensorRT engine и проверяет,
что engine детектирует не хуже исходной модели. За один запуск выполняется одна
операция:

- `onnx` — пишет ONNX-граф на CPU;
- `build` — собирает из него TensorRT engine для одной GPU в FP32 или FP16;
- `verify` — сравнивает engine с исходным чекпойнтом на размеченном датасете.

Экспорт других семейств не поддерживается.

```bash
cy-export model=fasterrcnn/resnet50_fpn weights=./best.pth \
  export.operation=onnx export.device=cpu export.precision=fp32 output_dir=./exported \
  clearml.project_name=detection clearml.task_name=fasterrcnn-onnx 'clearml.tags=[export]'
```

TensorRT ставится отдельно и в зависимости проекта не входит. Engine привязан к GPU,
версиям TensorRT и CUDA, на которых собран. Для другой машины соберите и проверьте его
заново.

Подробнее: [DOCS.md](DOCS.md#export).

## Процессы команды

Каждая команда отвечает за процессы, которые запускает. Устройства она использует как
есть: без очереди, резервирования GPU и ожидания. Перед выходом — успешным, с ошибкой
или после прерывания — команда завершает все свои процессы, включая процессы
multi-GPU обучения и загрузчики данных. Затем проверяет, что они действительно
закрылись. Чужие процессы она не трогает. Для заданий из очереди это делает
`cy-queue`.

Чтобы остановить запуск, нажмите `Ctrl+C` и дождитесь, пока завершатся процессы,
которые запустила команда.

Подробнее: [DOCS.md](DOCS.md#process-ownership).

## Очередь

`cy-queue` пригодится, если одну машину с GPU делят несколько запусков или людей. Это
отдельный пакет. Он хранит задания, ждёт свободные GPU, запускает `cy` или `cy-train`
от имени владельца задания и следит за каждым запуском. Прямым командам и ClearML Agent
очередь не нужна.

```bash
cy-queue submit --gpus 1 -- --config-dir cy-config --config-name cy
cy-queue worker
```

Перед отправкой уберите устройства из YAML (`device: null`): GPU назначает очередь.
Установка, настройка и команды описаны в документации `cy-queue`. Правила для
администратора общей очереди — в разделе ниже.

Если очередь не запускает задание, проверьте, запущен ли ваш worker и хватает ли
свободных GPU. Прямая команда GPU не ждёт.

Подробнее: [DOCS.md](DOCS.md#queue).

## Диагностика

Каждая команда эксперимента сохраняет весь вывод консоли в локальные логи, показывает
его в терминале и публикует в ClearML Task. Ошибки выводятся кратко, пароли и токены
в них скрываются. С `LOGURU_LEVEL=TRACE` в лог добавляются начало и конец каждой
операции и периодические сообщения о том, на что уходит время. Это помогает разобрать
зависание.

Подробность лога задаёт `LOGURU_LEVEL`:

- `INFO` — коротко;
- `DEBUG` — с местом каждой ошибки в коде (по умолчанию);
- `TRACE` — для разбора зависаний.

Подробнее: [DOCS.md](DOCS.md#diagnostics).

## Дедупликация кэша

`cy-dedup` освобождает место в кэше изображений (`$CY_HOME/.cache`). На файловой системе
Linux с поддержкой reflink одинаковые файлы с одинаковым именем начинают занимать место
один раз. Пути и содержимое файлов не меняются. ClearML Task команда не создаёт.

Сначала остановите запись в кэш и посмотрите, что будет сделано:

```bash
cy-dedup --dry-run
cy-dedup
```

Подробнее: [DOCS.md](DOCS.md#filesystem-and-cache-deduplication).

## Рабочий каталог

Всё, что пишет CY, лежит в одном рабочем каталоге `CY_HOME`. По умолчанию это каталог
запуска. Там хранятся результаты запусков, логи, кэш подготовленных данных, таблица
batch size и временные файлы. Входные данные — CSV, изображения, чекпойнты — могут
лежать где угодно. Библиотеки вроде ClearML, Ultralytics, FiftyOne и Torch хранят свои
настройки и кэши в собственных каталогах.

Выходные каталоги (`run_dir`, `output_dir`), кэш и логи должны быть внутри `CY_HOME`.
Путь снаружи отклоняется до начала работы.

Подробнее: [DOCS.md](DOCS.md#filesystem-and-cache-deduplication).

## Совместимость и зависимости

CY ставится в окружение uv на Linux — по Git-ссылке на репозиторий или из исходников.
Одна установка даёт всё: все семейства моделей, экспорт в ONNX, ClearML и FiftyOne.
`digital-metrics` и `report-generator` берутся:

- при установке по Git-ссылке — из вашего индекса пакетов;
- при установке из исходников — из локальных копий утверждённых ревизий.

Драйверы GPU, TensorRT, доступ к ClearML и отдельный пакет `cy-queue` вы ставите
и настраиваете сами. Во время работы CY ничего не устанавливает.

Подробнее: [DOCS.md](DOCS.md#installation-and-dependencies).

## Разработка

Окружение для разработки ставится так же, как в разделе «Установка», для каждого
рабочего дерева отдельно.

Проверки, коммиты и релизы описаны в [AGENTS.md](AGENTS.md).
Устройство кода и правила для него — в [DOCS.md](DOCS.md#architecture-and-data-flow).
