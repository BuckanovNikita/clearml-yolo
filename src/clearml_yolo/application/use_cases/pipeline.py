"""Compose native execution and current-data evaluation under one tracking owner."""

import json
from collections.abc import Callable, Mapping
from dataclasses import fields, is_dataclass, replace
from pathlib import Path
from typing import Any

from clearml_yolo.application.contracts import (
    ClearMLConfig,
    DatasetFormat,
    GroundTruthInput,
    InferenceConfig,
    ModelRef,
    ResolvedGroundTruth,
)
from clearml_yolo.application.ground_truth import resolve_ground_truth
from clearml_yolo.application.ports import (
    Publisher,
    ResultProducer,
    TaskHandle,
    WorkflowDependencies,
)
from clearml_yolo.application.use_cases.compare import NoBaselineModelError
from clearml_yolo.application.use_cases.compare import compare as run_comparison
from clearml_yolo.application.use_cases.metrics import compute_metrics
from clearml_yolo.application.use_cases.predict import predict as run_prediction
from clearml_yolo.application.use_cases.publication import prepare_publisher, publish_results
from clearml_yolo.application.use_cases.report import report as run_report
from clearml_yolo.application.use_cases.train import train as run_training
from clearml_yolo.core.pipeline_outcome import PipelineOutcome, StageOutcome
from clearml_yolo.core.publication import FiftyOneConfig
from clearml_yolo.core.redaction import redact_text

PREDICTIONS_NAME = "predictions.csv"
METRICS_DIR = "metrics"
REPORTS_DIR = "reports"
COMPARISON_DIR = "comparison"


class _PipelineStages:
    """Own stage boundaries; all persistence and tracking cross explicit ports."""

    def __init__(self, directory: Path, task: TaskHandle | None, deps: WorkflowDependencies) -> None:
        self.directory = directory
        self.task = task
        self.deps = deps
        self.outcome = PipelineOutcome()

    def persist(self) -> None:
        try:
            self.deps.tracking.record_pipeline_outcome(self.task, self.outcome)
        except Exception as error:
            if not self.outcome.training_succeeded:
                raise
            self._persistence_failure("outcome_publication", error)
        try:
            self.deps.storage.atomic_write_text(
                self.directory / "pipeline_outcome.json", self.outcome.model_dump_json(indent=2)
            )
            self.deps.storage.atomic_write_text(self.directory / "pipeline_outcome.txt", self.outcome.summary())
        except Exception as error:
            if not self.outcome.training_succeeded:
                raise
            self._persistence_failure("outcome_storage", error)

    def _persistence_failure(self, stage: str, error: Exception) -> None:
        self.outcome.stages[stage] = StageOutcome(status="failed", reason=redact_text(str(error)))
        self.deps.resources.log_exception("Pipeline outcome persistence failed", error)

    def skip(self, name: str, reason: str) -> None:
        self.outcome.stages[name] = StageOutcome(status="skipped", reason=reason)
        self.persist()

    def run[Result](self, name: str, operation: Callable[[], Result]) -> Result | None:
        try:
            result = operation()
        except Exception as error:  # Stage boundary retains the actual failure.
            self.outcome.stages[name] = StageOutcome(status="failed", reason=redact_text(str(error)))
            try:
                self.persist()
            except Exception as persistence_error:  # noqa: BLE001 - preserve original stage error
                self.deps.resources.log_exception("Could not record failed stage outcome", persistence_error)
            if not self.outcome.training_succeeded:
                raise
            self.deps.resources.log_exception(
                "Pipeline stage failed; successful training retained",
                error,
                context={"stage": name},
            )
            return None
        except BaseException as error:
            self.outcome.fatal_error = True
            self.outcome.stages[name] = StageOutcome(
                status="failed", reason=redact_text(f"{type(error).__name__}: {error}")
            )
            try:
                self.persist()
            except Exception as persistence_error:  # noqa: BLE001 - retain interruption
                self.deps.resources.log_exception("Could not record interrupted stage outcome", persistence_error)
            raise
        self.outcome.stages[name] = StageOutcome(status="succeeded")
        self.persist()
        return result

    def succeeded(self, name: str) -> bool:
        return self.outcome.stages[name].status == "succeeded"

    def resources_ready(self) -> bool:
        if not self.outcome.training_succeeded or self.succeeded("training_resources"):
            return True
        # Queue contraction may already be durable: never infer that old leases remain valid.
        for name in ("prediction", "metrics", "comparison", "report", "visualization"):
            self.skip(name, "Post-training resource transition failed; compute admission unknown")
        return False

    def finish(self, results: dict[str, Any]) -> dict[str, Any]:
        self.persist()
        results["outcome"] = self.outcome.model_dump(mode="json")
        self.deps.resources.log(
            "WARNING" if self.outcome.status == "completed_with_warnings" else "INFO",
            "{}",
            self.outcome.summary(),
        )
        return results


def _as_dict(config: Any) -> dict[str, Any]:
    if is_dataclass(config) and (not isinstance(config, type)):
        values = {field.name: getattr(config, field.name) for field in fields(config)}
    elif isinstance(config, Mapping):
        values = dict(config)
    else:
        raise TypeError("Pipeline stages must be normalized mappings or dataclass requests")
    return {key: value for key, value in values.items() if key != "defaults"}


def routed_native(settings: dict[str, Any], project: Path, name: str) -> dict[str, Any]:
    """Reject conflicting native output keys instead of silently overwriting them."""
    chosen = dict(settings)
    expected = {"project": str(project), "name": name}
    for key, value in expected.items():
        if key in chosen and chosen[key] is not None and (str(chosen[key]) != value):
            raise ValueError(f"{key}={chosen[key]!r} conflicts with pipeline run_dir; expected {value}")
    if "save_dir" in chosen:
        raise ValueError("save_dir conflicts with pipeline run_dir; use run_dir to route outputs")
    return chosen | expected


def _stage_values(config: Any, allowed: set[str], stage: str) -> dict[str, Any]:
    values = _as_dict(config)
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(f"Pipeline {stage} keys {sorted(unknown)} are unsupported; outputs use run_dir")
    return values


def pipeline_stage_settings(
    metrics: Any, report: Any, compare: Any
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Share effect-free stage-key validation with submission preflight."""
    return (
        _stage_values(metrics, {"evaluation", "calibration_split"}, "metrics"),
        _stage_values(report, {"report_config_path"}, "report"),
        _stage_values(compare, {"baseline_model", "q", "bootstrap_iterations", "seed"}, "compare"),
    )


def _comparison_settings(settings: dict[str, Any]) -> InferenceConfig:
    fields = {key: settings[key] for key in ("conf", "iou", "imgsz", "batch", "device") if key in settings}
    ignored = {
        "model",
        "backend",
        "preset",
        "source",
        "stream",
        "project",
        "name",
        "save_dir",
        "mode",
        "task",
    }
    extras = {key: value for key, value in settings.items() if key not in {*fields, *ignored}}
    return InferenceConfig(**fields, ultralytics=extras)


def _required_training_splits(
    splits: list[str], *, skip_predict: bool, skip_metrics: bool, skip_compare: bool
) -> list[str]:
    """Require only the supplied CSV splits that an enabled pipeline stage consumes."""
    required = ["train", "val"]
    if not skip_predict or not skip_metrics:
        required.extend(splits)
    if not skip_compare:
        required.append("test")
    return list(dict.fromkeys(required))


def _compare_and_report(
    config: dict[str, Any],
    checkpoint: str | Path,
    thresholds: dict[str, float],
    ground_truth: GroundTruthInput,
    directory: Path,
    clearml: ClearMLConfig,
    inference: InferenceConfig,
    evaluation: Any,
    report_config: dict[str, Any],
    skip_report: bool,
    candidate_task_id: str | None = None,
    model_label: str | None = None,
    *,
    deps: WorkflowDependencies,
) -> dict[str, Any]:
    if candidate_task_id is None:
        local_weights = deps.storage.model_weights_path(checkpoint)
        if isinstance(local_weights, str):
            raise ValueError(
                "Local comparison requires a filesystem checkpoint; resolve remote weights before comparison"
            )
        candidate = ModelRef(source="local", weights=local_weights, thresholds=thresholds, label=model_label)
    else:
        candidate = ModelRef(source="clearml", task_id=candidate_task_id)
    task = deps.tracking.init_task(clearml, stage="compare")
    try:
        result = run_comparison(
            **config,
            candidate_model=candidate,
            ground_truth=ground_truth,
            output_dir=directory / COMPARISON_DIR,
            clearml=clearml,
            inference=inference,
            split="test",
            evaluation=evaluation,
            deps=deps,
        )
    except NoBaselineModelError as error:
        deps.tracking.record_run_configuration(task, {"comparison_status": {"status": "skipped", "reason": str(error)}})
        deps.tracking.complete_result_producer(task, "compare")
        return {"comparison_status": "skipped"}
    if result is None:
        return {"comparison_status": "skipped"}
    results: dict[str, Any] = {"comparison": result}
    if not skip_report:
        results["reports"] = run_report(
            comparison_dir=directory / COMPARISON_DIR,
            output_dir=directory / REPORTS_DIR,
            clearml=clearml,
            **report_config,
            deps=deps,
        )
    return results


def _train_from_ground_truth(
    train_params: dict[str, Any],
    clearml: ClearMLConfig,
    ground_truth: ResolvedGroundTruth,
    dataset_format: DatasetFormat,
    dataset_cache_dir: str | Path | None,
    required_splits: list[str],
    *,
    deps: WorkflowDependencies,
) -> tuple[Path, ResolvedGroundTruth]:
    trained = run_training(
        train_params,
        clearml,
        ground_truth=ground_truth,
        dataset_format=dataset_format,
        dataset_cache_dir=dataset_cache_dir,
        required_splits=required_splits,
        deps=deps,
    )
    return trained.weights, replace(ground_truth, path=trained.cleaned_ground_truth)


def _publish_pipeline(
    publisher: Publisher,
    task: TaskHandle | None,
    directory: Path,
    effective_ground_truth: str | Path,
    source_ground_truth: str | Path,
    predictions: Path,
    prediction_splits: list[str],
    evaluations: dict[str, Path],
    checkpoint: str | Path,
    metrics_cfg: dict[str, Any],
    skip_predict: bool,
    *,
    deps: WorkflowDependencies,
) -> None:
    if not publisher.enabled:
        return
    evaluation_metadata = metrics_cfg["evaluation"].model_dump(mode="json") | {
        "calibration_split": metrics_cfg["calibration_split"]
    }
    available_predictions = predictions if deps.storage.is_file(predictions) else None
    publish_results(
        publisher,
        task,
        output_dir=directory,
        ground_truth=effective_ground_truth,
        source_ground_truth=source_ground_truth,
        predictions=available_predictions,
        prediction_splits=prediction_splits if not skip_predict else None,
        evaluations=evaluations,
        metadata={"model": str(checkpoint), "evaluation": evaluation_metadata},
        deps=deps,
    )


def _result_producers(skip_predict: bool, skip_metrics: bool, skip_compare: bool) -> list[ResultProducer]:
    stages: tuple[tuple[ResultProducer, bool], ...] = (
        ("predict", skip_predict),
        ("metrics", skip_metrics),
        ("compare", skip_compare),
    )
    return [producer for producer, skipped in stages if not skipped]


def run_pipeline(
    ultralytics: dict[str, Any],
    ultralytics_predict: dict[str, Any],
    metrics: Any,
    report: Any,
    compare: Any,
    clearml: ClearMLConfig,
    ground_truth: GroundTruthInput,
    splits: list[str] | None = None,
    dataset_format: DatasetFormat = "ndjson",
    dataset_cache_dir: str | Path | None = None,
    run_id: str | None = None,
    run_dir: str | Path | None = None,
    weights: str | Path | None = None,
    skip_train: bool = False,
    skip_predict: bool = False,
    skip_metrics: bool = False,
    skip_report: bool = False,
    skip_compare: bool = False,
    fiftyone: FiftyOneConfig | None = None,
    model_label: str | None = None,
    *,
    deps: WorkflowDependencies,
) -> dict[str, Any]:
    """Pass real producer outputs to consumers and preserve files on any failure."""
    with deps.resources.trace_operation("workflow.pipeline"):
        task = deps.tracking.init_task(clearml, stage="pipeline")
        resolved_truth = resolve_ground_truth(ground_truth, task=task, deps=deps)
        publisher = prepare_publisher(task, fiftyone, factory=deps.publisher_factory, deps=deps)
        if weights is not None and (not skip_train):
            raise ValueError("weights is only valid with skip_train=true; training chooses its model")
        splits = list(dict.fromkeys(splits or ["train", "val", "test"]))
        directory = (
            deps.storage.resolve_run_dir(deps.storage.runs_root(), run_id or "", Path(run_dir) if run_dir else None)
            if run_dir or run_id
            else deps.storage.task_run_dir(deps.storage.runs_root(), *deps.tracking.task_identity(task))
        )
        if deps.dataset.dataset_cache_root(dataset_cache_dir).is_relative_to(deps.storage.resolve(directory)):
            raise ValueError("dataset_cache_dir must be outside run_dir")
        metrics_cfg, report_cfg, compare_cfg = pipeline_stage_settings(metrics, report, compare)
        train_params = routed_native(ultralytics, directory / "detect", "train")
        prediction_overrides = dict(ultralytics_predict)
        prediction_data_overrides: dict[str, dict[str, Any]] = {}
        if not skip_train:
            prediction_overrides, explicit_overrides = deps.dataset.apply_dataset_policy(prediction_overrides)
            prediction_data_overrides = {"ultralytics_predict": explicit_overrides}
        predict_params = routed_native(
            deps.model.prediction_settings(prediction_overrides), directory / "native", "predict"
        )
        deps.storage.mkdir(directory, parents=True, exist_ok=True)
        deps.storage.point_latest_at(deps.storage.runs_root(), directory)
        deps.tracking.declare_result_producers(
            task, _result_producers(skip_predict, skip_metrics, skip_compare), output_dir=directory
        )
        stages = _PipelineStages(directory, task, deps)
        results: dict[str, Any] = {"run_dir": directory}
        checkpoint = weights if weights is not None else directory / "detect/train/weights/best.pt"
        effective_ground_truth = resolved_truth
        if not skip_train:
            checkpoint, effective_ground_truth = _train_from_ground_truth(
                train_params,
                clearml,
                resolved_truth,
                dataset_format,
                dataset_cache_dir,
                _required_training_splits(
                    splits,
                    skip_predict=skip_predict,
                    skip_metrics=skip_metrics,
                    skip_compare=skip_compare,
                ),
                deps=deps,
            )
            if not deps.storage.is_file(checkpoint) or deps.storage.stat(checkpoint).st_size == 0:
                raise ValueError(f"Training did not produce a usable checkpoint: {checkpoint}")
            stages.outcome.training_succeeded = True
            stages.outcome.stages["training"] = StageOutcome(status="succeeded", artifacts=[str(checkpoint)])
            deps.tracking.preserve_training_success(task, checkpoint, directory / "pipeline_outcome.json")
            stages.persist()
            results["weights"] = checkpoint
            stages.run("training_resources", deps.resources.training_finished)
            stages.run(
                "training_metadata",
                lambda: deps.tracking.record_run_configuration(
                    task, {"prediction_data_overrides": prediction_data_overrides}
                ),
            )
        else:
            stages.skip("training", "Disabled by configuration")
        return _run_downstream(
            stages,
            results,
            directory,
            checkpoint,
            effective_ground_truth,
            resolved_truth,
            clearml,
            train_params,
            predict_params,
            metrics_cfg,
            compare_cfg,
            report_cfg,
            splits,
            model_label,
            skip_train,
            skip_predict,
            skip_metrics,
            skip_compare,
            skip_report,
            publisher,
            task,
            deps,
        )


def _run_downstream(
    stages: _PipelineStages,
    results: dict[str, Any],
    directory: Path,
    checkpoint: str | Path,
    effective_ground_truth: ResolvedGroundTruth,
    resolved_truth: ResolvedGroundTruth,
    clearml: ClearMLConfig,
    train_params: dict[str, Any],
    predict_params: dict[str, Any],
    metrics_cfg: dict[str, Any],
    compare_cfg: dict[str, Any],
    report_cfg: dict[str, Any],
    splits: list[str],
    model_label: str | None,
    skip_train: bool,
    skip_predict: bool,
    skip_metrics: bool,
    skip_compare: bool,
    skip_report: bool,
    publisher: Publisher,
    task: TaskHandle | None,
    deps: WorkflowDependencies,
) -> dict[str, Any]:
    if not stages.resources_ready():
        return stages.finish(results)
    predictions = directory / PREDICTIONS_NAME
    prediction_splits = list(dict.fromkeys(["val", *splits]))
    if skip_predict:
        stages.skip("prediction", "Disabled by configuration")
    else:
        predicted = stages.run(
            "prediction",
            lambda: run_prediction(
                checkpoint,
                effective_ground_truth,
                predictions,
                clearml,
                train_params,
                splits=prediction_splits,
                ultralytics_predict=predict_params,
                fiftyone=FiftyOneConfig(enabled=False),
                model_label=model_label,
                deps=deps,
            ),
        )
        if predicted is not None:
            predictions = predicted.predictions
            results["predictions"] = predictions
            stages.outcome.stages["prediction"].artifacts = [str(predictions)]
    # A failed producer's previous/partial file is never an eligible input.
    predictions_ready = skip_predict or stages.succeeded("prediction")
    if not skip_train and skip_predict:
        predictions_ready = False
    evaluations, thresholds = _pipeline_metrics(
        stages,
        results,
        directory,
        predictions,
        predictions_ready,
        effective_ground_truth,
        clearml,
        splits,
        model_label,
        metrics_cfg,
        skip_metrics,
        skip_train,
        skip_compare,
        deps,
    )
    comparison_ready = False
    if skip_compare:
        stages.skip("comparison", "Disabled by configuration")
        comparison_ready = skip_train
    elif thresholds is None:
        stages.skip("comparison", "Calibration thresholds unavailable in this attempt")
    else:
        compared = stages.run(
            "comparison",
            lambda: _compare_and_report(
                compare_cfg,
                checkpoint,
                thresholds,
                effective_ground_truth,
                directory,
                clearml,
                _comparison_settings(predict_params),
                metrics_cfg["evaluation"],
                report_cfg,
                True,
                candidate_task_id=str(task.id) if not skip_train and task is not None else None,
                model_label=model_label,
                deps=deps,
            ),
        )
        if compared is not None:
            results.update(compared)
            comparison_ready = "comparison" in compared
            if not comparison_ready:
                stages.skip("comparison", "Automatic baseline unavailable")
    _pipeline_report(stages, results, directory, clearml, report_cfg, skip_report, comparison_ready, deps)
    if predictions_ready:
        stages.run(
            "visualization",
            lambda: _publish_pipeline(
                publisher,
                task,
                directory,
                effective_ground_truth.path,
                resolved_truth.path,
                predictions,
                prediction_splits,
                evaluations,
                checkpoint,
                metrics_cfg,
                skip_predict,
                deps=deps,
            ),
        )
    else:
        stages.skip("visualization", "Prediction output unavailable in this attempt")
    return stages.finish(results)


def _pipeline_metrics(
    stages: _PipelineStages,
    results: dict[str, Any],
    directory: Path,
    predictions: Path,
    predictions_ready: bool,
    effective_ground_truth: ResolvedGroundTruth,
    clearml: ClearMLConfig,
    splits: list[str],
    model_label: str | None,
    metrics_cfg: dict[str, Any],
    skip_metrics: bool,
    skip_train: bool,
    skip_compare: bool,
    deps: WorkflowDependencies,
) -> tuple[dict[str, Path], dict[str, float] | None]:
    thresholds_path = directory / METRICS_DIR / "frozen_thresholds.json"
    evaluations: dict[str, Path] = {}
    thresholds: dict[str, float] | None = None
    if skip_metrics:
        stages.skip("metrics", "Disabled by configuration")
        if skip_train and not skip_compare:
            thresholds = stages.run("thresholds", lambda: json.loads(deps.storage.read_text(thresholds_path)))
    elif not predictions_ready:
        stages.skip("metrics", "No successful prediction producer in this training attempt")
    else:
        evaluated = stages.run(
            "metrics",
            lambda: compute_metrics(
                predictions,
                effective_ground_truth,
                directory / METRICS_DIR,
                clearml,
                splits=splits,
                fiftyone=FiftyOneConfig(enabled=False),
                model_label=model_label,
                **metrics_cfg,
                deps=deps,
            ),
        )
        if evaluated is not None:
            results["metrics"] = evaluated
            evaluations = evaluated.evaluations
            thresholds = stages.run("thresholds", lambda: next(iter(evaluated.best_confidences.values())))
            if thresholds is not None:
                stages.run(
                    "threshold_publication",
                    lambda: deps.storage.atomic_write_text(thresholds_path, json.dumps(thresholds)),
                )
    return evaluations, thresholds


def _pipeline_report(
    stages: _PipelineStages,
    results: dict[str, Any],
    directory: Path,
    clearml: ClearMLConfig,
    report_cfg: dict[str, Any],
    skip_report: bool,
    comparison_ready: bool,
    deps: WorkflowDependencies,
) -> None:
    if skip_report:
        stages.skip("report", "Disabled by configuration")
    elif not comparison_ready:
        stages.skip("report", "No successful comparison producer in this attempt")
    else:
        reported = stages.run(
            "report",
            lambda: run_report(
                comparison_dir=directory / COMPARISON_DIR,
                output_dir=directory / REPORTS_DIR,
                clearml=clearml,
                **report_cfg,
                deps=deps,
            ),
        )
        if reported is not None:
            results["reports"] = reported
            artifacts = [str(path) for path in (*reported.dev_reports.values(), *reported.business_reports.values())]
            stages.outcome.stages["report"].artifacts = artifacts
            if reported.issues:
                stages.outcome.stages["report"] = StageOutcome(
                    status="completed_with_warnings",
                    reason=f"{len(reported.issues)} training count issues; see report Issues sheet",
                    artifacts=artifacts,
                )
