"""Malformed native boxes must not stop project evaluation workflows."""

from functools import partial
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.comparison.evaluation_payload import EvaluationPayload
from clearml_yolo.comparison.reinfer import reinfer_split
from clearml_yolo.comparison.scoring import EvaluationConfig
from clearml_yolo.publishing.models import FiftyOneConfig
from clearml_yolo.tasks.compare import SettledInference, _scored
from clearml_yolo.tasks.metrics import MetricsResult, compute_metrics
from clearml_yolo.tasks.val import validate
from native_config_helpers import prediction_config

BOX_COLUMNS = ["bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]
PRED_COLUMNS = ["image_name", "instance_label", *BOX_COLUMNS, "confidence"]


def _inputs(tmp_path: Path) -> tuple[pd.DataFrame, Path]:
    rows = []
    for split in ("val", "test"):
        image = tmp_path / f"{split}.jpg"
        image.write_bytes(b"native inference is replaced in these tests")
        rows.append((image.name, str(image), "cat", 0, 0, 10, 10, split))
    truth = pd.DataFrame(
        rows, columns=["image_name", "image_path", "instance_label", *BOX_COLUMNS, "split"]
    )
    path = tmp_path / "ground_truth.csv"
    truth.to_csv(path, index=False)
    return truth, path


def _predictions(image_names: list[str], all_invalid: bool) -> pd.DataFrame:
    rows: list[tuple[object, ...]] = []
    for name in image_names:
        rows.extend(
            [
                (name, "cat", 0, 0, 0, 10, 0.99),
                (name, "cat", 10, 0, 0, 10, 0.99),
                (name, "cat", None, 0, 10, 10, 0.99),
                (name, "cat", "invalid", 0, 10, 10, 0.99),
                (name, "cat", 0, 0, float("inf"), 10, 0.99),
            ]
        )
        if not all_invalid:
            rows.extend([(name, "cat", 0, 0, 10, 10, 0.9), (name, "cat", 20, 20, 30, 30, 0.9)])
    return pd.DataFrame(rows, columns=PRED_COLUMNS)


def _assert_payload(payload: EvaluationPayload, all_invalid: bool) -> None:
    assert len(payload.ground_truth) == 1
    assert payload.ground_truth[0].status == ("FN" if all_invalid else "TP")
    assert len(payload.predictions) == (0 if all_invalid else 2)
    assert sorted(match.status for match in payload.matches) == (
        ["FN"] if all_invalid else ["FP", "TP"]
    )
    for match in payload.matches:
        if match.pred_index is not None:
            box = next(box for box in payload.predictions if box.index == match.pred_index)
            assert box.status == match.status
            assert box.image_name == payload.image_names[0]
            assert box.box == ((0, 0, 10, 10) if match.status == "TP" else (20, 20, 30, 30))


def _assert_metrics(result: MetricsResult, all_invalid: bool) -> None:
    dashboard = pd.read_excel(result.dashboards["test"], index_col=0)
    assert cast(pd.Series, dashboard.loc["cat", ["tp", "fp", "fn"]]).tolist() == (
        [0, 0, 1] if all_invalid else [1, 1, 0]
    )
    payload = EvaluationPayload.model_validate_json(result.evaluations["test"].read_text())
    _assert_payload(payload, all_invalid)


@pytest.mark.parametrize("all_invalid", [False, True], ids=["mixed", "all-invalid"])
def test_metrics_scores_valid_boxes_without_rewriting_raw_csv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, all_invalid: bool
) -> None:
    _, truth_path = _inputs(tmp_path)
    predictions = tmp_path / "predictions.csv"
    _predictions(["val.jpg", "test.jpg"], all_invalid).to_csv(predictions, index=False)
    original = predictions.read_bytes()
    monkeypatch.setattr("clearml_yolo.tasks.metrics.init_task", lambda *_args, **_kwargs: None)

    result = compute_metrics(
        predictions,
        truth_path,
        tmp_path / "metrics",
        clearml=ClearMLConfig(),
        evaluation=EvaluationConfig(),
        splits=["test"],
        fiftyone=FiftyOneConfig(enabled=False),
    )

    assert predictions.read_bytes() == original
    _assert_metrics(result, all_invalid)


@pytest.mark.parametrize("imgsz", [640, 960])
@pytest.mark.parametrize("all_invalid", [False, True], ids=["mixed", "all-invalid"])
def test_validation_routes_native_invalid_boxes_through_real_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, imgsz: int, all_invalid: bool
) -> None:
    _, truth_path = _inputs(tmp_path)
    weights = tmp_path / "weights.pt"
    weights.write_bytes(b"native checkpoint loading is replaced")
    observed_sizes: list[int] = []

    def predictor(_weights: object, paths: list[str], **kwargs: Any) -> pd.DataFrame:
        observed_sizes.append(kwargs["imgsz"])
        return _predictions([Path(path).name for path in paths], all_invalid)

    for module in ("val", "predict", "metrics"):
        monkeypatch.setattr(f"clearml_yolo.tasks.{module}.init_task", lambda *_a, **_kw: None)
    monkeypatch.setattr("clearml_yolo.inference.trained_imgsz", lambda _weights: 640)
    monkeypatch.setattr("clearml_yolo.tasks.predict.predict_on_images", predictor)
    destination = tmp_path / "validation"

    result = validate(
        weights,
        truth_path,
        destination,
        clearml=ClearMLConfig(),
        ultralytics={},
        ultralytics_predict=prediction_config(imgsz=imgsz, device="cpu"),
        evaluation=EvaluationConfig(),
        splits=["test"],
    )

    assert observed_sizes == [imgsz, imgsz]
    raw = pd.read_csv(destination / "predictions.csv")
    assert len(raw) == (10 if all_invalid else 14)
    assert raw["bbox_x_tl"].eq("invalid").sum() == 2
    _assert_metrics(result, all_invalid)


@pytest.mark.parametrize("imgsz", [640, 960])
@pytest.mark.parametrize("all_invalid", [False, True], ids=["mixed", "all-invalid"])
def test_comparison_scores_invalid_native_output_and_preserves_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, imgsz: int, all_invalid: bool
) -> None:
    truth, _ = _inputs(tmp_path)
    source_truth = truth.copy(deep=True)
    observed_sizes: list[int] = []
    expected = _predictions(["test.jpg"], all_invalid)

    def predictor(_weights: object, paths: list[str], **kwargs: Any) -> pd.DataFrame:
        assert [Path(path).name for path in paths] == ["test.jpg"]
        observed_sizes.append(kwargs["imgsz"])
        return expected.copy(deep=True)

    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.reinfer_split",
        partial(reinfer_split, predictor=predictor, class_names=lambda _weights: {0: "cat"}),
    )
    output = tmp_path / "predictions.csv"
    evaluated, _, evidence, archive = _scored(
        tmp_path / "weights.pt",
        truth,
        "test",
        output,
        tmp_path,
        "candidate",
        SettledInference(
            conf=0.001,
            iou=0.7,
            imgsz=imgsz,
            batch=1,
            device="cpu",
            image_name="name",
            reuse_existing=False,
        ),
        {"cat": 0.5},
        ["cat"],
        evaluation=EvaluationConfig(),
    )

    assert observed_sizes == [imgsz]
    assert evidence.effective_args["imgsz"] == imgsz
    assert archive.is_file()
    assert output.read_text() == expected.to_csv(index=False)
    pd.testing.assert_frame_equal(truth, source_truth)
    counts = evaluated.outcome.counts["cat"]
    assert (counts.tp, counts.fp, counts.fn) == ((0, 0, 1) if all_invalid else (1, 1, 0))
    if all_invalid:
        assert evaluated.metrics["cat"].ap50 == 0
    else:
        assert evaluated.metrics["cat"].ap50 > 0.9
    _assert_payload(evaluated.evaluation_payload, all_invalid)


def test_filtered_predictions_still_score_raw_map_identically_to_clean_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, truth_path = _inputs(tmp_path)
    dirty = _predictions(["val.jpg", "test.jpg"], all_invalid=False)
    clean = dirty[dirty["confidence"] == 0.9].copy()
    monkeypatch.setattr("clearml_yolo.tasks.metrics.init_task", lambda *_args, **_kwargs: None)
    dashboards: list[pd.DataFrame] = []
    for name, frame in (("dirty", dirty), ("clean", clean)):
        path = tmp_path / f"{name}.csv"
        frame.to_csv(path, index=False)
        original = path.read_bytes()
        result = compute_metrics(
            path,
            truth_path,
            tmp_path / name,
            clearml=ClearMLConfig(),
            evaluation=EvaluationConfig(preprocess_preds_conf_threshold=0.95),
            splits=["test"],
            fiftyone=FiftyOneConfig(enabled=False),
        )
        assert path.read_bytes() == original
        _assert_metrics(result, all_invalid=True)
        dashboards.append(pd.read_excel(result.dashboards["test"], index_col=0))
    pd.testing.assert_frame_equal(dashboards[0], dashboards[1])
    assert cast(float, dashboards[0].loc["cat", "ap50"]) > 0.9
