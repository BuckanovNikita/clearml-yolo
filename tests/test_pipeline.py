"""Pipeline routing rejects conflicting native and stage-owned outputs."""

from pathlib import Path
from typing import Any

import pytest

from clearml_yolo.clearml_session import ClearMLConfig
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
    monkeypatch.setattr(pipeline, "upload_artifact", lambda *a, **k: None)
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
        return SimpleNamespace(best_confidences={"val": {"cat": 0.5}, "test": {"cat": 0.5}})

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
        "upload_artifact",
        lambda _task, name, value: calls["uploads"].append((name, value)),
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
        return SimpleNamespace(best_confidences={"val": {"cat": 0.5}})

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
    )

    assert calls["truth"] == [cleaned, cleaned]
    assert (
        "predict_data_overrides",
        {
            "ultralytics_predict": {
                "classes": {"requested": [0], "effective": None},
            },
        },
    ) in calls["uploads"]
