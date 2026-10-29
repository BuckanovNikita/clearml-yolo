# Предсказания, метрики и сравнение

## Предварительные условия

Нужны CSV с непересекающимися `val` и `test`, обученные веса, доступ к ClearML и
рабочий каталог внутри `CY_HOME`. Подготовьте их по [первому уроку](quickstart.html)
и [уроку обучения](training.html). В примерах `./best.pt` — реальный YOLO-чекпойнт;
замените путь на полученный при обучении. Для других семейств выберите `model=...`
и `model.predict.device` вместо `ultralytics_predict.device`.

## Пример

### Сохранить предсказания отдельно

```bash
cy-predict weights=./best.pt ground_truth=./tutorial-data/ground_truth.csv \
  'splits=[val,test]' ultralytics_predict.device=cpu \
  output=./prediction/predictions.csv model_label=tutorial-yolo fiftyone.enabled=false \
  clearml.project_name=cy-tutorial clearml.task_name=predict 'clearml.tags=[tutorial,predict]'
```

[splits](/#field=splits) выбирает изображения. [image_name](/#field=image_name)
оставьте `name` для дальнейшей оценки. `stem` и `path` допустимы только для сырого
экспорта и не поддерживаются оценкой. CSV содержит имя изображения, строковый
класс, confidence и абсолютные пиксельные координаты. Отсутствие детекций на
изображении допустимо; его принадлежность набору известна из ground truth.

[ultralytics_predict.conf](/#field=ultralytics_predict.conf) — фильтр вывода модели,
а не итоговый калиброванный порог класса. Слишком высокий фильтр заранее удалит
детекции, необходимые для анализа precision/recall. Стандартное низкое значение
`0.001` сохраняет кандидатов для дальнейшей оценки.

### Оценить уже сохранённый CSV

```bash
cy-metrics ground_truth=./tutorial-data/ground_truth.csv \
  predictions=./prediction/predictions.csv 'splits=[val,test]' \
  output_dir=./metrics model_label=tutorial-yolo fiftyone.enabled=false \
  calibration_split=val evaluation.iou_threshold=0.5 \
  clearml.project_name=cy-tutorial clearml.task_name=metrics 'clearml.tags=[tutorial,metrics]'
```

Эта команда не запускает модель. [calibration_split](/#field=calibration_split)
должен быть `val`: пороги подбираются на валидации и без изменений применяются к
`test`. Предсказания должны включать калибровочную выборку даже при
`splits=[test]`. Подбор порогов по test нарушает контракт и отклоняется.

[evaluation.iou_threshold](/#field=evaluation.iou_threshold),
[evaluation.matching_strategy](/#field=evaluation.matching_strategy) и
[evaluation.ap_method](/#field=evaluation.ap_method) описывают оценку; они отличаются
от NMS IoU при инференсе. Изменяя метод, применяйте одинаковый протокол к обеим
моделям. Предобработка оценки включается отдельно через
[evaluation.preprocess](/#field=evaluation.preprocess), а nullable-пороги
предобработки не следует подменять итоговыми per-class thresholds.

Для инференса и оценки одной командой:

```bash
cy-val weights=./best.pt ground_truth=./tutorial-data/ground_truth.csv \
  'splits=[val,test]' model_label=tutorial-yolo ultralytics_predict.device=cpu \
  output_dir=./validation clearml.project_name=cy-tutorial \
  clearml.task_name=validate 'clearml.tags=[tutorial,validation]'
```

У `cy-val` нет группы `fiftyone`. Валидация всё равно использует `val` для
калибровки, если в списке оцениваемых выборок оставить только `test`.

### Сравнить baseline и candidate

После двух завершённых экспериментов с сохранёнными весами и порогами:

```bash
cy-compare ground_truth=./tutorial-data/ground_truth.csv \
  baseline_model.task_id=BASELINE_TASK_ID candidate_model.task_id=CANDIDATE_TASK_ID \
  ultralytics_predict.device=cpu output_dir=./comparison \
  clearml.project_name=cy-tutorial clearml.task_name=compare 'clearml.tags=[tutorial,comparison]'
```

Замените ID реальными задачами. Обе модели заново предсказывают на одинаковых
текущих test-изображениях. Исторические показатели не подменяют новую оценку.
[inference.reuse_existing](/#field=inference.reuse_existing) разрешает совместимый
кэш; его наличие не даёт права использовать другие изображения или настройки.

Для локальных моделей сохраните YAML со ссылками. Значения thresholds ниже
показаны как форма: замените их **точной** картой, полученной при калибровке каждой
модели; не используйте один произвольный порог для обоих чекпойнтов.

```yaml
baseline_model:
  source: local
  weights: ./baseline/best.pt
  label: baseline-yolo
  thresholds: {square: 0.37}
candidate_model:
  source: local
  weights: ./candidate/best.pt
  label: candidate-yolo
  thresholds: {square: 0.42}
```

Смотрите [baseline_model.thresholds](/#field=baseline_model.thresholds) и
[candidate_model.thresholds](/#field=candidate_model.thresholds). Числа в примере
не являются измерением этого урока. Для внешних native-весов без встроенного
описания также нужны согласованные backend, preset, class_names и preprocessing.
Смешанные семейства поддерживаются через отдельные ссылки на модели.

### Построить отчёты и открыть FiftyOne

```bash
cy-report comparison_dir=./comparison output_dir=./reports \
  clearml.project_name=cy-tutorial clearml.task_name=reports 'clearml.tags=[tutorial,reports]'
```

[comparison_dir](/#field=comparison_dir) должен содержать манифест и обе оценённые
книги сравнения. Для своего шаблона задайте
[report_config_path](/#field=report_config_path). Для старого манифеста без
идентичности предусмотрены `baseline_label` и `candidate_label`.

FiftyOne — отдельная необязательная публикация изображений и оценок. В командах
с группой [fiftyone.enabled](/#field=fiftyone.enabled) можно включить её после
настройки сервера и media-доступа. Датасет и его evaluation keys указаны в
опубликованной конфигурации; приложение просмотра открывается отдельно. Для
нативного просмотра CY-оценок требуется установленный на сервере/backend плагин
`@clearml-yolo/evaluation`; публикация не устанавливает его автоматически.
Работа с выборкой в App не означает автоматического пересчёта исходного отчёта.

## Ожидаемый результат

`cy-predict` сохраняет CSV и sidecar происхождения, но сам не оценивает модель.
`cy-metrics` и `cy-val` создают frozen thresholds, книги метрик и графики;
standalone metrics не регистрирует новую модель. Сравнение создаёт
`comparison_manifest.json`, парные оценённые книги и таблицы сравнения. Отчётный
шаг создаёт технический и бизнес-отчёты XLSX.

## Частые ошибки

- Нет val-предсказаний: добавьте `val` при инференсе, даже если интересует только test.
- Неизвестные имена изображений: используйте canonical basename и исходный ground truth.
- Нет происхождения: задайте [model_label](/#field=model_label) для локальных
  входов; это подпись, а не выдуманный ID обучающей задачи.
- Hash mismatch: перенесите исходные CSV/веса вместе с их sidecar; не редактируйте
  подписанные результаты на месте. Книги для повторного использования пересоздавайте.
- FiftyOne недоступен: необязательная публикация выдаёт предупреждение;
  обязательная загрузка в ClearML по-прежнему должна завершиться успешно.

## Проверка

Сопоставьте `gt_csv` и `predicts_csv` с исходными строками и выборками; сохраните
`.identity.json` и `.provenance.json`. Сверьте пороги val с применёнными test-порогами,
checkpoint identity и настройки обеих моделей. Откройте confusion matrix и test
precision-recall; отсутствие GT и отсутствие предсказаний — разные случаи.
Для сравнения проверьте одинаковое текущее image membership, обе книги и манифест;
для отчётов — реальные созданные XLSX и опубликованные артефакты.
