"""Assembling two scored splits into the frame both reports read.

The tests lean on the contracts the consumers pin: the column set in
``comparison/workbook.py`` and the pooled/BH conventions in ``clearml_report.py``.
"""

from __future__ import annotations

import math
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from clearml_yolo.clearml_report import COMPARED_METRICS, POOLED_COLUMN
from clearml_yolo.comparison.assemble import (
    DEGRADED,
    IMPROVED,
    NOT_SIGNIFICANT,
    UNKNOWN_TO_BASELINE,
    UNKNOWN_TO_BOTH,
    ComparisonTables,
    build_comparison_rows,
)
from clearml_yolo.comparison.scoring import ClassCounts, SplitOutcome
from clearml_yolo.comparison.workbook import COMPARISON_COLUMNS, write_comparison_workbook


def _settled(**overrides: Any) -> Any:
    """Inference settings with every "decide this for me" already decided."""
    from clearml_yolo.tasks.compare import SettledInference

    return SettledInference(
        conf=0.001,
        iou=0.7,
        imgsz=640,
        batch=16,
        device=None,
        image_name="name",
        reuse_existing=True,
        ultralytics={"half": False},
    ).model_copy(update=overrides)


def _assert_native_audit_artifacts(uploads: dict[str, object]) -> None:
    effective = uploads["compare_effective_inference"]
    assert isinstance(effective, dict)
    assert effective["baseline"]["device"] == "normalized-baseline"
    assert effective["candidate"]["device"] == "normalized-candidate"
    locations = uploads["compare_native_output_locations"]
    assert isinstance(locations, dict)
    assert locations["baseline"]["native_save_dir"].endswith("native/baseline_test")
    candidate_archive = uploads["compare_native_outputs_candidate_test"]
    assert isinstance(candidate_archive, Path)
    with zipfile.ZipFile(candidate_archive) as bundle:
        assert bundle.namelist() == ["labels/image.txt"]


CLASSES = ["car", "van"]
IMAGES = [f"img{index}.png" for index in range(40)]


def _outcome(detected: dict[str, list[bool]], correct: dict[str, list[bool]]) -> SplitOutcome:
    """Build a scored split from per-class detected/true-positive flags.

    One ground-truth box and one prediction per image per class keeps the bootstrap's
    per-image resampling meaningful while staying readable.
    """
    counts: dict[str, ClassCounts] = {}
    gt_rows: list[dict[str, object]] = []
    pred_rows: list[dict[str, object]] = []
    index = 0

    for class_name in CLASSES:
        flags = detected[class_name]
        hits = correct[class_name]
        for image, is_detected, is_tp in zip(IMAGES, flags, hits, strict=True):
            gt_rows.append(
                {
                    "gt_index": index,
                    "image_name": image,
                    "instance_label": class_name,
                    "detected": is_detected,
                }
            )
            pred_rows.append(
                {
                    "pred_index": index,
                    "image_name": image,
                    "instance_label": class_name,
                    "is_tp": is_tp,
                }
            )
            index += 1
        counts[class_name] = ClassCounts(
            tp=sum(hits),
            fp=len(hits) - sum(hits),
            fn=len(flags) - sum(flags),
        )

    return SplitOutcome(
        counts=counts,
        gt_status=pd.DataFrame(gt_rows),
        pred_status=pd.DataFrame(pred_rows),
    )


def _flags(per_class: dict[str, int]) -> dict[str, list[bool]]:
    """``count`` leading True flags per class, over the fixed image list."""
    return {
        name: [index < count for index in range(len(IMAGES))]
        for name, count in per_class.items()
    }


def _tables(
    baseline_hits: dict[str, int],
    candidate_hits: dict[str, int],
    **kwargs: Any,
) -> ComparisonTables:
    baseline = _outcome(_flags(baseline_hits), _flags(baseline_hits))
    candidate = _outcome(_flags(candidate_hits), _flags(candidate_hits))
    return build_comparison_rows(
        baseline,
        candidate,
        thresholds_baseline={"car": 0.3, "van": 0.4},
        thresholds_candidate={"car": 0.35, "van": 0.45},
        images=IMAGES,
        iterations=200,
        seed=0,
        **kwargs,
    )


def test_every_column_the_workbook_pins_is_present() -> None:
    tables = _tables({"car": 20, "van": 20}, {"car": 30, "van": 20})

    required = {POOLED_COLUMN, *(name for name, _ in COMPARISON_COLUMNS)}
    assert required <= set(tables.rows.columns)


def test_the_workbook_accepts_the_assembled_frame(tmp_path: Path) -> None:
    """The two halves have never met before; this is the join."""
    tables = _tables({"car": 20, "van": 20}, {"car": 34, "van": 20})

    destination = tmp_path / "comparison.xlsx"
    write_comparison_workbook(tables.rows, tables.excluded, tables.methodology, destination)

    assert destination.exists()


def test_exactly_one_pooled_row_and_it_sits_outside_the_family() -> None:
    tables = _tables({"car": 20, "van": 20}, {"car": 30, "van": 20})
    rows = tables.rows

    pooled = rows[rows[POOLED_COLUMN].astype(bool)]
    assert len(pooled) == 1
    # Folding the pooled summary into the family would count the same evidence twice.
    assert math.isnan(float(pooled["precision_p_bh"].iloc[0]))
    assert math.isnan(float(pooled["recall_p_bh"].iloc[0]))


def test_declared_family_size_matches_the_adjusted_p_values() -> None:
    """clearml_report warns loudly when these disagree, so they must not."""
    tables = _tables({"car": 20, "van": 20}, {"car": 30, "van": 25})
    rows = tables.rows

    per_class = rows[~rows[POOLED_COLUMN].astype(bool)]
    adjusted = sum(
        int(pd.to_numeric(per_class[metric.adjusted_p_column], errors="coerce").notna().sum())
        for metric in COMPARED_METRICS
    )
    assert tables.methodology["family_size"] == adjusted


def test_a_large_recall_gain_is_called_an_improvement() -> None:
    tables = _tables({"car": 4, "van": 20}, {"car": 36, "van": 20})
    rows = tables.rows

    car = rows[rows["class_name"] == "car"].iloc[0]
    assert car["recall_delta"] > 0
    assert car["recall_verdict"] == IMPROVED


def test_a_large_recall_loss_is_called_a_degradation() -> None:
    tables = _tables({"car": 36, "van": 20}, {"car": 4, "van": 20})
    rows = tables.rows

    car = rows[rows["class_name"] == "car"].iloc[0]
    assert car["recall_delta"] < 0
    assert car["recall_verdict"] == DEGRADED


def test_an_identical_model_is_never_called_changed() -> None:
    tables = _tables({"car": 20, "van": 20}, {"car": 20, "van": 20})
    rows = tables.rows

    assert set(rows["precision_verdict"]) == {NOT_SIGNIFICANT}
    assert set(rows["recall_verdict"]) == {NOT_SIGNIFICANT}


def test_a_class_the_baseline_cannot_predict_is_excluded_not_scored() -> None:
    """A model that never heard of a class has no recall on it, not a recall of zero."""
    tables = _tables(
        {"car": 20, "van": 20},
        {"car": 20, "van": 20},
        baseline_classes={"car"},
        candidate_classes={"car", "van"},
    )

    excluded = tables.excluded
    assert list(excluded["class_name"]) == ["van"]
    assert list(excluded["reason"]) == [UNKNOWN_TO_BASELINE]
    assert "van" not in set(tables.rows["class_name"])


def test_a_class_neither_model_knows_is_not_blamed_on_the_new_one() -> None:
    """A labelling gap is not a difference between the models; saying so misdirects."""
    tables = _tables(
        {"car": 20, "van": 20},
        {"car": 20, "van": 20},
        baseline_classes={"car"},
        candidate_classes={"car"},
    )

    assert list(tables.excluded["reason"]) == [UNKNOWN_TO_BOTH]


def test_the_pooled_row_is_judged_on_its_own_p_value() -> None:
    """It sits outside the BH family, but "not significant" beside a large delta lies."""
    tables = _tables({"car": 4, "van": 4}, {"car": 36, "van": 36})
    rows = tables.rows

    pooled = rows[rows[POOLED_COLUMN].astype(bool)].iloc[0]
    assert pooled["recall_delta"] > 0
    assert pooled["recall_verdict"] == IMPROVED


def test_nothing_comparable_is_an_error_rather_than_an_empty_report() -> None:
    with pytest.raises(ValueError, match="No class can be compared"):
        _tables(
            {"car": 20, "van": 20},
            {"car": 20, "van": 20},
            baseline_classes=set(),
            candidate_classes=set(),
        )


def test_each_checkpoint_gets_its_own_prediction_cache(tmp_path: Path) -> None:
    """Two comparisons in one directory must not score each other's detections.

    Keyed on the role alone, a rerun reused the previous run's predictions for whatever
    checkpoint it was now given.
    """
    from clearml_yolo.tasks.compare import SettledInference, _prediction_cache

    settings = _settled(device="0")
    first = tmp_path / "a.pt"
    second = tmp_path / "b.pt"
    first.write_bytes(b"one")
    second.write_bytes(b"two-different-length")

    def cache(weights: Path, inference: SettledInference = settings) -> Path:
        return _prediction_cache(tmp_path, "baseline", "test", weights, inference)

    assert cache(first) != cache(second)
    # The same checkpoint must still hit its cache, or nothing is ever reused.
    assert cache(first) == cache(first)
    # A retrained checkpoint at an unchanged path is a different model.
    before = cache(first)
    first.write_bytes(b"retrained, quite different")
    assert cache(first) != before


def test_a_cache_is_not_reused_across_inference_settings(tmp_path: Path) -> None:
    """Predictions taken at one confidence, resolution or precision are not the same boxes.

    The cache survives a rerun, so without the settings in its key a comparison could score
    one model's detections against the other's taken at a different operating point — a
    warm FP32 cache against fresh FP16 detections, say.
    """
    from clearml_yolo.tasks.compare import _prediction_cache

    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"weights")
    # A device is named so the FP16 decision does not depend on the test machine's cards.
    baseline = _settled(device="0")

    for changed in (
        baseline.model_copy(update={"conf": 0.25}),
        baseline.model_copy(update={"iou": 0.5}),
        baseline.model_copy(update={"imgsz": 1280}),
        baseline.model_copy(update={"device": "cpu"}),
        # Ultralytics letterboxes per batch according to whether that batch's images
        # share a shape, so which batch an image travelled in decides its geometry.
        baseline.model_copy(update={"batch": 32}),
        baseline.model_copy(update={"ultralytics": {"half": True}}),
    ):
        assert _prediction_cache(tmp_path, "baseline", "test", checkpoint, changed) != (
            _prediction_cache(tmp_path, "baseline", "test", checkpoint, baseline)
        )


def test_a_cache_is_not_reused_when_current_image_content_changes(tmp_path: Path) -> None:
    from clearml_yolo.tasks.compare import _prediction_cache, _split_fingerprint

    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"weights")
    image = tmp_path / "image.jpg"
    image.write_bytes(b"first")
    truth = pd.DataFrame(
        [{"image_name": "image.jpg", "image_path": str(image), "split": "test"}]
    )
    before = _prediction_cache(
        tmp_path, "baseline", "test", checkpoint, _settled(), _split_fingerprint(truth, "test")
    )

    image.write_bytes(b"second")
    after = _prediction_cache(
        tmp_path, "baseline", "test", checkpoint, _settled(), _split_fingerprint(truth, "test")
    )

    assert before != after


def test_native_output_archive_excludes_source_derived_images(tmp_path: Path) -> None:
    from clearml_yolo.tasks.compare import _archive_native_outputs

    native = tmp_path / "native"
    (native / "labels").mkdir(parents=True)
    (native / "labels" / "image.txt").write_text("0 0.5 0.5 1 1\n", encoding="utf-8")
    (native / "predictions.csv").write_text("class,confidence\ncat,0.9\n", encoding="utf-8")
    (native / "args.yaml").write_text(
        "access_key: yaml-secret\nendpoint: https://user:pass@example.test/x?token=query-secret\n",
        encoding="utf-8",
    )
    (native / "results.json").write_text(
        '{"api-key": "json-secret", "score": 0.9}', encoding="utf-8"
    )
    (native / "image.jpg").write_bytes(b"derived-image")

    archive = _archive_native_outputs(native, tmp_path, role="candidate", split="test")

    with zipfile.ZipFile(archive) as bundle:
        assert bundle.namelist() == [
            "args.yaml",
            "labels/image.txt",
            "predictions.csv",
            "results.json",
        ]
        yaml_config = bundle.read("args.yaml").decode()
        json_config = bundle.read("results.json").decode()
        assert "yaml-secret" not in yaml_config
        assert "pass" not in yaml_config
        assert "query-secret" not in yaml_config
        assert "json-secret" not in json_config
        assert "<redacted>" in yaml_config
        assert "<redacted>" in json_config


def test_comparing_a_model_against_itself_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two lookups can land on one task; every delta is then zero, which reads as a result."""
    from clearml_yolo.clearml_session import ClearMLConfig
    from clearml_yolo.tasks.compare import InferenceConfig, ModelRef, compare

    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"")
    monkeypatch.setattr("clearml_yolo.tasks.compare.init_task", lambda *_args, **_kwargs: None)
    same = ModelRef(source="local", weights=checkpoint, thresholds={"car": 0.4})
    (tmp_path / "gt.csv").write_text("image_name,split\na.png,test\n", encoding="utf-8")

    with pytest.raises(ValueError, match="same checkpoint"):
        compare(
            baseline_model=same,
            candidate_model=same.model_copy(),
            ground_truth=tmp_path / "gt.csv",
            output_dir=tmp_path / "out",
            clearml=ClearMLConfig(),
            inference=InferenceConfig(device="cpu"),
        )


def test_thresholds_are_carried_through_per_model() -> None:
    tables = _tables({"car": 20, "van": 20}, {"car": 30, "van": 20})
    rows = tables.rows

    car = rows[rows["class_name"] == "car"].iloc[0]
    assert car["threshold_baseline"] == pytest.approx(0.3)
    assert car["threshold_candidate"] == pytest.approx(0.35)


def test_local_model_requires_checkpoint_and_exact_thresholds() -> None:
    from pydantic import ValidationError

    from clearml_yolo.tasks.compare import ModelRef

    with pytest.raises(ValidationError, match="weights"):
        ModelRef(source="local", thresholds={"car": 0.4})
    with pytest.raises(ValidationError, match="thresholds"):
        ModelRef(source="local", weights=Path("best.pt"))


def test_model_reference_rejects_checkpoint_fields_from_the_other_source() -> None:
    from pydantic import ValidationError

    from clearml_yolo.tasks.compare import ModelRef

    with pytest.raises(ValidationError, match=r"source='clearml'.*weights"):
        ModelRef(source="clearml", weights=Path("best.pt"))
    with pytest.raises(ValidationError, match=r"source='local'.*task_id"):
        ModelRef(
            source="local",
            weights=Path("best.pt"),
            thresholds={"car": 0.4},
            task_id="remote-task",
        )


@pytest.mark.parametrize(
    ("model", "values", "unexpected"),
    [
        ("evaluation", {"preprocess_pred_conf_threshold": 0.5}, "preprocess_pred"),
        ("inference", {"ultralytic": {"half": True}}, "ultralytic"),
        ("model_ref", {"checkpoint": "best.pt"}, "checkpoint"),
    ],
)
def test_input_models_reject_unknown_override_names(
    model: str, values: dict[str, object], unexpected: str
) -> None:
    from pydantic import ValidationError

    from clearml_yolo.comparison.scoring import EvaluationConfig
    from clearml_yolo.tasks.compare import InferenceConfig, ModelRef

    validators: dict[str, Callable[[object], object]] = {
        "evaluation": EvaluationConfig.model_validate,
        "inference": InferenceConfig.model_validate,
        "model_ref": ModelRef.model_validate,
    }
    with pytest.raises(ValidationError, match=unexpected):
        validators[model](values)


def test_inference_image_name_mode_rejects_unknown_fallback() -> None:
    from pydantic import ValidationError

    from clearml_yolo.tasks.compare import InferenceConfig

    with pytest.raises(ValidationError, match="image_name"):
        InferenceConfig(image_name="filename")  # type: ignore[arg-type]


def test_evaluation_mapping_overlays_legacy_comparison_defaults() -> None:
    from clearml_yolo.tasks.compare import _normalize_evaluation

    legacy = _normalize_evaluation(None, iou_threshold=0.25, matching_strategy="greedy")
    mapped = _normalize_evaluation(
        {"ap_method": "continuous"},
        iou_threshold=0.25,
        matching_strategy="greedy",
    )
    overridden = _normalize_evaluation(
        {"iou_threshold": 0.75, "matching_strategy": "hungarian"},
        iou_threshold=0.25,
        matching_strategy="greedy",
    )

    assert (legacy.iou_threshold, legacy.matching_strategy) == (0.25, "greedy")
    assert (mapped.iou_threshold, mapped.matching_strategy, mapped.ap_method) == (
        0.25,
        "greedy",
        "continuous",
    )
    assert (overridden.iou_threshold, overridden.matching_strategy) == (0.75, "hungarian")


def test_nonfinite_model_threshold_is_rejected() -> None:
    from pydantic import ValidationError

    from clearml_yolo.tasks.compare import ModelRef

    with pytest.raises(ValidationError, match="finite"):
        ModelRef(source="local", weights=Path("best.pt"), thresholds={"car": float("nan")})


@pytest.mark.parametrize("key", ["source", "model", "project", "name", "save_dir"])
def test_inference_native_mapping_cannot_override_owned_keys(key: str) -> None:
    from pydantic import ValidationError

    from clearml_yolo.tasks.compare import InferenceConfig

    with pytest.raises(ValidationError, match=key):
        InferenceConfig(ultralytics={key: "override"})


@pytest.mark.parametrize(
    "explicit",
    [
        {"project_name": "chosen-project"},
        {"task_name": "chosen-task"},
        {"tags": ["candidate-baseline"]},
    ],
)
def test_explicit_missing_baseline_is_an_error(
    explicit: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.tasks.compare import (
        ModelRef,
        NoBaselineModelError,
        _is_automatic_baseline,
        _resolve_model,
    )

    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.latest_completed_task_id", lambda *_args, **_kwargs: None
    )

    model = ModelRef.model_validate(explicit)
    assert not _is_automatic_baseline(model)
    with pytest.raises(ValueError, match="No completed") as error:
        _resolve_model(
            model,
            "test",
            "fallback-project",
            exclude_task_id="current-task",
            automatic_absence_is_skip=_is_automatic_baseline(model),
        )

    assert not isinstance(error.value, NoBaselineModelError)


def test_default_missing_baseline_is_the_only_skippable_lookup() -> None:
    from clearml_yolo.tasks.compare import ModelRef, _is_automatic_baseline

    assert _is_automatic_baseline(ModelRef())


def test_resolved_clearml_model_keeps_exact_task_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.tasks.compare import ModelRef, _resolve_model

    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"weights")
    task_id = "a" * 32
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.resolve_task_weights", lambda _task_id: checkpoint
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.fetch_best_confidences",
        lambda _task_id, _split: {"cat": 0.5},
    )

    resolved = _resolve_model(
        ModelRef(task_id=task_id),
        "test",
        "project",
        exclude_task_id=None,
        automatic_absence_is_skip=False,
    )

    assert resolved.task_id == task_id


def test_compare_dashboards_and_statistics_share_the_same_test_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.clearml_session import ClearMLConfig
    from clearml_yolo.comparison.reinfer import VocabularyReport
    from clearml_yolo.inference import ScoredResolution
    from clearml_yolo.tasks.compare import InferenceConfig, ModelRef, compare

    baseline_weights = tmp_path / "baseline.pt"
    candidate_weights = tmp_path / "candidate.pt"
    baseline_weights.write_bytes(b"baseline")
    candidate_weights.write_bytes(b"candidate")
    image = tmp_path / "image.jpg"
    empty = tmp_path / "empty.jpg"
    image.write_bytes(b"image")
    empty.write_bytes(b"empty")
    truth = pd.DataFrame(
        [
            ("image.jpg", str(image), "cat", 0.0, 0.0, 10.0, 10.0, "test"),
            ("empty.jpg", str(empty), None, None, None, None, None, "test"),
        ],
        columns=[
            "image_name",
            "image_path",
            "instance_label",
            "bbox_x_tl",
            "bbox_y_tl",
            "bbox_x_br",
            "bbox_y_br",
            "split",
        ],
    )
    truth_path = tmp_path / "truth.csv"
    truth.to_csv(truth_path, index=False)
    columns = [
        "image_name",
        "instance_label",
        "bbox_x_tl",
        "bbox_y_tl",
        "bbox_x_br",
        "bbox_y_br",
        "confidence",
    ]

    def fake_reinfer(weights: Path, *_args: Any, **_kwargs: Any) -> tuple[pd.DataFrame, Any]:
        rows = []
        if Path(weights).name == "candidate.pt":
            rows = [
                ("image.jpg", "cat", 0.0, 0.0, 10.0, 10.0, 0.9),
                ("empty.jpg", "cat", 20.0, 20.0, 30.0, 30.0, 0.8),
            ]
        frame = pd.DataFrame(rows, columns=columns)
        role = "candidate" if Path(weights).name == "candidate.pt" else "baseline"
        save_dir = tmp_path / "comparison" / "native" / f"{role}_test"
        (save_dir / "labels").mkdir(parents=True, exist_ok=True)
        (save_dir / "labels" / "image.txt").write_text("prediction", encoding="utf-8")
        (save_dir / "image.jpg").write_bytes(b"must-not-upload")
        frame.attrs["effective_args"] = {"device": f"normalized-{role}"}
        frame.attrs["save_dir"] = str(save_dir)
        return frame, VocabularyReport(
            model_classes=["cat"], unknown_to_model=[], unknown_to_ground_truth=[]
        )

    uploads: dict[str, object] = {}
    expected: list[str] = []

    class FakeTask:
        id = "current-task"

    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.init_task", lambda *_args, **_kwargs: FakeTask()
    )
    monkeypatch.setattr("clearml_yolo.tasks.compare.report_comparison", lambda *_args: None)
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.upload_artifact",
        lambda _task, name, value: uploads.setdefault(name, value),
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.expect_artifacts",
        lambda _task, names: expected.extend(names),
    )
    monkeypatch.setattr("clearml_yolo.tasks.compare.reinfer_split", fake_reinfer)
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.resolution_of",
        lambda *_args, **_kwargs: ScoredResolution(trained_at=640, scored_at=640),
    )
    monkeypatch.setattr("clearml_yolo.tasks.compare.trained_imgsz", lambda *_args: 640)

    result = compare(
        ModelRef(source="local", weights=baseline_weights, thresholds={"cat": 0.5}),
        ModelRef(source="local", weights=candidate_weights, thresholds={"cat": 0.5}),
        truth_path,
        tmp_path / "comparison",
        ClearMLConfig(),
        InferenceConfig(imgsz=640, device="cpu"),
        bootstrap_iterations=20,
    )

    assert result is not None
    baseline = pd.read_excel(result.baseline_dashboard, index_col=0)
    candidate = pd.read_excel(result.candidate_dashboard, index_col=0)
    statistics = pd.read_excel(result.workbook, sheet_name="Сравнение")
    row = statistics[statistics["Класс"] == "cat"].iloc[0]
    assert (baseline.loc["cat", "tp"], baseline.loc["cat", "fp"], baseline.loc["cat", "fn"]) == (
        row["TP прод"],
        row["FP прод"],
        row["FN прод"],
    )
    assert (
        candidate.loc["cat", "tp"],
        candidate.loc["cat", "fp"],
        candidate.loc["cat", "fn"],
    ) == (row["TP новая"], row["FP новая"], row["FN новая"])
    assert candidate.loc["cat", "fp"] == 1
    _assert_native_audit_artifacts(uploads)
    assert {
        "compare_ground_truth",
        "compare_model_references",
        "compare_effective_inference",
        "compare_image_membership_test",
        "compare_thresholds_baseline_test",
        "compare_thresholds_candidate_test",
        "compare_counts_test",
        "compare_exclusions_test",
        "compare_methodology_test",
        "compare_dashboard_dtrk_baseline_test",
        "compare_dashboard_dtrk_candidate_test",
        "compare_matches_gt_baseline_test",
        "compare_matches_preds_candidate_test",
        "compare_confusion_matrix_baseline_test",
        "compare_plot_recall_candidate_test",
        "compare_metrics_summary_baseline_test",
        "compare_metrics_raw_candidate_test",
        "compare_manifest",
    } <= set(uploads)
    assert set(expected) == set(uploads)


def test_comparison_scoring_uses_the_full_evaluation_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.comparison.reinfer import VocabularyReport
    from clearml_yolo.comparison.scoring import EvaluationConfig, evaluate_split
    from clearml_yolo.tasks.compare import _scored

    image = tmp_path / "image.jpg"
    empty = tmp_path / "empty.jpg"
    image.write_bytes(b"image")
    empty.write_bytes(b"empty")
    truth = pd.DataFrame(
        [
            ("image.jpg", str(image), "cat", 0.0, 0.0, 10.0, 10.0, "test"),
            # Metrics preprocessing removes this duplicate before matching.
            ("image.jpg", str(image), "cat", 0.0, 0.0, 10.0, 10.0, "test"),
            ("empty.jpg", str(empty), None, None, None, None, None, "test"),
        ],
        columns=[
            "image_name",
            "image_path",
            "instance_label",
            "bbox_x_tl",
            "bbox_y_tl",
            "bbox_x_br",
            "bbox_y_br",
            "split",
        ],
    )
    raw_predictions = pd.DataFrame(
        [
            ("image.jpg", "cat", 0.0, 0.0, 10.0, 10.0, 0.9),
            ("empty.jpg", "cat", 20.0, 20.0, 30.0, 30.0, 0.4),
        ],
        columns=[
            "image_name",
            "instance_label",
            "bbox_x_tl",
            "bbox_y_tl",
            "bbox_x_br",
            "bbox_y_br",
            "confidence",
        ],
    )
    native_dir = tmp_path / "native" / "candidate_test"
    raw_predictions.attrs["effective_args"] = {"device": "cpu"}
    raw_predictions.attrs["save_dir"] = str(native_dir)
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.reinfer_split",
        lambda *_args, **_kwargs: (
            raw_predictions,
            VocabularyReport(
                model_classes=["cat"], unknown_to_model=[], unknown_to_ground_truth=[]
            ),
        ),
    )
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def observed_evaluation(*args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        return evaluate_split(*args, **kwargs)

    monkeypatch.setattr("clearml_yolo.tasks.compare.evaluate_split", observed_evaluation)
    weights = tmp_path / "candidate.pt"
    weights.write_bytes(b"candidate")

    evaluated, _, _, _ = _scored(
        weights,
        truth,
        "test",
        tmp_path / "candidate_predictions.csv",
        tmp_path,
        "candidate",
        _settled(),
        {"cat": 0.0},
        ["cat"],
        evaluation=EvaluationConfig(
            iou_threshold=0.3,
            matching_strategy="greedy",
            ap_method="continuous",
            preprocess=True,
            preprocess_preds_conf_threshold=0.5,
        ),
    )

    args, kwargs = calls[0]
    assert len(args[0]) == 2  # one GT box plus the empty-image membership row
    assert len(args[1]) == 2  # mAP and raw artifacts keep unfiltered inference
    assert len(args[2]) == 1  # fixed-threshold counts use preprocessed predictions
    assert kwargs["iou_threshold"] == 0.3
    assert kwargs["matching_strategy"] == "greedy"
    assert kwargs["ap_method"] == "continuous"
    assert kwargs["skip_cohen_kappa"] is True
    assert evaluated.thresholds == {"cat": 0.0}  # comparison never recalibrates
    assert evaluated.outcome.counts["cat"] == ClassCounts(tp=1, fp=0, fn=0)


def test_prediction_only_class_requires_its_saved_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.comparison.reinfer import VocabularyReport
    from clearml_yolo.comparison.scoring import EvaluationConfig
    from clearml_yolo.tasks.compare import _scored

    image = tmp_path / "image.jpg"
    image.write_bytes(b"image")
    truth = pd.DataFrame(
        [("image.jpg", str(image), "cat", 0.0, 0.0, 10.0, 10.0, "test")],
        columns=[
            "image_name",
            "image_path",
            "instance_label",
            "bbox_x_tl",
            "bbox_y_tl",
            "bbox_x_br",
            "bbox_y_br",
            "split",
        ],
    )
    predictions = pd.DataFrame(
        [("image.jpg", "bird", 20.0, 20.0, 30.0, 30.0, 0.9)],
        columns=[
            "image_name",
            "instance_label",
            "bbox_x_tl",
            "bbox_y_tl",
            "bbox_x_br",
            "bbox_y_br",
            "confidence",
        ],
    )
    predictions.attrs["save_dir"] = str(tmp_path / "native" / "candidate_test")
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.reinfer_split",
        lambda *_args, **_kwargs: (
            predictions,
            VocabularyReport(
                model_classes=["cat", "bird"],
                unknown_to_model=[],
                unknown_to_ground_truth=["bird"],
            ),
        ),
    )

    with pytest.raises(ValueError, match=r"missing required class.*bird"):
        _scored(
            tmp_path / "candidate.pt",
            truth,
            "test",
            tmp_path / "candidate_predictions.csv",
            tmp_path,
            "candidate",
            _settled(),
            {"cat": 0.5},
            ["cat"],
            evaluation=EvaluationConfig(),
        )


def test_automatic_baseline_absence_still_evaluates_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.clearml_session import ClearMLConfig
    from clearml_yolo.comparison.reinfer import VocabularyReport
    from clearml_yolo.inference import ScoredResolution
    from clearml_yolo.tasks.compare import InferenceConfig, ModelRef, compare

    candidate = tmp_path / "candidate.pt"
    candidate.write_bytes(b"candidate")
    image = tmp_path / "image.jpg"
    image.write_bytes(b"image")
    truth = pd.DataFrame(
        [("image.jpg", str(image), "cat", 0.0, 0.0, 10.0, 10.0, "test")],
        columns=[
            "image_name",
            "image_path",
            "instance_label",
            "bbox_x_tl",
            "bbox_y_tl",
            "bbox_x_br",
            "bbox_y_br",
            "split",
        ],
    )
    truth_path = tmp_path / "truth.csv"
    truth.to_csv(truth_path, index=False)
    predictions = pd.DataFrame(
        [("image.jpg", "cat", 0.0, 0.0, 10.0, 10.0, 0.9)],
        columns=[
            "image_name",
            "instance_label",
            "bbox_x_tl",
            "bbox_y_tl",
            "bbox_x_br",
            "bbox_y_br",
            "confidence",
        ],
    )

    uploads: dict[str, object] = {}
    expected: list[str] = []

    class FakeTask:
        id = "current-task"

    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.init_task", lambda *_args, **_kwargs: FakeTask()
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.expect_artifacts",
        lambda _task, names: expected.extend(names),
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.upload_artifact",
        lambda _task, name, value: uploads.setdefault(name, value),
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.latest_completed_task_id", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.reinfer_split",
        lambda *_args, **_kwargs: (
            predictions,
            VocabularyReport(
                model_classes=["cat"],
                unknown_to_model=[],
                unknown_to_ground_truth=[],
            ),
        ),
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.resolution_of",
        lambda *_args, **_kwargs: ScoredResolution(trained_at=640, scored_at=640),
    )

    result = compare(
        ModelRef(),
        ModelRef(source="local", weights=candidate, thresholds={"cat": 0.5}),
        truth_path,
        tmp_path / "comparison",
        ClearMLConfig(),
        InferenceConfig(imgsz=640, device="cpu"),
        bootstrap_iterations=20,
    )

    assert result is None
    assert list((tmp_path / "comparison").glob("full_dashboard_candidate_test.xlsx"))
    assert uploads["comparison_status"] == {
        "status": "skipped",
        "reason": "No completed ClearML task in project 'clearml-yolo' tagged ['prod']",
    }
    assert set(expected) == set(uploads)
