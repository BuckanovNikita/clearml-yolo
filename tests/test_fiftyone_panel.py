"""Panel contracts; local views exercise exact detection filtering without an App."""

import importlib
import math
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from clearml_yolo.comparison.evaluation_payload import EvaluationReport
from test_fiftyone_evaluation_results import payload as source_payload

payload = source_payload


def test_panel_module_is_available() -> None:
    assert importlib.util.find_spec("clearml_yolo.publishing.fiftyone_panel") is not None


@pytest.mark.skipif(os.environ.get("CY_TEST_FIFTYONE") != "1", reason="Isolated FiftyOne required")
def test_report_keeps_source_precision_and_marks_subset_unavailable() -> None:
    from clearml_yolo.publishing.fiftyone_panel import report_data

    report = EvaluationReport.model_validate(
        {
            "classes": ["01", "雪"],
            "confusion_matrix": {
                "labels": ["01", "雪", "background"],
                "counts": [[1, 0, 0], [0, 0, 0], [0, 0, 0]],
            },
            "pr_curves": [
                {
                    "class_name": "01",
                    "recall": [0.5, 1.0],
                    "precision": [1.0, 0.5],
                    "confidence": [0.9, 0.2],
                    "tp": [1, 2],
                    "fp": [0, 2],
                    "gt_count": 2,
                    "ap50": 0.7123456789012345,
                    "integration_method": "source",
                }
            ],
            "average_precisions": {
                "01": {"ap50": 0.7123456789012345, "ap75": 0.6123456789012345, "ap50_95": 0.4},
                "雪": {"ap50": None, "ap75": None, "ap50_95": None},
            },
        }
    )
    data = report_data(report, is_subset=False)
    assert data["average_precisions"][0] == {
        "class": "01",
        "AP50": 0.7123456789012345,
        "AP75": 0.6123456789012345,
        "AP50-95": 0.4,
    }
    assert data["average_precisions"][1]["AP50"] is None
    assert data["curves"][0]["x"] == [0.5, 1.0]
    assert data["curves"][0]["y"] == [1.0, 0.5]
    assert report_data(report, is_subset=True)["available"] is False
    assert report_data(report, is_subset=True)["curves"] == []
    assert report_data(None, is_subset=False)["available"] is False


@pytest.fixture
def dataset() -> Iterator[Any]:
    if os.environ.get("CY_TEST_FIFTYONE") != "1":
        pytest.skip("Real FiftyOne views require the isolated test environment")
    import fiftyone as fo

    instance = fo.Dataset("cy-panel-" + uuid4().hex)
    try:
        yield instance
    finally:
        instance.delete()


def test_exact_view_removes_unrelated_same_class_labels(dataset: Any, tmp_path: Path) -> None:
    import fiftyone as fo

    from clearml_yolo.publishing.fiftyone_panel import select_evaluation_labels

    truth = [fo.Detection(label="a"), fo.Detection(label="a")]
    predictions = [fo.Detection(label="b"), fo.Detection(label="b")]
    sample = fo.Sample(
        filepath=str(tmp_path / "fixture.png"),
        truth=fo.Detections(detections=truth),
        predictions=fo.Detections(detections=predictions),
    )
    dataset.add_sample(sample)
    view = select_evaluation_labels(
        dataset.view(), "truth", "predictions", [truth[0].id], [predictions[1].id]
    )
    assert view.values("truth.detections.id", unwind=True) == [truth[0].id]
    assert view.values("predictions.detections.id", unwind=True) == [predictions[1].id]
    assert len(select_evaluation_labels(dataset.view(), "truth", "predictions", [], [])) == 0


@pytest.fixture
def evaluated(dataset: Any, payload: Any, tmp_path: Path) -> Any:
    import fiftyone as fo

    from clearml_yolo.publishing.fiftyone_evaluation import publish_evaluation

    truth = [fo.Detection(label=box.label, dm_index=box.index) for box in payload.ground_truth]
    predictions = [
        fo.Detection(label=box.label, confidence=0.8, dm_index=box.index)
        for box in payload.predictions
    ]
    dataset.add_sample(
        fo.Sample(
            filepath=str(tmp_path / "image.png"),
            image_name="image.png",
            gt=fo.Detections(detections=truth),
            pred=fo.Detections(detections=predictions),
        )
    )
    publish_evaluation(dataset, dataset.view(), payload, "imported", "gt", "pred", run_key="run")
    return dataset


def _context(dataset: Any, *, params: dict[str, Any] | None = None, view: Any = None) -> Any:
    from fiftyone.operators.executor import ExecutionContext, Executor

    parameters = {
        "panel_id": "panel-fixture",
        "panel_state": {"view": {"key": "imported"}, "evaluation_key": "imported"},
    }
    parameters.update(params or {})
    request = {"dataset_name": dataset.name, "params": parameters}
    if view is not None:
        request["view"] = view._serialize()
    return ExecutionContext(request, executor=Executor())


def _panel_data(ctx: Any) -> dict[str, Any]:
    data = {}
    for request in ctx.executor._requests:
        if request.operator_uri == "patch_panel_data":
            data.update(request.params["data"])
    return data


def test_native_headlines_and_reports_render_with_real_panel_context(evaluated: Any) -> None:
    from clearml_yolo.publishing.fiftyone_panel import EvaluationReportsPanel, NativeEvaluationPanel

    native = NativeEvaluationPanel()
    data = native.get_evaluation_data_cacheable(_context(evaluated))
    assert (data["metrics"]["tp"], data["metrics"]["fp"], data["metrics"]["fn"]) == (1, 3, 2)
    assert data["metrics"]["mAR"] is None
    reports = EvaluationReportsPanel()
    ctx = _context(evaluated)
    reports.load_report(ctx)
    assert _panel_data(ctx)["report"]["available"] is True
    assert reports.render(ctx).to_json()["type"]["properties"]["pr_curves"]
    ctx = _context(evaluated, view=evaluated.limit(0))
    reports.load_report(ctx)
    assert _panel_data(ctx)["report"]["available"] is False
    assert "markdown" in reports.render(ctx).to_json()["type"]["properties"]


def test_exact_matrix_callback_emits_view_with_only_associated_labels(evaluated: Any) -> None:
    from fiftyone.core.view import DatasetView

    from clearml_yolo.publishing.fiftyone_panel import NativeEvaluationPanel

    ctx = _context(evaluated, params={"type": "matrix", "options": {"x": "dog", "y": "background"}})
    NativeEvaluationPanel().load_view(ctx)
    request = ctx.executor._requests[-1]
    view = DatasetView._build(evaluated, request.params["view"])
    assert view.values("pred.detections.dm_index", unwind=True) == [1, 2]
    assert view.values("gt.detections.dm_index", unwind=True) == []


def test_plugin_explicit_install_registers_both_panels(
    dataset: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import fiftyone as fo
    from fiftyone.plugins.context import PluginContext
    from fiftyone.plugins.definitions import PluginDefinition

    from clearml_yolo.publishing.fiftyone_panel import install_evaluation_plugin

    monkeypatch.setattr(fo.config, "plugins_dir", str(tmp_path / "plugins"))
    installed = install_evaluation_plugin()
    definition = PluginDefinition.from_disk(str(installed / "fiftyone.yml"))
    assert set(definition.operators) == {"native_evaluation", "evaluation_reports"}
    assert installed.joinpath("__init__.py").is_file()
    context = PluginContext(definition)
    context.register_all()
    assert not context.errors
    assert {instance.config.name for instance in context.instances} == {
        "native_evaluation",
        "evaluation_reports",
    }


def test_matrix_comparison_selects_exact_labels_from_both_runs(
    evaluated: Any, payload: Any
) -> None:
    import fiftyone as fo
    from fiftyone.core.view import DatasetView

    from clearml_yolo.publishing.fiftyone_evaluation import publish_evaluation
    from clearml_yolo.publishing.fiftyone_panel import NativeEvaluationPanel

    sample = evaluated.first()
    sample["other_pred"] = fo.Detections(
        detections=[
            fo.Detection(label=box.label, confidence=0.8, dm_index=box.index)
            for box in payload.predictions
        ]
    )
    sample.save()
    publish_evaluation(
        evaluated, evaluated.view(), payload, "other", "gt", "other_pred", run_key="other"
    )
    ctx = _context(
        evaluated,
        params={
            "type": "matrix",
            "options": {"x": "dog", "y": "background"},
            "panel_state": {"view": {"key": "imported", "compareKey": "other"}},
        },
    )
    NativeEvaluationPanel().load_view(ctx)
    request = ctx.executor._requests[-1]
    view = DatasetView._build(evaluated, request.params["view"])
    assert view.values("pred.detections.dm_index", unwind=True) == [1, 2]
    assert view.values("other_pred.detections.dm_index", unwind=True) == [1, 2]


@pytest.mark.parametrize(
    ("status", "gt_indices", "pred_indices"),
    [
        ("tp", [0], [0]),
        ("fp", [], [1, 2, 3]),
        ("fn", [1, 2], []),
    ],
)
def test_status_callback_selects_exact_source_labels(
    evaluated: Any, status: str, gt_indices: list[int], pred_indices: list[int]
) -> None:
    from fiftyone.core.view import DatasetView

    from clearml_yolo.publishing.fiftyone_panel import NativeEvaluationPanel

    ctx = _context(evaluated, params={"type": "field", "options": {"field": status}})
    NativeEvaluationPanel().load_view(ctx)
    view = DatasetView._build(evaluated, ctx.executor._requests[-1].params["view"])
    assert view.values("gt.detections.dm_index", unwind=True) == gt_indices
    assert view.values("pred.detections.dm_index", unwind=True) == pred_indices


def test_project_callbacks_ignore_stale_native_result_cache(evaluated: Any) -> None:
    from clearml_yolo.publishing.fiftyone_panel import NativeEvaluationPanel

    cached = evaluated.load_evaluation_results("imported")
    cached.source_data["matches"] = []
    assert cached.tp_fp_fn() == (0, 0, 0)
    panel = NativeEvaluationPanel()
    data = panel.get_evaluation_data_cacheable(_context(evaluated))
    assert (data["metrics"]["tp"], data["metrics"]["fp"], data["metrics"]["fn"]) == (1, 3, 2)
    scenario = {"type": "sample_field", "field": "image_name", "subsets": ["image.png", "absent"]}
    data = panel.get_scenario_data_cacheable(_context(evaluated), scenario)
    metrics = data["subsets_data"]["image.png"]["metrics"]
    assert (metrics["tp"], metrics["fp"], metrics["fn"]) == (1, 3, 2)
    assert data["subsets_data"]["absent"]["metrics"]["mAP"] is None


def test_native_rename_delete_refreshes_panel_state(evaluated: Any) -> None:
    from clearml_yolo.publishing.fiftyone_panel import NativeEvaluationPanel

    panel = NativeEvaluationPanel()
    ctx = _context(evaluated, params={"old_name": "imported", "new_name": "renamed"})
    panel.rename_evaluation(ctx)
    assert ctx.panel.get_state("view")["key"] == "renamed"
    assert [item["key"] for item in ctx.panel.get_state("evaluations")] == ["renamed"]
    ctx.params["eval_key"] = "renamed"
    panel.delete_evaluation(ctx)
    assert ctx.panel.get_state("view")["page"] == "overview"
    assert ctx.panel.get_state("evaluations") == []


def test_removed_scenario_reports_unavailable_without_crashing(evaluated: Any) -> None:
    from clearml_yolo.publishing.fiftyone_panel import NativeEvaluationPanel

    ctx = _context(evaluated, params={"id": "removed", "refresh_cache": True})
    NativeEvaluationPanel().load_scenario(ctx)
    assert ctx.panel.get_state("scenario_loading") is False
    assert ctx.panel.get_state("scenario_load_error")["code"] == "scenario_load_error"


def test_wrong_class_cell_selects_only_its_exact_pair(evaluated: Any, payload: Any) -> None:
    from fiftyone.core.view import DatasetView

    from clearml_yolo.publishing.fiftyone_evaluation import publish_evaluation
    from clearml_yolo.publishing.fiftyone_panel import NativeEvaluationPanel

    # A wrong-class prediction claims GT 1 before its duplicate same-class FP.
    changed = payload.model_copy(deep=True)
    changed.matches = [payload.matches[index] for index in (0, 3, 2, 1, 4, 5)]
    changed.report.confusion_matrix.counts = [[1, 1, 0], [0, 0, 1], [1, 1, 0]]
    evaluated.delete_evaluation("imported")
    publish_evaluation(
        evaluated, evaluated.view(), changed, "imported", "gt", "pred", run_key="run"
    )
    ctx = _context(evaluated, params={"type": "matrix", "options": {"x": "dog", "y": "cat"}})
    NativeEvaluationPanel().load_view(ctx)
    view = DatasetView._build(evaluated, ctx.executor._requests[-1].params["view"])
    assert view.values("gt.detections.dm_index", unwind=True) == [1]
    assert view.values("pred.detections.dm_index", unwind=True) == [2]


def test_stock_evaluation_retains_builtin_counts(dataset: Any, tmp_path: Path) -> None:
    import fiftyone as fo

    from clearml_yolo.publishing.fiftyone_panel import NativeEvaluationPanel

    dataset.add_sample(
        fo.Sample(
            filepath=str(tmp_path / "stock.png"),
            gt=fo.Detections(
                detections=[fo.Detection(label="cat", bounding_box=[0.1, 0.1, 0.4, 0.4])]
            ),
            pred=fo.Detections(
                detections=[
                    fo.Detection(label="cat", bounding_box=[0.1, 0.1, 0.4, 0.4], confidence=0.9),
                    fo.Detection(label="dog", bounding_box=[0.8, 0.8, 0.1, 0.1], confidence=0.8),
                ]
            ),
        )
    )
    dataset.evaluate_detections("pred", gt_field="gt", eval_key="stock", method="coco")
    ctx = _context(dataset, params={"panel_state": {"view": {"key": "stock"}}})
    data = NativeEvaluationPanel().get_evaluation_data(ctx)
    assert (data["metrics"]["tp"], data["metrics"]["fp"], data["metrics"]["fn"]) == (1, 1, 0)


def test_native_matrix_includes_classes_with_zero_diagonal(evaluated: Any, payload: Any) -> None:
    from clearml_yolo.publishing.fiftyone_panel import NativeEvaluationPanel

    panel = NativeEvaluationPanel()
    ctx = _context(evaluated)
    panel.load_evaluation(ctx)
    matrix = _panel_data(ctx)["evaluation_imported"]["confusion_matrix"]
    assert list(matrix["classes"]) == ["cat", "dog", "background"]
    assert matrix["matrix"].tolist() == payload.report.confusion_matrix.counts
    updates = [
        request.params["state"]
        for request in ctx.executor._requests
        if request.operator_uri == "patch_panel_state" and request.params.get("full_merge")
    ]
    matrix_key = panel.get_evaluation_id(evaluated, "imported") + "_cmc"
    assert updates[-1][matrix_key]["skipZeroCount"] is False
    assert updates[-1][matrix_key]["sortBy"] == "default"
    assert updates[-1][matrix_key]["limit"] is None


def test_empty_and_unit_confusion_colorscales_are_finite(evaluated: Any) -> None:
    from clearml_yolo.publishing.fiftyone_panel import NativeEvaluationPanel

    panel = NativeEvaluationPanel()
    results = evaluated.load_evaluation_results("imported", cache=False)
    gt_ids, pred_ids = results.label_ids("field", status="tp")
    true_positive = evaluated.select_labels(ids=[*gt_ids, *pred_ids], fields=["gt", "pred"])
    for view in (evaluated.limit(0), true_positive):
        with results.use_subset(view):
            matrix = panel.get_confusion_matrix(results)
        for key, scale in matrix.items():
            if "colorscale" in key:
                assert all(math.isfinite(position) for position, _ in scale)
