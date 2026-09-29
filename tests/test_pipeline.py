"""Pipeline routing rejects conflicting native and stage-owned outputs."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.publishing.models import FiftyOneConfig, PublicationReceipt
from clearml_yolo.tasks.pipeline import routed_native
from native_config_helpers import prediction_config, training_settings


def test_routing_fills_only_output_ownership(tmp_path: Path) -> None:
    result = routed_native({"device": [0, 1], "batch": -1}, tmp_path, "train")
    assert result == {"device": [0, 1], "batch": -1, "project": str(tmp_path), "name": "train"}


@pytest.mark.parametrize(
    "settings", [{"project": "/different"}, {"name": "different"}, {"save_dir": "/different"}]
)
def test_conflicting_native_routing_fails(tmp_path: Path, settings: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="run_dir"):
        routed_native(settings, tmp_path, "train")


def test_hydra_pipeline_passes_real_stage_objects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace
    from typing import Any

    from hydra import compose, initialize_config_module
    from hydra_zen import store, zen

    import clearml_yolo.configs  # noqa: F401
    from clearml_yolo.tasks import pipeline

    calls: list[Any] = []
    monkeypatch.setattr(pipeline, "init_task", lambda *a, **k: object())
    monkeypatch.setattr(pipeline, "record_run_configuration", lambda *a, **k: None)
    monkeypatch.setattr(pipeline, "point_latest_at", lambda *a: None)
    monkeypatch.setattr(
        pipeline,
        "run_training",
        lambda params, tracking, **kwargs: SimpleNamespace(
            weights=tmp_path / "actual.pt",
            cleaned_ground_truth=tmp_path / "cleaned.csv",
            dataset_reference=tmp_path / "data.yaml",
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "run_prediction",
        lambda *a, **k: SimpleNamespace(predictions=tmp_path / "predictions.csv"),
    )

    def evaluate(*args: object, **kwargs: object) -> SimpleNamespace:
        calls.append(kwargs["evaluation"])
        (tmp_path / "metrics").mkdir()
        return SimpleNamespace(
            best_confidences={"val": {"cat": 0.5}, "test": {"cat": 0.5}}, evaluations={}
        )

    monkeypatch.setattr(pipeline, "compute_metrics", evaluate)
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=[
                f"run_dir={tmp_path}",
                "ground_truth=explicit.csv",
                "skip_compare=true",
                "skip_report=true",
                "fiftyone.enabled=false",
            ],
        )
    result = zen(pipeline.run_pipeline)(config)
    assert result["weights"] == tmp_path / "actual.pt"
    assert calls[0].iou_threshold == 0.5


def test_pipeline_routes_cleaned_truth_and_prediction_policy_after_csv_training(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from clearml_yolo.tasks import pipeline

    cleaned = tmp_path / "cleaned.csv"
    calls: dict[str, Any] = {"truth": [], "uploads": []}
    monkeypatch.setattr(pipeline, "init_task", lambda *args, **kwargs: object())
    monkeypatch.setattr(pipeline, "point_latest_at", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        pipeline,
        "record_run_configuration",
        lambda _task, values: calls["uploads"].extend(values.items()),
    )

    def training(*args: Any, **kwargs: Any) -> SimpleNamespace:
        assert kwargs["ground_truth"] == "source.csv"
        assert kwargs["dataset_format"] == "flat"
        assert kwargs["required_splits"] == ["train", "val", "test"]
        return SimpleNamespace(
            weights=tmp_path / "actual.pt",
            cleaned_ground_truth=cleaned,
            dataset_reference=tmp_path / "data.yaml",
        )

    def prediction(*args: Any, **kwargs: Any) -> SimpleNamespace:
        calls["truth"].append(args[1])
        assert args[4]["classes"] is None
        assert kwargs["ultralytics_predict"]["classes"] is None
        return SimpleNamespace(predictions=tmp_path / "predictions.csv")

    def metrics(*args: Any, **kwargs: Any) -> SimpleNamespace:
        calls["truth"].append(args[1])
        Path(args[2]).mkdir(parents=True)
        return SimpleNamespace(best_confidences={"val": {"cat": 0.5}}, evaluations={})

    monkeypatch.setattr(pipeline, "run_training", training)
    monkeypatch.setattr(pipeline, "run_prediction", prediction)
    monkeypatch.setattr(pipeline, "compute_metrics", metrics)

    pipeline.run_pipeline(
        ultralytics=training_settings()
        | {"model": "architecture.pt", "classes": [1], "task": "detect"},
        ultralytics_predict=prediction_config() | {"classes": [0]},
        metrics={"evaluation": object(), "calibration_split": "val"},
        report={"report_config_path": None},
        compare={"baseline_model": object(), "q": 0.05, "bootstrap_iterations": 1, "seed": 0},
        clearml=ClearMLConfig(),
        ground_truth="source.csv",
        splits=["test"],
        run_dir=tmp_path,
        dataset_format="flat",
        skip_compare=True,
        skip_report=True,
        fiftyone=FiftyOneConfig(enabled=False),
    )

    assert calls["truth"] == [cleaned, cleaned]
    assert (
        "prediction_data_overrides",
        {
            "ultralytics_predict": {
                "classes": {"requested": [0], "effective": None},
            },
        },
    ) in calls["uploads"]


def test_pipeline_preflights_once_and_publishes_effective_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from clearml_yolo.tasks import pipeline
    from clearml_yolo.tasks.metrics import EvaluationConfig

    source = tmp_path / "source.csv"
    source.write_text("image_name,image_path,split\na,a.jpg,val\n", encoding="utf-8")
    cleaned = tmp_path / "cleaned.csv"
    predictions = tmp_path / "predictions.csv"
    evaluation_path = tmp_path / "metrics/evaluation_test.json"
    checkpoint = tmp_path / "detect/train/weights/best.pt"
    task = SimpleNamespace(id="pipeline-task")
    events: list[str] = []
    requests: list[Any] = []
    nested: list[FiftyOneConfig] = []

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
                task_id="pipeline-task",
                run_key="pipeline-task",
                ground_truth_sha256="effective-hash",
                source_ground_truth_sha256="source-hash",
                dataset_reused=False,
                sample_count=1,
                fields={"evaluation_test": "evaluation_test_pipeline-task"},
            )

    monkeypatch.setattr(pipeline, "init_task", lambda *_args, **_kwargs: task)
    monkeypatch.setattr(pipeline, "create_publisher", lambda _config: FakePublisher())
    monkeypatch.setattr(pipeline, "point_latest_at", lambda *_args: None)
    monkeypatch.setattr(pipeline, "record_run_configuration", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "clearml_yolo.tasks.publication.record_run_configuration", lambda *_args: None
    )

    def train(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        events.append("train")
        cleaned.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text("weights", encoding="utf-8")
        return SimpleNamespace(weights=checkpoint, cleaned_ground_truth=cleaned)

    def predict(*_args: Any, **kwargs: Any) -> SimpleNamespace:
        nested.append(kwargs["fiftyone"])
        predictions.write_text("image_name\na\n", encoding="utf-8")
        return SimpleNamespace(predictions=predictions)

    def metrics(*_args: Any, **kwargs: Any) -> SimpleNamespace:
        nested.append(kwargs["fiftyone"])
        evaluation_path.parent.mkdir(parents=True)
        evaluation_path.write_text("{}", encoding="utf-8")
        return SimpleNamespace(
            best_confidences={"test": {"cat": 0.5}},
            evaluations={"test": evaluation_path},
        )

    monkeypatch.setattr(pipeline, "run_training", train)
    monkeypatch.setattr(pipeline, "run_prediction", predict)
    monkeypatch.setattr(pipeline, "compute_metrics", metrics)
    evaluation = EvaluationConfig()

    pipeline.run_pipeline(
        ultralytics=training_settings() | {"model": "architecture.pt"},
        ultralytics_predict=prediction_config(),
        metrics={"evaluation": evaluation, "calibration_split": "val"},
        report={"report_config_path": None},
        compare={"baseline_model": None, "q": 0.05, "bootstrap_iterations": 1, "seed": 0},
        clearml=ClearMLConfig(),
        ground_truth=str(source),
        splits=["test"],
        run_dir=tmp_path,
        skip_compare=True,
        skip_report=True,
        fiftyone=FiftyOneConfig(),
    )

    assert events == ["preflight", "train", "publish"]
    assert len(nested) == 2
    assert all(not config.enabled for config in nested)
    request = requests[0]
    assert request.task_id == "pipeline-task"
    assert request.ground_truth == cleaned
    assert request.source_ground_truth == source
    assert request.predictions == predictions
    assert request.prediction_splits == ["val", "test"]
    assert request.evaluations == {"test": evaluation_path}
    assert request.metadata == {
        "model": str(checkpoint),
        "evaluation": evaluation.model_dump(mode="json") | {"calibration_split": "val"},
    }
    assert (tmp_path / "fiftyone_publication.json").is_file()


@pytest.mark.parametrize("existing", [False, True])
def test_pipeline_publishes_only_existing_predictions_when_prediction_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bool
) -> None:
    from types import SimpleNamespace

    from clearml_yolo.tasks import pipeline
    from clearml_yolo.tasks.metrics import EvaluationConfig

    predictions = tmp_path / "predictions.csv"
    if existing:
        predictions.write_text("image_name\na\n", encoding="utf-8")
    requests: list[Any] = []

    class FakePublisher:
        enabled = True

        def preflight(self) -> None:
            pass

        def publish(self, request: Any) -> PublicationReceipt:
            requests.append(request)
            return PublicationReceipt(
                dataset_complete=True,
                run_complete=True,
                payload_paths={},
                published_at=datetime(2026, 9, 29, tzinfo=UTC),
                dataset_name="fixture",
                task_id="pipeline-task",
                run_key="pipeline-task",
                ground_truth_sha256="hash",
                source_ground_truth_sha256="hash",
                dataset_reused=True,
                sample_count=1,
                fields={},
            )

    monkeypatch.setattr(
        pipeline, "init_task", lambda *_args, **_kwargs: SimpleNamespace(id="pipeline-task")
    )
    monkeypatch.setattr(pipeline, "create_publisher", lambda _config: FakePublisher())
    monkeypatch.setattr(pipeline, "point_latest_at", lambda *_args: None)
    monkeypatch.setattr(
        "clearml_yolo.tasks.publication.record_run_configuration", lambda *_args: None
    )

    pipeline.run_pipeline(
        ultralytics=training_settings(),
        ultralytics_predict=prediction_config(),
        metrics={"evaluation": EvaluationConfig(), "calibration_split": "val"},
        report={"report_config_path": None},
        compare={"baseline_model": None, "q": 0.05, "bootstrap_iterations": 1, "seed": 0},
        clearml=ClearMLConfig(),
        ground_truth=str(tmp_path / "truth.csv"),
        splits=["test"],
        run_dir=tmp_path,
        weights="best.pt",
        skip_train=True,
        skip_predict=True,
        skip_metrics=True,
        skip_compare=True,
        skip_report=True,
        fiftyone=FiftyOneConfig(),
    )

    assert requests[0].predictions == (predictions if existing else None)
    assert requests[0].prediction_splits is None


def test_pipeline_publication_failure_propagates_after_preserving_predictions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from clearml_yolo.tasks import pipeline
    from clearml_yolo.tasks.metrics import EvaluationConfig

    predictions = tmp_path / "predictions.csv"

    class FailingPublisher:
        enabled = True

        def preflight(self) -> None:
            pass

        def publish(self, _request: Any) -> PublicationReceipt:
            raise RuntimeError("publication failed")

    monkeypatch.setattr(
        pipeline, "init_task", lambda *_args, **_kwargs: SimpleNamespace(id="pipeline-task")
    )
    monkeypatch.setattr(pipeline, "create_publisher", lambda _config: FailingPublisher())
    monkeypatch.setattr(pipeline, "point_latest_at", lambda *_args: None)

    def predict(*_args: Any, **kwargs: Any) -> SimpleNamespace:
        assert not kwargs["fiftyone"].enabled
        predictions.write_text("image_name\na\n", encoding="utf-8")
        return SimpleNamespace(predictions=predictions)

    monkeypatch.setattr(pipeline, "run_prediction", predict)

    with pytest.raises(RuntimeError, match="publication failed"):
        pipeline.run_pipeline(
            ultralytics=training_settings(),
            ultralytics_predict=prediction_config(),
            metrics={"evaluation": EvaluationConfig(), "calibration_split": "val"},
            report={"report_config_path": None},
            compare={
                "baseline_model": None,
                "q": 0.05,
                "bootstrap_iterations": 1,
                "seed": 0,
            },
            clearml=ClearMLConfig(),
            ground_truth=str(tmp_path / "truth.csv"),
            splits=["test"],
            run_dir=tmp_path,
            weights="best.pt",
            skip_train=True,
            skip_metrics=True,
            skip_compare=True,
            skip_report=True,
            fiftyone=FiftyOneConfig(),
        )

    assert predictions.read_text(encoding="utf-8") == "image_name\na\n"


@pytest.mark.parametrize("explicit", ["none", "run_dir", "run_id"])
def test_pipeline_uses_active_task_root_and_preserves_explicit_routing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, explicit: str
) -> None:
    from types import SimpleNamespace

    from clearml_yolo.tasks import pipeline

    monkeypatch.chdir(tmp_path)
    task = SimpleNamespace(
        name="actual/task", id="unique-id", get_project_name=lambda: "team/project"
    )
    monkeypatch.setattr(pipeline, "init_task", lambda *a, **k: task)
    monkeypatch.setattr(pipeline, "point_latest_at", lambda *a: None)
    captured: dict[str, Any] = {}

    def predict(*args: Any, **kwargs: Any) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(predictions=args[2])

    monkeypatch.setattr(pipeline, "run_prediction", predict)
    run_dir = tmp_path / "explicit" if explicit == "run_dir" else None
    run_id = "custom" if explicit == "run_id" else None
    result = pipeline.run_pipeline(
        training_settings(),
        prediction_config(),
        {},
        {},
        {},
        ClearMLConfig(),
        "truth.csv",
        run_dir=run_dir,
        run_id=run_id,
        weights="weights.pt",
        skip_train=True,
        skip_metrics=True,
        skip_compare=True,
        skip_report=True,
        fiftyone=FiftyOneConfig(enabled=False),
    )
    expected = {
        "none": tmp_path / "runs/team%2Fproject/actual%2Ftask-unique-id",
        "run_dir": tmp_path / "explicit",
        "run_id": tmp_path / "runs/custom",
    }[explicit]
    assert result["run_dir"] == expected
    assert result["predictions"] == expected / "predictions.csv"
    assert set(captured["splits"]) == {"train", "val", "test"}
    assert captured["fiftyone"].enabled is False
    assert captured["ultralytics_predict"]["project"] == str(expected / "native")


def test_pipeline_comparison_uses_its_native_candidate_source_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from clearml_yolo.tasks import pipeline
    from clearml_yolo.tasks.compare import InferenceConfig, ModelRef
    from clearml_yolo.tasks.metrics import EvaluationConfig

    received: list[ModelRef] = []
    monkeypatch.setattr(
        pipeline, "init_task", lambda *_args, **_kwargs: SimpleNamespace(id="owner")
    )
    monkeypatch.setattr(
        pipeline, "run_comparison", lambda **kwargs: received.append(kwargs["candidate_model"])
    )
    pipeline._compare_and_report(
        {},
        tmp_path / "best.pt",
        {"cat": 0.3},
        tmp_path / "truth.csv",
        tmp_path,
        ClearMLConfig(),
        InferenceConfig(conf=0.001, iou=0.7, imgsz=96, batch=1, device="cpu"),
        EvaluationConfig(),
        {},
        True,
        candidate_task_id="owner",
    )
    assert received[0].source == "clearml"
    assert received[0].task_id == "owner"
    assert received[0].thresholds is None


@pytest.mark.parametrize("explicit", [False, True])
def test_cache_cannot_live_inside_pipeline_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, explicit: bool
) -> None:
    from clearml_yolo.tasks import pipeline

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setattr(pipeline, "init_task", lambda *a, **k: object())
    with pytest.raises(ValueError, match="outside run_dir"):
        pipeline.run_pipeline(
            ground_truth="source.csv",
            ultralytics=training_settings(),
            ultralytics_predict={},
            clearml=ClearMLConfig(),
            run_dir=tmp_path,
            metrics={},
            report={},
            compare={},
            dataset_cache_dir=tmp_path / "cache" if explicit else None,
            fiftyone=FiftyOneConfig(enabled=False),
        )
