# Hydra: YAML, переопределения, переборы и DDP

## Предварительные условия

Нужен установленный CY. Просмотр композиции не требует датасета или модели, но
реальное выполнение требует всех входов из [первого урока](quickstart.html).
Обычные CLI `--help`/`--cfg` могут создать локальные scratch/логи; проверяйте их
в отдельном рабочем каталоге. Предпросмотр `cy-docs` не запускает приложение.

## Пример

### Сгенерировать самостоятельное дерево

```bash
cy-init-config train-config --command cy-train --model rfdetr/small
cy-train --config-dir train-config --config-name cy-train --cfg job
```

Экспорт содержит wrapper `cy-train.yaml`, локальную базу `train.yaml`, выбранную
модель, оба профиля аугментаций и YAML их defaults. При YOLO экспортируются обе
native-группы. Команды metrics/report/ground-truth не используют model group;
`cy-export` выбирает Faster R-CNN. Если `--command` опущен, экспортируется только `cy`.

Сохраните существующие файлы перед намеренным `--force`; новая папка удобна для
сравнения. Не удаляйте сгенерированный `defaults`: он задаёт порядок композиции.
В `train-config/cy-train.yaml` измените входы, а в
`train-config/model/rfdetr/small.yaml` — параметры `train` и `predict`.

Для YOLO файлы `ultralytics/default.yaml` и `ultralytics_predict/default.yaml`
содержат **bare keys**, без дополнительной обёртки `ultralytics:`.

```yaml
epochs: 10
imgsz: 640
batch: 4
device: cpu
```

В wrapper входы имеют обычную форму:

```yaml
ground_truth: ./tutorial-data/ground_truth.csv
clearml:
  project_name: cy-tutorial
  task_name: configured-training
  tags: [tutorial, configuration]
```

### Порядок и типы переопределений

CLI применяется поверх выбранной композиции; последнее переопределение одного
значения побеждает. Выбор `model=rfdetr/small` заменяет группу, а
`model.train.epochs=2` меняет поле выбранного объекта.

```bash
cy-train --config-dir train-config --config-name cy-train \
  model.train.epochs=2 model.train.device=cpu --cfg job
```

Hydra использует собственную грамматику: кавычки shell сохраняют один аргумент,
списки пишутся `[a,b]`, nullable-ввод — `null`, а не строка `"null"`.

```bash
cy-predict ground_truth=./tutorial-data/ground_truth.csv weights=./best.pt \
  'splits=[val,test]' ultralytics_predict.device=cpu fiftyone.enabled=false --cfg job
cy-train ground_truth=./tutorial-data/ground_truth.csv ultralytics.batch=null --cfg job
```

`+key=value` добавляет отсутствующий ключ на уровне композиции, `++key=value`
добавляет или заменяет, `~key` удаляет. Возможность создать ключ в Hydra не означает,
что runtime CY принимает этот ключ. Предпочитайте существующие публичные поля
справочника. Nullable [dataset_cache_dir](/#field=dataset_cache_dir) и
[ultralytics.batch](/#field=ultralytics.batch) имеют разные значения `null`;
объяснение находится у каждого поля.

### Интерполяция и предпросмотр

```yaml
ultralytics:
  imgsz: 640
ultralytics_predict:
  imgsz: ${ultralytics.imgsz}
```

Справочник показывает исходное выражение и выбранное значение отдельно. Изменение
training image size меняет унаследованный prediction size, пока он не переопределён
явно. Prediction batch/conf/device имеют собственные defaults.

В редакторе `cy-docs` выберите команду, добавьте именованные YAML-документы и
упорядоченные overrides. Сравните итоговый YAML и различия, исправьте schema errors,
затем скопируйте команду и скачайте конфигурацию. `???` означает обязательный
незаполненный ввод. Выражения вида `${oc.env:DATASET_CSV}` и custom resolvers остаются
неразрешёнными: предпросмотр не читает ваше окружение и не вызывает пользовательские
функции. Он также не читает датасеты, веса или JSON аугментаций.

Ограничения preview: 32 документа, 1 MiB запроса, не более 100 вариантов sweep,
15 секунд на worker. Имена документов должны оканчиваться на `.yaml`, как требует
источник файлов Hydra; `.yml` не принимается. Пользовательские блоки `hydra`,
Hydra overrides, внешние search paths и замена plugins/launcher/sweeper отклоняются
до композиции. Параметры runtime Hydra передавайте в терминале. Произвольные Python
targets не исполняются. Для реального запуска
действуют runtime-проверки и доступность внешних ресурсов.

### Перебор параметров

```bash
cy-train -m ground_truth=./tutorial-data/ground_truth.csv ultralytics.model=yolo11n.pt \
  ultralytics.epochs=1,2 ultralytics.batch=2 ultralytics.device=cpu \
  ultralytics.compile=false clearml.project_name=cy-tutorial \
  clearml.task_name=sweep 'clearml.tags=[tutorial,sweep]'
```

Прямой multirun использует последовательный BasicLauncher. Запятая в override
задаёт варианты; список в квадратных скобках — одно значение. Для диапазонов
используйте грамматику Hydra, например `'ultralytics.epochs=range(1,4)'`.
В `cy-docs` включите sweep-предпросмотр и проверьте число jobs перед запуском.
Перебор использует порядок и обработку повторных ключей штатного BasicSweeper Hydra;
не смешивайте удаление, добавление и повторную замену одного ключа внутри sweep.
Multirun добавляет один общий читаемый тег, сохраняя ваши теги.

### Несколько GPU — один эксперимент

DDP отличается от sweep: одна модель обучается несколькими процессами. Выберите
реально доступные устройства и отдельное устройство предсказаний:

```bash
cy ground_truth=./tutorial-data/ground_truth.csv ultralytics.model=yolo11n.pt \
  'ultralytics.device=[0,1]' ultralytics.batch=8 ultralytics_predict.device=0 \
  run_dir=./runs/ddp-yolo fiftyone.enabled=false clearml.project_name=cy-tutorial \
  clearml.task_name=ddp-yolo 'clearml.tags=[tutorial,ddp]'
```

Для DEIMv2/RF-DETR/Faster R-CNN/FCOS служит `'model.train.device=[0,1]'`, а
`model.predict.device=0` остаётся single-device. Публичный native batch глобальный,
делится поровну между ranks; accumulation отдельно определяет эффективный optimizer
batch. Используйте [model.train.batch](/#field=model.train.batch) и настройки
выбранного backend. Только владелец invocation публикует ClearML, rank zero владеет
чекпойнтом. Наличие схемы и CPU-DDP тестов не подтверждает физический GPU/NCCL запуск
на вашей машине. Для очереди устройства выбираются её интерфейсом, см.
[операционный урок](operations.html).

## Ожидаемый результат

`--cfg job` и preview показывают composed YAML; `--resolve` у настоящего CLI может
разрешить доступные ему выражения. Сайт показывает unresolved значения и отложенные
runtime-проверки. Реальный sweep создаёт несколько запусков, DDP — один эксперимент
с несколькими native ranks.

## Частые ошибки

- Потерян defaults: восстановите свежий экспорт в другом каталоге и сравните.
- Ключ находится не в той группе: фильтруйте справочник по команде и модели.
- Shell разделил список или интерполяцию: заключите весь override в одинарные кавычки.
- Preview отклонил external search path: перенесите нужные локальные YAML как
  именованные документы; plugin replacement в этой функции не поддерживается.
- DDP batch не делится на ranks или GPU занят: исправьте конфигурацию/выбор ресурсов;
  не подменяйте это успешной композицией.

## Проверка

Сравните экспортированный wrapper, итоговую композицию и CLI overrides. Убедитесь,
что нет незаполненных обязательных полей, и отдельно проверьте внешние входы.
Для запуска сверяйте effective configuration из ClearML. Для DDP подтвердите
реальные ranks, один best Output Model, owner-only публикацию и корректное завершение
всех дочерних процессов; для sweep — число jobs и общий тег.

Справочник общих флагов Hydra: [вывод конфигурации](/#field=hydra.--cfg),
[каталог](/#field=hydra.--config-dir), [имя](/#field=hydra.--config-name),
[перебор](/#field=hydra.--multirun). Эти флаги передаются в терминале;
редактор принимает YAML и упорядоченные переопределения полей.
