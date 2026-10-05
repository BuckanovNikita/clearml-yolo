"""Native training forwards settings and reads actual parent-process outputs."""

import sys
import types
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.dataset import PreparedDataset
from clearml_yolo.dataset_export import DatasetFormat
from clearml_yolo.tasks.train import TrainResult, train
from native_config_helpers import training_settings


@pytest.fixture(autouse=True)
def native_publication_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.native_ddp_relay",
        lambda *a: nullcontext(types.SimpleNamespace(replay=lambda trainer: None)),
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.finalize_native_model", lambda *a: None, raising=False
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.record_run_configuration", lambda *a: None, raising=False
    )
    monkeypatch.setattr("clearml_yolo.tasks.train.register_ground_truth", lambda *a, **k: None)


def test_missing_ground_truth_is_rejected_before_task_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.init_task",
        lambda *_args, **_kwargs: pytest.fail("missing input must fail before task creation"),
    )

    with pytest.raises(TypeError, match="ground_truth"):
        train(training_settings(), ClearMLConfig())  # type: ignore[call-arg]


def test_train_result_requires_prepared_dataset_paths(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        TrainResult(weights=tmp_path / "best.pt", save_dir=tmp_path)  # type: ignore[call-arg]


@pytest.mark.parametrize("dataset_format", ["ndjson", "flat"])
@pytest.mark.parametrize("device", ["cpu", [0, 1]])
def test_csv_training_uses_prepared_data_and_returns_cleaned_ground_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dataset_format: DatasetFormat,
    device: Any,
) -> None:
    expected_format = dataset_format
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

    @contextmanager
    def cached_dataset(
        source: str | Path,
        cache_dir: Path,
        dataset_format: str = "ndjson",
        required_splits: tuple[str, ...] = ("train", "val"),
    ) -> Iterator[PreparedDataset]:
        assert source == "source.csv"
        assert cache_dir == tmp_path.parent / (tmp_path.name + "-cache")
        assert dataset_format == expected_format
        assert required_splits == ("train", "val", "test")
        calls["locked"] = True
        yield PreparedDataset(
            data=data,
            ground_truth=cleaned,
            manifest=manifest,
            dataset_format=expected_format,
            artifacts=[ndjson, labels],
        )

        calls["locked"] = False

    monkeypatch.setattr("clearml_yolo.tasks.train.cached_dataset", cached_dataset, raising=False)
    monkeypatch.setattr("clearml_yolo.tasks.train.init_task", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.expect_artifacts", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.connect_config_file",
        lambda *args, **kwargs: calls["connections"].append((args, kwargs)) or alternate,
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.register_ground_truth",
        lambda _task, truth, **kwargs: calls["uploads"].append((truth, kwargs["output_dir"])),
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
            assert calls["locked"]
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
            "device": device,
            "batch": -1,
            "amp": False,
            "compile": False,
            "project": str(tmp_path),
            "name": "asked",
        },
        clearml=ClearMLConfig(),
        ground_truth="source.csv",
        dataset_format=dataset_format,
        dataset_cache_dir=tmp_path.parent / (tmp_path.name + "-cache"),
        required_splits=["train", "val", "test"],
    )

    assert calls["native"]["data"] == str(data)
    assert calls["native"]["device"] == device
    assert calls["native"]["batch"] == -1
    assert calls["native"]["amp"] is False
    assert calls["native"]["compile"] is False
    assert calls["connections"][0][0][1:] == ("dataset", data)
    assert calls["connections"][0][1]["allow_remote_override"] is False
    assert calls["uploads"] == [(cleaned, tmp_path)]
    assert calls["locked"] is False
    assert result.weights == native_dir / "weights/best.pt"
    assert result.cleaned_ground_truth == cleaned
    assert result.dataset_reference == data


def test_csv_training_rejects_preparation_directory_outside_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("clearml_yolo.tasks.train.init_task", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.expect_artifacts", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.cached_dataset",
        lambda *args, **kwargs: pytest.fail("escaped path must not reach dataset preparation"),
        raising=False,
    )

    with pytest.raises(ValueError, match="training output directory"):
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
        train(training_settings(model=None), ClearMLConfig(), ground_truth="truth.csv")


def test_csv_training_rejects_non_detection_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import clearml_yolo.tasks.train as training

    module = types.ModuleType("ultralytics.models")
    module.YOLO = lambda *args, **kwargs: types.SimpleNamespace(task="segment")  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", module)
    prepared = PreparedDataset(
        data=tmp_path / "data.yaml",
        ground_truth=tmp_path / "ground_truth.csv",
        manifest=tmp_path / "preparation.json",
        dataset_format="ndjson",
        artifacts=[],
    )
    with pytest.raises(ValueError, match="detection model"):
        training._execute_training(
            object(),
            "model.pt",
            training_settings(project=str(tmp_path), name="native", data=str(prepared.data)),
            prepared,
        )


def test_implicit_training_name_uses_active_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from clearml_yolo.tasks import train as module

    task = SimpleNamespace(name="renamed/task", id="id", get_project_name=lambda: "project")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.setattr(module, "init_task", lambda *a, **k: task)
    monkeypatch.setattr(module, "expect_artifacts", lambda *a: None, raising=False)

    def capture(_task: object, settings: dict[str, Any], *args: Any) -> Any:
        assert settings["name"] == "renamed%2Ftask"
        assert settings["project"] == str(tmp_path / "runs/project/renamed%2Ftask-id/detect")
        raise RuntimeError("captured routing")

    monkeypatch.setattr(module, "_prepare_csv_dataset", capture)
    with pytest.raises(RuntimeError, match="captured routing"):
        train(training_settings(), ClearMLConfig(task_name="requested"), ground_truth="truth.csv")


@pytest.mark.parametrize("explicit", [False, True])
def test_cache_cannot_live_inside_training_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, explicit: bool
) -> None:
    from clearml_yolo.tasks.train import _prepare_csv_dataset

    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.cached_dataset",
        lambda *a, **k: pytest.fail("run-owned cache must be rejected before preparation"),
    )
    with (
        pytest.raises(ValueError, match="outside the run-owned training project"),
        _prepare_csv_dataset(
            object(),
            {"project": str(tmp_path), "name": "train"},
            "source.csv",
            "ndjson",
            None,
            tmp_path / "cache" if explicit else None,
        ),
    ):
        pytest.fail("unsafe cache accepted")


def test_native_ddp_events_replay_before_model_finalization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.tasks.train import _execute_training

    events: list[str] = []
    directory = tmp_path / "train"
    (directory / "weights").mkdir(parents=True)
    (directory / "weights/best.pt").write_bytes(b"native checkpoint")

    class Model:
        def __init__(self, _architecture: object) -> None:
            self.task = "detect"
            self.trainer = types.SimpleNamespace(save_dir=directory)

        def train(self, **settings: Any) -> None:
            events.append("train")
            self.trainer.args = types.SimpleNamespace(**settings)

    @contextmanager
    def relay(_task: object, _model: object) -> Iterator[Any]:
        yield types.SimpleNamespace(replay=lambda _trainer: events.append("replay"))
        events.append("relay_closed")

    module = types.ModuleType("ultralytics.models")
    module.YOLO = Model  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", module)
    monkeypatch.setattr("clearml_yolo.tasks.train.native_ddp_relay", relay, raising=False)
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.finalize_native_model", lambda *args: events.append("finalize")
    )
    prepared = PreparedDataset(
        data=tmp_path / "data.yaml",
        ground_truth=tmp_path / "ground_truth.csv",
        manifest=tmp_path / "preparation.json",
        dataset_format="ndjson",
        artifacts=[],
    )
    _execute_training(
        object(),
        "model.pt",
        training_settings()
        | {"project": str(tmp_path), "name": "train", "data": str(prepared.data)},
        prepared,
    )
    assert events == ["train", "replay", "finalize", "relay_closed"]
