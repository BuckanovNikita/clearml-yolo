"""Shared statistics preserve local comparison policy and optional injection."""

import inspect
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pandas as pd
import pytest

from clearml_yolo.adapters.clearml.session import ClearMLConfig
from clearml_yolo.adapters.evaluation.comparison import compare_outcomes
from clearml_yolo.application.contracts import (
    InferenceConfig,
    ModelRef,
    ResolvedModel,
    SettledInference,
    VocabularyReport,
)
from clearml_yolo.application.ports import (
    EvaluationEngine,
    PairedComparisonEngine,
    WorkflowDependencies,
)
from clearml_yolo.application.use_cases import compare as workflow
from clearml_yolo.core.comparison.assemble import ComparisonTables, build_comparison_rows
from clearml_yolo.core.evaluation.models import ClassCounts, SplitOutcome
from clearml_yolo.entrypoints.composition import build_dependencies

LABELS = ["0001", "1", "кошка"]
IMAGES = [str(index) for index in range(8)] + ["background"]


def _outcome(candidate: bool, scenario: str) -> SplitOutcome:
    gt_rows: list[dict[str, object]] = []
    pred_rows: list[dict[str, object]] = []
    counts = {}
    for class_index, label in enumerate(LABELS):
        hits = 0
        for image in range(8):
            detected = (image + class_index) % (2 if candidate else 3) == 0
            hits += detected
            index = class_index * 8 + image
            image_name = "outside" if scenario == "outside" and image == 7 else str(image)
            gt_rows.append(
                {
                    "gt_index": index + (100 if candidate and scenario == "unpaired" else 0),
                    "image_name": image_name,
                    "instance_label": label,
                    "detected": detected,
                }
            )
            pred_rows.append(
                {
                    "pred_index": index,
                    "image_name": image_name,
                    "instance_label": label,
                    "is_tp": detected,
                }
            )
        counts[label] = ClassCounts(tp=hits, fp=8 - hits, fn=8 - hits)
    gt = pd.DataFrame(gt_rows)
    predictions = pd.DataFrame(pred_rows)
    if scenario == "no_predictions" and candidate:
        predictions = predictions.iloc[:0]
        counts = {label: ClassCounts(fn=8) for label in LABELS}
    if scenario == "empty":
        gt, predictions = gt.iloc[:0], predictions.iloc[:0]
        counts = {label: ClassCounts() for label in LABELS}
    return SplitOutcome(counts, gt, predictions)


@pytest.mark.parametrize("seed", [0, 19, 93])
@pytest.mark.parametrize(
    "scenario", ["eligible", "one_sided", "empty", "no_predictions", "outside", "unpaired"]
)
def test_shared_statistics_equal_legacy_tables_and_callback_sequences(
    seed: int, scenario: str
) -> None:
    baseline, candidate = _outcome(False, scenario), _outcome(True, scenario)
    expected_events: list[tuple[str, str | None]] = []
    actual_events: list[tuple[str, str | None]] = []
    arguments: dict[str, Any] = {
        "thresholds_baseline": {"0001": 0.5, "1": 0.4},
        "thresholds_candidate": {"0001": 0.5, "кошка": 0.7},
        "images": IMAGES,
        "q": 0.1,
        "iterations": 127,
        "seed": seed,
    }
    if scenario == "one_sided":
        arguments.update(baseline_classes={"0001", "1"}, candidate_classes={"0001", "кошка"})
    expected = build_comparison_rows(
        baseline,
        candidate,
        **arguments,
        observe_class=lambda label: expected_events.append(("class", label)),
        diagnostic=lambda message: expected_events.append(("diagnostic", message)),
        summary=lambda message: expected_events.append(("summary", message)),
    )
    actual = compare_outcomes(
        baseline,
        candidate,
        **arguments,
        observe_class=lambda label: actual_events.append(("class", label)),
        diagnostic=lambda message: actual_events.append(("diagnostic", message)),
        summary=lambda message: actual_events.append(("summary", message)),
    )
    pd.testing.assert_frame_equal(actual.rows, expected.rows, check_exact=True)
    pd.testing.assert_frame_equal(actual.excluded, expected.excluded, check_exact=True)
    assert actual.methodology == expected.methodology
    assert actual_events == expected_events
    assert [value for event, value in actual_events if event == "class"] == [*LABELS, None]
    if scenario in {"outside", "unpaired", "no_predictions"}:
        assert any(event == "diagnostic" for event, _ in actual_events)


def test_composition_exposes_optional_statistics_without_changing_dependency_constructor() -> None:
    dependencies = build_dependencies()
    assert isinstance(dependencies.evaluation, PairedComparisonEngine)
    assert dependencies.evaluation.compare_outcomes is compare_outcomes
    signature = inspect.signature(WorkflowDependencies)
    assert list(signature.parameters) == [
        "dataset",
        "model",
        "repository",
        "evaluation",
        "evaluation_writer",
        "renderer",
        "storage",
        "resources",
        "tracking",
        "publisher_factory",
        "disabled_publisher",
        "exporter",
    ]
    for name, parameter in signature.parameters.items():
        assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        if name == "exporter":
            assert parameter.default is None
        else:
            assert parameter.default is inspect.Parameter.empty


class _SelectedComparisonError(Exception):
    """Stop immediately at the selected comparison seam, before output effects."""


class _OptionalStatistics:
    def compare_outcomes(self, *_args: object, **_kwargs: object) -> ComparisonTables:
        raise _SelectedComparisonError("optional")


@pytest.mark.parametrize("optional", [False, True])
def test_workflow_uses_optional_capability_and_keeps_legacy_injection_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, optional: bool
) -> None:
    dependencies = build_dependencies()
    evaluation = _OptionalStatistics() if optional else object()
    dependencies = replace(dependencies, evaluation=cast("EvaluationEngine", evaluation))
    assert isinstance(dependencies.evaluation, PairedComparisonEngine) is optional
    monkeypatch.setattr(dependencies.tracking, "init_task", lambda *_a, **_kw: None)
    monkeypatch.setattr(dependencies.model, "stage_settings", lambda *_a, **_kw: {})
    truth = tmp_path / "truth.csv"
    image = tmp_path / "0.jpg"
    image.write_bytes(b"fixture image")
    pd.DataFrame(
        {
            "image_name": ["0"],
            "image_path": [str(image)],
            "instance_label": ["0001"],
            "bbox_x_tl": [0],
            "bbox_y_tl": [0],
            "bbox_x_br": [10],
            "bbox_y_br": [10],
            "split": ["test"],
        }
    ).to_csv(truth, index=False)
    (tmp_path / "baseline.pt").write_bytes(b"resolved baseline fixture")
    (tmp_path / "candidate.pt").write_bytes(b"resolved candidate fixture")
    models = iter(
        [
            ResolvedModel(
                source="local", weights=tmp_path / "baseline.pt", thresholds={"0001": 0.5}
            ),
            ResolvedModel(
                source="local", weights=tmp_path / "candidate.pt", thresholds={"0001": 0.5}
            ),
        ]
    )
    monkeypatch.setattr(workflow, "_resolve_model", lambda *_a, **_kw: next(models))
    inference = InferenceConfig(conf=0.001, iou=0.7, imgsz=640, batch=1, device=None)
    monkeypatch.setattr(
        workflow, "_settled", lambda *_a, **_kw: SettledInference(**inference.model_dump())
    )
    monkeypatch.setattr(workflow, "_prediction_cache", lambda *_a, **_kw: tmp_path / "pred.csv")
    outcome = _outcome(False, "eligible")
    monkeypatch.setattr(
        workflow,
        "_scored",
        lambda *_a, **_kw: (
            SimpleNamespace(outcome=outcome, thresholds={"0001": 0.5}, image_names=IMAGES),
            VocabularyReport(model_classes=LABELS, unknown_to_model=[], unknown_to_ground_truth=[]),
            None,
            None,
        ),
    )

    def legacy(*_args: object, **_kwargs: object) -> ComparisonTables:
        raise _SelectedComparisonError("legacy")

    monkeypatch.setattr(workflow, "build_comparison_rows", legacy)
    with pytest.raises(_SelectedComparisonError, match="optional" if optional else "legacy"):
        workflow.compare(
            ModelRef(
                source="local",
                weights=tmp_path / "baseline.pt",
                label="Baseline",
                thresholds={"0001": 0.5},
            ),
            ModelRef(
                source="local",
                weights=tmp_path / "candidate.pt",
                label="Candidate",
                thresholds={"0001": 0.5},
            ),
            truth,
            tmp_path / "comparison",
            ClearMLConfig(),
            inference,
            bootstrap_iterations=127,
            deps=dependencies,
        )
