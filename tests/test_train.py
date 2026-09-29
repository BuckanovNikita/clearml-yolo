"""Native training forwards settings and reads actual parent-process outputs."""

import sys
import types
from pathlib import Path
from typing import Any

import pytest

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.dataset import PreparedDataset
from clearml_yolo.tasks.train import train
from native_config_helpers import training_settings


@pytest.mark.parametrize("device", ["cpu", [0, 1]])
def test_native_forwarding_and_actual_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    device: Any,
) -> None:
    calls: dict[str, Any] = {}
    source = tmp_path / "original.yaml"
    source.write_text("path: original\n")
    override = tmp_path / "override.yaml"
    override.write_text("path: override\n")
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.connect_config_file", lambda *args, **kwargs: override
    )
    actual = tmp_path / "native-incremented"
    (actual / "weights").mkdir(parents=True)
    (actual / "weights/best.pt").write_bytes(b"checkpoint")
    (actual / "weights/last.pt").write_bytes(b"last")

    class Model:
        def __init__(self, model: str) -> None:
            calls["model"] = model
            self.task = "detect"
            self.trainer = types.SimpleNamespace(
                save_dir=actual, args=types.SimpleNamespace(), data={}
            )

        def train(self, **kwargs: Any) -> None:
            assert not (Path(kwargs["project"]) / kwargs["name"]).exists()
            calls.update(kwargs)
            self.trainer.args = types.SimpleNamespace(**kwargs)

    module = types.ModuleType("ultralytics.models")
    module.YOLO = Model  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", module)
    monkeypatch.setattr("clearml_yolo.tasks.train.init_task", lambda *a, **k: object())
    monkeypatch.setattr("clearml_yolo.tasks.train.expect_artifacts", lambda *a, **k: None)
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.upload_artifact", lambda *a, **k: None, raising=False
    )
    result = train(
        ultralytics=training_settings()
        | {
            "model": "architecture.pt",
            "data": str(source),
            "device": device,
            "batch": -1,
            "amp": False,
            "compile": False,
            "project": str(tmp_path),
            "name": "asked",
        },
        clearml=ClearMLConfig(),
    )
    assert calls["data"] == str(override)
    assert calls["device"] == device
    assert calls["batch"] == -1
    assert calls["amp"] is False
    assert calls["compile"] is False
    assert result.weights == actual / "weights/best.pt"


def test_csv_training_uses_prepared_data_and_returns_cleaned_ground_truth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared_dir = tmp_path / ".datasets" / "asked"
    data = prepared_dir / "data.yaml"
    cleaned = prepared_dir / "cleaned.csv"
    manifest = prepared_dir / "preparation.json"
    ndjson = prepared_dir / "dataset.ndjson"
    labels = prepared_dir / "labels.zip"
    for path in (data, cleaned, manifest, ndjson, labels):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("prepared\n", encoding="utf-8")
    alternate = tmp_path / "remote-data.yaml"
    alternate.write_text("remote\n", encoding="utf-8")
    calls: dict[str, Any] = {"uploads": [], "connections": []}

    def prepare_dataset(
        source: str | Path,
        directory: Path,
        dataset_format: str = "ndjson",
        required_splits: tuple[str, ...] = ("train", "val"),
    ) -> Any:
        assert source == "source.csv"
        assert directory == prepared_dir
        assert dataset_format == "flat"
        assert required_splits == ("train", "val", "test")
        return PreparedDataset(
            data=data,
            ground_truth=cleaned,
            manifest=manifest,
            dataset_format="flat",
            artifacts=[ndjson, labels],
        )

    monkeypatch.setattr("clearml_yolo.tasks.train.prepare_dataset", prepare_dataset)
    monkeypatch.setattr("clearml_yolo.tasks.train.init_task", lambda *args, **kwargs: object())
    monkeypatch.setattr("clearml_yolo.tasks.train.expect_artifacts", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.connect_config_file",
        lambda *args, **kwargs: calls["connections"].append((args, kwargs)) or alternate,
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.upload_artifact",
        lambda _task, name, value: calls["uploads"].append((name, value)),
    )
    native_dir = tmp_path / "native"
    (native_dir / "weights").mkdir(parents=True)
    (native_dir / "weights" / "best.pt").write_bytes(b"checkpoint")

    class Model:
        def __init__(self, _model: str) -> None:
            self.task = "detect"
            self.trainer = types.SimpleNamespace(
                save_dir=native_dir, args=types.SimpleNamespace(), data={}
            )

        def train(self, **kwargs: Any) -> None:
            calls["native"] = kwargs
            self.trainer.args = types.SimpleNamespace(**kwargs)

    module = types.ModuleType("ultralytics.models")
    module.YOLO = Model  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", module)

    result = train(
        ultralytics=training_settings()
        | {
            "model": "architecture.pt",
            "data": "stale.yaml",
            "project": str(tmp_path),
            "name": "asked",
        },
        clearml=ClearMLConfig(),
        ground_truth="source.csv",
        dataset_format="flat",
        required_splits=["train", "val", "test"],
    )

    assert calls["native"]["data"] == str(data)
    assert calls["connections"][0][0][1:] == ("dataset_configuration", data)
    assert calls["connections"][0][1]["allow_remote_override"] is False
    assert {name for name, _ in calls["uploads"]} >= {
        "dataset_preparation",
        "dataset_ground_truth",
        "dataset_ndjson",
        "dataset_labels",
        "train_data_overrides",
    }
    assert result.cleaned_ground_truth == cleaned
    assert result.dataset_reference == data


def test_csv_training_rejects_preparation_directory_outside_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("clearml_yolo.tasks.train.init_task", lambda *args, **kwargs: object())
    monkeypatch.setattr("clearml_yolo.tasks.train.expect_artifacts", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.prepare_dataset",
        lambda *args, **kwargs: pytest.fail("escaped path must not reach dataset preparation"),
    )

    with pytest.raises(ValueError, match="run-owned dataset directory"):
        train(
            ultralytics=training_settings() | {"project": str(tmp_path), "name": "../outside"},
            clearml=ClearMLConfig(),
            ground_truth="source.csv",
        )


def test_native_ddp_children_inherit_tracking_isolation() -> None:
    import os
    import subprocess

    from clearml_yolo.native_runtime import native_runtime

    with native_runtime():
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from ultralytics.utils import SETTINGS; "
                    "from ultralytics.utils.callbacks import clearml; "
                    "assert SETTINGS['clearml'] is False; assert not clearml.callbacks"
                ),
            ],
            env=dict(os.environ, LOCAL_RANK="-1"),
            capture_output=True,
            text=True,
            check=False,
        )
    assert result.returncode == 0, result.stderr


def test_training_has_no_implicit_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("clearml_yolo.tasks.train.init_task", lambda *args, **kwargs: object())
    with pytest.raises(ValueError, match=r"ultralytics\.model"):
        train(training_settings(model=None), ClearMLConfig())


def test_native_data_training_rejects_non_detection_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import clearml_yolo.tasks.train as training

    monkeypatch.setattr(training, "init_task", lambda *args, **kwargs: object())
    monkeypatch.setattr(training, "expect_artifacts", lambda *args, **kwargs: None)
    monkeypatch.setattr(training, "upload_artifact", lambda *args, **kwargs: None)
    module = types.ModuleType("ultralytics.models")
    module.YOLO = lambda *args, **kwargs: types.SimpleNamespace(task="segment")  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", module)
    with pytest.raises(ValueError, match="detection model"):
        train(training_settings(project=str(tmp_path), name="native", data=None), ClearMLConfig())


def test_implicit_training_name_uses_active_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from clearml_yolo.tasks import train as module

    task = SimpleNamespace(name="renamed/task", id="id", get_project_name=lambda: "project")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "init_task", lambda *a, **k: task)
    monkeypatch.setattr(module, "expect_artifacts", lambda *a: None)

    def capture(_task: object, settings: dict[str, Any], *args: Any) -> Any:
        assert settings["name"] == "renamed%2Ftask"
        assert settings["project"] == str(tmp_path / "runs/project/renamed%2Ftask-id/detect")
        raise RuntimeError("captured routing")

    monkeypatch.setattr(module, "_prepare_csv_dataset", capture)
    with pytest.raises(RuntimeError, match="captured routing"):
        train(training_settings(), ClearMLConfig(task_name="requested"), ground_truth="truth.csv")
