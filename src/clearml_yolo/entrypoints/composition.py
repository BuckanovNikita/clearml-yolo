"""Compose explicit workflow dependencies at the outer application boundary."""

from pathlib import Path

from clearml_yolo.adapters.clearml.models import (
    fetch_best_confidences as _repository_fetch_best_confidences,
)
from clearml_yolo.adapters.clearml.models import (
    latest_completed_task_id as _repository_latest_completed_task_id,
)
from clearml_yolo.adapters.clearml.models import (
    resolve_task_model as _repository_resolve_task_model,
)
from clearml_yolo.adapters.clearml.models import (
    resolve_weights_with_identity as _repository_resolve_weights_with_identity,
)
from clearml_yolo.adapters.clearml.native import (
    associate_calibration_thresholds as _tracking_associate_calibration_thresholds,
)
from clearml_yolo.adapters.clearml.native import owned_native_model
from clearml_yolo.adapters.clearml.report import report_comparison as _tracking_report_comparison
from clearml_yolo.adapters.clearml.report import report_scalars as _tracking_report_scalars
from clearml_yolo.adapters.clearml.report import report_table as _tracking_report_table
from clearml_yolo.adapters.clearml.results import file_digest as _tracking_file_digest
from clearml_yolo.adapters.clearml.results import (
    prediction_checkpoint_hash as _tracking_prediction_checkpoint_hash,
)
from clearml_yolo.adapters.clearml.results import (
    prediction_model_identity as _tracking_prediction_model_identity,
)
from clearml_yolo.adapters.clearml.results import publish_evaluation as _tracking_publish_evaluation
from clearml_yolo.adapters.clearml.results import (
    register_ground_truth as _tracking_register_ground_truth,
)
from clearml_yolo.adapters.clearml.results import (
    register_predictions as _tracking_register_predictions,
)
from clearml_yolo.adapters.clearml.results import (
    write_prediction_provenance as _tracking_write_prediction_provenance,
)
from clearml_yolo.adapters.clearml.session import (
    connect_config_file as _tracking_connect_config_file,
)
from clearml_yolo.adapters.clearml.session import expect_artifacts as _tracking_expect_artifacts
from clearml_yolo.adapters.clearml.session import init_task as _tracking_init_task
from clearml_yolo.adapters.clearml.session import publish_table as _tracking_publish_table
from clearml_yolo.adapters.clearml.session import (
    record_run_configuration as _tracking_record_run_configuration,
)
from clearml_yolo.adapters.clearml.session import task_identity as _tracking_task_identity
from clearml_yolo.adapters.clearml.session import upload_artifact as _tracking_upload_artifact
from clearml_yolo.adapters.evaluation.scoring import (
    calibrate_thresholds as _evaluation_calibrate_thresholds,
)
from clearml_yolo.adapters.evaluation.scoring import (
    compute_evaluation as _evaluation_compute_evaluation,
)
from clearml_yolo.adapters.evaluation.scoring import (
    filter_invalid_prediction_boxes as _evaluation_filter_invalid_prediction_boxes,
)
from clearml_yolo.adapters.evaluation.scoring import (
    prepare_ground_truth as _evaluation_prepare_ground_truth,
)
from clearml_yolo.adapters.evaluation.scoring import (
    prepare_predictions as _evaluation_prepare_predictions,
)
from clearml_yolo.adapters.fiftyone.noop import NoOpPublisher
from clearml_yolo.adapters.integrations.native_runtime import (
    release_training_memory as _resources_training_finished,
)
from clearml_yolo.adapters.integrations.training import execute_training as _execute_training
from clearml_yolo.adapters.observability.diagnostics import (
    log as _resources_log,
)
from clearml_yolo.adapters.observability.diagnostics import (
    log_exception as _resources_log_exception,
)
from clearml_yolo.adapters.observability.progress import (
    progress_callback as _resources_progress_callback,
)
from clearml_yolo.adapters.observability.progress import track as _resources_track
from clearml_yolo.adapters.reporting.comparison_workbook import (
    write_comparison_workbook as _renderer_write_comparison_workbook,
)
from clearml_yolo.adapters.reporting.evaluation import (
    render_evaluation as _evaluation_writer_render_evaluation,
)
from clearml_yolo.adapters.reporting.evaluation import summarize_evaluation as summarize_metrics
from clearml_yolo.adapters.reporting.evaluation_workbook import (
    write_candidate_workbook,
)
from clearml_yolo.adapters.reporting.evaluation_workbook import (
    write_evaluation_workbook as _write_evaluation_workbook,
)
from clearml_yolo.adapters.reporting.reports import build_reports as _build_reports
from clearml_yolo.adapters.reporting.workbook_identity import (
    annotate_workbook as _renderer_annotate_workbook,
)
from clearml_yolo.adapters.reporting.workbook_identity import (
    read_dashboard as _renderer_read_dashboard,
)
from clearml_yolo.adapters.reporting.workbook_identity import (
    workbook_identities as _renderer_workbook_identities,
)
from clearml_yolo.adapters.storage.dataset import (
    apply_dataset_policy as _dataset_apply_dataset_policy,
)
from clearml_yolo.adapters.storage.dataset_cache import cached_dataset as _dataset_cached_dataset
from clearml_yolo.adapters.storage.dataset_cache import (
    dataset_cache_root as _dataset_dataset_cache_root,
)
from clearml_yolo.adapters.storage.file_io import mkdir as _mkdir
from clearml_yolo.adapters.storage.file_io import read_csv as _read_csv
from clearml_yolo.adapters.storage.file_io import read_text as _read_text
from clearml_yolo.adapters.storage.file_io import write_csv as _write_csv
from clearml_yolo.adapters.storage.file_io import write_text as _write_text
from clearml_yolo.adapters.storage.filesystem import (
    model_weights_path as _storage_model_weights_path,
)
from clearml_yolo.adapters.storage.filesystem import runs_root as _storage_runs_root
from clearml_yolo.adapters.storage.filesystem import write_path as _storage_write_path
from clearml_yolo.adapters.storage.identity import (
    read_checkpoint_identity as _repository_read_checkpoint_identity,
)
from clearml_yolo.adapters.storage.native_archive import (
    archive_native_outputs as _archive_native_outputs,
)
from clearml_yolo.adapters.storage.run_identity import point_latest_at as _storage_point_latest_at
from clearml_yolo.adapters.storage.run_identity import resolve_run_dir as _storage_resolve_run_dir
from clearml_yolo.adapters.storage.run_identity import (
    safe_path_component as _storage_safe_path_component,
)
from clearml_yolo.adapters.storage.run_identity import task_run_dir as _storage_task_run_dir
from clearml_yolo.adapters.yolo.config import execution_settings as _model_execution_settings
from clearml_yolo.adapters.yolo.config import prediction_settings as _model_prediction_settings
from clearml_yolo.adapters.yolo.config import requested_settings as _model_requested_settings
from clearml_yolo.adapters.yolo.config import stage_settings as _model_stage_settings
from clearml_yolo.adapters.yolo.config import write_native_yaml as _model_write_native_yaml
from clearml_yolo.adapters.yolo.ground_truth import (
    build_ground_truth as _dataset_build_ground_truth,
)
from clearml_yolo.adapters.yolo.inference import predict_on_images as _model_predict_on_images
from clearml_yolo.adapters.yolo.inference import resolution_of as _model_resolution_of
from clearml_yolo.adapters.yolo.inference import trained_imgsz as _model_trained_imgsz
from clearml_yolo.adapters.yolo.reinfer import reinfer_split as _model_reinfer_split
from clearml_yolo.application.ports import (
    Publisher,
    WorkflowDependencies,
)
from clearml_yolo.core.publication import FiftyOneConfig


def _has_owned_native_model(task: object) -> bool:
    return owned_native_model(task) is not None


class _DatasetStore:
    apply_dataset_policy = staticmethod(_dataset_apply_dataset_policy)
    build_ground_truth = staticmethod(_dataset_build_ground_truth)
    cached_dataset = staticmethod(_dataset_cached_dataset)
    dataset_cache_root = staticmethod(_dataset_dataset_cache_root)


class _ModelRunner:
    execution_settings = staticmethod(_model_execution_settings)
    predict_on_images = staticmethod(_model_predict_on_images)
    prediction_settings = staticmethod(_model_prediction_settings)
    reinfer_split = staticmethod(_model_reinfer_split)
    requested_settings = staticmethod(_model_requested_settings)
    resolution_of = staticmethod(_model_resolution_of)
    stage_settings = staticmethod(_model_stage_settings)
    trained_imgsz = staticmethod(_model_trained_imgsz)
    write_native_yaml = staticmethod(_model_write_native_yaml)
    train = staticmethod(_execute_training)


class _ModelRepository:
    fetch_best_confidences = staticmethod(_repository_fetch_best_confidences)
    latest_completed_task_id = staticmethod(_repository_latest_completed_task_id)
    read_checkpoint_identity = staticmethod(_repository_read_checkpoint_identity)
    resolve_task_model = staticmethod(_repository_resolve_task_model)
    resolve_weights_with_identity = staticmethod(_repository_resolve_weights_with_identity)


class _EvaluationEngine:
    calibrate_thresholds = staticmethod(_evaluation_calibrate_thresholds)
    filter_invalid_prediction_boxes = staticmethod(_evaluation_filter_invalid_prediction_boxes)
    prepare_ground_truth = staticmethod(_evaluation_prepare_ground_truth)
    prepare_predictions = staticmethod(_evaluation_prepare_predictions)
    compute_evaluation = staticmethod(_evaluation_compute_evaluation)


class _EvaluationWriter:
    render_evaluation = staticmethod(_evaluation_writer_render_evaluation)
    summarize_metrics = staticmethod(summarize_metrics)


class _ReportRenderer:
    write_candidate_workbook = staticmethod(write_candidate_workbook)
    annotate_workbook = staticmethod(_renderer_annotate_workbook)
    read_dashboard = staticmethod(_renderer_read_dashboard)
    workbook_identities = staticmethod(_renderer_workbook_identities)
    write_comparison_workbook = staticmethod(_renderer_write_comparison_workbook)
    build_reports = staticmethod(_build_reports)
    write_evaluation_workbook = staticmethod(_write_evaluation_workbook)


class _RunStorage:
    model_weights_path = staticmethod(_storage_model_weights_path)
    point_latest_at = staticmethod(_storage_point_latest_at)
    resolve_run_dir = staticmethod(_storage_resolve_run_dir)
    runs_root = staticmethod(_storage_runs_root)
    safe_path_component = staticmethod(_storage_safe_path_component)
    task_run_dir = staticmethod(_storage_task_run_dir)
    write_path = staticmethod(_storage_write_path)
    archive_native_outputs = staticmethod(_archive_native_outputs)
    mkdir = staticmethod(_mkdir)
    is_file = staticmethod(Path.is_file)
    is_dir = staticmethod(Path.is_dir)
    stat = staticmethod(Path.stat)
    resolve = staticmethod(Path.resolve)
    absolute = staticmethod(Path.absolute)
    read_text = staticmethod(_read_text)
    write_text = staticmethod(_write_text)
    read_csv = staticmethod(_read_csv)
    write_csv = staticmethod(_write_csv)


class _ExecutionResources:
    log = staticmethod(_resources_log)
    progress_callback = staticmethod(_resources_progress_callback)
    log_exception = staticmethod(_resources_log_exception)
    track = staticmethod(_resources_track)
    training_finished = staticmethod(_resources_training_finished)


class _TrackingSession:
    associate_calibration_thresholds = staticmethod(_tracking_associate_calibration_thresholds)
    connect_config_file = staticmethod(_tracking_connect_config_file)
    expect_artifacts = staticmethod(_tracking_expect_artifacts)
    file_digest = staticmethod(_tracking_file_digest)
    init_task = staticmethod(_tracking_init_task)
    prediction_checkpoint_hash = staticmethod(_tracking_prediction_checkpoint_hash)
    prediction_model_identity = staticmethod(_tracking_prediction_model_identity)
    publish_evaluation = staticmethod(_tracking_publish_evaluation)
    publish_table = staticmethod(_tracking_publish_table)
    record_run_configuration = staticmethod(_tracking_record_run_configuration)
    register_ground_truth = staticmethod(_tracking_register_ground_truth)
    register_predictions = staticmethod(_tracking_register_predictions)
    report_comparison = staticmethod(_tracking_report_comparison)
    report_scalars = staticmethod(_tracking_report_scalars)
    report_table = staticmethod(_tracking_report_table)
    task_identity = staticmethod(_tracking_task_identity)
    upload_artifact = staticmethod(_tracking_upload_artifact)
    write_prediction_provenance = staticmethod(_tracking_write_prediction_provenance)
    has_owned_native_model = staticmethod(_has_owned_native_model)


def build_dependencies() -> WorkflowDependencies:
    """Construct an independent dependency bundle for one command invocation."""
    return WorkflowDependencies(
        dataset=_DatasetStore(),
        model=_ModelRunner(),
        repository=_ModelRepository(),
        evaluation=_EvaluationEngine(),
        evaluation_writer=_EvaluationWriter(),
        renderer=_ReportRenderer(),
        storage=_RunStorage(),
        resources=_ExecutionResources(),
        tracking=_TrackingSession(),
        publisher_factory=create_publisher,
        disabled_publisher=NoOpPublisher(),
    )


def create_publisher(config: FiftyOneConfig | None = None) -> Publisher:
    """Select visual publication once at the composition boundary."""
    selected = config if config is not None else FiftyOneConfig()
    if not selected.enabled:
        return NoOpPublisher()
    from clearml_yolo.adapters.fiftyone.publisher import FiftyOnePublisher

    return FiftyOnePublisher(selected)
