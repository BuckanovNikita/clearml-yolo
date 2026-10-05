"""Observe SDK plotting payloads without contacting ClearML."""

import json
from typing import Any
from urllib.parse import unquote

import pytest

from clearml_yolo.clearml_report import report_confusion_matrices, report_pr_curves
from clearml_yolo.result_schema import ConfusionMatrixPayload, PRCurve, ResultContext


class RecordingTask:
    def __init__(self) -> None:
        self.plots: list[dict[str, Any]] = []

    def get_logger(self) -> "RecordingTask":
        return self

    def report_plotly(self, **kwargs: Any) -> None:
        self.plots.append(kwargs)


CONTEXT = ResultContext(context_id="candidate/a", model_id="weights/猫", split="val")


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
    assert len(task.plots) == 4
    raw, row, column, total = [p["figure"]["data"][0] for p in task.plots]
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
        ap50=0.75,
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
    assert method in figure["layout"]["title"]
    assert "AP50=0.75" in figure["layout"]["title"]
    assert "candidate/a" in figure["layout"]["title"]


@pytest.mark.parametrize(("gt_count", "ap"), [(0, "unavailable"), (2, "0")])
def test_pr_empty_populations_have_explicit_annotation(gt_count: int, ap: str) -> None:
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
    assert all(not trace["x"] and not trace["y"] for trace in figure["data"])
    assert f"AP50={ap}" in figure["layout"]["title"]
    annotation = figure["layout"]["annotations"][-1]["text"]
    assert ("recall unavailable" if gt_count == 0 else "No predictions") in annotation


def test_plot_identity_is_reversible_and_distinguishes_context_and_class() -> None:
    task = RecordingTask()
    for context_id, model_id, split, class_name in [
        ("a/b", "猫", "val", "10"),
        ("a", "b/猫", "val", "10"),
        ("a/b", "猫", "test", "10"),
        ("a/b", "猫", "val", "2"),
        ("a/b", "猫", "val", "猫/%"),
    ]:
        context = ResultContext(context_id=context_id, model_id=model_id, split=split)
        curve = PRCurve(
            class_name=class_name,
            recall=[],
            precision=[],
            confidence=[],
            tp=[],
            fp=[],
            gt_count=0,
            ap50=None,
            integration_method="continuous",
        )
        report_pr_curves(task, context, [curve])
        assert json.loads(unquote(task.plots[-1]["series"])) == [
            context_id,
            model_id,
            split,
            class_name,
        ]
    assert len({(p["title"], p["series"]) for p in task.plots}) == 5


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
    assert "AP50=0" in caption
    assert "continuous" in caption
    assert "candidate/a" in caption
    assert "weights/猫" in caption
    assert "val" in caption
