"""Assembling two scored splits into the frame both reports read.

The tests lean on the contracts the consumers pin: the column set in
``comparison/workbook.py`` and the pooled/BH conventions in ``clearml_report.py``.
"""

import math
import zipfile
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

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
from clearml_yolo.comparison.scoring import ClassCounts, EvaluatedSplit, SplitOutcome
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
        ultralytics={"quantize": None},
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
        name: [index < count for index in range(len(IMAGES))] for name, count in per_class.items()
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


def test_one_sided_class_keeps_metrics_but_is_excluded_from_statistics() -> None:
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
    van = tables.rows.set_index("class_name").loc["van"]
    assert math.isnan(cast(float, van["tp_baseline"]))
    assert math.isnan(cast(float, van["recall_baseline"]))
    assert math.isnan(cast(float, van["threshold_baseline"]))
    assert van["tp_candidate"] == 20
    assert van["recall_candidate"] == 0.5
    assert van["threshold_candidate"] == 0.45
    assert van["recall_verdict"] == "unavailable"
    assert tables.methodology["family_size"] == 2


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


def test_disjoint_vocabularies_produce_metrics_and_unavailable_pooled_row() -> None:
    tables = _tables(
        {"car": 0, "van": 20},
        {"car": 20, "van": 0},
        baseline_classes={"car", "unused_baseline"},
        candidate_classes={"van", "unused_candidate"},
    )
    rows = tables.rows.set_index("class_name")
    assert set(rows.index) == {"car", "van", "unused_baseline", "unused_candidate", "pooled"}
    assert rows.loc["car", "recall_baseline"] == 0
    assert math.isnan(cast(float, rows.loc["car", "recall_candidate"]))
    assert rows.loc["van", "recall_candidate"] == 0
    assert rows.loc["unused_candidate", "tp_candidate"] == 0
    assert rows.loc["pooled", "recall_verdict"] == "unavailable"
    assert math.isnan(cast(float, rows.loc["pooled", "tp_baseline"]))
    assert tables.methodology["family_size"] == 0


def test_pooled_tests_use_the_same_shared_classes_as_counts() -> None:
    tables = _tables(
        {"car": 4, "van": 36},
        {"car": 36, "van": 4},
        baseline_classes={"car"},
        candidate_classes={"car", "van"},
    )
    rows = tables.rows.set_index("class_name")
    pooled = rows.loc["pooled"]
    car = rows.loc["car"]
    assert pooled["tp_baseline"] == 4
    assert pooled["tp_candidate"] == 36
    for metric in ("precision", "recall"):
        for suffix in ("delta", "p_value", "ci_lower", "ci_upper"):
            assert pooled[f"{metric}_{suffix}"] == pytest.approx(car[f"{metric}_{suffix}"])
    assert tables.methodology["family_size"] == 2


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


def test_immutable_images_are_not_hashed_for_prediction_cache(tmp_path: Path) -> None:
    from clearml_yolo.tasks.compare import _prediction_cache, _split_fingerprint

    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"weights")
    image = tmp_path / "image.jpg"
    image.write_bytes(b"first")
    truth = pd.DataFrame([{"image_name": "image.jpg", "image_path": str(image), "split": "test"}])
    before = _prediction_cache(
        tmp_path, "baseline", "test", checkpoint, _settled(), _split_fingerprint(truth, "test")
    )

    image.write_bytes(b"second")
    after = _prediction_cache(
        tmp_path, "baseline", "test", checkpoint, _settled(), _split_fingerprint(truth, "test")
    )

    assert before == after


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
            inference=InferenceConfig(conf=0.001, iou=0.7, imgsz=640, batch=1, device="cpu"),
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
        InferenceConfig(
            conf=0.001,
            iou=0.7,
            imgsz=640,
            batch=1,
            device=None,
            image_name="filename",  # type: ignore[arg-type]
        )


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
        InferenceConfig(
            conf=0.001, iou=0.7, imgsz=640, batch=1, device=None, ultralytics={key: "override"}
        )


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
        "clearml_yolo.tasks.compare.resolve_task_model",
        lambda task_id: (checkpoint, {"task_id": task_id}),
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.fetch_best_confidences",
        lambda _task_id: {"cat": 0.5},
    )

    resolved = _resolve_model(
        ModelRef(task_id=task_id),
        "project",
        exclude_task_id=None,
        automatic_absence_is_skip=False,
    )

    assert resolved.task_id == task_id


def _assert_recovered_sources(configurations: dict[str, Any], legacy_role: str | None) -> None:
    if legacy_role is not None:
        for role in ("baseline", "candidate"):
            source = configurations["comparison"][role]
            assert source["task_id"] == role
            if legacy_role in (role, "both"):
                assert "model_id" not in source
                assert source["artifact_name"] == "model"
            else:
                assert source["model_id"] == f"{role}-model"


def _stub_comparison_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, object], dict[str, Any], list[str], list[dict[str, Any]]]:
    uploads: dict[str, object] = {}
    configurations: dict[str, Any] = {}
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.record_run_configuration",
        lambda _task, values: configurations.update(values),
        raising=False,
    )
    expected: list[str] = []
    evaluations: list[dict[str, Any]] = []

    def publish_evaluation(
        _task: object, evaluated: EvaluatedSplit, truth: Path, predictions: Path, **kwargs: Any
    ) -> None:
        # The invocation-owned adapter is tested separately; this boundary records
        # the exact scored populations handed off by comparison.
        evaluations.append(
            {
                "evaluated": evaluated,
                "truth": truth,
                "predictions": predictions,
                **kwargs,
            }
        )

    monkeypatch.setattr("clearml_yolo.tasks.compare.publish_evaluation", publish_evaluation)

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
        "clearml_yolo.tasks.compare.publish_table",
        lambda _task, name, value, **kwargs: uploads.setdefault(name, value),
        raising=False,
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.expect_artifacts",
        lambda _task, names: expected.extend(names),
    )
    return uploads, configurations, expected, evaluations


def _recovered_comparison_models(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    legacy_role: str | None,
    override: bool,
    baseline_weights: Path,
    candidate_weights: Path,
) -> dict[str, Any]:
    from clearml_yolo.tasks.compare import ModelRef

    models = {
        role: ModelRef(source="local", weights=weights, thresholds={"cat": 0.5})
        for role, weights in [("baseline", baseline_weights), ("candidate", candidate_weights)]
    }
    if legacy_role is not None:
        threshold_file = tmp_path / "thresholds.csv"
        threshold_file.write_text("class_name,confidence\ncat,0.5\n", encoding="utf-8")
        sources = {}
        for role, weights in [("baseline", baseline_weights), ("candidate", candidate_weights)]:
            output = SimpleNamespace(
                id=f"{role}-model",
                url=f"https://files.example/{role}.pt",
                get_metadata=lambda _key: "best",
                get_local_copy=lambda weights=weights: str(weights),
            )
            artifacts = (
                {
                    "model": SimpleNamespace(get_local_copy=lambda weights=weights: str(weights)),
                    "dashboard_full_test": SimpleNamespace(
                        get=lambda: pd.DataFrame({"confidence": [0.5]}, index=["cat"]),
                        get_local_copy=lambda: "",
                    ),
                }
                if legacy_role in (role, "both")
                else {
                    "metrics_best_confidences_val": SimpleNamespace(
                        get_local_copy=lambda: str(threshold_file)
                    )
                }
            )
            outputs = [] if legacy_role in (role, "both") else [output]
            sources[role] = SimpleNamespace(
                id=role,
                name=role,
                artifacts=artifacts,
                get_models=lambda outputs=outputs: {"output": outputs},
                get_output_log_web_page=lambda role=role: f"https://clearml.example/{role}",
            )
            models[role] = ModelRef(task_id=role, thresholds={"cat": 0.7} if override else None)
        monkeypatch.setattr("clearml_yolo.clearml_models._task", sources.__getitem__)

    return models


def _assert_evaluation_handoffs(
    evaluations: list[dict[str, Any]],
    truth: Path,
    split: str,
    dashboards: tuple[Path, Path],
    prediction_paths: tuple[Path, Path],
) -> None:
    assert [call["role"] for call in evaluations] == [
        "comparison_baseline",
        "comparison_candidate",
    ]
    for call, dashboard, predictions in zip(
        evaluations,
        dashboards,
        prediction_paths,
        strict=True,
    ):
        assert call["truth"] == truth
        assert call["predictions"] == predictions
        assert call["output_dir"] == predictions.parent
        assert call["evaluated"].dashboard_path == dashboard
        assert call["evaluated"].dtrk_dashboard_path.is_file()
        assert call["evaluated"].split == split
        assert call["model_id"]


@pytest.mark.parametrize("legacy_role", [None, "baseline", "candidate", "both"])
@pytest.mark.parametrize("split", ["test", "val"])
@pytest.mark.parametrize("override", [False, True])
def test_compare_dashboards_and_statistics_share_the_same_test_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    legacy_role: str | None,
    split: str,
    override: bool,
) -> None:
    from clearml_yolo.clearml_session import ClearMLConfig
    from clearml_yolo.comparison.reinfer import VocabularyReport
    from clearml_yolo.inference import ScoredResolution
    from clearml_yolo.tasks.compare import InferenceConfig, compare

    baseline_weights, candidate_weights = tmp_path / "baseline.pt", tmp_path / "candidate.pt"
    baseline_weights.write_bytes(b"baseline")
    candidate_weights.write_bytes(b"candidate")
    image, empty = tmp_path / "image.jpg", tmp_path / "empty.jpg"
    image.write_bytes(b"image")
    empty.write_bytes(b"empty")
    truth = pd.DataFrame(
        [
            ("image.jpg", str(image), "cat", 0.0, 0.0, 10.0, 10.0, split),
            ("empty.jpg", str(empty), None, None, None, None, None, split),
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

    membership: list[tuple[str, list[str]]] = []

    def fake_reinfer(
        weights: Path, current: pd.DataFrame, selected_split: str, output: Path, **_kwargs: Any
    ) -> tuple[pd.DataFrame, Any]:
        membership.append(
            (selected_split, current.loc[current["split"] == selected_split, "image_name"].tolist())
        )
        rows = []
        if Path(weights).name == "candidate.pt":
            rows = [
                ("image.jpg", "cat", 0.0, 0.0, 10.0, 10.0, 0.9),
                ("empty.jpg", "cat", 20.0, 20.0, 30.0, 30.0, 0.8),
            ]
        frame = pd.DataFrame(rows, columns=columns)
        role = "candidate" if Path(weights).name == "candidate.pt" else "baseline"
        save_dir = tmp_path / "comparison" / "native" / f"{role}_{split}"
        (save_dir / "labels").mkdir(parents=True, exist_ok=True)
        (save_dir / "labels" / "image.txt").write_text("prediction", encoding="utf-8")
        (save_dir / "image.jpg").write_bytes(b"must-not-upload")
        frame.attrs.update(effective_args={"device": f"normalized-{role}"}, save_dir=str(save_dir))
        frame.to_csv(output, index=False)
        return frame, VocabularyReport(
            model_classes=["cat"], unknown_to_model=[], unknown_to_ground_truth=[]
        )

    uploads, configurations, expected, evaluations = _stub_comparison_publication(monkeypatch)
    monkeypatch.setattr("clearml_yolo.tasks.compare.reinfer_split", fake_reinfer)
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.resolution_of",
        lambda *_args, **_kwargs: ScoredResolution(trained_at=640, scored_at=640),
    )
    monkeypatch.setattr("clearml_yolo.tasks.compare.trained_imgsz", lambda *_args: 640)

    models = _recovered_comparison_models(
        tmp_path, monkeypatch, legacy_role, override, baseline_weights, candidate_weights
    )

    result = compare(
        models["baseline"],
        models["candidate"],
        truth_path,
        tmp_path / "comparison",
        ClearMLConfig(),
        InferenceConfig(conf=0.001, iou=0.7, imgsz=640, batch=1, device="cpu"),
        bootstrap_iterations=20,
        split=split,
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
    assert membership == [(split, ["image.jpg", "empty.jpg"])] * 2
    threshold = 0.7 if override and legacy_role is not None else 0.5
    assert baseline.loc["cat", "confidence"] == threshold
    assert candidate.loc["cat", "confidence"] == threshold
    _assert_recovered_sources(configurations, legacy_role)
    assert set(uploads) == {
        f"compare_workbook_{split}",
        f"compare_workbook_{split}_excluded",
    }
    assert set(expected) == {f"compare_workbook_{split}"}
    _assert_evaluation_handoffs(
        evaluations,
        truth_path,
        split,
        (result.baseline_dashboard, result.candidate_dashboard),
        (result.baseline_predictions, result.candidate_predictions),
    )


def test_comparison_scoring_uses_the_full_evaluation_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.comparison.reinfer import VocabularyReport
    from clearml_yolo.comparison.scoring import EvaluationConfig, evaluate_split
    from clearml_yolo.tasks.compare import _scored

    image, empty = tmp_path / "image.jpg", tmp_path / "empty.jpg"
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

    uploads, configurations, expected, evaluations = _stub_comparison_publication(monkeypatch)
    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.latest_completed_task_id", lambda *_args, **_kwargs: None
    )

    def fake_reinfer(
        _weights: Path, _truth: pd.DataFrame, _split: str, output: Path, **_kwargs: Any
    ) -> tuple[pd.DataFrame, VocabularyReport]:
        predictions.to_csv(output, index=False)
        return predictions, VocabularyReport(
            model_classes=["cat"],
            unknown_to_model=[],
            unknown_to_ground_truth=[],
        )

    monkeypatch.setattr(
        "clearml_yolo.tasks.compare.reinfer_split",
        fake_reinfer,
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
        InferenceConfig(conf=0.001, iou=0.7, imgsz=640, batch=1, device="cpu"),
        bootstrap_iterations=20,
    )

    assert result is None
    assert list((tmp_path / "comparison").glob("full_dashboard_candidate_test.xlsx"))
    assert configurations["comparison_status"] == {
        "status": "skipped",
        "reason": "No completed ClearML task in project 'clearml-yolo' tagged ['prod']",
    }
    # Comparison itself has no paired artifact to publish; its candidate evaluation
    # is handed to the canonical CSV/dashboard/interactive-plot owner.
    assert uploads == {}
    assert expected == []
    assert len(evaluations) == 1
    published = evaluations[0]
    assert published["role"] == "comparison_candidate"
    assert published["truth"] == truth_path
    assert published["predictions"].parent == tmp_path / "comparison"
    assert published["predictions"].name.startswith("candidate_predictions_test_")
    assert published["predictions"].is_file()
    assert published["evaluated"].dashboard_path.is_file()
    assert published["evaluated"].dtrk_dashboard_path.is_file()
    assert published["evaluated"].outcome.counts["cat"].tp == 1
    assert published["evaluated"].confusion_matrix.counts
    assert published["evaluated"].pr_curves[0].ap50 == pytest.approx(1)


def test_shared_class_without_predictions_keeps_zero_counts_and_unavailable_tests() -> None:
    baseline = _outcome(_flags({"car": 20, "van": 0}), _flags({"car": 20, "van": 0}))
    candidate = _outcome(_flags({"car": 30, "van": 0}), _flags({"car": 30, "van": 0}))

    def without_van_predictions(outcome: SplitOutcome) -> SplitOutcome:
        return SplitOutcome(
            counts={"car": outcome.counts["car"], "van": ClassCounts(fn=40)},
            gt_status=outcome.gt_status,
            pred_status=outcome.pred_status[outcome.pred_status["instance_label"] == "car"],
        )

    tables = build_comparison_rows(
        without_van_predictions(baseline),
        without_van_predictions(candidate),
        thresholds_baseline={"car": 0.3, "van": 0.4},
        thresholds_candidate={"car": 0.3, "van": 0.4},
        images=IMAGES,
        iterations=200,
    )
    rows = tables.rows.set_index("class_name")
    assert rows.loc["van", "tp_baseline"] == 0
    assert rows.loc["van", "recall_baseline"] == 0
    assert rows.loc["van", "recall_verdict"] == "unavailable"
    assert rows.loc["pooled", "fn_baseline"] == 20
    assert rows.loc["pooled", "recall_delta"] == rows.loc["car", "recall_delta"]
    assert tables.methodology["pooled_classes"] == ["car"]
    assert tables.methodology["family_size"] == 2


def test_disjoint_workbook_preserves_real_zero_and_unavailable_pooled_cells(tmp_path: Path) -> None:
    from openpyxl import load_workbook  # type: ignore[import-untyped]

    tables = _tables(
        {"car": 0, "van": 20},
        {"car": 20, "van": 0},
        baseline_classes={"car"},
        candidate_classes={"van"},
    )
    path = tmp_path / "disjoint.xlsx"
    write_comparison_workbook(tables.rows, tables.excluded, tables.methodology, path)
    sheet = load_workbook(path)["Сравнение"]
    headers = [cell.value for cell in sheet[1]]

    def cell(row: int, header: str) -> Any:
        return sheet.cell(row=row, column=headers.index(header) + 1)

    assert cell(2, "Recall прод").value == 0
    assert cell(2, "Recall новая").value == "NA"
    assert cell(3, "Recall новая").value == 0
    assert cell(3, "Recall прод").value == "NA"
    for header in ("TP прод", "Recall прод", "Δ Recall", "p BH (R)", "Вердикт (R)"):
        assert cell(4, header).value == "NA"
        assert cell(4, header).fill.fill_type is None
