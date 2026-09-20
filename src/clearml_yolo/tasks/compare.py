"""Re-infer and evaluate two checkpoints on the same current test images."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml
from digital_metrics import summarize_metrics
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, model_validator

from clearml_yolo import artifact_names
from clearml_yolo.clearml_models import (
    fetch_best_confidences,
    latest_completed_task_id,
    resolve_task_weights,
)
from clearml_yolo.clearml_report import report_comparison
from clearml_yolo.clearml_session import (
    ClearMLConfig,
    expect_artifacts,
    init_task,
    sanitize_configuration,
    upload_artifact,
)
from clearml_yolo.comparison.assemble import ComparisonTables, build_comparison_rows
from clearml_yolo.comparison.reinfer import InferenceEvidence, VocabularyReport, reinfer_split
from clearml_yolo.comparison.scoring import (
    EvaluatedSplit,
    EvaluationConfig,
    classes_from_ground_truth,
    evaluate_split,
    prepare_ground_truth,
    prepare_predictions,
    validate_split_membership,
    validate_thresholds,
)
from clearml_yolo.comparison.workbook import write_comparison_workbook
from clearml_yolo.inference import ImageNameMode, resolution_of, trained_imgsz

ModelSource = Literal["clearml", "local"]
MANIFEST_NAME = "comparison_manifest.json"


class NoBaselineModelError(LookupError):
    """Automatic baseline resolution found no previous promoted run."""


class ModelRef(BaseModel):
    """A checkpoint and the exact thresholds calibrated for it."""

    model_config = ConfigDict(extra="forbid")

    source: ModelSource = "clearml"
    task_id: str | None = None
    project_name: str | None = None
    task_name: str | None = None
    tags: list[str] = Field(default_factory=lambda: ["prod"])
    weights: Path | None = None
    thresholds: dict[str, float] | None = None

    @model_validator(mode="after")
    def _validate_source(self) -> ModelRef:
        if self.source == "local":
            if self.weights is None:
                raise ValueError("source='local' requires weights")
            if not self.thresholds:
                raise ValueError("source='local' requires exact thresholds")
            if self.task_id is not None:
                raise ValueError("source='local' cannot specify a ClearML task_id")
        elif self.weights is not None:
            raise ValueError("source='clearml' cannot specify local weights")
        if self.thresholds is not None:
            self.thresholds = validate_thresholds(self.thresholds, list(self.thresholds))
        return self


class ResolvedModel(BaseModel):
    """A model reference after lookup, with its exact provenance retained."""

    source: ModelSource
    weights: Path
    thresholds: dict[str, float]
    task_id: str | None = None


def _is_automatic_baseline(model: ModelRef) -> bool:
    """Whether the conventional latest ``prod`` lookup may be absent."""
    return (
        model.source == "clearml"
        and model.task_id is None
        and model.project_name is None
        and model.task_name is None
        and model.weights is None
        and model.tags == ["prod"]
    )


def _resolved_task_id(
    model: ModelRef,
    fallback_project: str,
    *,
    exclude_task_id: str | None,
    automatic_absence_is_skip: bool,
) -> str:
    if model.task_id:
        return model.task_id
    project = model.project_name or fallback_project
    found = latest_completed_task_id(
        project,
        model.task_name,
        model.tags,
        exclude_task_id=exclude_task_id,
    )
    if found is not None:
        return found
    tagged = f" tagged {model.tags}" if model.tags else ""
    message = f"No completed ClearML task in project {project!r}{tagged}"
    if automatic_absence_is_skip:
        raise NoBaselineModelError(message)
    raise ValueError(message)


def _resolve_model(
    model: ModelRef,
    split: str,
    fallback_project: str,
    *,
    exclude_task_id: str | None,
    automatic_absence_is_skip: bool,
) -> ResolvedModel:
    if model.source == "local":
        if model.weights is None or model.thresholds is None:
            raise RuntimeError("Validated local model is missing weights or thresholds")
        if not model.weights.is_file():
            raise FileNotFoundError(f"Local checkpoint does not exist: {model.weights}")
        return ResolvedModel(
            source="local", weights=model.weights, thresholds=dict(model.thresholds)
        )

    task_id = _resolved_task_id(
        model,
        fallback_project,
        exclude_task_id=exclude_task_id,
        automatic_absence_is_skip=automatic_absence_is_skip,
    )
    thresholds = (
        dict(model.thresholds)
        if model.thresholds is not None
        else fetch_best_confidences(task_id, split)
    )
    return ResolvedModel(
        source="clearml",
        task_id=task_id,
        weights=resolve_task_weights(task_id),
        thresholds=thresholds,
    )


class InferenceConfig(BaseModel):
    """Native inference settings applied identically to both checkpoints."""

    model_config = ConfigDict(extra="forbid")

    conf: float = 0.001
    iou: float = 0.7
    imgsz: int | list[int] | None = None
    batch: int = 1
    device: str | int | list[int] | None = None
    image_name: ImageNameMode = "name"
    reuse_existing: bool = True
    ultralytics: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _no_duplicate_native_keys(self) -> InferenceConfig:
        fixed = {
            "batch",
            "conf",
            "device",
            "image_name",
            "imgsz",
            "iou",
            "mode",
            "model",
            "name",
            "project",
            "save_dir",
            "source",
            "stream",
            "task",
        }
        overlap = sorted(fixed & set(self.ultralytics))
        if overlap:
            raise ValueError(f"inference.ultralytics duplicates explicit key(s): {overlap}")
        return self


class SettledInference(BaseModel):
    """Inference settings after checkpoint-derived resolution is filled."""

    conf: float
    iou: float
    imgsz: int | list[int]
    batch: int
    device: str | int | list[int] | None
    image_name: ImageNameMode
    reuse_existing: bool
    ultralytics: dict[str, Any] = Field(default_factory=dict)


class ComparisonManifest(BaseModel):
    split: str
    baseline_dashboard: str
    candidate_dashboard: str
    baseline_predictions: str
    candidate_predictions: str
    statistical_workbook: str


class CompareResult(BaseModel):
    """Statistical report plus the paired inputs for developer/business reports."""

    workbook: Path
    baseline_dashboard: Path
    candidate_dashboard: Path
    baseline_predictions: Path
    candidate_predictions: Path
    manifest: Path
    classes_compared: int
    classes_excluded: int
    degraded_classes: list[str] = Field(default_factory=list)


def _prediction_cache(
    destination: Path,
    role: str,
    split: str,
    weights: Path,
    inference: SettledInference,
    split_fingerprint: str = "",
) -> Path:
    identity = str(weights.resolve())
    if weights.is_file():
        stat = weights.stat()
        identity = f"{identity}:{stat.st_size}:{stat.st_mtime_ns}"
    settings = json.dumps(inference.model_dump(mode="json"), sort_keys=True, ensure_ascii=True)
    digest = hashlib.sha256(
        f"{identity}:{settings}:{split_fingerprint}".encode()
    ).hexdigest()[:12]
    return destination / f"{role}_predictions_{split}_{digest}.csv"


def _split_fingerprint(ground_truth: pd.DataFrame, split: str) -> str:
    """Hash ordered split membership and image bytes for safe prediction-cache reuse."""
    required = {"image_name", "image_path", "split"}
    missing = sorted(required - set(ground_truth.columns))
    if missing:
        raise ValueError(f"Ground truth is missing cache identity column(s): {missing}")
    rows = ground_truth.loc[
        ground_truth["split"] == split, ["image_name", "image_path"]
    ].drop_duplicates()
    digest = hashlib.sha256()
    for row in rows.sort_values(["image_name", "image_path"]).itertuples(index=False):
        path = Path(str(row.image_path))
        digest.update(str(row.image_name).encode())
        digest.update(b"\0")
        digest.update(str(path.resolve()).encode())
        digest.update(b"\0")
        if not path.is_file():
            raise FileNotFoundError(f"Current comparison image does not exist: {path}")
        with path.open("rb") as image:
            for chunk in iter(lambda: image.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _settled(
    inference: InferenceConfig, candidate: Path, baseline: Path | None
) -> SettledInference:
    resolution = resolution_of(candidate, inference.imgsz)
    baseline_resolution = trained_imgsz(baseline) if baseline is not None else None
    if baseline_resolution is not None and baseline_resolution != resolution.scored_at:
        logger.warning(
            "The baseline was trained at imgsz {} and the candidate is scored at {}; "
            "both are re-inferred at {}",
            baseline_resolution,
            resolution.scored_at,
            resolution.scored_at,
        )
    return SettledInference(
        **inference.model_dump(exclude={"imgsz"}),
        imgsz=resolution.scored_at,
    )


def _scored(
    weights: Path,
    ground_truth: pd.DataFrame,
    split: str,
    output: Path,
    destination: Path,
    role: str,
    inference: SettledInference,
    thresholds: dict[str, float],
    classes: list[str],
    *,
    evaluation: EvaluationConfig,
) -> tuple[EvaluatedSplit, VocabularyReport, InferenceEvidence, Path]:
    native_project = destination / "native"
    native_name = f"{role}_{split}"
    predictions, vocabulary = reinfer_split(
        weights,
        ground_truth,
        split,
        output,
        conf=inference.conf,
        iou=inference.iou,
        imgsz=inference.imgsz,
        batch=inference.batch,
        device=inference.device,
        image_name=inference.image_name,
        native_project=native_project,
        native_name=native_name,
        native_kwargs=inference.ultralytics,
        reuse_existing=inference.reuse_existing,
    )
    fallback_args = {
        **inference.model_dump(mode="json", exclude={"reuse_existing", "ultralytics"}),
        **inference.ultralytics,
        "project": str(native_project.resolve()),
        "name": native_name,
    }
    evidence = InferenceEvidence.model_validate(
        {
            "effective_args": predictions.attrs.get("effective_args", fallback_args),
            "save_dir": predictions.attrs.get(
                "save_dir", str(native_project.resolve() / native_name)
            ),
        }
    )
    native_archive = _archive_native_outputs(
        Path(evidence.save_dir), destination, role=role, split=split
    )
    prepared_truth = prepare_ground_truth(ground_truth, deduplicate=evaluation.preprocess)
    raw_predictions = predictions.copy().reset_index(drop=True)
    prepared_predictions = prepare_predictions(
        raw_predictions,
        preprocess_conf_threshold=evaluation.preprocess_preds_conf_threshold,
        preprocess_nms_containment_threshold=(
            evaluation.preprocess_preds_nms_containment_threshold
        ),
        preprocess_nms_iou_threshold=evaluation.preprocess_preds_nms_iou_threshold,
    )
    model_classes = set(vocabulary.model_classes)
    prediction_classes = {
        str(value) for value in prepared_predictions["instance_label"].dropna().unique()
    }
    required = sorted((set(classes) & model_classes) | prediction_classes)
    scored_classes = sorted(set(classes) | model_classes)
    evaluated = evaluate_split(
        prepared_truth,
        raw_predictions,
        prepared_predictions,
        split=split,
        classes=scored_classes,
        thresholds=thresholds,
        required_classes=required,
        iou_threshold=evaluation.iou_threshold,
        matching_strategy=evaluation.matching_strategy,
        ap_method=evaluation.ap_method,
        skip_cohen_kappa=evaluation.skip_cohen_kappa,
        output_dir=destination,
        suffix=f"{role}_{split}",
        dashboard_classes=model_classes,
    )
    return evaluated, vocabulary, evidence, native_archive


def _archive_native_outputs(
    save_dir: Path, destination: Path, *, role: str, split: str
) -> Path:
    """Archive native tabular/text outputs without copying source-derived images."""
    archive = destination / f"native_outputs_{role}_{split}.zip"
    allowed = {".csv", ".json", ".txt", ".yaml", ".yml"}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        if save_dir.is_dir():
            for path in sorted(save_dir.rglob("*")):
                if path.is_file() and path.suffix.lower() in allowed:
                    relative = path.relative_to(save_dir)
                    suffix = path.suffix.lower()
                    if suffix == ".json":
                        content = json.loads(path.read_text(encoding="utf-8"))
                        bundle.writestr(
                            relative.as_posix(),
                            json.dumps(
                                sanitize_configuration(content),
                                indent=2,
                                ensure_ascii=False,
                            )
                            + "\n",
                        )
                    elif suffix in {".yaml", ".yml"}:
                        content = yaml.safe_load(path.read_text(encoding="utf-8"))
                        bundle.writestr(
                            relative.as_posix(),
                            yaml.safe_dump(
                                sanitize_configuration(content),
                                sort_keys=False,
                                allow_unicode=True,
                            ),
                        )
                    else:
                        bundle.write(path, relative)
    return archive


def _degraded(tables: ComparisonTables) -> list[str]:
    per_class = tables.rows[~tables.rows["is_pooled"].astype(bool)]
    degraded = per_class["precision_verdict"].eq("degraded") | per_class[
        "recall_verdict"
    ].eq("degraded")
    return [str(name) for name in per_class.loc[degraded, "class_name"]]


def _write_manifest(
    destination: Path,
    split: str,
    baseline: EvaluatedSplit,
    candidate: EvaluatedSplit,
    baseline_predictions: Path,
    candidate_predictions: Path,
    workbook: Path,
) -> Path:
    manifest = ComparisonManifest(
        split=split,
        baseline_dashboard=baseline.dashboard_path.name,
        candidate_dashboard=candidate.dashboard_path.name,
        baseline_predictions=baseline_predictions.name,
        candidate_predictions=candidate_predictions.name,
        statistical_workbook=workbook.name,
    )
    path = destination / MANIFEST_NAME
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return path


def _evaluated_artifact_names(role: str, split: str) -> list[str]:
    names = [
        artifact_names.per_split(f"compare_dashboard_{role}", split),
        artifact_names.per_split(f"compare_dashboard_dtrk_{role}", split),
        artifact_names.per_split(f"compare_matches_gt_{role}", split),
        artifact_names.per_split(f"compare_matches_preds_{role}", split),
        artifact_names.per_split(f"compare_confusion_matrix_{role}", split),
        artifact_names.per_split(f"compare_metrics_summary_{role}", split),
        artifact_names.per_split(f"compare_metrics_raw_{role}", split),
        artifact_names.per_split(f"compare_inference_metadata_{role}", split),
        artifact_names.per_split(f"compare_native_outputs_{role}", split),
    ]
    names.extend(
        artifact_names.per_split(f"compare_plot_{metric}_{role}", split)
        for metric in ("recall", "precision", "perebrak", "nedobrak")
    )
    return names


def _evaluated_artifacts(
    role: str,
    split: str,
    evaluated: EvaluatedSplit,
    predictions: Path,
    native_archive: Path,
) -> list[tuple[str, object]]:
    per_class, _ = summarize_metrics(evaluated.metrics)
    values: list[tuple[str, object]] = [
        (
            artifact_names.per_split(f"compare_dashboard_{role}", split),
            evaluated.dashboard_path,
        ),
        (
            artifact_names.per_split(f"compare_dashboard_dtrk_{role}", split),
            evaluated.dtrk_dashboard_path,
        ),
        (
            artifact_names.per_split(f"compare_matches_gt_{role}", split),
            evaluated.gt_matches,
        ),
        (
            artifact_names.per_split(f"compare_matches_preds_{role}", split),
            evaluated.pred_matches,
        ),
        (
            artifact_names.per_split(f"compare_confusion_matrix_{role}", split),
            evaluated.confusion_matrix_path,
        ),
        (
            artifact_names.per_split(f"compare_metrics_summary_{role}", split),
            per_class,
        ),
        (
            artifact_names.per_split(f"compare_metrics_raw_{role}", split),
            {name: metric.model_dump() for name, metric in evaluated.metrics.items()},
        ),
        (
            artifact_names.per_split(f"compare_inference_metadata_{role}", split),
            predictions.with_suffix(".metadata.json"),
        ),
        (
            artifact_names.per_split(f"compare_native_outputs_{role}", split),
            native_archive,
        ),
    ]
    values.extend(
        (
            artifact_names.per_split(f"compare_plot_{metric}_{role}", split),
            path,
        )
        for metric, path in evaluated.plot_paths.items()
    )
    return values


def _upload_many(task: Any, artifacts: list[tuple[str, object]]) -> None:
    if task is None:
        return
    for name, value in artifacts:
        upload_artifact(task, name, value)


def _common_artifacts(
    ground_truth: Path,
    models: dict[str, object],
    evidence: dict[str, InferenceEvidence],
    output_locations: dict[str, dict[str, str]],
    split: str,
    image_names: list[str],
) -> list[tuple[str, object]]:
    return [
        ("compare_ground_truth", ground_truth),
        ("compare_model_references", models),
        (
            "compare_effective_inference",
            {role: item.effective_args for role, item in evidence.items()},
        ),
        ("compare_native_output_locations", output_locations),
        (artifact_names.per_split("compare_image_membership", split), image_names),
    ]


def _output_location(
    evidence: InferenceEvidence, predictions: Path, native_archive: Path
) -> dict[str, str]:
    return {
        "predictions": str(predictions.resolve()),
        "metadata": str(predictions.with_suffix(".metadata.json").resolve()),
        "native_save_dir": str(Path(evidence.save_dir).resolve()),
        "native_outputs": str(native_archive.resolve()),
    }


def _skip_without_baseline(
    *,
    task: Any,
    reason: str,
    candidate: ResolvedModel,
    truth: pd.DataFrame,
    ground_truth_path: Path,
    destination: Path,
    inference: InferenceConfig,
    split: str,
    classes: list[str],
    evaluation: EvaluationConfig,
) -> None:
    settled = _settled(inference, candidate.weights, None)
    fingerprint = _split_fingerprint(truth, split)
    predictions = _prediction_cache(
        destination,
        "candidate",
        split,
        candidate.weights,
        settled,
        fingerprint,
    )
    expected = [
        "compare_ground_truth",
        "compare_model_references",
        "compare_effective_inference",
        "compare_native_output_locations",
        artifact_names.per_split("compare_image_membership", split),
        artifact_names.per_split("compare_predictions_candidate", split),
        artifact_names.per_split("compare_thresholds_candidate", split),
        "comparison_status",
        *_evaluated_artifact_names("candidate", split),
    ]
    if task is not None:
        expect_artifacts(task, expected)
    evaluated, _, candidate_evidence, candidate_archive = _scored(
        candidate.weights,
        truth,
        split,
        predictions,
        destination,
        "candidate",
        settled,
        candidate.thresholds,
        classes,
        evaluation=evaluation,
    )
    artifacts = _common_artifacts(
        ground_truth_path,
        {"candidate": candidate.model_dump(mode="json")},
        {"candidate": candidate_evidence},
        {
            "candidate": _output_location(
                candidate_evidence, predictions, candidate_archive
            )
        },
        split,
        evaluated.image_names,
    )
    artifacts.extend(
        [
            (artifact_names.per_split("compare_predictions_candidate", split), predictions),
            (
                artifact_names.per_split("compare_thresholds_candidate", split),
                evaluated.thresholds,
            ),
            ("comparison_status", {"status": "skipped", "reason": reason}),
            *_evaluated_artifacts(
                "candidate", split, evaluated, predictions, candidate_archive
            ),
        ]
    )
    _upload_many(task, artifacts)


def _normalize_evaluation(
    evaluation: EvaluationConfig | dict[str, Any] | None,
    *,
    iou_threshold: float,
    matching_strategy: str,
) -> EvaluationConfig:
    """Overlay sparse evaluation overrides on the legacy comparison settings."""
    if isinstance(evaluation, EvaluationConfig):
        return evaluation
    values: dict[str, Any] = {
        "iou_threshold": iou_threshold,
        "matching_strategy": matching_strategy,
    }
    values.update(evaluation or {})
    return EvaluationConfig.model_validate(values)


def compare(
    baseline_model: ModelRef,
    candidate_model: ModelRef,
    ground_truth: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    inference: InferenceConfig,
    split: str = "test",
    iou_threshold: float = 0.5,
    matching_strategy: str = "iou_prior",
    q: float = 0.05,
    bootstrap_iterations: int = 10_000,
    seed: int = 0,
    evaluation: EvaluationConfig | dict[str, Any] | None = None,
) -> CompareResult | None:
    """Evaluate both models once on current data and share those exact outcomes."""
    task = init_task(clearml, stage="compare")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    current_task_id = str(task.id) if task is not None else None
    evaluation_config = _normalize_evaluation(
        evaluation,
        iou_threshold=iou_threshold,
        matching_strategy=matching_strategy,
    )
    if evaluation_config.backend is not None:
        raise ValueError(
            "Frozen thresholds require the native digital-metrics backend; "
            f"backend={evaluation_config.backend!r} is unsupported"
        )

    ground_truth_path = Path(ground_truth)
    truth = pd.read_csv(
        ground_truth_path,
        dtype={"image_name": str, "instance_label": str, "split": str},
    )
    validate_split_membership(truth)
    try:
        baseline = _resolve_model(
            baseline_model,
            split,
            clearml.project_name,
            exclude_task_id=current_task_id,
            automatic_absence_is_skip=_is_automatic_baseline(baseline_model),
        )
    except NoBaselineModelError as error:
        classes = classes_from_ground_truth(truth[truth["split"] == split])
        candidate = _resolve_model(
            candidate_model,
            split,
            clearml.project_name,
            exclude_task_id=None,
            automatic_absence_is_skip=False,
        )
        _skip_without_baseline(
            task=task,
            reason=str(error),
            candidate=candidate,
            truth=truth,
            ground_truth_path=ground_truth_path,
            destination=destination,
            inference=inference,
            split=split,
            classes=classes,
            evaluation=evaluation_config,
        )
        return None
    candidate = _resolve_model(
        candidate_model,
        split,
        clearml.project_name,
        exclude_task_id=None,
        automatic_absence_is_skip=False,
    )
    if baseline.weights.resolve() == candidate.weights.resolve():
        raise ValueError(
            f"Both sides resolved to the same checkpoint ({candidate.weights}), so there is "
            "nothing to compare"
        )

    classes = classes_from_ground_truth(truth[truth["split"] == split])
    settled = _settled(inference, candidate.weights, baseline.weights)
    split_fingerprint = _split_fingerprint(truth, split)
    baseline_predictions = _prediction_cache(
        destination, "baseline", split, baseline.weights, settled, split_fingerprint
    )
    candidate_predictions = _prediction_cache(
        destination, "candidate", split, candidate.weights, settled, split_fingerprint
    )
    expected = [
        "compare_ground_truth",
        "compare_model_references",
        "compare_effective_inference",
        "compare_native_output_locations",
        artifact_names.per_split("compare_image_membership", split),
        artifact_names.per_split("compare_predictions_baseline", split),
        artifact_names.per_split("compare_predictions_candidate", split),
        artifact_names.per_split("compare_thresholds_baseline", split),
        artifact_names.per_split("compare_thresholds_candidate", split),
        artifact_names.per_split("compare_counts", split),
        artifact_names.per_split("compare_exclusions", split),
        artifact_names.per_split("compare_methodology", split),
        artifact_names.per_split(artifact_names.COMPARISON_WORKBOOK_PREFIX, split),
        "compare_manifest",
        *_evaluated_artifact_names("baseline", split),
        *_evaluated_artifact_names("candidate", split),
    ]
    if task is not None:
        expect_artifacts(task, expected)
    (
        baseline_evaluated,
        baseline_vocabulary,
        baseline_evidence,
        baseline_archive,
    ) = _scored(
        baseline.weights,
        truth,
        split,
        baseline_predictions,
        destination,
        "baseline",
        settled,
        baseline.thresholds,
        classes,
        evaluation=evaluation_config,
    )
    (
        candidate_evaluated,
        candidate_vocabulary,
        candidate_evidence,
        candidate_archive,
    ) = _scored(
        candidate.weights,
        truth,
        split,
        candidate_predictions,
        destination,
        "candidate",
        settled,
        candidate.thresholds,
        classes,
        evaluation=evaluation_config,
    )

    tables = build_comparison_rows(
        baseline_evaluated.outcome,
        candidate_evaluated.outcome,
        thresholds_baseline=baseline_evaluated.thresholds,
        thresholds_candidate=candidate_evaluated.thresholds,
        images=baseline_evaluated.image_names,
        baseline_classes=set(baseline_vocabulary.model_classes),
        candidate_classes=set(candidate_vocabulary.model_classes),
        q=q,
        iterations=bootstrap_iterations,
        seed=seed,
    )
    tables.methodology.update(
        {
            "baseline_weights": str(baseline.weights),
            "candidate_weights": str(candidate.weights),
            "split": split,
            **evaluation_config.model_dump(),
        }
    )
    workbook = destination / f"{artifact_names.COMPARISON_WORKBOOK_PREFIX}_{split}.xlsx"
    write_comparison_workbook(tables.rows, tables.excluded, tables.methodology, workbook)
    report_comparison(task, split, tables.rows, tables.methodology)
    manifest = _write_manifest(
        destination,
        split,
        baseline_evaluated,
        candidate_evaluated,
        baseline_predictions,
        candidate_predictions,
        workbook,
    )
    artifacts = _common_artifacts(
        ground_truth_path,
        {
            "baseline": baseline.model_dump(mode="json"),
            "candidate": candidate.model_dump(mode="json"),
        },
        {"baseline": baseline_evidence, "candidate": candidate_evidence},
        {
            "baseline": _output_location(
                baseline_evidence, baseline_predictions, baseline_archive
            ),
            "candidate": _output_location(
                candidate_evidence, candidate_predictions, candidate_archive
            ),
        },
        split,
        baseline_evaluated.image_names,
    )
    artifacts.extend(
        [
            (artifact_names.per_split("compare_predictions_baseline", split), baseline_predictions),
            (
                artifact_names.per_split("compare_predictions_candidate", split),
                candidate_predictions,
            ),
            (
                artifact_names.per_split("compare_thresholds_baseline", split),
                baseline_evaluated.thresholds,
            ),
            (
                artifact_names.per_split("compare_thresholds_candidate", split),
                candidate_evaluated.thresholds,
            ),
            (artifact_names.per_split("compare_counts", split), tables.rows),
            (artifact_names.per_split("compare_exclusions", split), tables.excluded),
            (artifact_names.per_split("compare_methodology", split), tables.methodology),
            (
                artifact_names.per_split(artifact_names.COMPARISON_WORKBOOK_PREFIX, split),
                workbook,
            ),
            ("compare_manifest", manifest),
            *_evaluated_artifacts(
                "baseline",
                split,
                baseline_evaluated,
                baseline_predictions,
                baseline_archive,
            ),
            *_evaluated_artifacts(
                "candidate",
                split,
                candidate_evaluated,
                candidate_predictions,
                candidate_archive,
            ),
        ]
    )
    _upload_many(task, artifacts)

    degraded = _degraded(tables)
    return CompareResult(
        workbook=workbook,
        baseline_dashboard=baseline_evaluated.dashboard_path,
        candidate_dashboard=candidate_evaluated.dashboard_path,
        baseline_predictions=baseline_predictions,
        candidate_predictions=candidate_predictions,
        manifest=manifest,
        classes_compared=len(tables.rows) - 1,
        classes_excluded=len(tables.excluded),
        degraded_classes=degraded,
    )
