"""Compose explicit workflow dependencies at the outer application boundary."""

from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, override

from clearml_yolo.adapters.clearml import datasets as clearml_datasets
from clearml_yolo.adapters.clearml import models as clearml_models
from clearml_yolo.adapters.clearml import native as clearml_native
from clearml_yolo.adapters.clearml import report as clearml_report
from clearml_yolo.adapters.clearml import results as clearml_results
from clearml_yolo.adapters.clearml import session as clearml_session
from clearml_yolo.adapters.evaluation import comparison, scoring
from clearml_yolo.adapters.fiftyone import noop
from clearml_yolo.adapters.integrations import native_runtime, training
from clearml_yolo.adapters.observability import diagnostics, progress, tracing
from clearml_yolo.adapters.reporting import (
    comparison_workbook,
    evaluation_workbook,
    reports,
    workbook_identity,
)
from clearml_yolo.adapters.reporting import evaluation as reporting_evaluation
from clearml_yolo.adapters.runtime import execution_lifecycle
from clearml_yolo.adapters.storage import (
    dataset,
    dataset_cache,
    file_io,
    filesystem,
    identity,
    native_archive,
    run_identity,
)
from clearml_yolo.adapters.yolo import config as yolo_config
from clearml_yolo.adapters.yolo import ground_truth as yolo_ground_truth
from clearml_yolo.adapters.yolo import inference, reinfer
from clearml_yolo.application.contracts import DatasetFormat, ModelRef, PreparedDataset, TrainResult
from clearml_yolo.application.ports import (
    Publisher,
    WorkflowDependencies,
)
from clearml_yolo.core.models import ModelConfig
from clearml_yolo.core.publication import FiftyOneConfig
from clearml_yolo.core.transforms import TransformConfig


def _has_owned_native_model(task: object) -> bool:
    return clearml_native.owned_native_model(task) is not None


class _DatasetStore:
    apply_dataset_policy = staticmethod(dataset.apply_dataset_policy)
    build_ground_truth = staticmethod(yolo_ground_truth.build_ground_truth)
    dataset_cache_root = staticmethod(dataset_cache.dataset_cache_root)

    @staticmethod
    def cached_dataset(
        ground_truth: str | Path,
        cache_dir: str | Path | None = None,
        dataset_format: DatasetFormat = "ndjson",
        required_splits: tuple[str, ...] = ("train", "val"),
    ) -> AbstractContextManager[PreparedDataset]:
        if dataset_format == "coco":
            raise ValueError("Ultralytics training requires ndjson or flat dataset_format")
        return dataset_cache.cached_dataset(
            ground_truth, cache_dir, dataset_format, required_splits=required_splits
        )


class _DetectorDatasetStore(_DatasetStore):
    @staticmethod
    @override
    def cached_dataset(
        ground_truth: str | Path,
        cache_dir: str | Path | None = None,
        dataset_format: DatasetFormat = "ndjson",
        required_splits: tuple[str, ...] = ("train", "val"),
    ) -> AbstractContextManager[PreparedDataset]:
        # Native adapters own their COCO representation, including callers that
        # use the shared programmatic train API's legacy default argument.
        del dataset_format
        return dataset_cache.cached_dataset(
            ground_truth, cache_dir, "coco", required_splits=required_splits
        )


class _ModelRunner:
    def __init__(self, transforms: TransformConfig | None = None) -> None:
        self.transforms = transforms

    @staticmethod
    def bind_reference(weights: Path, reference: ModelRef) -> None:
        del weights
        if reference.backend not in {None, "ultralytics"}:
            raise ValueError("A native detector reference requires the detector dispatcher")

    execution_settings = staticmethod(yolo_config.execution_settings)
    predict_on_images = staticmethod(inference.predict_on_images)
    prediction_settings = staticmethod(yolo_config.prediction_settings)
    reinfer_split = staticmethod(reinfer.reinfer_split)
    requested_settings = staticmethod(yolo_config.requested_settings)
    resolution_of = staticmethod(inference.resolution_of)
    stage_settings = staticmethod(yolo_config.stage_settings)
    trained_imgsz = staticmethod(inference.trained_imgsz)
    write_native_yaml = staticmethod(yolo_config.write_native_yaml)

    def train(
        self,
        task: object,
        architecture: str | Path,
        settings: dict[str, Any],
        prepared: PreparedDataset,
    ) -> TrainResult:
        return training.execute_training(
            task, architecture, settings, prepared, transforms=self.transforms
        )


class _ModelRepository:
    fetch_best_confidences = staticmethod(clearml_models.fetch_best_confidences)
    latest_completed_task_id = staticmethod(clearml_models.latest_completed_task_id)
    read_checkpoint_identity = staticmethod(identity.read_checkpoint_identity)
    resolve_task_model = staticmethod(clearml_models.resolve_task_model)
    resolve_weights_with_identity = staticmethod(clearml_models.resolve_weights_with_identity)


class _EvaluationEngine:
    compare_outcomes = staticmethod(comparison.compare_outcomes)
    calibrate_thresholds = staticmethod(scoring.calibrate_thresholds)
    filter_invalid_prediction_boxes = staticmethod(scoring.filter_invalid_prediction_boxes)
    prepare_ground_truth = staticmethod(scoring.prepare_ground_truth)
    prepare_predictions = staticmethod(scoring.prepare_predictions)
    compute_evaluation = staticmethod(scoring.compute_evaluation)


class _EvaluationWriter:
    render_evaluation = staticmethod(reporting_evaluation.render_evaluation)
    summarize_metrics = staticmethod(reporting_evaluation.summarize_evaluation)


class _ReportRenderer:
    write_candidate_workbook = staticmethod(evaluation_workbook.write_candidate_workbook)
    annotate_workbook = staticmethod(workbook_identity.annotate_workbook)
    read_dashboard = staticmethod(workbook_identity.read_dashboard)
    workbook_identities = staticmethod(workbook_identity.workbook_identities)
    write_comparison_workbook = staticmethod(comparison_workbook.write_comparison_workbook)
    build_reports = staticmethod(reports.build_reports)
    write_evaluation_workbook = staticmethod(evaluation_workbook.write_evaluation_workbook)


class _RunStorage:
    model_weights_path = staticmethod(filesystem.model_weights_path)
    point_latest_at = staticmethod(run_identity.point_latest_at)
    resolve_run_dir = staticmethod(run_identity.resolve_run_dir)
    runs_root = staticmethod(filesystem.runs_root)
    safe_path_component = staticmethod(run_identity.safe_path_component)
    task_run_dir = staticmethod(run_identity.task_run_dir)
    write_path = staticmethod(filesystem.write_path)
    archive_native_outputs = staticmethod(native_archive.archive_native_outputs)
    mkdir = staticmethod(file_io.mkdir)
    is_file = staticmethod(Path.is_file)
    is_dir = staticmethod(Path.is_dir)
    stat = staticmethod(Path.stat)
    resolve = staticmethod(Path.resolve)
    absolute = staticmethod(Path.absolute)
    read_text = staticmethod(file_io.read_text)
    write_text = staticmethod(file_io.write_text)
    read_csv = staticmethod(file_io.read_csv)
    read_detection_csv = staticmethod(file_io.read_detection_csv)
    read_ground_truth = staticmethod(file_io.read_ground_truth)
    write_csv = staticmethod(file_io.write_csv)


class _ExecutionResources:
    trace_operation = staticmethod(tracing.trace_operation)
    log = staticmethod(diagnostics.log)
    progress_callback = staticmethod(progress.progress_callback)
    log_exception = staticmethod(diagnostics.log_exception)
    track = staticmethod(progress.track)

    @staticmethod
    def training_finished() -> None:
        native_runtime.release_training_memory()
        execution_lifecycle.notify_training_finished()


class _TrackingSession:
    publish_training_parameters = staticmethod(clearml_session.publish_training_parameters)
    declare_result_producers = staticmethod(clearml_results.declare_result_producers)
    complete_result_producer = staticmethod(clearml_results.complete_result_producer)
    associate_calibration_thresholds = staticmethod(clearml_native.associate_calibration_thresholds)
    connect_config_file = staticmethod(clearml_session.connect_config_file)
    expect_artifacts = staticmethod(clearml_session.expect_artifacts)
    file_digest = staticmethod(clearml_results.file_digest)
    init_task = staticmethod(clearml_session.init_task)
    prediction_checkpoint_hash = staticmethod(clearml_results.prediction_checkpoint_hash)
    prediction_image_name = staticmethod(clearml_results.prediction_image_name)
    prediction_model_identity = staticmethod(clearml_results.prediction_model_identity)
    publish_evaluation = staticmethod(clearml_results.publish_evaluation)
    publish_table = staticmethod(clearml_session.publish_table)
    record_run_configuration = staticmethod(clearml_session.record_run_configuration)
    register_ground_truth = staticmethod(clearml_results.register_ground_truth)
    register_predictions = staticmethod(clearml_results.register_predictions)
    report_comparison = staticmethod(clearml_report.report_comparison)
    report_scalars = staticmethod(clearml_report.report_scalars)
    report_table = staticmethod(clearml_report.report_table)
    task_identity = staticmethod(clearml_session.task_identity)
    upload_artifact = staticmethod(clearml_session.upload_artifact)
    write_prediction_provenance = staticmethod(clearml_results.write_prediction_provenance)
    has_owned_native_model = staticmethod(_has_owned_native_model)


def build_dependencies(
    model: ModelConfig | dict[str, Any] | None = None,
    *,
    transforms: TransformConfig | None = None,
) -> WorkflowDependencies:
    """Construct an independent dependency bundle for one command invocation."""
    from clearml_yolo.adapters.integrations.detectors import DetectorRunner
    from clearml_yolo.adapters.integrations.export_operations import DetectorExporter

    selected = model if isinstance(model, ModelConfig) else ModelConfig.model_validate(model or {})
    return WorkflowDependencies(
        dataset=_DatasetStore() if selected.backend == "ultralytics" else _DetectorDatasetStore(),
        ground_truth_repository=clearml_datasets.ClearMLGroundTruthRepository(),
        model=DetectorRunner(selected, _ModelRunner(transforms), transforms=transforms),
        repository=_ModelRepository(),
        evaluation=_EvaluationEngine(),
        evaluation_writer=_EvaluationWriter(),
        renderer=_ReportRenderer(),
        storage=_RunStorage(),
        resources=_ExecutionResources(),
        tracking=_TrackingSession(),
        publisher_factory=create_publisher,
        disabled_publisher=noop.NoOpPublisher(),
        exporter=DetectorExporter(selected),
    )


def create_publisher(config: FiftyOneConfig | None = None) -> Publisher:
    """Select visual publication once at the composition boundary."""
    selected = config if config is not None else FiftyOneConfig()
    if not selected.enabled:
        return noop.NoOpPublisher()
    from clearml_yolo.adapters.fiftyone.bounded import BoundedFiftyOnePublisher

    return BoundedFiftyOnePublisher(selected)
