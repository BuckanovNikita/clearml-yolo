# clearml-yolo

`clearml-yolo` — набор приложений Hydra/hydra-zen для обучения YOLO, инференса,
оценки, отчётов и сравнения моделей. Параметры исполнения передаются самому
Ultralytics; проект сохраняет воспроизводимые входы, результаты и артефакты в
ClearML.

## Установка

```bash
uv sync
```

Python проекта — 3.12. Перед первым запуском настройте ClearML: для своей
интерактивной работы подойдёт `uv run clearml-init` либо переменные окружения
`CLEARML_API_HOST`, `CLEARML_WEB_HOST`, `CLEARML_FILES_HOST`,
`CLEARML_API_ACCESS_KEY` и `CLEARML_API_SECRET_KEY`. Переменные окружения имеют
приоритет над `~/clearml.conf`.

## Приложения

| Команда | Назначение |
|---|---|
| `cy` | полный конвейер: обучение, предсказания, метрики, сравнение и отчёты |
| `cy-train` | обучение YOLO |
| `cy-predict` | инференс и таблица предсказаний |
| `cy-val` | инференс checkpoint на `val` и указанных сплитах, калибровка и оценка |
| `cy-metrics` | метрики, точные пороги, таблицы, дашборды и графики |
| `cy-report` | developer и business отчёты из парной текущей оценки |
| `cy-compare` | сравнение baseline и candidate на одних текущих test-изображениях |
| `cy-ground-truth` | преобразование разметки YOLO из `data.yaml` в CSV |

Команд `cy-queue` и `cy-init-config` больше нет. Проект не управляет очередью,
лизами GPU, подбором batch, пользовательскими JSON-аугментациями и отключённым
треккингом. `auto_gpu`, `--force-gpu`, `clearml.enabled=false` и удалённые поля
вызывают явную ошибку.

## Быстрый старт

Сначала постройте CSV разметки:

```bash
uv run cy-ground-truth data_yaml=data.yaml output=ground_truth.csv
```

Запустите полный конвейер. `run_dir` принадлежит конвейеру и изолирует все его
выходы:

```bash
uv run cy \
  run_dir=./runs/experiment-030 \
  clearml.project_name=detection \
  clearml.task_name=yolo11n-v3 \
  ground_truth=ground_truth.csv \
  +train.ultralytics.data=data.yaml \
  +train.ultralytics.epochs=100 \
  +train.ultralytics.device=0 \
  +predict.ultralytics.device=0
```

Входные пути обязательны: команды не выбирают файлы из текущей папки по умолчанию.
Для отдельной стадии их задают так:

```bash
uv run cy-train cfg=training.yaml +ultralytics.device=0
uv run cy-predict weights=./weights/best.pt ground_truth=ground_truth.csv \
  output=./runs/predictions.csv +ultralytics.device=0
uv run cy-val weights=./weights/best.pt ground_truth=ground_truth.csv \
  output_dir=./runs/validation +ultralytics.device=0
```

## Нативные параметры Ultralytics

Параметры модели находятся в разреженном отображении `ultralytics`; у `cy` это
`train.ultralytics` и `predict.ultralytics`. Рядом с отображением ключ `cfg`
называет исходный YAML Ultralytics. Порядок приоритета такой:

1. значения по умолчанию Ultralytics;
2. YAML из `cfg`;
3. встроенные `ultralytics` значения, включая явно заданное значение по умолчанию;
4. оверрайды Hydra в командной строке.

Обычный оверрайд меняет уже существующий ключ; `+` добавляет отсутствующий:

```bash
uv run cy-train cfg=training.yaml +ultralytics.epochs=10 +ultralytics.batch=16
uv run cy ground_truth=ground_truth.csv +train.ultralytics.data=data.yaml \
  +train.ultralytics.epochs=10 +train.ultralytics.compile=true
```

Нативный файл `training.yaml` может содержать обычные параметры Ultralytics:

```yaml
model: yolo11n.pt
data: data.yaml
epochs: 100
batch: 16
```

Для встроенных значений создайте `experiment.yaml` поверх конфигурации конвейера:

```yaml
defaults:
  - pipeline
  - _self_
train:
  cfg: training.yaml
  ultralytics:
    epochs: 20
    device: 0
predict:
  ultralytics:
    device: 0
```

```bash
uv run cy --config-dir=. --config-name=experiment \
  ground_truth=ground_truth.csv train.ultralytics.epochs=10
```

Указывайте `device`, `batch`, `amp` и `compile` как нативные параметры. Ultralytics
проверяет неизвестные параметры сам. Проект записывает эффективные аргументы и
фактически созданные пути в артефакты запуска.

В конвейере нельзя направлять отдельные этапы через собственные выходные пути и
нельзя задавать `train.ultralytics.project` или `train.ultralytics.name`, если
они противоречат каталогу, выбранному `run_dir`: команда откажется до выполнения.

## Оценка и сравнение

Кандидатские пороги калибруются ровно один раз на `val`, а затем остаются
неизменными на `test`. Если есть baseline, обе модели проходят один и тот же
текущий набор test-изображений с одинаковыми настройками инференса. Точные
пороги сохраняются в артефакте `metrics_best_confidences_<split>`; значения на
дашборде округлены.

`cy-compare` принимает ссылки `baseline_model` и `candidate_model`, текущий
`ground_truth`, настройки инференса, `split=test` и выходной каталог. По умолчанию
baseline — последняя завершённая задача с тегом `prod`, кроме текущей задачи. Если
автоматический поиск ничего не находит, сравнение отмечается пропущенным. Некорректно
названная явно задача или checkpoint, а также отсутствие требуемых точных порогов —
ошибка.

Исторические дашборды не сравниваются. Парные результаты текущего test-набора
лежат в `comparison_dir` и одновременно служат источником статистики, developer- и
business-отчётов. Поэтому числа, исключённые классы и пороги во всех отчётах
описывают одну и ту же оценку.

## ClearML и артефакты

Каждое обращение к команде создаёт ровно одну задачу ClearML. Вложенные стадии
конвейера используют того же владельца; воркеры и callback Ultralytics не создают
дополнительных задач, моделей, метрик или загрузок. Задача считается завершённой
только после синхронной загрузки всех обязательных результатов.

Сохраняются исходные конфиги без секретов, разрешённая конфигурация, конфигурация
датасета при её наличии, ссылки на модели, эффективные аргументы и пути Ultralytics,
методология оценки и итоговый манифест. Загружаются checkpoint, таблицы разметки и
предсказаний, точные пороги, метрики, графики и отчёты соответствующих включённых
стадий. Учётные данные и изображения датасета не сохраняются. Нативный вывод консоли
остаётся локальным: автоматический захват сырых аргументов мог бы сохранить секреты. Ошибка вычисления,
загрузки, сброса SDK или прерывание завершает задачу и команду ошибкой, но локальные
файлы остаются на месте.

## Разработка

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
```

Это проверки без доказательства реального обучения, GPU или загрузки артефактов.
Для интеграционной проверки используйте отдельный проект ClearML, доступный датасет
и явно выбранное устройство. Порядок проверки описан в
[руководстве](specs/001-release-030/quickstart.md), изменения конфигурации — в
[миграции на 0.3.0](docs/migration-030.md).
