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


def _params(tmp_path: Path, **overrides: Any) -> dict[str, Any]:
    """A train.yaml-shaped block: the keys the run decides are null unless overridden."""
    return {
        "model": "yolo11n.pt",
        "data": "data.yaml",
        "epochs": 1,
        "imgsz": 640,
        "batch": 16,
        "project": str(tmp_path / "runs"),
        "name": "run",
        "amp": None,
        "compile": None,
        **overrides,
    }


def _train(devices: list[int] | str, tmp_path: Path, **overrides: Any) -> dict[str, Any]:
    selection = DeviceSelection(devices=devices, batch=16, batch_per_gpu=16)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "clearml_yolo.tasks.train.resolve_devices", lambda *_args, **_kwargs: selection
        )
        train(
            ultralytics=_params(tmp_path, **overrides),
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


def test_a_value_in_the_config_wins_over_the_defaults(tmp_path: Path) -> None:
    """Both change the numbers a run produces, so reproducing an older run must opt out."""
    kwargs = _train([0], tmp_path, amp=False, compile=False)

    assert kwargs["amp"] is False
    assert kwargs["compile"] is False


def test_every_other_ultralytics_param_reaches_the_trainer_untouched(tmp_path: Path) -> None:
    """The block is the whole of ultralytics' configuration, not a list this stage knows."""
    kwargs = _train([0], tmp_path, lr0=0.5, mosaic=0.0, optimizer="AdamW", patience=3)

    assert kwargs["lr0"] == 0.5
    assert kwargs["mosaic"] == 0.0
    assert kwargs["optimizer"] == "AdamW"
    assert kwargs["patience"] == 3


def test_the_model_reaches_the_constructor_and_not_the_training_call(tmp_path: Path) -> None:
    """Ultralytics lets a `model=` keyword win over the object it was asked to build, so
    passing it both ways is two answers to which checkpoint this run started from."""
    kwargs = _train([0], tmp_path)

    assert "model" not in kwargs
    assert FakeYolo.last.model == "yolo11n.pt"  # type: ignore[union-attr]


def test_an_unnamed_run_lands_in_the_experiment_it_belongs_to(tmp_path: Path) -> None:
    """`name` unset means the ClearML task name, so the run directory always says which
    experiment produced it rather than saying `train` for every one of them."""
    kwargs = _train([0], tmp_path, name=None)

    assert kwargs["name"] == DISABLED.task_name


def test_the_project_is_anchored_to_the_working_directory(tmp_path: Path) -> None:
    """A relative project is otherwise resolved against ultralytics' own runs_dir."""
    kwargs = _train([0], tmp_path, project="runs/detect")

    assert Path(kwargs["project"]).is_absolute()
    assert kwargs["project"].endswith("runs/detect")


def test_a_run_nobody_gave_a_directory_names_one_after_itself(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`cy-train` is a run of its own, and two of them in one folder trained into the same
    `runs/detect/<task name>` — with `exist_ok` set, the second start deletes the first
    run's checkpoints rather than landing beside them. So an unset project is a directory
    named after the experiment, the machine and the moment, exactly as `cy` names one."""
    monkeypatch.chdir(tmp_path)

    project = Path(_train([0], tmp_path, project=None)["project"])

    assert project.name == "detect"
    assert project.parent.parent == (tmp_path / "runs").resolve()
    assert project.parent.name.startswith(DISABLED.task_name)


def test_a_run_that_names_its_own_directory_repoints_latest_at_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The link is how every later standalone command finds this run: `cy-predict` loads
    `runs/latest/detect/<task name>/weights/best.pt` with no weights named, and before the
    training stage moved the link that path was the pipeline's last run — so inference
    silently scored a model this command never trained."""
    monkeypatch.chdir(tmp_path)

    project = Path(_train([0], tmp_path, project=None)["project"])

    assert (tmp_path / "runs" / "latest").is_symlink()
    assert (tmp_path / "runs" / "latest").resolve() == project.parent


def test_a_run_told_where_to_write_moves_no_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Which is what the pipeline does to every stage: one directory for the whole run,
    named once by the run and not again by each stage. A stage that repointed `latest`
    from inside a run would name the run's training directory as the run itself."""
    monkeypatch.chdir(tmp_path)

    _train([0], tmp_path, project=str(tmp_path / "elsewhere"))

    assert not (tmp_path / "runs" / "latest").exists()


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
            ultralytics=_params(tmp_path, project=project),
            auto_gpu=AutoGpuConfig(),
            clearml=DISABLED,
        )

    assert str(result.weights) == CHECKPOINT.format(project=project, name="run")
