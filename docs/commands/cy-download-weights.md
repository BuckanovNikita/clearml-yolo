# cy-download-weights

`cy-download-weights` заранее готовит веса (weights) всех поддерживаемых именованных моделей и исходники DEIMv2 в их родных кэшах (cache), где их ищут библиотеки моделей. Команда нужна при подготовке GPU-хоста, особенно без прямого доступа к интернету: после неё обучение и предсказание находят веса локально.

## Примеры

```bash
cy-download-weights
```

Готовит все веса и печатает итог.

```bash
export GHR=https://artifactory.example/artifactory/github-files
cy-download-weights
```

Скачивает архивы весов через зеркало GitHub release.

```bash
CY_WEIGHTS_DOWNLOAD_TIMEOUT=3600 cy-download-weights
```

Увеличивает лимит времени на одну попытку скачать архив.

## Синтаксис и аргументы

```text
cy-download-weights [-h]
```

| Аргумент | По умолчанию | Описание |
| --- | --- | --- |
| `-h`, `--help` | — | Показать справку и выйти. |

Других аргументов нет. Поведение настраивается переменными окружения (environment variable) `GHR`, `CY_WEIGHTS_DOWNLOAD_TIMEOUT` и `SSL_CERT_FILE`; их описание — в [Установке](../installation.md#переменные-окружения) и в разделе [Зеркала весов](../installation.md#зеркала-весов) ([weight mirror](../../GLOSSARY.md#weight-mirror)).

## Как это работает

1. Команда записывает абсолютный путь каталога весов Ultralytics (`weights_dir`) в настройки Ultralytics, если там был относительный путь.
2. Она составляет список: все модели из `cy-batch-estimate --list`, кроме `deimv2/l` и `deimv2/x`, и исходники DEIMv2. Одинаковые файлы в одном месте учитываются один раз.
3. Для каждого файла:
   1. Если в родном кэше ([native cache](../../GLOSSARY.md#native-cache)) уже лежит корректный файл, он используется без скачивания.
   2. Иначе команда берёт его из закреплённого GitHub release проекта: скачивает архив весов в `CY_HOME/.cache/clearml-yolo/weight-bundles/` (см. [Рабочий каталог](../workspace.md) ([workspace](../../GLOSSARY.md#workspace))), проверяет размер и SHA-256 архива и файла внутри и кладёт файл в родной кэш. Уже скачанный и проверенный архив повторно не скачивается.
   3. Архив скачивается сначала через зеркало `GHR`, если оно задано, затем напрямую с GitHub; на каждый адрес — две попытки, каждая ограничена `CY_WEIGHTS_DOWNLOAD_TIMEOUT` секунд (по умолчанию 1800).
   4. Адрес на зеркале — корень `GHR` плюс путь GitHub без изменений: `<GHR>/<owner>/<repo>/releases/download/<tag>/<файл>`.
4. Ошибка одного файла не останавливает остальные.
5. Итог записывается в `CY_HOME/.cache/clearml-yolo/preparation/`. Каждый ручной запуск выполняет подготовку заново. Второй запуск с тем же набором файлов ждёт, пока первый закончит.

`GH` и `HF_ENDPOINT` этой командой не используются: она берёт веса только из родных кэшей и из release проекта.

## Результат

Веса в родных кэшах библиотек и архивы в `CY_HOME/.cache/clearml-yolo/weight-bundles/`. В stdout:

```text
Cache destination: <каталог кэша>
Prepared: <путь к файлу>
Failed: <модель>: <причина>
Prepared <N> assets; <M> failures.
```

`Cache destination` выводится для каждого каталога кэша, `Prepared` — для каждого готового файла, `Failed` — для каждой ошибки. При ошибках после итога печатается подсказка:

```text
If Artifactory is required, configure its repository roots and retry:
  # Files remote of https://github.com (release archives):
  export GHR=https://artifactory.example/artifactory/github-files
Use per-host ~/.netrc credentials for GHR HTTP requests.
GH (VCS) and HF_ENDPOINT apply only to standalone source/Hub resolution; they are not needed for bulk weights.
Bulk preparation uses valid native caches or this project's pinned release only.
GHR preserves owner/repo/releases/download/tag/file.
For slow archive transfers, set CY_WEIGHTS_DOWNLOAD_TIMEOUT=3600 (positive finite seconds; default 1800 per attempt).
Keep TLS verification enabled; configure SSL_CERT_FILE for a private CA.
Retry: cy-download-weights
Details: DOCS.md, section Model assets
```

Строка `Details: DOCS.md, section Model assets` ссылается на файл, которого в документации нет; нужные сведения — на этой странице и в [Установке](../installation.md#зеркала-весов).

### Коды завершения

| Код | Значение |
| --- | --- |
| `0` | Все файлы готовы. |
| `1` | Хотя бы один файл не подготовлен (`failures` больше нуля). |
| `2` | Неизвестный аргумент. |

## Частые ошибки

Строка ошибки имеет вид `Failed: <модель>: Asset preparation failed: BundlePreparationError: <причина>`. Вместо модели может стоять `deimv2/source` (исходники DEIMv2) или `catalogue` (ошибка самой подготовки, например нет записи в `CY_HOME`). Причины:

| Причина | Что делать |
| --- | --- |
| `Pinned release <tag> archive <файл> unavailable; GHR Files remote: HTTP 404; GitHub release: ...` | Архив не скачался ни через зеркало, ни с GitHub. Проверьте `GHR`, доступ к сети и учётные данные в `~/.netrc`. |
| `... GitHub release (GHR not configured): ...` | Зеркало не задано, а GitHub недоступен. Задайте `GHR`. |
| `download timeout; increase CY_WEIGHTS_DOWNLOAD_TIMEOUT` | Архив не успел скачаться. Увеличьте `CY_WEIGHTS_DOWNLOAD_TIMEOUT`. |
| `CY_WEIGHTS_DOWNLOAD_TIMEOUT must be positive finite seconds` | Значение переменной не является положительным конечным числом. |
| `Invalid GHR Files remote repository root` | Значение `GHR` не подходит как корень зеркала. Проверьте адрес. |
| `archive/member size mismatch`, `archive/member SHA-256 mismatch` | Скачанный файл не совпадает с ожидаемым. Проверьте, что зеркало отдаёт файл без изменений. |
| `Packaged weights manifest is missing; reinstall a release with weights-manifest.json` | Пакет установлен без списка весов. Переустановите CY (см. [Установка](../installation.md)). |

## См. также

- [Установка и окружение](../installation.md)
- [Рабочий каталог](../workspace.md)
- [Модель](../configuration/model.md)
- [Сценарии](../scenarios.md)
