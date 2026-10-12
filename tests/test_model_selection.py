"""Model selection rejects ambiguous recipes before native imports or admission."""

import subprocess
import sys

import pytest
from pydantic import ValidationError

from clearml_yolo.core.models import ModelConfig, model_preset


@pytest.mark.parametrize(
    ("selection", "backend", "preset", "size"),
    [
        ("deimv2/s", "deimv2", "s", 640),
        ("rfdetr/nano", "rfdetr", "nano", 384),
        ("rfdetr/large", "rfdetr", "large", 704),
        ("fasterrcnn/dinov2_small", "fasterrcnn", "dinov2_small", 800),
    ],
)
def test_selected_recipe_supplies_backend_and_native_resolution(
    selection: str, backend: str, preset: str, size: int
) -> None:
    model = model_preset(selection)
    assert (model.backend, model.preset, model.train.imgsz) == (backend, preset, size)


@pytest.mark.parametrize(
    "values",
    [
        {"backend": "rfdetr", "preset": "resnet50_fpn"},
        {"backend": "rfdetr", "preset": "small", "train": {"epohs": 1}},
        {"backend": "deimv2", "preset": "s", "predict": {"batch": 0}},
        {"backend": "fasterrcnn", "preset": "swin_tiny", "train": {"device": True}},
        {"backend": "rfdetr", "preset": "nano", "train": {"imgsz": 65}},
        {"backend": "fasterrcnn", "preset": "resnet50_fpn", "predict": {"conf": 1.1}},
    ],
)
def test_invalid_model_configuration_fails_before_execution(values: dict[str, object]) -> None:
    with pytest.raises((ValueError, ValidationError)):
        ModelConfig.model_validate(values)


def test_model_configuration_does_not_import_native_sdks() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; from clearml_yolo.core.models import model_preset; "
                "model_preset('rfdetr/small'); "
                "heavy = {'torch', 'torchvision', 'rfdetr', 'timm', 'clearml'}; "
                "assert not heavy & sys.modules.keys()"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
