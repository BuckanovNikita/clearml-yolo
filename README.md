# clearml-yolo

`clearml-yolo` — набор приложений Hydra/hydra-zen для обучения YOLO, инференса,
оценки, отчётов и сравнения моделей. Параметры исполнения передаются самому
Ultralytics; проект сохраняет воспроизводимые входы, результаты и артефакты в
ClearML.

## Установка

Для локальной разработки инициализируйте подмодули и установите зависимости:

```bash
git submodule update --init --recursive
uv sync --locked
```

`digital-metrics` и `report-generator` находятся в `external/` как Git-подмодули.
Оба подмодуля отслеживают upstream-ветку `main`; точные ревизии закреплены в
родительском репозитории. `uv sync` устанавливает оба
пакета в editable-режиме из этих каталогов; изменения исходников видны без
переустановки. После переключения ветки или обновления репозитория повторите
обе команды. При первом клонировании можно использовать `git clone --recurse-submodules`.

Для обновления обоих подмодулей до текущей `main`:

```bash
git submodule update --remote --recursive
uv sync
```

Сохраняйте обновлённые ревизии подмодулей и `uv.lock` вместе.

Для установки без подмодулей задайте свои Git-источники. Установите
`DIGITAL_METRICS_GIT_URL` и `REPORT_GENERATOR_GIT_URL` в адреса нужных репозиториев
(`https://…` или `ssh://git@…`, без префикса `git+`). Оба upstream-репозитория
используют `main`; для репозиториев с веткой `master` замените имя ветки:

```bash
uv add --no-sync --branch main \
  "digital-metrics @ git+${DIGITAL_METRICS_GIT_URL:?}" \
  "report-generator @ git+${REPORT_GENERATOR_GIT_URL:?}"
uv sync --locked --no-dev
```

Эта команда заменяет оба пути в `[tool.uv.sources]` файла `pyproject.toml`
на Git-источники с `branch = "main"` и обновляет `uv.lock`; сохраняйте их вместе
для воспроизводимости. Lock-файл фиксирует выбранные коммиты. Для обновления
Git-источников до текущей ветки выполните
`uv lock --upgrade-package digital-metrics --upgrade-package report-generator`,
затем `uv sync --locked --no-dev`.
Переменные используются оболочкой только при выполнении команды. Сам флаг
`--no-dev` исключает инструменты разработки, но не переключает источники.
Настройка источников описана в [документации uv](https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-sources).

Для возврата к локальным подмодулям:

```bash
git submodule update --init --recursive
uv add --no-sync --editable ./external/digital-metrics ./external/report-generator
uv sync --locked
```

При установке wheel через `uv pip install` или `pip install` передавайте оба
Git-требования из примера выше с суффиксом `@main` (либо `@master`) после URL
вместе с путём к wheel. Эти команды не используют `[tool.uv.sources]`, а внешние
пакеты не включаются в дистрибутив `clearml-yolo`.

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
| `cy-init-config` | создание каталога с примерами конфигураций |

Команды `cy-queue` больше нет. Проект не управляет очередью,
лизами GPU, подбором batch, пользовательскими JSON-аугментациями и отключённым
треккингом. `auto_gpu`, `--force-gpu`, `clearml.enabled=false` и удалённые поля
вызывают явную ошибку.

## Быстрый старт

Создайте каталог с редактируемыми примерами:

```bash
uv run cy-init-config ./conf
```

Команда создаёт восемь файлов: `cy.yaml`, `cy-train.yaml`, `cy-predict.yaml`,
`cy-val.yaml`, `cy-metrics.yaml`, `cy-report.yaml`, `cy-compare.yaml` и
`cy-ground-truth.yaml`. Они содержат текущие настройки команд и подсказки по
нативным параметрам. Замените обязательные значения `???`, задайте входные пути
и настройки ClearML. Относительные пути считаются от рабочей директории запуска.
Инициализация не требует подключения к ClearML и не создаёт задачу.
Существующие примеры защищены от перезаписи; для их замены используйте
`uv run cy-init-config ./conf --force`. Остальные файлы каталога сохраняются.

Пример запуска с созданной конфигурацией:

```bash
uv run cy-train --config-dir=./conf --config-name=cy-train \
  +ultralytics.data=data.yaml +ultralytics.model=yolo11n.pt +ultralytics.epochs=10 \
  clearml.project_name=detection clearml.tags='[example]'
```

Для полного конвейера сначала постройте CSV разметки:

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

Каждая команда исполнения создаёт ровно одну задачу ClearML; `cy-init-config`
только записывает локальные YAML. Вложенные стадии конвейера используют того же
владельца; воркеры и callback Ultralytics не создают
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
