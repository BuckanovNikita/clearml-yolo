"""Shared inert declarations for utility command parsing and Russian help reference.

Parser construction neither initializes runtime environments nor invokes applications.
The original English argparse text remains stable; Russian semantics are separate metadata.
"""

# ruff: noqa: RUF001 -- Public configuration documentation is intentionally Russian.

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OptionDeclaration:
    flags: tuple[str, ...]
    kwargs: dict[str, Any]
    description: str
    examples: tuple[str, ...]


def integer_list(value: str) -> tuple[int, ...]:
    try:
        result = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use comma-separated integer values") from error
    if not result or len(set(result)) != len(result) or min(result) < 0:
        raise argparse.ArgumentTypeError("Values must be unique nonnegative integers")
    return result


_HELP = OptionDeclaration(
    ("-h", "--help"),
    {"action": "help", "default": argparse.SUPPRESS, "help": "show this help message and exit"},
    "Показать справку команды и завершить работу без её выполнения.",
    ("--help",),
)

OPTION_DECLARATIONS: dict[str, tuple[OptionDeclaration, ...]] = {
    "cy-init-config": (
        _HELP,
        OptionDeclaration(
            ("directory",),
            {"help": "directory for example YAML configurations"},
            "Каталог с примерами YAML или кэш изображений; назначение определяется командой.",
            ("configs",),
        ),
        OptionDeclaration(
            ("--command",),
            {
                "choices": (
                    "cy",
                    "cy-train",
                    "cy-predict",
                    "cy-val",
                    "cy-metrics",
                    "cy-report",
                    "cy-compare",
                    "cy-ground-truth",
                    "cy-export",
                ),
                "default": "cy",
                "help": "execution command to configure (default: cy)",
            },
            "Команда CY, для которой создаётся редактируемое дерево YAML.",
            ("--command cy-train",),
        ),
        OptionDeclaration(
            ("--force",),
            {"action": "store_true", "help": "overwrite existing example files"},
            "Разрешить замену уже существующих файлов примеров.",
            ("--force",),
        ),
        OptionDeclaration(
            ("--model",),
            {"help": "model preset (default: ultralytics; Faster R-CNN for cy-export)"},
            "Пресет модели backend/preset; по умолчанию Ultralytics, для экспорта — Faster R-CNN.",
            ("--model rfdetr/small",),
        ),
    ),
    "cy-dedup": (
        _HELP,
        OptionDeclaration(
            ("directory",),
            {
                "nargs": "?",
                "type": Path,
                "help": (
                    "cache to scan (default: CY_HOME/.cache or .cache in the current directory)"
                ),
            },
            "Каталог с примерами YAML или кэш изображений; назначение определяется командой.",
            ("configs",),
        ),
        OptionDeclaration(
            ("--dry-run",),
            {
                "action": "store_true",
                "help": "report duplicate candidates without creating or replacing files",
            },
            "Показать кандидатов на дедупликацию без создания и замены файлов.",
            ("--dry-run",),
        ),
    ),
    "cy-batch-estimate": (
        _HELP,
        OptionDeclaration(
            ("--imgsz",),
            {"type": int, "required": True, "help": "nominal square training resolution"},
            "Обязательное положительное квадратное разрешение измерения обучающего пакета.",
            ("--imgsz 640",),
        ),
        OptionDeclaration(
            ("--classes",),
            {"type": int, "default": 150, "help": "synthetic classes (default: 150)"},
            "Положительное число классов синтетической нагрузки.",
            ("--classes 150",),
        ),
        OptionDeclaration(
            ("--objects-per-image",),
            {"type": int, "default": 300, "help": "synthetic objects (default: 300)"},
            "Количество синтетических объектов на изображение для измерения памяти.",
            ("--objects-per-image 300",),
        ),
        OptionDeclaration(
            ("--models",),
            {"help": "comma-separated model presets or YOLO asset names; default: all"},
            (
                "Модели через запятую: зарегистрированные пресеты или имена YOLO; без"
                " параметра измеряются все."
            ),
            ("--models rfdetr/small",),
        ),
        OptionDeclaration(
            ("--devices",),
            {"type": integer_list, "help": "ordered logical visible CUDA indexes; default: all"},
            "Уникальные неотрицательные логические индексы видимых CUDA-устройств через запятую.",
            ("--devices 0,1",),
        ),
        OptionDeclaration(
            ("--gpu-counts",),
            {
                "type": integer_list,
                "help": (
                    "report recommendations for first N selected GPUs; no extra searches;"
                    " default: 1..all"
                ),
            },
            (
                "Положительное количество первых выбранных GPU для экстраполяции; "
                "отдельные поиски не запускаются."
            ),
            ("--gpu-counts 1,2",),
        ),
        OptionDeclaration(
            ("--refresh",),
            {"action": "store_true", "help": "repeat completed compatible cases"},
            "Повторить уже завершённые совместимые измерения вместо использования кэша.",
            ("--refresh",),
        ),
        OptionDeclaration(
            ("--memory-budget",),
            {
                "type": float,
                "default": 0.9,
                "help": "fraction of each GPU's total memory (default: 0.9)",
            },
            "Доля полной памяти GPU, доступная измеряемому запуску, строго больше 0 и не больше 1.",
            ("--memory-budget 0.9",),
        ),
        OptionDeclaration(
            ("--search-limit",),
            {
                "type": int,
                "default": 1024,
                "help": (
                    "per-GPU search ceiling (default: 1024); extrapolated global batches "
                    "may exceed it"
                ),
            },
            (
                "Положительный верхний предел поиска пакета на одном GPU; "
                "экстраполированные пакеты могут быть больше."
            ),
            ("--search-limit 1024",),
        ),
        OptionDeclaration(
            ("--trial-timeout",),
            {"type": float, "default": 300, "help": "seconds per fresh trial group (default: 300)"},
            "Положительный таймаут одной свежей группы проб в секундах.",
            ("--trial-timeout 300",),
        ),
    ),
    "cy-download-weights": (_HELP,),
    "cy-docs": (
        _HELP,
        OptionDeclaration(
            ("--port",),
            {"type": int, "default": 0, "help": "local port (default: choose an available port)"},
            "Порт локального сервера от 0 до 65535; 0 выбирает свободный порт.",
            ("--port 8765",),
        ),
        OptionDeclaration(
            ("--no-browser",),
            {"action": "store_true", "help": "print the URL without opening a browser"},
            "Напечатать адрес локального сайта без открытия браузера.",
            ("--no-browser",),
        ),
        OptionDeclaration(
            ("--check",),
            {
                "action": "store_true",
                "help": "check packaged documentation without starting a server",
            },
            "Проверить полноту справочника, материалы и примеры без запуска сервера.",
            ("--check",),
        ),
    ),
}

COMMAND_DESCRIPTIONS: dict[str, str] = {
    "cy-init-config": "CLI: initialize a directory with editable example configurations.",
    "cy-dedup": "Reflink identical, same-named cache images without starting application services.",
    "cy-batch-estimate": (
        "Measure single-GPU training capacity and extrapolate selected allocations."
    ),
    "cy-download-weights": (
        "Prepare supported named model weights in their native discovery caches."
    ),
    "cy-docs": "Open the local Russian configuration reference and tutorials.",
}

_PROGRAMS: dict[str, str | None] = {
    "cy-init-config": None,
    "cy-dedup": None,
    "cy-batch-estimate": "cy-batch-estimate",
    "cy-download-weights": "cy-download-weights",
    "cy-docs": "cy-docs",
}


def parser_for(command: str) -> argparse.ArgumentParser:
    """Build a fresh parser without importing or executing the command implementation."""
    parser = argparse.ArgumentParser(
        prog=_PROGRAMS[command], description=COMMAND_DESCRIPTIONS[command], add_help=False
    )
    for option in OPTION_DECLARATIONS[command]:
        parser.add_argument(*option.flags, **option.kwargs)
    return parser
