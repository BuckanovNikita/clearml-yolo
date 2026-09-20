"""Pipeline routing rejects conflicting native and stage-owned outputs."""

from __future__ import annotations

from pathlib import Path

import pytest

from clearml_yolo.tasks.pipeline import routed_native


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
        lambda params, tracking: SimpleNamespace(weights=tmp_path / "actual.pt"),
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
