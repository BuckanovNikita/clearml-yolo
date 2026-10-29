"""Russian declarations for the explicitly supported native parameter surface."""

# Russian reference prose intentionally uses Cyrillic letters.
# ruff: noqa: RUF001

import re
from typing import Any

from clearml_yolo.adapters.yolo.config import (
    INACTIVE_KEYS,
    KNOWN_KEYS,
    PREDICT_KEYS,
    TRAIN_KEYS,
    native_defaults,
    native_template,
)
from clearml_yolo.core.documentation import FieldDoc

# Explicit inventory: dependency additions cannot acquire a generic description silently.
MEANINGS = {
    "task": "Тип задачи; CY поддерживает detect (обнаружение объектов).",
    "mode": "Режим нативного запуска: train для обучения, predict для предсказаний.",
    "model": "Архитектура YAML или веса YOLO; для дообучения укажите локальный .pt.",
    "data": "Нативный датасет; CY формирует его из ground_truth и владеет этим значением.",
    "epochs": "Максимальное число эпох обучения.",
    "time": "Ограничение длительности нативного обучения в часах; null отключает лимит.",
    "patience": "Число эпох без улучшения до ранней остановки.",
    "batch": (
        "Размер пакета. Для обучения null выбирает сохранённую совместимую оценку "
        "cy-batch-estimate; без неё запуск завершается ошибкой. Нативные "
        "дробные/отрицательные значения имеют семантику Ultralytics. Для предсказания "
        "нужен положительный integer."
    ),
    "imgsz": (
        "Размер входного изображения; CY по умолчанию использует 960. Предсказание "
        "допускает пару высота/ширина."
    ),
    "save": "Сохранять нативные результаты; публикацией CY управляет владелец запуска.",
    "save_period": "Интервал сохранения промежуточных весов в эпохах; -1 отключает.",
    "cache": (
        "Кэш изображений Ultralytics: false, true, ram или disk; не путать с dataset_cache_dir CY."
    ),
    "device": (
        "Устройство: cpu, индекс CUDA, список индексов или null. Обучение и "
        "предсказание выбирают устройства независимо; -1 использует нативный "
        "автоматический выбор."
    ),
    "workers": "Число процессов загрузки данных.",
    "project": "Нативный корень результатов; маршрутизацией каталога владеет CY.",
    "name": "Нативное имя запуска; итоговый каталог назначает CY.",
    "exist_ok": (
        "Разрешить Ultralytics существующий каталог результата; изоляция запуска "
        "остаётся обязанностью CY."
    ),
    "pretrained": "Использовать предобученную инициализацию: boolean или путь к весам.",
    "optimizer": "Оптимизатор Ultralytics, например auto, SGD или AdamW.",
    "verbose": "Подробный нативный вывод.",
    "seed": "Начальное значение генераторов случайных чисел.",
    "deterministic": "Запросить детерминированные нативные операции.",
    "single_cls": "Объединить классы в один при нативной обработке; CSV-классы контролирует CY.",
    "rect": "Использовать прямоугольные пакеты вместо квадратного дополнения.",
    "cos_lr": "Косинусное расписание learning rate.",
    "close_mosaic": "Отключить Mosaic за указанное число эпох до завершения.",
    "resume": (
        "Продолжение нативного запуска; CSV-обучение CY не поддерживает resume, "
        "используйте fine-tuning весов."
    ),
    "amp": "Смешанная точность: boolean или fp16/bf16/fp32, согласно нативному backend.",
    "fraction": (
        "Доля или количество изображений; допускается список train/val[/test]. "
        "CSV-членством управляет CY."
    ),
    "profile": "Включить нативное профилирование.",
    "freeze": "Заморозить первые N слоёв или список индексов; null не замораживает.",
    "multi_scale": "Диапазон изменения масштаба изображения во время обучения.",
    "compile": (
        "Компиляция PyTorch: boolean или строка режима. CY задаёт true; при проблемах "
        "начните с false."
    ),
    "channels_last": "Использовать формат памяти channels-last в нативном backend.",
    "cls_remap": "Разрешить нативное переназначение классов предобученной головы.",
    "val": "Выполнять внутреннюю нативную валидацию во время обучения.",
    "split": "Нативный раздел валидации; разделами CSV и метрик управляет CY.",
    "save_json": "Сохранять нативные результаты в JSON.",
    "conf": (
        "Минимальная уверенность детекции. Для калибровки CY prediction по умолчанию "
        "0.001; это не порог решения из val."
    ),
    "iou": "Порог IoU для нативного подавления пересекающихся рамок (NMS).",
    "max_det": "Максимальное число детекций на изображение.",
    "quantize": (
        "Нативный режим квантования, например fp32, fp16 или int8; поддержка зависит от "
        "модели/runtime."
    ),
    "nms": "Включить нативное NMS; CY по умолчанию true.",
    "plots": "Создавать нативные графики обучения и валидации.",
    "source": (
        "Нативный источник изображений; в CY членство задаётся ground_truth, значение "
        "должно оставаться null."
    ),
    "dnn": "Использовать OpenCV DNN при поддерживаемом формате модели.",
    "show": "Показывать изображения в нативном графическом окне.",
    "save_txt": "Сохранять нативные детекции в текстовом формате.",
    "save_conf": "Добавлять уверенность в нативный текстовый экспорт.",
    "save_crop": "Сохранять вырезанные области детекций.",
    "show_labels": "Рисовать названия классов на нативных изображениях.",
    "show_conf": "Рисовать уверенность рядом с рамками.",
    "show_boxes": "Рисовать рамки на нативных изображениях.",
    "line_width": "Толщина линии рамки; null выбирает её автоматически.",
    "augment": "Нативная test-time augmentation при предсказании.",
    "agnostic_nms": "Подавлять пересечения независимо от класса.",
    "classes": "Оставить указанные индексы классов; CSV-классы и сравнение контролирует CY.",
    "visualize": "Сохранить визуализацию промежуточных признаков.",
    "lr0": "Начальная learning rate.",
    "lrf": "Множитель конечной learning rate относительно начальной.",
    "momentum": "Momentum SGD или коэффициент beta1 Adam.",
    "weight_decay": "Коэффициент регуляризации весов.",
    "warmup_epochs": "Длительность прогрева в эпохах, допускается дробное число.",
    "warmup_momentum": "Начальный momentum во время прогрева.",
    "warmup_bias_lr": "Начальная learning rate смещений во время прогрева.",
    "distill_model": "Модель-учитель для поддерживаемого нативного обучения с дистилляцией.",
    "dis": "Вес нативной функции потерь дистилляции.",
    "box": "Вес функции потерь локализации рамок.",
    "cls": "Вес функции потерь классификации.",
    "cls_pw": "Степень весов классов при дисбалансе: 0 отключает, 1 задаёт обратную частоту.",
    "dfl": "Вес Distribution Focal Loss.",
    "nbs": "Номинальный размер пакета для нормирования нативной оптимизации.",
    "hsv_h": "Амплитуда случайного изменения оттенка HSV.",
    "hsv_s": "Амплитуда случайного изменения насыщенности HSV.",
    "hsv_v": "Амплитуда случайного изменения яркости HSV.",
    "degrees": "Максимальный угол случайного поворота в градусах.",
    "translate": "Доля случайного сдвига относительно размера изображения.",
    "scale": "Амплитуда изменения масштаба или пара минимального/максимального масштаба.",
    "shear": "Амплитуда случайного сдвига формы в градусах.",
    "perspective": "Амплитуда случайной перспективной деформации.",
    "flipud": "Вероятность вертикального отражения.",
    "fliplr": "Вероятность горизонтального отражения.",
    "bgr": "Вероятность перестановки цветовых каналов RGB/BGR.",
    "mosaic": (
        "Вероятность нативного Mosaic; пользовательский Albumentations заменяет "
        "случайные нативные аугментации."
    ),
    "mixup": "Вероятность смешивания изображений MixUp.",
    "cutmix": "Вероятность смешивания областей CutMix.",
    "augmentations": (
        "Дополнительный нативный список аугментаций; общим Albumentations-конвейером "
        "управляет transforms."
    ),
    "overlap_mask": "Объединение пересекающихся масок сегментации.",
    "mask_ratio": "Масштаб уменьшения масок сегментации.",
    "dropout": "Вероятность dropout классификационной модели.",
    "pose": "Вес функции потерь положения ключевых точек.",
    "kobj": "Вес функции потерь наличия ключевой точки.",
    "rle": "Нативный параметр кодирования/потерь ключевых точек.",
    "angle": "Вес угловой компоненты для ориентированных рамок.",
    "dlog": "Нативный коэффициент задачи depth; для detection не применяется.",
    "dgrad": "Нативный коэффициент градиента depth; для detection не применяется.",
    "dlam": "Параметр дисперсии SILog для depth: 1 — инвариантность масштаба, 0 — log-RMSE.",
    "copy_paste": "Вероятность Copy-Paste для сегментации.",
    "copy_paste_mode": "Режим Copy-Paste для сегментации.",
    "auto_augment": "Стратегия автоматических аугментаций классификации.",
    "erasing": "Вероятность случайного стирания для классификации.",
    "vid_stride": "Шаг кадров видео; CY обрабатывает изображения из CSV.",
    "stream_buffer": "Буфер кадров потока; CY не использует потоковый источник.",
    "embed": "Индексы слоёв embeddings; ненулевое значение не поддерживается detection records CY.",
    "save_frames": "Сохранение кадров видео; не применяется к CSV-предсказаниям.",
    "retina_masks": "Маски сегментации повышенного разрешения.",
    "format": (
        "Нативный формат экспорта Ultralytics; отдельный cy-export имеет собственный контракт."
    ),
    "optimize": "Нативная мобильная оптимизация экспорта.",
    "dynamic": "Динамические размеры нативного экспорта.",
    "simplify": "Упрощение графа при нативном экспорте.",
    "opset": "Версия ONNX opset для нативного экспорта.",
    "workspace": "Нативный workspace TensorRT; cy-export использует export.workspace_gib.",
    "cfg": "Внешний нативный конфиг; CY требует null и использует Hydra-композицию.",
    "tracker": "Конфигурация трекера; трекинг объектов не относится к командам CY.",
}

SHAPES = {
    "device": "integer | string | list[integer] | null",
    "imgsz": "positive integer | list[positive integer]",
    "batch": "number | null (train); positive integer (predict)",
    "model": "string | null",
    "data": "string | null",
    "pretrained": "boolean | string",
    "cache": "boolean | 'ram' | 'disk'",
    "amp": "boolean | 'fp16' | 'bf16' | 'fp32'",
    "compile": "boolean | string",
    "fraction": "number | list[number]",
    "scale": "number | [number, number]",
    "classes": "list[integer] | null",
    "freeze": "integer | list[integer] | null",
    "augmentations": "list[mapping]",
    "quantize": "8 | 16 | 32 | int8 | fp16 | fp32 | w8a8 | w16a16 | w32a32 | w8a16 | w8a32",
}

RANGES = dict.fromkeys(
    [
        "lr0",
        "lrf",
        "cls_pw",
        "momentum",
        "weight_decay",
        "warmup_momentum",
        "warmup_bias_lr",
        "hsv_h",
        "hsv_s",
        "hsv_v",
        "translate",
        "perspective",
        "flipud",
        "fliplr",
        "bgr",
        "mosaic",
        "mixup",
        "cutmix",
        "conf",
        "iou",
        "multi_scale",
    ],
    "Число в диапазоне [0, 1].",
) | {
    "epochs": "Целое не меньше 1.",
    "patience": "Целое не меньше 0.",
    "nbs": "Целое не меньше 1.",
    "max_det": "Целое не меньше 1.",
    "seed": "Целое не меньше 0.",
    "imgsz": "Положительные целые размеры; prediction допускает один или два размера.",
    "fraction": "Положительное количество или доля (0, 1]; список train/val[/test].",
    "scale": "Число [0, 1] или ровно два числовых значения.",
    "cfg": "Только null; внешний нативный cfg запрещён.",
    "embed": "Только null для detection records CY.",
    "task": "Только detect.",
    "mode": "train для обучения; predict для предсказания.",
}


def _upstream_annotations() -> dict[str, tuple[str, str]]:
    result = {}
    for line in native_template().splitlines():
        match = re.match(r"^(\w+):.*?#\s*\(([^)]+)\)\s*(.*)$", line)
        if match:
            result[match[1]] = match[2], match[3]
    return result


def native_fields(commands: list[str]) -> list[FieldDoc]:
    if set(MEANINGS) != KNOWN_KEYS:
        raise ValueError(
            f"Native documentation coverage mismatch: {sorted(set(MEANINGS) ^ KNOWN_KEYS)}"
        )
    defaults: dict[str, Any] = native_defaults() | {"augmentations": []}
    annotations = _upstream_annotations()
    result = []
    for group, active in (("ultralytics", TRAIN_KEYS), ("ultralytics_predict", PREDICT_KEYS)):
        for key in sorted(KNOWN_KEYS):
            value = defaults.get(key)
            inactive = key not in active
            controlled = key in {"task", "mode", "data", "project", "name"} or (
                group == "ultralytics_predict" and key in {"source", "model"}
            )
            applicability = (
                "Не применяется в этом этапе; сохраняется для совместимости нативного YAML."
                if inactive
                else "YOLO: "
                + (
                    "обучение и внутренняя валидация."
                    if group == "ultralytics"
                    else "предсказание."
                )
            )
            if key in INACTIVE_KEYS:
                applicability += " Не относится к detection-сценарию CY."
            if controlled:
                applicability += " Эффективное значение контролирует обёртка CY."
            shape, detail = annotations.get(key, (type(value).__name__, ""))
            result.append(
                FieldDoc(
                    id=f"{group}.{key}",
                    path=f"{group}.{key}",
                    description=MEANINGS[key],
                    shapes=SHAPES.get(key, shape),
                    constraints=(
                        RANGES.get(key, "Проверка установленным нативным backend.")
                        + " Неактивные поля не передаются этапу. "
                        + (f"Пояснение установленного Ultralytics: {detail}" if detail else "")
                    ),
                    applicability=applicability,
                    examples=[value],
                    source=(
                        f"clearml_yolo.adapters.yolo.config:{key}; "
                        "installed ultralytics/cfg/default.yaml"
                    ),
                    commands=commands,
                )
            )
    return result
