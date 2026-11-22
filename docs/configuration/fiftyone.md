# Группа `fiftyone`

Группа конфигурации (config group) `fiftyone` управляет публикацией разметки ([ground truth](../../GLOSSARY.md#ground-truth)), предсказаний и результатов сопоставления в FiftyOne. Публикация необязательна: если FiftyOne недоступен, команда пишет предупреждение и продолжает работу. Адрес базы данных FiftyOne задаётся не здесь, а в настройках самого FiftyOne (см. [Установка: FiftyOne](../installation.md#fiftyone)).

## Где действует группа

| Команда | Что публикуется |
| --- | --- |
| `cy` | Один раз в конце пайплайна ([pipeline](../../GLOSSARY.md#pipeline)): разметка, предсказания и результаты этапа ([stage](../../GLOSSARY.md#stage)) метрик. Публикация выполняется, только если этап предсказания завершился успешно или пропущен через `skip_predict=true`. |
| `cy-predict` | Разметка и предсказания. |
| `cy-metrics` | Разметка, предсказания и результаты сопоставления по каждому split. |

`cy-val` публикацию в FiftyOne всегда отключает, у этой команды нет группы `fiftyone`. У остальных команд группы тоже нет.

Значения ключей проверяются, когда команда переходит к работе, то есть уже после создания задачи ClearML (task). Недопустимое значение даёт ошибку, и задача помечается как неуспешная.

Override `fiftyone=null` не поддерживается: команда завершается ошибкой до создания задачи ClearML (task) и подсказывает `fiftyone.enabled=false`. Чтобы отключить публикацию, задайте `fiftyone.enabled=false`.

```text
fiftyone=null is not supported; use fiftyone.enabled=false to turn FiftyOne publication off
```

С тем же сообщением завершается запуск сохранённой конфигурации с `fiftyone: null`: объекта конфигурации ([configuration object](../../GLOSSARY.md#configuration-object)) `run` клона задачи, который выполняет агент ClearML, или сохранённого YAML. Замените в ней `fiftyone: null` на `fiftyone: {enabled: false}`.

## Ключи

| Ключ | По умолчанию | Допустимые значения | Описание |
| --- | --- | --- | --- |
| `enabled` | `true` | `true`, `false` | `false` отключает публикацию в FiftyOne: команда не обращается к FiftyOne вообще. |
| `preflight_timeout_seconds` | `60.0` | конечное число больше `0` | Сколько секунд ждать предварительной проверки ([FiftyOne preflight](../../GLOSSARY.md#fiftyone-preflight)) FiftyOne в начале команды. |
| `publish_timeout_seconds` | `900.0` | конечное число больше `0` | Сколько секунд ждать публикации целиком: загрузка FiftyOne, запись датасета и выход процесса публикации. |
| `lock_timeout_seconds` | `30.0` | конечное число больше `0` | Сколько секунд ждать блокировку датасета, если его в тот же момент пишет другой запуск. |
| `dataset_prefix` | `clearml-yolo` | латинские буквы, цифры, `-` и `_`; первый символ — буква или цифра | Начало имени датасета FiftyOne. Полное имя: `<dataset_prefix>-v1-<SHA-256 CSV разметки>`. |

Что именно создаётся в FiftyOne, как работают проверка и таймауты и что происходит при недоступности FiftyOne, описано в разделе [Публикация: FiftyOne](../publication.md#fiftyone).

## Пример

```bash
cy-predict weights=weights/best.pt ground_truth=data/ground_truth.csv \
  fiftyone.dataset_prefix=my-project fiftyone.publish_timeout_seconds=1800 \
  clearml.project_name=my-project clearml.task_name=my-run
```

Отключить публикацию:

```bash
cy-metrics predictions=runs/my-run/predict.csv ground_truth=data/ground_truth.csv \
  fiftyone.enabled=false clearml.project_name=my-project clearml.task_name=my-run
```

## См. также

- [Публикация в ClearML и FiftyOne](../publication.md)
- [Установка: подключение к FiftyOne](../installation.md#fiftyone)
- [Как устроена конфигурация](README.md)
