"""Observe SDK plotting payloads without contacting ClearML."""

import json
from typing import Any

import pytest

from clearml_yolo.clearml_report import report_confusion_matrices, report_pr_curves
from clearml_yolo.model_identity import ModelIdentity
from clearml_yolo.result_schema import ConfusionMatrixPayload, PRCurve, ResultContext


class RecordingTask:
    def __init__(self) -> None:
        self.plots: list[dict[str, Any]] = []

    def get_logger(self) -> "RecordingTask":
        return self

    def report_plotly(self, **kwargs: Any) -> None:
        self.plots.append(kwargs)


CONTEXT = ResultContext(
    context_id="candidate:opaque-context", model_id="opaque-model-id", split="test",
    model_identity=ModelIdentity(model_name="Road detector 猫", training_task_id="opaque-task-id"),
)


def test_confusion_counts_and_normalization_preserve_orientation() -> None:
    task = RecordingTask()
    matrix = ConfusionMatrixPayload(
        labels=["10", "2", "猫", "background"],
        counts=[
            [1, 3, 0, 0],
            [2, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ],
    )
    report_confusion_matrices(task, CONTEXT, matrix)
    assert len(task.plots) == 1
    figure = task.plots[0]["figure"]
    raw, row, column, total = figure["data"]
    assert [trace["visible"] for trace in figure["data"]] == [True, False, False, False]
    buttons = figure["layout"]["updatemenus"][0]["buttons"]
    assert [button["label"] for button in buttons] == ["Counts", "Row %", "Column %", "Overall %"]
    for index, button in enumerate(buttons):
        assert button["args"][0]["visible"] == [i == index for i in range(4)]
    assert task.plots[0]["title"] == "Confusion matrix"
    assert task.plots[0]["series"] == "Road detector 猫 · test"
    assert raw["z"] == matrix.counts
    assert all(type(value) is int for values in raw["z"] for value in values)
    assert row["z"][0] == [25, 75, 0, 0]
    assert column["z"][0][0] == pytest.approx(100 / 3)
    assert column["z"][1][0] == pytest.approx(200 / 3)
    assert total["z"][0][1] == 50
    for plot in task.plots:
        layout = plot["figure"]["layout"]
        assert layout["xaxis"]["ticktext"] == matrix.labels
        assert layout["yaxis"]["ticktext"] == matrix.labels
        assert layout["xaxis"]["title"] == "Predicted class"
        assert layout["yaxis"]["title"] == "True class"
        assert layout["yaxis"]["autorange"] == "reversed"
    for trace in [row, column, total]:
        assert (trace["zmin"], trace["zmax"]) == (0, 100)
    assert row["customdata"][0][1][:2] == [3, 4]
    assert column["customdata"][1][0][:2] == [2, 3]
    assert row["customdata"][2][0][2] == "no observations"


def test_all_zero_matrix_is_finite_and_explicit() -> None:
    task = RecordingTask()
    report_confusion_matrices(
        task,
        CONTEXT,
        ConfusionMatrixPayload(
            labels=["background"],
            counts=[[0]],
        ),
    )
    for plot in task.plots:
        assert plot["figure"]["data"][0]["z"] == [[0]]
        assert plot["figure"]["data"][0]["customdata"][0][0] == [0, 0, "no observations"]
        json.dumps(plot, allow_nan=False)


@pytest.mark.parametrize("method", ["coco", "continuous"])
def test_pr_points_ties_and_hover_are_preserved(method: str) -> None:
    task = RecordingTask()
    curve = PRCurve(
        class_name="猫",
        recall=[0.5, 0.5, 1],
        precision=[1, 0.5, 2 / 3],
        confidence=[0.9, 0.9, 0.4],
        tp=[1, 1, 2],
        fp=[0, 1, 1],
        gt_count=2,
        ap50=0.75123456789,
        integration_method=method,
    )
    report_pr_curves(task, CONTEXT, [curve])
    figure = task.plots[0]["figure"]
    trace = figure["data"][0]
    assert trace["x"] == curve.recall
    assert trace["y"] == curve.precision
    assert trace["customdata"] == [[0.9, 1, 0], [0.9, 1, 1], [0.4, 2, 1]]
    assert figure["layout"]["xaxis"]["range"] == [0, 1]
    assert figure["layout"]["yaxis"]["range"] == [0, 1]
    assert method in trace["name"]
    assert "AP50=0.751235" in trace["name"]
    assert trace["meta"][1] == curve.ap50
    assert "Road detector 猫" in figure["layout"]["title"]


@pytest.mark.parametrize(("gt_count", "ap"), [(0, "unavailable"), (2, "0")])
def test_pr_empty_populations_keep_legend_without_numerical_points(gt_count: int, ap: str) -> None:
    task = RecordingTask()
    curve = PRCurve(
        class_name="2",
        recall=[],
        precision=[],
        confidence=[],
        tp=[],
        fp=[],
        gt_count=gt_count,
        ap50=None if gt_count == 0 else 0,
        integration_method="continuous",
    )
    report_pr_curves(task, CONTEXT, [curve])
    figure = task.plots[0]["figure"]
    assert all(trace["x"] == [None] and trace["y"] == [None] for trace in figure["data"])
    assert f"AP50={ap}" in figure["data"][0]["name"]
    legend = figure["data"][0]["name"]
    assert ("recall unavailable" if gt_count == 0 else "No predictions") in legend


def test_pr_classes_share_one_chart_without_identifiers() -> None:
    task = RecordingTask()
    curves = [PRCurve(
        class_name=name, recall=[0.5], precision=[1], confidence=[0.9], tp=[1], fp=[0],
        gt_count=2, ap50=0.5, integration_method="continuous",
    ) for name in ["10", "2", "猫/%", "<car>"]]
    report_pr_curves(task, CONTEXT, curves)
    assert len(task.plots) == 1
    plot = task.plots[0]
    assert plot["title"] == "Precision-recall"
    assert plot["series"] == "Road detector 猫 · test"
    assert len(plot["figure"]["data"]) == 4
    assert plot["figure"]["layout"]["showlegend"] is True
    assert plot["figure"]["data"][-1]["name"].startswith("&lt;car&gt;")
    serialized = json.dumps(plot)
    assert "opaque-" not in serialized
    assert "%5B" not in serialized


@pytest.mark.parametrize("split", ["val", "train", "validation", "unassigned"])
def test_pr_is_test_only(split: str) -> None:
    task = RecordingTask()
    curve = PRCurve(
        class_name="car", recall=[1], precision=[1], confidence=[0.9], tp=[1], fp=[0],
        gt_count=1, ap50=1, integration_method="continuous",
    )
    report_pr_curves(task, CONTEXT.model_copy(update={"split": split}), [curve])
    assert task.plots == []


def test_readable_fallback_and_explicit_slot() -> None:
    task = RecordingTask()
    context = ResultContext(context_id="opaque-context", model_id="opaque-model", split="test")
    matrix = ConfusionMatrixPayload(labels=["background"], counts=[[0]])
    report_confusion_matrices(task, context, matrix)
    assert task.plots[0]["series"] == "Current model · test"
    report_confusion_matrices(task, context, matrix, display_label="Detector · test · Prediction 2")
    assert task.plots[1]["series"] == "Detector · test · Prediction 2"


def test_workers_do_not_report() -> None:
    report_confusion_matrices(None, CONTEXT, ConfusionMatrixPayload(labels=[], counts=[]))
    report_pr_curves(None, CONTEXT, [])


def test_metadata_survives_sdk_title_replacement() -> None:
    task = RecordingTask()
    curve = PRCurve(
        class_name="猫",
        recall=[],
        precision=[],
        confidence=[],
        tp=[],
        fp=[],
        gt_count=2,
        ap50=0,
        integration_method="continuous",
    )
    report_pr_curves(task, CONTEXT, [curve])
    plot = task.plots[0]
    # This is the actual ClearML SDK report_plotly transformation.
    plot["figure"]["layout"]["title"] = plot["series"]
    caption = plot["figure"]["layout"]["annotations"][0]["text"]
    assert "Road detector 猫" in caption
    assert "test" in caption
    assert "opaque-" not in caption
    assert "AP50=0" in plot["figure"]["data"][0]["name"]
    assert "continuous" in plot["figure"]["data"][0]["name"]
