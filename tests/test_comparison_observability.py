"""Comparison observations preserve progress, diagnostic levels and cleanup."""

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from loguru import logger

from clearml_yolo.adapters.observability import progress
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.core.comparison.significance import TestResult as ComparisonTestResult
from clearml_yolo.core.evaluation.models import SplitOutcome
from workflow_dependencies import (
    workflow_dependencies as workflow_dependencies,  # noqa: PLC0414 - fixture export
)


@pytest.fixture
def messages() -> Iterator[list[tuple[str, str]]]:
    recorded: list[tuple[str, str]] = []
    sink = logger.add(
        lambda message: recorded.append(
            (message.record["level"].name, message.record["message"]),
        )
    )
    try:
        yield recorded
    finally:
        logger.remove(sink)


def test_class_observations_preserve_completed_work_progress(
    monkeypatch: pytest.MonkeyPatch,
    messages: list[tuple[str, str]],
) -> None:
    assert hasattr(progress, "progress_callback"), (
        "Callback progress must preserve the existing tracker"
    )
    monkeypatch.setattr(sys.stderr, "isatty", lambda: False)
    with progress.progress_callback("Testing classes", total=2, unit="class") as observe:
        observe("cat")
        assert messages == []
        observe("dog")
        assert len(messages) == 1
        assert messages[0][0] == "INFO"
        assert messages[0][1].startswith("Testing classes: 1/2 (50%) class in ")
    assert len(messages) == 2
    assert messages[1][0] == "INFO"
    assert messages[1][1].startswith("Testing classes: 2 class in ")


def test_exception_does_not_report_the_unfinished_class_as_completed(
    monkeypatch: pytest.MonkeyPatch,
    messages: list[tuple[str, str]],
) -> None:
    monkeypatch.setattr(sys.stderr, "isatty", lambda: False)

    def fail_during_progress() -> None:
        with progress.progress_callback("Testing classes", total=2, unit="class") as observe:
            observe("cat")
            raise RuntimeError("calculation failed")

    with pytest.raises(RuntimeError, match="calculation failed"):
        fail_during_progress()
    assert messages == []


def test_exception_closes_terminal_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    closed: list[bool] = []

    def terminal(*args: object, **kwargs: object) -> Iterator[int]:
        del args, kwargs
        try:
            yield 0
            yield 1
        finally:
            closed.append(True)

    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)
    monkeypatch.setattr(progress, "tqdm", terminal)

    def fail_during_progress() -> None:
        with progress.progress_callback("Testing classes", total=2, unit="class") as observe:
            observe("cat")
            raise RuntimeError("failed")

    with pytest.raises(RuntimeError):
        fail_during_progress()
    assert closed == [True]


def _outcomes() -> tuple[SplitOutcome, SplitOutcome]:
    import pandas as pd

    from clearml_yolo.core.evaluation.models import ClassCounts, SplitOutcome

    ground_truth = pd.DataFrame(
        {
            "gt_index": [0],
            "image_name": ["a"],
            "instance_label": ["cat"],
            "detected": [False],
        }
    )
    predictions = pd.DataFrame(columns=["pred_index", "image_name", "instance_label", "is_tp"])
    baseline = SplitOutcome({"cat": ClassCounts(fn=1)}, ground_truth, predictions)
    candidate = SplitOutcome(
        {"cat": ClassCounts(tp=1)},
        ground_truth.assign(detected=True),
        pd.DataFrame(
            {
                "pred_index": [0],
                "image_name": ["a"],
                "instance_label": ["cat"],
                "is_tp": [True],
            }
        ),
    )
    return baseline, candidate


def _comparison_messages(messages: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return [
        entry
        for entry in messages
        if entry[1].startswith(
            (
                "The precision bootstrap",
                "Testing classes",
                "Comparison assembled",
            )
        )
    ]


def _assert_observation_sequence(messages: list[tuple[str, str]]) -> None:
    filtered = _comparison_messages(messages)
    warning = ("WARNING", "The precision bootstrap needs rows from both models, got 0 and 1")
    assert len(filtered) == 4
    assert filtered[0] == filtered[2] == warning
    assert filtered[1][0] == "INFO"
    assert filtered[1][1].startswith("Testing classes: 1 class in ")
    assert filtered[3] == (
        "INFO",
        "Comparison assembled: 1 classes compared, 0 excluded, BH family of 1",
    )


def test_standalone_core_callbacks_preserve_warning_progress_and_summary_order(
    monkeypatch: pytest.MonkeyPatch,
    messages: list[tuple[str, str]],
) -> None:
    from clearml_yolo.adapters.observability.diagnostics import log
    from clearml_yolo.core.comparison.assemble import build_comparison_rows

    monkeypatch.setattr(sys.stderr, "isatty", lambda: False)
    baseline, candidate = _outcomes()
    with progress.progress_callback("Testing classes", total=1, unit="class") as observe:
        tables = build_comparison_rows(
            baseline,
            candidate,
            thresholds_baseline={"cat": 0.5},
            thresholds_candidate={"cat": 0.5},
            images=["a"],
            iterations=8,
            observe_class=observe,
            diagnostic=lambda message: log("WARNING", message),
            summary=lambda message: log("INFO", message),
        )
    assert tables.rows["class_name"].tolist() == ["cat", "pooled"]
    _assert_observation_sequence(messages)


@pytest.mark.parametrize("failure_phase", ["class", "pooled"])
def test_comparison_failure_reports_only_classes_already_completed(
    monkeypatch: pytest.MonkeyPatch,
    messages: list[tuple[str, str]],
    failure_phase: str,
) -> None:
    from clearml_yolo.adapters.observability.diagnostics import log
    from clearml_yolo.core.comparison import assemble

    monkeypatch.setattr(sys.stderr, "isatty", lambda: False)
    baseline, candidate = _outcomes()
    original = assemble._test_pair

    def fail_at_phase(
        *args: Any, **kwargs: Any
    ) -> tuple[ComparisonTestResult, ComparisonTestResult, ComparisonTestResult]:
        if (args[2] is None) == (failure_phase == "pooled"):
            raise RuntimeError("calculation failed")
        return original(*args, **kwargs)

    monkeypatch.setattr(assemble, "_test_pair", fail_at_phase)
    with (
        pytest.raises(RuntimeError),
        progress.progress_callback(
            "Testing classes",
            total=1,
            unit="class",
        ) as observe,
    ):
        assemble.build_comparison_rows(
            baseline,
            candidate,
            thresholds_baseline={"cat": 0.5},
            thresholds_candidate={"cat": 0.5},
            images=["a"],
            iterations=8,
            observe_class=observe,
            diagnostic=lambda message: log("WARNING", message),
            summary=lambda message: log("INFO", message),
        )
    completed = [entry for entry in messages if entry[1].startswith("Testing classes")]
    assert len(completed) == int(failure_phase == "pooled")
    assert not any(message.startswith("Comparison assembled") for _, message in messages)


def test_app_comparison_wires_original_observations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    messages: list[tuple[str, str]],
    workflow_dependencies: WorkflowDependencies,
) -> None:
    import pandas as pd

    from clearml_yolo.application.contracts import (
        ClearMLConfig,
        InferenceConfig,
        ModelRef,
        ScoredResolution,
        VocabularyReport,
    )
    from clearml_yolo.application.use_cases.compare import compare
    from test_comparison_assemble import _stub_comparison_publication

    monkeypatch.setattr(sys.stderr, "isatty", lambda: False)
    _stub_comparison_publication(monkeypatch, workflow_dependencies=workflow_dependencies)
    baseline, candidate = tmp_path / "baseline.pt", tmp_path / "candidate.pt"
    baseline.write_bytes(b"baseline")
    candidate.write_bytes(b"candidate")
    image = tmp_path / "a"
    image.write_bytes(b"image")
    columns = ["image_name", "instance_label", "bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]
    truth = pd.DataFrame([("a", "cat", 0, 0, 10, 10)], columns=columns).assign(
        image_path=str(image),
        split="test",
    )
    truth_path = tmp_path / "truth.csv"
    truth.to_csv(truth_path, index=False)

    def infer(
        weights: Path,
        _truth: pd.DataFrame,
        _split: str,
        output: Path,
        **_kwargs: Any,
    ) -> tuple[pd.DataFrame, VocabularyReport]:
        rows = [] if weights == baseline else [("a", "cat", 0, 0, 10, 10, 0.9)]
        frame = pd.DataFrame(rows, columns=[*columns, "confidence"])
        frame.to_csv(output, index=False)
        return frame, VocabularyReport(
            model_classes=["cat"],
            unknown_to_model=[],
            unknown_to_ground_truth=[],
        )

    monkeypatch.setattr(workflow_dependencies.model, "reinfer_split", infer)
    monkeypatch.setattr(
        workflow_dependencies.model,
        "resolution_of",
        lambda *_args: ScoredResolution(
            trained_at=640,
            scored_at=640,
        ),
    )
    monkeypatch.setattr(workflow_dependencies.model, "trained_imgsz", lambda *_args: 640)
    result = compare(
        ModelRef(source="local", label="baseline", weights=baseline, thresholds={"cat": 0.5}),
        ModelRef(source="local", label="candidate", weights=candidate, thresholds={"cat": 0.5}),
        ground_truth=truth_path,
        output_dir=tmp_path / "comparison",
        clearml=ClearMLConfig(),
        inference=InferenceConfig(conf=0.001, iou=0.7, imgsz=640, batch=1, device="cpu"),
        bootstrap_iterations=8,
        deps=workflow_dependencies,
    )
    assert result is not None
    assert result.workbook.is_file()
    _assert_observation_sequence(messages)


def test_app_native_resolution_warning_keeps_original_text_and_level(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    messages: list[tuple[str, str]],
    workflow_dependencies: WorkflowDependencies,
) -> None:
    from clearml_yolo.application.contracts import InferenceConfig, ScoredResolution
    from clearml_yolo.application.use_cases.compare import _settled

    monkeypatch.setattr(
        workflow_dependencies.model,
        "resolution_of",
        lambda *_args: ScoredResolution(trained_at=640, scored_at=960),
    )
    monkeypatch.setattr(workflow_dependencies.model, "trained_imgsz", lambda *_args: 640)
    result = _settled(
        InferenceConfig(conf=0.001, iou=0.7, imgsz=960, batch=1, device="cpu"),
        tmp_path / "candidate.pt",
        tmp_path / "baseline.pt",
        deps=workflow_dependencies,
    )
    assert result.imgsz == 960
    assert messages == [
        (
            "WARNING",
            (
                "The baseline was trained at imgsz 640 and the candidate requests imgsz 960; "
                "both are passed the same requested imgsz 960 before native normalization"
            ),
        )
    ]
