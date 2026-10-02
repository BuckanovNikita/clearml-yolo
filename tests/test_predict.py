"""The predict stage records the scale it inferred at, not only the boxes it found."""

import sys
import types
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from clearml_yolo import artifact_names
from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.inference import PREDICTION_COLUMNS
from clearml_yolo.publishing.models import FiftyOneConfig, PublicationReceipt
from clearml_yolo.tasks import predict as predict_module
from clearml_yolo.tasks.predict import predict
from native_config_helpers import prediction_config


@pytest.fixture
def checkpoint_recording(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Stand in for the checkpoint reader, which would otherwise need a real .pt file."""

    def _record(train_args: dict[str, Any]) -> None:
        module = types.ModuleType("ultralytics.nn.tasks")
        module.torch_safe_load = lambda path: ({"train_args": train_args}, path)  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "ultralytics.nn.tasks", module)

    return _record


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> dict[str, pd.DataFrame]:
    """Everything the stage would have published to ClearML, keyed by section/series."""
    tables: dict[str, pd.DataFrame] = {}

    def report_table(_: object, title: str, series: str, frame: pd.DataFrame) -> None:
        tables[f"{title}/{series}"] = frame

    monkeypatch.setattr(predict_module, "report_table", report_table)
    monkeypatch.setattr(predict_module, "init_task", lambda *_a, **_k: object())
    monkeypatch.setattr(predict_module, "publish_table", lambda *_a, **_k: None)
    monkeypatch.setattr(predict_module, "record_run_configuration", lambda *_a, **_k: None)
    monkeypatch.setattr(predict_module, "resolve_weights", lambda weights: weights)
    monkeypatch.setattr(
        predict_module, "predict_on_images", lambda *_, **__: pd.DataFrame({"image_name": []})
    )
    return tables


def _ground_truth(tmp_path: Path) -> Path:
    truth = tmp_path / "ground_truth.csv"
    truth.write_text("image_path,split\na.png,test\n")
    return truth


def _predict(tmp_path: Path, imgsz: int | None) -> Any:
    return predict(
        weights="best.pt",
        ground_truth=_ground_truth(tmp_path),
        output=tmp_path / "predictions.csv",
        clearml=ClearMLConfig(),
        ultralytics={},
        ultralytics_predict=prediction_config(imgsz=imgsz, device="cpu", batch=1),
        fiftyone=FiftyOneConfig(enabled=False),
    )


def test_the_scale_inference_ran_at_reaches_the_run_record(
    tmp_path: Path, checkpoint_recording: Any, published: dict[str, pd.DataFrame]
) -> None:
    """ClearML captures the warning in the console log, where an hour of a run buries it.
    The table is the same fact somewhere a reviewer can find it later."""
    checkpoint_recording({"imgsz": 1280})

    _predict(tmp_path, 640)

    section = f"{artifact_names.PREDICT_SECTION}/{artifact_names.RESOLUTION_SERIES}"
    rows = published[section]
    assert dict(zip(rows["parameter"], rows["value"], strict=True)) == {
        "trained at imgsz": "1280",
        "requested inference imgsz": "640",
        "same requested size?": "different requested size; compare the normalized predictor target",
    }


def test_the_resolution_travels_with_the_predictions(
    tmp_path: Path, checkpoint_recording: Any, published: dict[str, pd.DataFrame]
) -> None:
    """The report stage publishes numbers measured at this scale, and reopening the
    checkpoint to ask a second time is how the two would come to disagree."""
    checkpoint_recording({"imgsz": 1280})

    result = _predict(tmp_path, 1280)

    assert result.predictions == tmp_path / "predictions.csv"
    assert result.resolution.scored_at == 1280
    assert not result.resolution.was_trained_elsewhere


def test_splits_are_inferred_separately_for_reproducible_test_batches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    checkpoint_recording: Any,
    published: dict[str, pd.DataFrame],
) -> None:
    checkpoint_recording({"imgsz": 64})
    truth = tmp_path / "truth.csv"
    truth.write_text("image_path,split\nz.png,val\na.png,test\nb.png,test\n")
    calls: list[list[str]] = []

    def infer(_: object, paths: list[str], **kwargs: Any) -> pd.DataFrame:
        calls.append(paths)
        assert kwargs["project"] == str(tmp_path / "native")
        assert kwargs["name"] == "predict"
        return pd.DataFrame({"image_name": paths})

    monkeypatch.setattr(predict_module, "predict_on_images", infer)
    predict(
        "best.pt",
        truth,
        tmp_path / "pred.csv",
        ClearMLConfig(),
        {},
        ["val", "test"],
        ultralytics_predict=prediction_config(),
        fiftyone=FiftyOneConfig(enabled=False),
    )
    assert calls == [["z.png"], ["a.png", "b.png"]]


def test_prediction_preflights_before_compute_and_publishes_exact_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    checkpoint_recording: Any,
    published: dict[str, pd.DataFrame],
) -> None:
    checkpoint_recording({"imgsz": 64})
    task = types.SimpleNamespace(id="predict-task")
    events: list[str] = []
    requests: list[Any] = []

    class FakePublisher:
        enabled = True

        def preflight(self) -> None:
            events.append("preflight")

        def publish(self, request: Any) -> PublicationReceipt:
            events.append("publish")
            requests.append(request)
            return PublicationReceipt(
                dataset_complete=True,
                run_complete=True,
                payload_paths={},
                published_at=datetime(2026, 9, 29, tzinfo=UTC),
                dataset_name="clearml-yolo-fixture",
                task_id="predict-task",
                run_key="predict-task",
                ground_truth_sha256="ground-truth-hash",
                source_ground_truth_sha256="ground-truth-hash",
                dataset_reused=False,
                sample_count=1,
                fields={"predictions": "predictions_predict-task"},
            )

    monkeypatch.setattr(predict_module, "init_task", lambda *_a, **_k: task)
    monkeypatch.setattr(predict_module, "create_publisher", lambda _config: FakePublisher())

    def infer(*_: Any, **__: Any) -> pd.DataFrame:
        events.append("compute")
        return pd.DataFrame({"image_name": []})

    monkeypatch.setattr(predict_module, "predict_on_images", infer)
    monkeypatch.setattr(
        "clearml_yolo.tasks.publication.record_run_configuration", lambda *_args: None
    )
    truth = _ground_truth(tmp_path)

    predict(
        weights="best.pt",
        ground_truth=truth,
        output=tmp_path / "predictions.csv",
        clearml=ClearMLConfig(),
        ultralytics={},
        splits=["test"],
        ultralytics_predict=prediction_config(imgsz=64, device="cpu", batch=1),
        fiftyone=FiftyOneConfig(),
    )

    assert events == ["preflight", "compute", "publish"]
    request = requests[0]
    assert request.task_id == "predict-task"
    assert request.ground_truth == truth
    assert request.source_ground_truth is None
    assert request.predictions == tmp_path / "predictions.csv"
    assert request.prediction_splits == ["test"]
    assert request.evaluations == {}
    assert request.metadata == {"model": "best.pt"}
    assert (tmp_path / "fiftyone_publication.json").is_file()


def test_prediction_satisfies_its_registered_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    checkpoint_recording: Any,
    published: dict[str, pd.DataFrame],
) -> None:
    checkpoint_recording({"imgsz": 64})
    published_names: list[str] = []
    monkeypatch.setattr(
        predict_module, "publish_table", lambda task, name, value: published_names.append(name)
    )
    monkeypatch.setattr(
        predict_module,
        "record_run_configuration",
        lambda *_args: None,
    )
    _predict(tmp_path, 64)
    assert published_names == [artifact_names.PREDICTIONS, "ground_truth"]


def test_empty_prediction_output_has_canonical_header_and_is_published(
    tmp_path: Path,
    checkpoint_recording: Any,
    published: dict[str, pd.DataFrame],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkpoint_recording({"imgsz": 64})
    tables: dict[str, Path] = {}
    monkeypatch.setattr(
        predict_module, "publish_table", lambda _task, name, path: tables.setdefault(name, path)
    )

    result = _predict(tmp_path, 64)

    assert set(tables) == {"ground_truth", artifact_names.PREDICTIONS}
    assert list(pd.read_csv(result.predictions)) == PREDICTION_COLUMNS


def test_prediction_settings_use_resolved_group_and_produced_checkpoint() -> None:
    from clearml_yolo.native_config import prediction_settings

    settings = prediction_settings(
        prediction_config(batch=4, conf=0.001, imgsz=640),
        "best.pt",
    )
    assert settings["model"] == "best.pt"
    assert settings["batch"] == 4
    assert settings["imgsz"] == 640
    assert "epochs" not in settings


def test_prediction_explicit_model_conflict_fails() -> None:
    from clearml_yolo.native_config import prediction_settings

    with pytest.raises(ValueError, match=r"ultralytics_predict\.model"):
        prediction_settings(prediction_config(model="different.pt"), "best.pt")


def test_prediction_autobatch_requires_override() -> None:
    from clearml_yolo.native_config import prediction_settings

    with pytest.raises(ValueError, match="batch"):
        prediction_settings(prediction_config(batch=-1), "best.pt")


@pytest.mark.parametrize(("weights", "expected"), [("best.pt", "best.pt"), (None, None)])
def test_prediction_model_uses_explicit_weights_or_resolved_null(
    weights: str | None, expected: str | None
) -> None:
    from clearml_yolo.native_config import prediction_settings

    assert (
        prediction_settings(prediction_config(model=None), weights)["model"]
        == expected
    )


def test_source_cannot_override_ground_truth_membership() -> None:
    from clearml_yolo.native_config import prediction_settings

    with pytest.raises(ValueError, match="ground_truth"):
        prediction_settings(prediction_config(source="different-images.txt"))


def test_native_failure_preserves_replay_config_and_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    checkpoint_recording: Any,
    published: dict[str, pd.DataFrame],
) -> None:
    import yaml

    checkpoint_recording({"imgsz": 64})

    def fail(*args: Any, **kwargs: Any) -> pd.DataFrame:
        raise RuntimeError("native failure")

    monkeypatch.setattr(predict_module, "predict_on_images", fail)
    with pytest.raises(RuntimeError, match="native failure"):
        _predict(tmp_path, 64)
    settings = yaml.safe_load((tmp_path / "ultralytics_predict.yaml").read_text())
    assert settings["model"] == "best.pt"
    assert Path(settings["source"]).is_file()


@pytest.mark.parametrize("changed", [False, True])
def test_prediction_run_records_only_meaningful_native_changes(
    tmp_path: Path,
    checkpoint_recording: Any,
    published: dict[str, pd.DataFrame],
    monkeypatch: pytest.MonkeyPatch,
    changed: bool,
) -> None:
    checkpoint_recording({"imgsz": 64})
    recorded: list[dict[str, Any]] = []
    monkeypatch.setattr(
        predict_module, "record_run_configuration", lambda _t, values: recorded.append(values)
    )

    def infer(*_args: Any, **settings: Any) -> pd.DataFrame:
        frame = pd.DataFrame(columns=PREDICTION_COLUMNS)
        frame.attrs["effective_args"] = {"augment": changed}
        frame.attrs["normalized_imgsz"] = [96, 96] if changed else [64, 64]
        return frame

    monkeypatch.setattr(predict_module, "predict_on_images", infer)
    _predict(tmp_path, 64)
    result = recorded[0]["prediction_result"]
    assert result["model"] == "best.pt"
    assert "requested" not in result
    assert "effective" not in result
    changes = result["native_normalization"]
    assert "device" not in changes
    assert "batch" not in changes
    if changed:
        assert changes["augment"] == {"requested": False, "effective": True}
        assert changes["imgsz"] == {"requested": 64, "effective": [96, 96]}
    else:
        assert changes == {}
