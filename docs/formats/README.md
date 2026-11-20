# Форматы файлов

Здесь описаны файлы, которые команды `cy` читают и записывают. Откройте страницу формата, когда готовите входные данные или разбираете результат запуска.

| Формат | Что это |
| --- | --- |
| [Разметка (ground truth)](ground-truth.md) ([ground truth](../../GLOSSARY.md#ground-truth)) | CSV с рамками (bounding box) объектов, путями к изображениям и split; пишет `cy-ground-truth` или вы сами; вход для обучения, предсказаний, валидации, метрик, сравнения и экспорта |
| [Предсказания](predictions.md) | CSV, который пишут `cy-predict`, `cy-val`, `cy-compare` и этап ([stage](../../GLOSSARY.md#stage)) предсказаний `cy`, и файл `.provenance.json` рядом с ним; вход для `cy-metrics` |
| [Датасеты](datasets.md) | YAML-описание YOLO-датасета для `cy-ground-truth`, ключи `dataset_format` и `dataset_cache_dir`, рабочая копия ([prepared dataset copy](../../GLOSSARY.md#prepared-dataset-copy)) датасета для обучения |
| [Книги Excel](workbooks.md) | Книги Excel (workbook) метрик, отчёта и сравнения, их листы, подпись модели ([model identity](../../GLOSSARY.md#model-identity)) внизу и файлы рядом с ними |
| [Таблица batch size](batch-table.md) ([batch size table](../../GLOSSARY.md#batch-size-table)) | Редактируемый YAML с batch size на GPU, из которого обучение берёт batch, когда он не задан |
