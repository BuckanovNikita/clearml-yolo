"""Command publication lifecycle and nested-owner suppression."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.publishing import NoOpPublisher
from clearml_yolo.publishing.models import FiftyOneConfig
from clearml_yolo.tasks.metrics import EvaluationConfig, MetricsResult


def test_worker_publication_is_disabled_without_reading_task_identity(tmp_path: Path) -> None:
    from clearml_yolo.tasks.publication import prepare_publisher, publish_results

    publisher = prepare_publisher(None, FiftyOneConfig(enabled=True))

    assert isinstance(publisher, NoOpPublisher)
    assert (
        publish_results(
            publisher,
            None,
            output_dir=tmp_path / "must-not-be-created",
            ground_truth=tmp_path / "missing.csv",
        )
        is None
    )
    assert not (tmp_path / "must-not-be-created").exists()


def test_validation_disables_nested_prediction_and_metrics_publication(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from clearml_yolo.tasks import val

    nested: list[FiftyOneConfig] = []
    predictions = tmp_path / "predictions.csv"
    expected = MetricsResult(output_dir=tmp_path / "metrics")
    monkeypatch.setattr(val, "init_task", lambda *_args, **_kwargs: SimpleNamespace(id="val-task"))

    def predict(*_args: Any, **kwargs: Any) -> SimpleNamespace:
        nested.append(kwargs["fiftyone"])
        return SimpleNamespace(predictions=predictions)

    def metrics(*_args: Any, **kwargs: Any) -> MetricsResult:
        nested.append(kwargs["fiftyone"])
        return expected

    monkeypatch.setattr(val, "predict", predict)
    monkeypatch.setattr(val, "compute_metrics", metrics)

    result = val.validate(
        weights="best.pt",
        ground_truth=tmp_path / "truth.csv",
        output_dir=tmp_path,
        clearml=ClearMLConfig(),
        ultralytics={},
        evaluation=EvaluationConfig(),
    )

    assert result is expected
    assert len(nested) == 2
    assert all(not config.enabled for config in nested)
