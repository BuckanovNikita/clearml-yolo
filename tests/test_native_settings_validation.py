"""Effect-free native preflight rejects requests that the native parser rejects."""

from typing import Any

import pytest

from clearml_yolo.adapters.yolo.config import execution_settings, native_defaults, stage_settings


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("conf", 2.0),
        ("iou", -0.1),
        ("fraction", 0),
        ("fraction", True),
        ("fraction", [1, 0]),
        ("fraction", [0.5, 1.5]),
        ("scale", [0.5]),
        ("save", 1),
        ("epochs", 0),
        ("max_det", 0),
        ("seed", -1),
        ("workers", 1.5),
        ("warmup_epochs", "bad"),
        ("compile", 2),
        ("optimizer", 3),
        ("amp", "broken"),
        ("amp", None),
        ("quantize", "invalid"),
        ("epochs", None),
    ],
)
def test_native_values_fail_before_runtime(key: str, value: Any) -> None:
    settings = stage_settings(native_defaults(), "train") | {"mode": "train", key: value}
    with pytest.raises((TypeError, ValueError), match=key):
        execution_settings(settings, "train")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("conf", None),
        ("conf", 0),
        ("conf", 1),
        ("iou", 0),
        ("iou", 1),
        ("fraction", 0.5),
        ("fraction", 2),
        ("fraction", [2, 3, 0]),
        ("fraction", [0.5, 1.0]),
        ("scale", [0.5, 2.0]),
        ("batch", -1),
        ("batch", 0.5),
        ("patience", 0),
        ("save_period", -1),
        ("workers", 0),
        ("compile", "max-autotune"),
        ("amp", "BF16"),
        ("amp", False),
        ("quantize", "w8a16"),
        ("quantize", "int8"),
        ("quantize", 16),
    ],
)
def test_valid_native_edge_values_are_preserved(key: str, value: Any) -> None:
    settings = stage_settings(native_defaults(), "train") | {"mode": "train", key: value}
    assert execution_settings(settings, "train")[key] == value
