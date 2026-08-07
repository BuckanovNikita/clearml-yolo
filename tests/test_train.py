"""What the training stage forwards to ultralytics, and where it reads the checkpoint from.

Training itself never runs here: a fake YOLO records the call and writes the checkpoint
ultralytics would have written, which is enough to pin the settings and the save-directory
handling without a GPU.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import pytest

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.gpu import AutoGpuConfig, DeviceSelection
from clearml_yolo.tasks.train import CHECKPOINT, train

DISABLED = ClearMLConfig(enabled=False)


class FakeTrainer:
    def __init__(self, save_dir: Path) -> None:
        self.save_dir = save_dir


class FakeYolo:
    """Records the training call and lays down the checkpoint ultralytics would write."""

    last: FakeYolo | None = None
    save_root: Path

    def __init__(self, model: str) -> None:
        self.model = model
        self.kwargs: dict[str, Any] = {}
        self.trainer: FakeTrainer | None = None
        FakeYolo.last = self

    def train(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        save_dir = FakeYolo.save_root / str(kwargs["name"])
        (save_dir / "weights").mkdir(parents=True, exist_ok=True)
        (save_dir / "weights" / "best.pt").write_bytes(b"trained")
        self.trainer = FakeTrainer(save_dir)


@pytest.fixture(autouse=True)
def fake_ultralytics(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = types.ModuleType("ultralytics.models")
    module.YOLO = FakeYolo  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", module)
    FakeYolo.save_root = tmp_path / "runs"


def _train(devices: list[int] | str, tmp_path: Path) -> dict[str, Any]:
    selection = DeviceSelection(devices=devices, batch=16, batch_per_gpu=16)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "clearml_yolo.tasks.train.resolve_devices", lambda *_args, **_kwargs: selection
        )
        train(
            model="yolo11n.pt",
            data="data.yaml",
            epochs=1,
            imgsz=640,
            batch=16,
            project=str(tmp_path / "runs"),
            name="run",
            auto_gpu=AutoGpuConfig(),
            clearml=DISABLED,
        )
    return FakeYolo.last.kwargs  # type: ignore[union-attr]


def test_a_gpu_run_trains_in_mixed_precision_and_compiles(tmp_path: Path) -> None:
    """Training's half precision is AMP — the weights themselves cannot be cast — and a run
    is long enough that compilation is paid once and amortised over every epoch."""
    kwargs = _train([0], tmp_path)

    assert kwargs["amp"] is True
    assert kwargs["compile"] is True


def test_a_cpu_run_asks_for_neither(tmp_path: Path) -> None:
    kwargs = _train("cpu", tmp_path)

    assert kwargs["amp"] is False
    assert kwargs["compile"] is False


def test_train_kwargs_win_over_the_defaults(tmp_path: Path) -> None:
    """Both change the numbers a run produces, so reproducing an older run must opt out."""
    selection = DeviceSelection(devices=[0], batch=16, batch_per_gpu=16)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "clearml_yolo.tasks.train.resolve_devices", lambda *_args, **_kwargs: selection
        )
        train(
            model="yolo11n.pt",
            data="data.yaml",
            epochs=1,
            imgsz=640,
            batch=16,
            project=str(tmp_path / "runs"),
            name="run",
            auto_gpu=AutoGpuConfig(),
            clearml=DISABLED,
            train_kwargs={"amp": False, "compile": False},
        )

    kwargs = FakeYolo.last.kwargs  # type: ignore[union-attr]
    assert kwargs["amp"] is False
    assert kwargs["compile"] is False


def test_the_checkpoint_comes_from_the_trainer_not_the_requested_name(tmp_path: Path) -> None:
    """Ultralytics may deduplicate the run name, and only it knows where the file went."""
    result = _train([0], tmp_path)

    assert result["name"] == "run"
    assert FakeYolo.last.trainer is not None  # type: ignore[union-attr]


def test_the_checkpoint_template_names_the_file_training_writes(tmp_path: Path) -> None:
    """The pipeline predicts this path when training is skipped, so a template that drifts
    from the layout training uses would point a skipped run at a file nobody wrote."""
    selection = DeviceSelection(devices=[0], batch=16, batch_per_gpu=16)
    project = str(tmp_path / "runs")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "clearml_yolo.tasks.train.resolve_devices", lambda *_args, **_kwargs: selection
        )
        result = train(
            model="yolo11n.pt",
            data="data.yaml",
            epochs=1,
            imgsz=640,
            batch=16,
            project=project,
            name="run",
            auto_gpu=AutoGpuConfig(),
            clearml=DISABLED,
        )

    assert str(result.weights) == CHECKPOINT.format(project=project, name="run")
