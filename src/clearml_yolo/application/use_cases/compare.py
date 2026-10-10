"""Re-infer and evaluate two checkpoints on the same current test images."""

__all__ = [
    "CompareResult",
    "ComparisonManifest",
    "InferenceConfig",
    "ModelRef",
    "ResolvedModel",
    "SettledInference",
]
import hashlib
import json
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd

from clearml_yolo.application.contracts import (
    ClearMLConfig,
    CompareResult,
    ComparisonManifest,
    InferenceConfig,
    InferenceEvidence,
    ModelRef,
    ResolvedModel,
    SettledInference,
    VocabularyReport,
)
from clearml_yolo.application.evaluation import evaluate_split
from clearml_yolo.application.ports import TaskHandle, WorkflowDependencies
from clearml_yolo.core import artifact_names
from clearml_yolo.core.comparison.assemble import ComparisonTables, build_comparison_rows
from clearml_yolo.core.comparison.significance import validate_q
from clearml_yolo.core.evaluation.models import EvaluatedSplit, EvaluationConfig
from clearml_yolo.core.evaluation.policy import classes_from_ground_truth, validate_split_membership
from clearml_yolo.core.evaluation.result_rows import assign_source_ids
from clearml_yolo.core.identity import ModelIdentity, require_model_identity
from clearml_yolo.core.redaction import sanitize_configuration

ModelSource = Literal["clearml", "local"]
MANIFEST_NAME = "comparison_manifest.json"


class NoBaselineModelError(LookupError):
    """Automatic baseline resolution found no previous promoted run."""


def _is_automatic_baseline(model: ModelRef) -> bool:
    """Whether the conventional latest ``prod`` lookup may be absent."""
    return (
        model.source == "clearml"
        and model.task_id is None
        and (model.project_name is None)
        and (model.task_name is None)
        and (model.weights is None)
        and (model.tags == ["prod"])
    )


def _resolved_task_id(
    model: ModelRef,
    fallback_project: str,
    *,
    exclude_task_id: str | None,
    automatic_absence_is_skip: bool,
    deps: WorkflowDependencies,
) -> str:
    if model.task_id:
        return model.task_id
    project = model.project_name or fallback_project
    found = deps.repository.latest_completed_task_id(
        project, model.task_name, model.tags, exclude_task_id=exclude_task_id
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
    fallback_project: str,
    *,
    exclude_task_id: str | None,
    automatic_absence_is_skip: bool,
    deps: WorkflowDependencies,
) -> ResolvedModel:
    if model.source == "local":
        if model.weights is None or model.thresholds is None:
            raise RuntimeError("Validated local model is missing weights or thresholds")
        if not deps.storage.is_file(model.weights):
            raise FileNotFoundError(f"Local checkpoint does not exist: {model.weights}")
        return ResolvedModel(
            source="local",
            weights=model.weights,
            thresholds=dict(model.thresholds),
            identity=require_model_identity(
                deps.repository.read_checkpoint_identity(model.weights),
                model.label,
                checkpoint_hash=deps.tracking.file_digest(model.weights),
            ),
        )
    task_id = _resolved_task_id(
        model,
        fallback_project,
        exclude_task_id=exclude_task_id,
        automatic_absence_is_skip=automatic_absence_is_skip,
        deps=deps,
    )
    thresholds = (
        dict(model.thresholds)
        if model.thresholds is not None
        else deps.repository.fetch_best_confidences(task_id)
    )
    weights, links = deps.repository.resolve_task_model(task_id)
    return ResolvedModel(
        source="clearml",
        task_id=task_id,
        weights=weights,
        links=links,
        thresholds=thresholds,
        identity=require_model_identity(
            ModelIdentity.from_provenance(links) if "model_name" in links else None, model.label
        ),
    )


def _prediction_cache(
    destination: Path,
    role: str,
    split: str,
    weights: Path,
    inference: SettledInference,
    split_fingerprint: str = "",
    *,
    deps: WorkflowDependencies,
) -> Path:
    identity = str(deps.storage.resolve(weights))
    if deps.storage.is_file(weights):
        # ClearML refreshes checkpoint mtimes on cache lookup. Content also detects
        # replacement weights whose size and modification time remain unchanged.
        identity = f"{identity}:{deps.tracking.file_digest(weights)}"
    # Cache policy selects whether to consume existing predictions; it does not
    # describe their scientific identity. All native settings remain authoritative.
    settings = json.dumps(
        inference.model_dump(mode="json", exclude={"reuse_existing"}),
        sort_keys=True,
        ensure_ascii=True,
    )
    digest = hashlib.sha256(f"{identity}:{settings}:{split_fingerprint}".encode()).hexdigest()[:12]
    return destination / f"{role}_predictions_{artifact_names.split_component(split)}_{digest}.csv"


def _split_fingerprint(
    ground_truth: pd.DataFrame, split: str, *, deps: WorkflowDependencies
) -> str:
    """Identify current membership under the immutable-image contract."""
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
        digest.update(b"\x00")
        digest.update(str(deps.storage.resolve(path)).encode())
        digest.update(b"\x00")
        if not deps.storage.is_file(path):
            raise FileNotFoundError(f"Current comparison image does not exist: {path}")
        digest.update(b"\x00")
    return digest.hexdigest()


def _settled(
    inference: InferenceConfig,
    candidate: Path,
    baseline: Path | None,
    *,
    deps: WorkflowDependencies,
) -> SettledInference:
    resolution = deps.model.resolution_of(candidate, inference.imgsz)
    baseline_resolution = deps.model.trained_imgsz(baseline) if baseline is not None else None
    if baseline_resolution is not None and baseline_resolution != resolution.scored_at:
        deps.resources.log(
            "WARNING",
            "The baseline was trained at imgsz {} and the candidate requests imgsz {}; "
            "both are passed the same requested imgsz {} before native normalization",
            baseline_resolution,
            resolution.scored_at,
            resolution.scored_at,
        )
    return SettledInference(**inference.model_dump(exclude={"imgsz"}), imgsz=resolution.scored_at)


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
    task: TaskHandle | None = None,
    model_identity: ModelIdentity | None = None,
    deps: WorkflowDependencies,
) -> tuple[EvaluatedSplit, VocabularyReport, InferenceEvidence, Path]:
    with deps.resources.trace_operation("comparison.score", context={"split": split}):
        del task
        if inference.reuse_existing and deps.storage.is_file(output):
            _validate_cached_identity(output, weights, model_identity, deps=deps)
        native_project = destination / "native"
        native_name = f"{role}_{artifact_names.split_component(split)}"
        predictions, vocabulary = deps.model.reinfer_split(
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
        deps.tracking.write_prediction_provenance(output, weights, model_identity)
        fallback_args = {
            **inference.model_dump(mode="json", exclude={"reuse_existing", "ultralytics"}),
            **inference.ultralytics,
            "project": str(deps.storage.resolve(native_project)),
            "name": native_name,
        }
        evidence = InferenceEvidence.model_validate(
            {
                "effective_args": predictions.attrs.get("effective_args", fallback_args),
                "requested_args": predictions.attrs.get("requested_args", fallback_args),
                "normalized_imgsz": predictions.attrs.get("normalized_imgsz"),
                "checkpoint_design": predictions.attrs.get("checkpoint_design", {}),
                "save_dir": predictions.attrs.get(
                    "save_dir", str(deps.storage.resolve(native_project) / native_name)
                ),
            }
        )
        deps.model.write_native_yaml(
            destination
            / f"ultralytics_predict_{role}_{artifact_names.split_component(split)}.yaml",
            {key: value for key, value in evidence.effective_args.items() if key != "image_name"}
            | {"model": str(weights), "mode": "predict"},
            "predict",
        )
        deps.model.write_native_yaml(
            destination
            / f"ultralytics_predict_{role}_{artifact_names.split_component(split)}_requested.yaml",
            {key: value for key, value in evidence.requested_args.items() if key != "image_name"}
            | {"model": str(weights), "mode": "predict"},
            "predict",
        )
        native_archive = _archive_native_outputs(
            Path(evidence.save_dir), destination, role=role, split=split, deps=deps
        )
        predictions = assign_source_ids(predictions, row_type="prediction")
        prepared_truth = deps.evaluation.prepare_ground_truth(
            ground_truth, deduplicate=evaluation.preprocess
        )
        raw_predictions = deps.evaluation.filter_invalid_prediction_boxes(
            predictions.reset_index(drop=True)
        )
        prepared_predictions = deps.evaluation.prepare_predictions(
            raw_predictions,
            preprocess_conf_threshold=evaluation.preprocess_preds_conf_threshold,
            preprocess_nms_containment_threshold=evaluation.preprocess_preds_nms_containment_threshold,
            preprocess_nms_iou_threshold=evaluation.preprocess_preds_nms_iou_threshold,
        )
        model_classes = set(vocabulary.model_classes)
        prediction_classes = {
            str(value) for value in prepared_predictions["instance_label"].dropna().unique()
        }
        required = sorted(set(classes) & model_classes | prediction_classes)
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
            source_ground_truth=ground_truth,
            source_predictions=predictions,
            model_identity=model_identity,
            deps=deps,
        )
        return (evaluated, vocabulary, evidence, native_archive)


def _validate_cached_identity(
    predictions: Path, weights: Path, identity: ModelIdentity | None, *, deps: WorkflowDependencies
) -> None:
    """Reject stale source metadata before cached bytes can be reused or rebound."""
    previous = deps.tracking.prediction_model_identity(predictions)
    checkpoint_hash = deps.tracking.prediction_checkpoint_hash(predictions)
    if checkpoint_hash is not None and checkpoint_hash != deps.tracking.file_digest(weights):
        raise ValueError("Cached prediction provenance refers to a different checkpoint")
    if previous is not None and previous != identity:
        raise ValueError("Cached prediction source identity does not match the selected model")


def _archive_native_outputs(
    save_dir: Path, destination: Path, *, role: str, split: str, deps: WorkflowDependencies
) -> Path:
    return deps.storage.archive_native_outputs(save_dir, destination, role=role, split=split)


def _degraded(tables: ComparisonTables) -> list[str]:
    per_class = tables.rows[~tables.rows["is_pooled"].astype(bool)]
    degraded = per_class["precision_verdict"].eq("degraded") | per_class["recall_verdict"].eq(
        "degraded"
    )
    return [str(name) for name in per_class.loc[degraded, "class_name"]]


def _write_manifest(
    destination: Path,
    split: str,
    baseline: EvaluatedSplit,
    candidate: EvaluatedSplit,
    baseline_predictions: Path,
    candidate_predictions: Path,
    workbook: Path,
    *,
    deps: WorkflowDependencies,
) -> Path:
    manifest = ComparisonManifest(
        split=split,
        baseline_dashboard=baseline.dashboard_path.name,
        candidate_dashboard=candidate.dashboard_path.name,
        baseline_predictions=baseline_predictions.name,
        candidate_predictions=candidate_predictions.name,
        statistical_workbook=workbook.name,
        baseline_identity=baseline.model_identity,
        candidate_identity=candidate.model_identity,
    )
    path = destination / MANIFEST_NAME
    deps.storage.write_text(path, manifest.model_dump_json(indent=2), encoding="utf-8")
    return path


def _source_configuration(model: ResolvedModel) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        sanitize_configuration(
            (model.links or {"source": model.source, "weights": str(model.weights)})
            | {"model_identity": model.identity.model_dump(mode="json") if model.identity else None}
        ),
    )


def _publish_comparison_tables(
    task: TaskHandle | None,
    truth: Path,
    contexts: dict[str, tuple[Path, EvaluatedSplit, ResolvedModel]],
    *,
    deps: WorkflowDependencies,
) -> None:
    for role, (path, evaluated, model) in contexts.items():
        deps.tracking.publish_evaluation(
            task,
            evaluated,
            truth,
            path,
            output_dir=path.parent,
            model_id=model.links.get("model_id")
            or f"checkpoint:{deps.tracking.file_digest(model.weights)}",
            role=f"comparison_{role}",
        )


def _skip_without_baseline(
    *,
    task: TaskHandle | None,
    reason: str,
    candidate: ResolvedModel,
    truth: pd.DataFrame,
    ground_truth_path: Path,
    destination: Path,
    inference: InferenceConfig,
    split: str,
    classes: list[str],
    evaluation: EvaluationConfig,
    deps: WorkflowDependencies,
) -> None:
    with deps.resources.trace_operation("comparison.skip_baseline", context={"split": split}):
        settled = _settled(inference, candidate.weights, None, deps=deps)
        fingerprint = _split_fingerprint(truth, split, deps=deps)
        predictions = _prediction_cache(
            destination, "candidate", split, candidate.weights, settled, fingerprint, deps=deps
        )
        evaluated, _, _, _ = _scored(
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
            task=task,
            model_identity=candidate.identity,
            deps=deps,
        )
        workbook = (
            destination
            / f"compare_evaluation_candidate_{artifact_names.split_component(split)}.xlsx"
        )
        per_class, summary = deps.evaluation_writer.summarize_metrics(evaluated.metrics)
        deps.renderer.write_candidate_workbook(workbook, per_class, summary)
        if candidate.identity is not None:
            deps.renderer.annotate_workbook(workbook, {"candidate": candidate.identity})
        tables: dict[str, Path] = {}
        for title, frame in {
            "thresholds": pd.DataFrame(
                list(candidate.thresholds.items()), columns=["class_name", "confidence"]
            ),
            "methodology": pd.DataFrame(
                [{"status": "skipped", "reason": reason, **_source_configuration(candidate)}]
            ),
        }.items():
            table_path = workbook.with_name(f"{workbook.stem}_{title}.csv")
            deps.storage.write_csv(frame, table_path, index=False, float_format="%.17g")
            tables[table_path.stem] = table_path
        if task is not None:
            deps.tracking.record_run_configuration(
                task,
                {
                    "comparison_status": {"status": "skipped", "reason": reason},
                    "comparison": {
                        "candidate": _source_configuration(candidate),
                        "inference": settled.model_dump(),
                        "evaluation": evaluation.model_dump(),
                    },
                },
            )
            _publish_comparison_tables(
                task,
                ground_truth_path,
                {"candidate": (predictions, evaluated, candidate)},
                deps=deps,
            )


def _native_inference(
    inference: dict[str, Any],
    ultralytics_predict: dict[str, Any] | None,
    *,
    deps: WorkflowDependencies,
) -> InferenceConfig:
    """Adapt public native groups to paired comparison's internal settings."""
    conflicts = {
        key
        for key in ("model", "project", "name")
        if (ultralytics_predict or {}).get(key) is not None
    }
    if conflicts:
        raise ValueError(
            f"Prediction {sorted(conflicts)} are owned by comparison; "
            "use baseline_model/candidate_model and output_dir"
        )
    unknown = set(inference) - {"reuse_existing", "image_name"}
    if unknown:
        raise ValueError(f"Unsupported inference settings: {sorted(unknown)}")
    settings = deps.model.prediction_settings(ultralytics_predict or {})
    fields = {
        key: settings[key] for key in ("conf", "iou", "imgsz", "batch", "device") if key in settings
    }
    owned = {"model", "source", "stream", "project", "name", "save_dir", "mode", "task"}
    extras = {key: value for key, value in settings.items() if key not in {*fields, *owned}}
    return InferenceConfig(**inference, **fields, ultralytics=extras)


def _evaluation_config(evaluation: EvaluationConfig | dict[str, Any] | None) -> EvaluationConfig:
    config = (
        evaluation
        if isinstance(evaluation, EvaluationConfig)
        else EvaluationConfig.model_validate(evaluation or {})
    )
    if config.backend is not None:
        raise ValueError(
            "Frozen thresholds require the native digital-metrics backend; "
            f"backend={config.backend!r} is unsupported"
        )
    return config


def compare(
    baseline_model: ModelRef,
    candidate_model: ModelRef,
    ground_truth: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    inference: InferenceConfig | dict[str, Any],
    split: str = "test",
    q: float = 0.05,
    bootstrap_iterations: int = 10000,
    seed: int = 0,
    evaluation: EvaluationConfig | dict[str, Any] | None = None,
    ultralytics: dict[str, Any] | None = None,
    ultralytics_predict: dict[str, Any] | None = None,
    *,
    deps: WorkflowDependencies,
) -> CompareResult | None:
    """Evaluate both models once on current data and share those exact outcomes."""
    with deps.resources.trace_operation("workflow.compare", context={"split": split}):
        validate_q(q)
        deps.model.stage_settings(ultralytics or {}, "train")
        if isinstance(inference, dict):
            inference = _native_inference(inference, ultralytics_predict, deps=deps)
        task = deps.tracking.init_task(clearml, stage="compare")
        destination = deps.storage.write_path(output_dir)
        deps.storage.mkdir(destination, parents=True, exist_ok=True)
        current_task_id = str(task.id) if task is not None else None
        evaluation_config = _evaluation_config(evaluation)
        ground_truth_path = Path(ground_truth)
        truth = assign_source_ids(
            deps.storage.read_csv(
                ground_truth_path,
                dtype={"image_name": str, "instance_label": str, "split": str},
                float_precision="round_trip",
            ),
            row_type="ground_truth",
        )
        validate_split_membership(truth)
        try:
            baseline = _resolve_model(
                baseline_model,
                clearml.project_name,
                exclude_task_id=current_task_id,
                automatic_absence_is_skip=_is_automatic_baseline(baseline_model),
                deps=deps,
            )
        except NoBaselineModelError as error:
            classes = classes_from_ground_truth(truth[truth["split"] == split])
            candidate = _resolve_model(
                candidate_model,
                clearml.project_name,
                exclude_task_id=None,
                automatic_absence_is_skip=False,
                deps=deps,
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
                deps=deps,
            )
            return None
        candidate = _resolve_model(
            candidate_model,
            clearml.project_name,
            exclude_task_id=None,
            automatic_absence_is_skip=False,
            deps=deps,
        )
        if deps.storage.resolve(baseline.weights) == deps.storage.resolve(candidate.weights):
            raise ValueError(
                f"Both sides resolved to the same checkpoint ({candidate.weights}), "
                "so there is nothing to compare"
            )
        classes = classes_from_ground_truth(truth[truth["split"] == split])
        settled = _settled(inference, candidate.weights, baseline.weights, deps=deps)
        split_fingerprint = _split_fingerprint(truth, split, deps=deps)
        baseline_predictions = _prediction_cache(
            destination, "baseline", split, baseline.weights, settled, split_fingerprint, deps=deps
        )
        candidate_predictions = _prediction_cache(
            destination,
            "candidate",
            split,
            candidate.weights,
            settled,
            split_fingerprint,
            deps=deps,
        )
        baseline_evaluated, baseline_vocabulary, _baseline_evidence, _baseline_archive = _scored(
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
            task=task,
            model_identity=baseline.identity,
            deps=deps,
        )
        candidate_evaluated, candidate_vocabulary, _candidate_evidence, _candidate_archive = (
            _scored(
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
                task=task,
                model_identity=candidate.identity,
                deps=deps,
            )
        )
        baseline_classes, candidate_classes = (
            set(baseline_vocabulary.model_classes),
            set(candidate_vocabulary.model_classes),
        )
        with (
            deps.resources.trace_operation("comparison.bootstrap", context={"split": split}),
            deps.resources.progress_callback(
                "Testing classes",
                total=len(
                    set(baseline_evaluated.outcome.counts)
                    | set(candidate_evaluated.outcome.counts)
                    | baseline_classes
                    | candidate_classes
                ),
                unit="class",
            ) as observe_class,
        ):
            tables = build_comparison_rows(
                baseline_evaluated.outcome,
                candidate_evaluated.outcome,
                thresholds_baseline=baseline_evaluated.thresholds,
                thresholds_candidate=candidate_evaluated.thresholds,
                images=baseline_evaluated.image_names,
                baseline_classes=baseline_classes,
                candidate_classes=candidate_classes,
                q=q,
                iterations=bootstrap_iterations,
                seed=seed,
                observe_class=observe_class,
                diagnostic=lambda message: deps.resources.log("WARNING", message),
                summary=lambda message: deps.resources.log("INFO", message),
            )
        tables.methodology.update(
            {
                "baseline_weights": str(baseline.weights),
                "candidate_weights": str(candidate.weights),
                "split": split,
                "baseline_source": _source_configuration(baseline),
                "candidate_source": _source_configuration(candidate),
                "baseline_architecture": _baseline_evidence.checkpoint_design,
                "candidate_architecture": _candidate_evidence.checkpoint_design,
                "shared_inference": settled.model_dump(),
                "image_count": len(baseline_evaluated.image_names),
                "images": baseline_evaluated.image_names,
                **evaluation_config.model_dump(),
            }
        )
        workbook = destination / (
            artifact_names.per_split(artifact_names.COMPARISON_WORKBOOK_PREFIX, split) + ".xlsx"
        )
        csv_tables = deps.renderer.write_comparison_workbook(
            tables.rows, tables.excluded, tables.methodology, workbook
        )
        identities = {
            role: model.identity
            for role, model in (("baseline", baseline), ("candidate", candidate))
            if model.identity is not None
        }
        deps.renderer.annotate_workbook(workbook, identities)
        deps.tracking.report_comparison(task, split, tables.rows, tables.methodology)
        manifest = _write_manifest(
            destination,
            split,
            baseline_evaluated,
            candidate_evaluated,
            baseline_predictions,
            candidate_predictions,
            workbook,
            deps=deps,
        )
        if task is not None:
            deps.tracking.record_run_configuration(
                task,
                {
                    "comparison": {
                        "baseline": _source_configuration(baseline),
                        "candidate": _source_configuration(candidate),
                        "inference": settled.model_dump(),
                        "evaluation": evaluation_config.model_dump(),
                    }
                },
            )
            _publish_comparison_tables(
                task,
                ground_truth_path,
                {
                    "baseline": (baseline_predictions, baseline_evaluated, baseline),
                    "candidate": (candidate_predictions, candidate_evaluated, candidate),
                },
                deps=deps,
            )
            name = artifact_names.per_split(artifact_names.COMPARISON_WORKBOOK_PREFIX, split)
            deps.tracking.expect_artifacts(task, [name])
            deps.tracking.upload_artifact(task, name, workbook)
            for name, table_path in csv_tables.items():
                if name.endswith("_excluded"):
                    deps.tracking.publish_table(task, name, table_path)
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
