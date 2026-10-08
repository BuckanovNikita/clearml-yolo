"""Validation-only calibration and frozen split evaluation."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from clearml_yolo.adapters.clearml.session import ClearMLConfig, invocation
from clearml_yolo.adapters.reporting.workbook_identity import read_dashboard
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.application.use_cases.metrics import (
    EvaluationConfig,
    MetricsResult,
    _prepare,
    compute_metrics,
)
from clearml_yolo.core.publication import FiftyOneConfig, PublicationReceipt, PublicationRequest
from test_clearml_session import FakeTask
from workflow_dependencies import patch_workflow
from workflow_dependencies import (
    workflow_dependencies as workflow_dependencies,  # noqa: PLC0414 - fixture export
)


@contextmanager
def _metric_owner(
    monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> Iterator[FakeTask]:
    from types import SimpleNamespace

    import clearml

    from clearml_yolo.application.use_cases import metrics as module

    task = FakeTask()
    patch_workflow(monkeypatch, workflow_dependencies, clearml.Task, "init", lambda **_kwargs: task)
    patch_workflow(
        monkeypatch, workflow_dependencies, clearml.Task, "get_task", lambda **_kwargs: task
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        task,
        "get_logger",
        lambda: SimpleNamespace(report_plotly=lambda **_kwargs: None),
        raising=False,
    )
    patch_workflow(
        monkeypatch, workflow_dependencies, module, "report_table", lambda *_args, **_kwargs: None
    )
    patch_workflow(
        monkeypatch, workflow_dependencies, module, "report_scalars", lambda *_args: None
    )
    with invocation(ClearMLConfig(), "metrics"):
        yield task


GT_COLUMNS = [
    "image_name",
    "image_path",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
    "split",
]
PRED_COLUMNS = [
    "image_name",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
    "confidence",
]


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    ground_truth = pd.DataFrame(
        [
            ("val.jpg", "/images/val.jpg", "cat", 0, 0, 10, 10, "val"),
            ("test.jpg", "/images/test.jpg", "cat", 0, 0, 10, 10, "test"),
            ("empty.jpg", "/images/empty.jpg", None, None, None, None, None, "test"),
        ],
        columns=GT_COLUMNS,
    )
    predictions = pd.DataFrame(
        [
            ("val.jpg", "cat", 0, 0, 10, 10, 0.8),
            ("val.jpg", "cat", 20, 20, 30, 30, 0.3),
            ("test.jpg", "cat", 0, 0, 10, 10, 0.6),
            ("empty.jpg", "cat", 20, 20, 30, 30, 0.7),
        ],
        columns=PRED_COLUMNS,
    )
    predictions_path = tmp_path / "predictions.csv"
    ground_truth_path = tmp_path / "ground_truth.csv"
    predictions.to_csv(predictions_path, index=False)
    ground_truth.to_csv(ground_truth_path, index=False)
    return (predictions_path, ground_truth_path)


def test_candidate_threshold_is_calibrated_on_val_and_reused_for_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.metrics.init_task",
        lambda *_args, **_kwargs: None,
    )
    result = compute_metrics(
        predictions,
        ground_truth,
        tmp_path / "metrics",
        clearml=ClearMLConfig(),
        evaluation=EvaluationConfig(),
        splits=["val", "test"],
        calibration_split="val",
        fiftyone=FiftyOneConfig(enabled=False),
        model_label="fixture detector",
        deps=workflow_dependencies,
    )
    assert result.best_confidences["val"] == {"cat": 0.8}
    assert result.best_confidences["test"] == {"cat": 0.8}
    test = read_dashboard(result.dashboards["test"], index_col=0)
    assert test.loc["cat", "confidence"] == pytest.approx(0.8)
    assert test.loc["cat", "tp"] == 0
    assert test.loc["cat", "fn"] == 1
    assert test.loc["cat", "fp"] == 0
    for split in ("val", "test"):
        for metric in ("recall", "precision", "perebrak", "nedobrak"):
            assert (tmp_path / "metrics" / f"{metric}_confidence_intervals_{split}.png").is_file()
        assert (tmp_path / "metrics" / f"matrix_{split}.xlsx").is_file()


def test_match_tables_preserve_excel_illegal_characters_in_csv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    frame = pd.read_csv(predictions)
    frame["diagnostic"] = "detail\x01with control character"
    frame.to_csv(predictions, index=False)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.metrics.init_task",
        lambda *_args, **_kwargs: None,
    )
    result = compute_metrics(
        predictions,
        ground_truth,
        tmp_path / "metrics",
        clearml=ClearMLConfig(),
        evaluation=EvaluationConfig(),
        splits=["test"],
        fiftyone=FiftyOneConfig(enabled=False),
        model_label="fixture detector",
        deps=workflow_dependencies,
    )
    matches = pd.read_csv(result.output_dir / "metrics_evaluation_test_prediction_matches.csv")
    assert list(matches["diagnostic"]) == ["detail\x01with control character"] * 4
    assert list(matches["predict_type"]) == ["filtered"] * 4


def test_match_table_larger_than_an_excel_sheet_is_saved_as_csv(
    tmp_path: Path, workflow_dependencies: WorkflowDependencies
) -> None:
    from dataclasses import replace

    from clearml_yolo.application.evaluation import evaluate_split
    from clearml_yolo.application.use_cases.metrics import _write_evaluation_workbook

    predictions_path, truth_path = _write_inputs(tmp_path)
    truth, raw, predictions, classes = _prepare(
        pd.read_csv(predictions_path),
        pd.read_csv(truth_path),
        EvaluationConfig(),
        deps=workflow_dependencies,
    )
    evaluated = evaluate_split(
        truth,
        raw,
        predictions,
        split="test",
        classes=classes,
        thresholds={"cat": 0.8},
        required_classes=classes,
        iou_threshold=0.5,
        matching_strategy="iou_prior",
        ap_method="interp",
        skip_cohen_kappa=True,
        output_dir=tmp_path,
        suffix="test",
        deps=workflow_dependencies,
    )
    rows = 1048577
    evaluated = replace(evaluated, pred_matches=pd.DataFrame({"pred_index": pd.RangeIndex(rows)}))
    workbook = tmp_path / "metrics_evaluation_test.xlsx"
    tables = _write_evaluation_workbook(
        workbook, evaluated, methodology={}, deps=workflow_dependencies
    )
    matches = pd.read_csv(tables["metrics_evaluation_test_prediction_matches"])
    assert len(matches) == rows
    assert matches.iloc[0].to_dict() == {"pred_index": 0}
    assert matches.iloc[-1].to_dict() == {"pred_index": rows - 1}
    assert set(pd.ExcelFile(workbook).sheet_names) == {"summary", "per_class", "confusion_matrix"}


def test_test_only_evaluation_still_requires_validation_membership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    frame = pd.read_csv(ground_truth)
    frame = frame[frame["split"] == "test"]
    frame.to_csv(ground_truth, index=False)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.metrics.init_task",
        lambda *_args, **_kwargs: None,
    )
    with pytest.raises(ValueError, match="calibration split 'val'"):
        compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            clearml=ClearMLConfig(),
            evaluation=EvaluationConfig(),
            splits=["test"],
            calibration_split="val",
            fiftyone=FiftyOneConfig(enabled=False),
            model_label="fixture detector",
            deps=workflow_dependencies,
        )


def test_calibration_split_must_be_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.metrics.init_task",
        lambda *_args, **_kwargs: None,
    )
    with pytest.raises(ValueError, match="exactly 'val'"):
        compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            clearml=ClearMLConfig(),
            evaluation=EvaluationConfig(),
            splits=["test"],
            calibration_split="test",
            fiftyone=FiftyOneConfig(enabled=False),
            model_label="fixture detector",
            deps=workflow_dependencies,
        )


def test_one_image_cannot_belong_to_validation_and_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    frame = pd.read_csv(ground_truth)
    frame.loc[frame["split"] == "test", "image_name"] = "val.jpg"
    frame.to_csv(ground_truth, index=False)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.metrics.init_task",
        lambda *_args, **_kwargs: None,
    )
    with pytest.raises(ValueError, match=r"both val and test.*val\.jpg"):
        compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            clearml=ClearMLConfig(),
            evaluation=EvaluationConfig(),
            splits=["test"],
            fiftyone=FiftyOneConfig(enabled=False),
            model_label="fixture detector",
            deps=workflow_dependencies,
        )


def test_prediction_only_classes_are_preserved_for_false_positive_accounting(
    workflow_dependencies: WorkflowDependencies,
) -> None:
    ground_truth = pd.DataFrame(
        [("val.jpg", "/images/val.jpg", "cat", 0, 0, 10, 10, "val")], columns=GT_COLUMNS
    )
    predictions = pd.DataFrame(
        [("val.jpg", "cat", 0, 0, 10, 10, 0.8), ("val.jpg", "bird", 20, 20, 30, 30, 0.7)],
        columns=PRED_COLUMNS,
    )
    _, raw, prepared, classes = _prepare(
        predictions, ground_truth, EvaluationConfig(), deps=workflow_dependencies
    )
    assert classes == ["bird", "cat"]
    assert list(raw["instance_label"]) == ["cat", "bird"]
    assert list(prepared["instance_label"]) == ["cat", "bird"]


def test_numeric_image_identifiers_remain_text_when_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    prediction_frame = pd.read_csv(predictions).assign(
        image_name=["000000000009", "000000000009", "000000000025", "000000000031"]
    )
    truth_frame = pd.read_csv(ground_truth).assign(
        image_name=["000000000009", "000000000025", "000000000031"]
    )
    prediction_frame.to_csv(predictions, index=False)
    truth_frame.to_csv(ground_truth, index=False)
    seen: dict[str, pd.DataFrame] = {}

    def capture(
        prediction_data: pd.DataFrame,
        truth_data: pd.DataFrame,
        _config: EvaluationConfig,
        *,
        deps: WorkflowDependencies,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
        assert deps is workflow_dependencies
        seen["predictions"] = prediction_data
        seen["ground_truth"] = truth_data
        raise RuntimeError("captured")

    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.metrics.init_task",
        lambda *_args, **_kwargs: None,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.metrics._prepare",
        capture,
    )
    with pytest.raises(RuntimeError, match="captured"):
        compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            clearml=ClearMLConfig(),
            evaluation=EvaluationConfig(),
            splits=["test"],
            fiftyone=FiftyOneConfig(enabled=False),
            model_label="fixture detector",
            deps=workflow_dependencies,
        )
    assert seen["predictions"]["image_name"].iloc[0] == "000000000009"
    assert seen["ground_truth"]["image_name"].iloc[0] == "000000000009"


def test_metrics_preflights_before_scoring_and_publishes_evaluation_payloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    from types import SimpleNamespace

    from clearml_yolo.application.use_cases import metrics as metrics_module

    predictions, ground_truth = _write_inputs(tmp_path)
    task = SimpleNamespace(id="metrics-task")
    events: list[str] = []
    requests: list[PublicationRequest] = []
    original_prepare = metrics_module._prepare

    class FakePublisher:
        enabled = True

        def preflight(self) -> None:
            events.append("preflight")

        def publish(self, request: PublicationRequest) -> PublicationReceipt:
            events.append("publish")
            requests.append(request)
            return PublicationReceipt(
                dataset_complete=True,
                run_complete=True,
                payload_paths={},
                published_at=datetime(2026, 9, 29, tzinfo=UTC),
                dataset_name="fixture",
                task_id="metrics-task",
                run_key="metrics-task",
                ground_truth_sha256="hash",
                source_ground_truth_sha256="hash",
                dataset_reused=False,
                sample_count=3,
                fields={"evaluation_test": "evaluation_test_metrics-task"},
            )

    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        metrics_module,
        "init_task",
        lambda *_args, **_kwargs: task,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        metrics_module,
        "create_publisher",
        lambda _config: FakePublisher(),
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        metrics_module,
        "register_predictions",
        lambda *_args, **_kwargs: None,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        metrics_module,
        "publish_evaluation",
        lambda *_args, **_kwargs: None,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        metrics_module,
        "owned_native_model",
        lambda *_args: None,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        metrics_module,
        "upload_artifact",
        lambda *_args, **_kwargs: None,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        metrics_module,
        "record_run_configuration",
        lambda *_args, **_kwargs: None,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        metrics_module,
        "report_table",
        lambda *_args, **_kwargs: None,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        metrics_module,
        "report_scalars",
        lambda *_args, **_kwargs: None,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.publication.record_run_configuration",
        lambda *_args: None,
    )

    def prepare(*args: Any, **kwargs: Any) -> Any:
        events.append("compute")
        return original_prepare(*args, **kwargs)

    patch_workflow(monkeypatch, workflow_dependencies, metrics_module, "_prepare", prepare)
    evaluation = EvaluationConfig()
    result = compute_metrics(
        predictions,
        ground_truth,
        tmp_path / "metrics",
        clearml=ClearMLConfig(),
        evaluation=evaluation,
        splits=["test"],
        calibration_split="val",
        fiftyone=FiftyOneConfig(),
        model_label="fixture detector",
        deps=workflow_dependencies,
    )
    assert events == ["preflight", "compute", "publish"]
    request = requests[0]
    assert request.task_id == "metrics-task"
    assert request.ground_truth == ground_truth
    assert request.source_ground_truth is None
    assert request.predictions == predictions
    assert request.prediction_splits is None
    assert request.evaluations == result.evaluations
    assert request.metadata == {
        "evaluation": evaluation.model_dump(mode="json") | {"calibration_split": "val"}
    }
    assert (tmp_path / "metrics/fiftyone_publication.json").is_file()


@pytest.mark.parametrize("zero_predictions", [False, True])
def test_metrics_publishes_only_canonical_tables_and_readable_workbooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    zero_predictions: bool,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    truth = pd.read_csv(ground_truth)
    train = truth[truth.split == "val"].assign(
        split="train", image_name="train.jpg", image_path="/images/train.jpg"
    )
    pd.concat([train, truth], ignore_index=True).to_csv(ground_truth, index=False)
    frame = pd.read_csv(predictions)
    train_predictions = frame[frame.image_name == "val.jpg"].assign(image_name="train.jpg")
    frame = pd.concat([train_predictions, frame], ignore_index=True)
    (frame.iloc[:0] if zero_predictions else frame).to_csv(predictions, index=False)
    with _metric_owner(monkeypatch, workflow_dependencies) as task:
        result = compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            ClearMLConfig(),
            EvaluationConfig(),
            fiftyone=FiftyOneConfig(enabled=False),
            model_label="fixture detector",
            deps=workflow_dependencies,
        )
    uploads = {item["name"]: item["artifact_object"] for item in task.uploads}
    _assert_readable_metrics_evidence(result, uploads, zero_predictions)


def _assert_readable_metrics_evidence(
    result: MetricsResult, uploads: dict[str, Any], zero_predictions: bool
) -> None:
    from clearml_yolo.core.evaluation.payload import EvaluationPayload

    assert set(uploads) == {
        "gt_csv",
        "predicts_csv",
        "metrics_best_confidences_val",
        *{
            f"metrics_dashboard_{kind}_{split}"
            for split in ("train", "val", "test")
            for kind in ("full", "dtrk")
        },
    }
    combined = pd.read_csv(uploads["predicts_csv"])
    assert set(combined["split"]) == {"train", "val", "test"}
    assert combined[combined["row_type"] == "predict"].empty == zero_predictions
    assert combined["source_row_id"].notna().all()
    thresholds = uploads["metrics_best_confidences_val"]
    assert isinstance(thresholds, Path)
    assert thresholds.is_file()
    assert list(pd.read_csv(thresholds)) == ["class_name", "confidence"]
    assert pd.read_csv(thresholds).iloc[0].to_dict() == {
        "class_name": "cat",
        "confidence": result.best_confidences["val"]["cat"],
    }
    for split in ("train", "val", "test"):
        workbook = uploads[f"metrics_dashboard_full_{split}"]
        assert workbook == result.dashboards[split]
        assert workbook.is_file()
        original = read_dashboard(workbook, index_col=0)
        assert "cat" in original.index
        dtrk = uploads[f"metrics_dashboard_dtrk_{split}"]
        assert dtrk.is_file()
        assert pd.ExcelFile(dtrk).sheet_names
        payload = EvaluationPayload.model_validate_json(result.evaluations[split].read_text())
        assert payload.schema_version == 1
        assert payload.split == split
        assert payload.thresholds == result.best_confidences[split]
        assert len(payload.ground_truth) == 1
        if zero_predictions:
            assert payload.predictions == []
            assert [
                (match.status, match.gt_index, match.pred_index) for match in payload.matches
            ] == [("FN", 0, None)]
        else:
            for match in payload.matches:
                if match.gt_index is not None:
                    box = next(box for box in payload.ground_truth if box.index == match.gt_index)
                    assert match.gt_label == box.label
                    assert match.status == box.status
                if match.pred_index is not None:
                    box = next(box for box in payload.predictions if box.index == match.pred_index)
                    assert match.pred_label == box.label
                    assert match.confidence == box.confidence
                    assert match.status == box.status
                if match.status == "TP":
                    assert match.iou == 1.0
    assert (
        result.best_confidences["train"]
        == result.best_confidences["val"]
        == result.best_confidences["test"]
    )
    assert "fiftyone_publication" not in uploads


def test_metrics_publishes_frozen_validation_thresholds_even_without_val_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    truth = pd.read_csv(ground_truth)
    unused = truth.iloc[[0]].assign(split="train", image_name="unused.jpg")
    pd.concat([truth, unused], ignore_index=True).to_csv(ground_truth, index=False)
    with _metric_owner(monkeypatch, workflow_dependencies) as task:
        compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            ClearMLConfig(),
            EvaluationConfig(),
            splits=["test"],
            fiftyone=FiftyOneConfig(enabled=False),
            model_label="fixture detector",
            deps=workflow_dependencies,
        )
    assert {item["name"] for item in task.uploads} == {
        "gt_csv",
        "predicts_csv",
        "metrics_best_confidences_val",
        "metrics_dashboard_full_test",
        "metrics_dashboard_dtrk_test",
    }
    combined_path = next(
        item["artifact_object"] for item in task.uploads if item["name"] == "predicts_csv"
    )
    assert set(pd.read_csv(combined_path)["split"]) == {"val", "test"}


def test_validation_threshold_csv_keeps_full_float_precision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    from clearml_yolo.application.use_cases import metrics as module

    predictions, ground_truth = _write_inputs(tmp_path)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        module,
        "calibrate_thresholds",
        lambda *_args, **_kwargs: {"cat": 0.12345678901234566},
    )
    with _metric_owner(monkeypatch, workflow_dependencies) as task:
        compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            ClearMLConfig(),
            EvaluationConfig(),
            splits=["test"],
            fiftyone=FiftyOneConfig(enabled=False),
            model_label="fixture detector",
            deps=workflow_dependencies,
        )
    uploads = {item["name"]: item["artifact_object"] for item in task.uploads}
    assert (
        uploads["metrics_best_confidences_val"].read_text(encoding="utf-8")
        == "class_name,confidence\ncat,0.12345678901234566\n"
    )


def test_missing_required_plot_fails_even_without_tracking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    from typing import Any

    from clearml_yolo.application.use_cases import metrics as module

    predictions, ground_truth = _write_inputs(tmp_path)
    from clearml_yolo.application.evaluation import evaluate_split

    original = evaluate_split

    def missing_plot(*args: Any, **kwargs: Any) -> Any:
        evaluated = original(*args, **kwargs)
        evaluated.plot_paths.pop("recall")
        return evaluated

    patch_workflow(monkeypatch, workflow_dependencies, module, "init_task", lambda *a, **k: None)
    patch_workflow(monkeypatch, workflow_dependencies, module, "evaluate_split", missing_plot)
    with pytest.raises(ValueError, match="inventory"):
        compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            ClearMLConfig(),
            EvaluationConfig(),
            splits=["test"],
            fiftyone=FiftyOneConfig(enabled=False),
            model_label="fixture detector",
            deps=workflow_dependencies,
        )


@pytest.mark.parametrize("case", ["missing", "empty"])
def test_unsupported_split_inputs_fail_clearly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    if case == "empty":
        pd.read_csv(ground_truth).iloc[:0].to_csv(ground_truth, index=False)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.metrics.init_task",
        lambda *a, **k: None,
    )
    with pytest.raises(ValueError, match=r"(?i)no ground-truth rows|no labelled objects"):
        compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            ClearMLConfig(),
            EvaluationConfig(),
            splits=["train"],
            fiftyone=FiftyOneConfig(enabled=False),
            model_label="fixture detector",
            deps=workflow_dependencies,
        )


def test_arbitrary_logical_split_keeps_outputs_inside_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    predictions, ground_truth = _write_inputs(tmp_path)
    split = "../../../escape/actual"
    frame = pd.read_csv(ground_truth)
    frame.loc[frame["split"] == "test", "split"] = split
    frame.to_csv(ground_truth, index=False)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.metrics.init_task",
        lambda *_args, **_kwargs: None,
    )
    destination = tmp_path / "metrics"
    result = compute_metrics(
        predictions,
        ground_truth,
        destination,
        clearml=ClearMLConfig(),
        evaluation=EvaluationConfig(),
        splits=[split],
        fiftyone=FiftyOneConfig(enabled=False),
        model_label="fixture detector",
        deps=workflow_dependencies,
    )
    assert result.dashboards[split].parent == destination
    assert result.dashboards[split].is_file()
    assert result.evaluations[split].parent == destination
    assert not (tmp_path / "escape").exists()


@pytest.mark.parametrize("already_suffixed", [False, True])
def test_dashboard_plot_contract_accepts_legacy_and_suffixed_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    already_suffixed: bool,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    from digital_metrics.reporting import get_dashboards

    from clearml_yolo.adapters.reporting import evaluation as scoring
    from clearml_yolo.core.artifact_names import PLOT_METRICS

    original = get_dashboards

    def dashboard(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        if already_suffixed:
            directory = Path(kwargs["path"])
            suffix = kwargs["suffix"]
            for metric in PLOT_METRICS:
                legacy = directory / f"{metric}_confidence_intervals.png"
                suffixed = directory / f"{metric}_confidence_intervals_{suffix}.png"
                if legacy.is_file():
                    legacy.replace(suffixed)
        return result

    patch_workflow(monkeypatch, workflow_dependencies, scoring, "get_dashboards", dashboard)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.metrics.init_task",
        lambda *_args, **_kwargs: None,
    )
    predictions, ground_truth = _write_inputs(tmp_path)
    result = compute_metrics(
        predictions,
        ground_truth,
        tmp_path / "metrics",
        clearml=ClearMLConfig(),
        evaluation=EvaluationConfig(),
        splits=["test"],
        fiftyone=FiftyOneConfig(enabled=False),
        model_label="fixture detector",
        deps=workflow_dependencies,
    )
    assert result.dashboards["test"].is_file()
    assert (tmp_path / "metrics" / "recall_confidence_intervals_test.png").is_file()


@pytest.mark.parametrize("already_suffixed", [False, True])
@pytest.mark.parametrize("suppress_recall", [False, True])
def test_reused_destination_requires_fresh_confidence_plots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    already_suffixed: bool,
    suppress_recall: bool,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    from digital_metrics.reporting import get_dashboards

    from clearml_yolo.adapters.reporting import evaluation as scoring
    from clearml_yolo.core.artifact_names import PLOT_METRICS

    destination = tmp_path / "metrics"
    destination.mkdir()
    stale = b"old confidence plot"
    other_split = destination / "recall_confidence_intervals_val.png"
    unrelated = destination / "notes.txt"
    other_split.write_bytes(stale)
    unrelated.write_bytes(stale)
    for metric in PLOT_METRICS:
        for suffix in ("", "_test"):
            (destination / f"{metric}_confidence_intervals{suffix}.png").write_bytes(stale)

    def dashboard(*args: Any, **kwargs: Any) -> Any:
        producer = tmp_path / "producer"
        producer.mkdir()
        result = get_dashboards(*args, **kwargs | {"path": str(producer)})
        directory = Path(kwargs["path"])
        for path in producer.iterdir():
            metric = next(
                (
                    name
                    for name in PLOT_METRICS
                    if path.name.startswith(f"{name}_confidence_intervals")
                ),
                None,
            )
            if metric is None:
                path.replace(directory / path.name)
            elif not (suppress_recall and metric == "recall"):
                suffix = "_test" if already_suffixed else ""
                path.replace(directory / f"{metric}_confidence_intervals{suffix}.png")
        return result

    patch_workflow(monkeypatch, workflow_dependencies, scoring, "get_dashboards", dashboard)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.metrics.init_task",
        lambda *_args, **_kwargs: None,
    )
    predictions, ground_truth = _write_inputs(tmp_path)

    def run() -> None:
        compute_metrics(
            predictions,
            ground_truth,
            destination,
            clearml=ClearMLConfig(),
            evaluation=EvaluationConfig(),
            splits=["test"],
            fiftyone=FiftyOneConfig(enabled=False),
            model_label="fixture detector",
            deps=workflow_dependencies,
        )

    if suppress_recall:
        with pytest.raises(FileNotFoundError, match="Required confidence interval plot"):
            run()
    else:
        run()
        for metric in PLOT_METRICS:
            plot = destination / f"{metric}_confidence_intervals_test.png"
            assert plot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert other_split.read_bytes() == stale
    assert unrelated.read_bytes() == stale
