"""Typed capabilities required by application workflows, supplied per invocation."""

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from os import stat_result
from pathlib import Path
from typing import Any, Literal, Protocol

import pandas as pd
from pydantic import JsonValue

from clearml_yolo.application.contracts import (
    ClearMLConfig,
    DatasetFormat,
    ImageNameMode,
    PreparedDataset,
    ScoredResolution,
    TrainResult,
    VocabularyReport,
)
from clearml_yolo.core.evaluation.models import (
    ComputedEvaluation,
    DetectionMetrics,
    EvaluatedSplit,
    EvaluationArtifacts,
)
from clearml_yolo.core.identity import ModelIdentity
from clearml_yolo.core.publication import FiftyOneConfig, PublicationReceipt, PublicationRequest

Stage = Literal["train", "predict"]


class TaskHandle(Protocol):
    @property
    def id(self) -> str: ...


class Publisher(Protocol):
    @property
    def enabled(self) -> bool: ...

    def preflight(self) -> None: ...

    def publish(self, request: PublicationRequest) -> PublicationReceipt | None: ...


class DatasetStore(Protocol):
    def apply_dataset_policy(
        self, settings: dict[str, Any], data: Path | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]: ...

    def build_ground_truth(
        self,
        data_yaml: str | Path,
        output: str | Path,
        *,
        test_fraction: float = 0.5,
        seed: int = 0,
    ) -> Path: ...

    def cached_dataset(
        self,
        source: str | Path,
        cache_dir: str | Path | None = None,
        dataset_format: DatasetFormat = "ndjson",
        required_splits: tuple[str, ...] = ("train", "val"),
    ) -> AbstractContextManager[PreparedDataset]: ...

    def dataset_cache_root(self, cache_dir: str | Path | None) -> Path: ...


class ModelRunner(Protocol):
    def execution_settings(self, settings: dict[str, Any], stage: Stage) -> dict[str, Any]: ...

    def predict_on_images(
        self,
        weights: str | Path,
        image_paths: Sequence[str],
        *,
        image_name: ImageNameMode = "name",
        manifest_dir: Path | None = None,
        **model_kwargs: Any,
    ) -> pd.DataFrame: ...

    def prediction_settings(
        self, ultralytics_predict: dict[str, Any], weights: str | Path | None = None
    ) -> dict[str, Any]: ...

    def reinfer_split(
        self,
        weights: str | Path,
        ground_truth: pd.DataFrame,
        split: str,
        output: Path,
        *,
        conf: float | None,
        iou: float,
        imgsz: int | list[int],
        batch: int,
        device: str | int | list[int] | None,
        image_name: str,
        native_project: Path,
        native_name: str,
        native_kwargs: dict[str, object] | None = None,
        reuse_existing: bool = True,
    ) -> tuple[pd.DataFrame, VocabularyReport]: ...

    def requested_settings(self, settings: dict[str, Any], stage: Stage) -> dict[str, Any]: ...

    def resolution_of(
        self, weights: str | Path, imgsz: int | list[int] | None
    ) -> ScoredResolution: ...

    def stage_settings(self, settings: dict[str, Any], stage: Stage) -> dict[str, Any]: ...

    def trained_imgsz(self, weights: str | Path) -> int | None: ...

    def write_native_yaml(self, path: Path, settings: dict[str, Any], stage: Stage) -> Path: ...

    def train(
        self,
        task: TaskHandle | None,
        architecture: str | Path,
        settings: dict[str, Any],
        prepared: PreparedDataset,
    ) -> TrainResult: ...


class ModelRepository(Protocol):
    def fetch_best_confidences(self, task_id: str) -> dict[str, float]: ...

    def latest_completed_task_id(
        self,
        project_name: str,
        task_name: str | None = None,
        tags: Sequence[str] | None = None,
        exclude_task_id: str | None = None,
    ) -> str | None: ...

    def read_checkpoint_identity(self, path: Path) -> ModelIdentity | None: ...

    def resolve_task_model(self, task_id: str) -> tuple[Path, dict[str, str]]: ...

    def resolve_weights_with_identity(
        self, weights: str | Path
    ) -> tuple[str | Path, ModelIdentity | None]: ...


class EvaluationEngine(Protocol):
    def calibrate_thresholds(
        self,
        ground_truth: pd.DataFrame,
        predictions: pd.DataFrame,
        *,
        calibration_split: str,
        classes: list[str],
        iou_threshold: float,
        matching_strategy: str,
        confidence_optimization: str,
    ) -> dict[str, float]: ...

    def filter_invalid_prediction_boxes(self, predictions: pd.DataFrame) -> pd.DataFrame: ...

    def prepare_ground_truth(
        self, ground_truth: pd.DataFrame, *, deduplicate: bool
    ) -> pd.DataFrame: ...

    def prepare_predictions(
        self,
        predictions: pd.DataFrame,
        *,
        preprocess_conf_threshold: float | None,
        preprocess_nms_containment_threshold: float | None,
        preprocess_nms_iou_threshold: float | None,
    ) -> pd.DataFrame: ...

    def compute_evaluation(
        self,
        ground_truth: pd.DataFrame,
        raw_predictions: pd.DataFrame,
        predictions: pd.DataFrame,
        *,
        split: str,
        classes: list[str],
        thresholds: Mapping[str, float | int],
        required_classes: list[str] | None,
        iou_threshold: float,
        matching_strategy: str,
        ap_method: str,
        skip_cohen_kappa: bool,
        methodology: Mapping[str, JsonValue] | None = None,
        source_ground_truth: pd.DataFrame | None = None,
        source_predictions: pd.DataFrame | None = None,
        model_identity: ModelIdentity | None = None,
    ) -> ComputedEvaluation: ...


class EvaluationWriter(Protocol):
    def render_evaluation(
        self,
        computed: ComputedEvaluation,
        *,
        output_dir: Path,
        suffix: str,
        dashboard_classes: set[str] | None = None,
    ) -> EvaluationArtifacts: ...

    def summarize_metrics(
        self, metrics: dict[str, DetectionMetrics]
    ) -> tuple[pd.DataFrame, dict[str, float]]: ...


class ReportRenderer(Protocol):
    def write_candidate_workbook(
        self, path: Path, per_class: pd.DataFrame, summary: dict[str, float]
    ) -> None: ...

    def annotate_workbook(
        self, path: str | Path, identities: Mapping[str, ModelIdentity]
    ) -> None: ...

    def read_dashboard(self, path: str | Path, **kwargs: Any) -> pd.DataFrame: ...

    def workbook_identities(self, path: str | Path) -> dict[str, ModelIdentity]: ...

    def write_comparison_workbook(
        self, rows: pd.DataFrame, excluded: pd.DataFrame, methodology: dict[str, object], path: Path
    ) -> dict[str, Path]: ...

    def build_reports(
        self,
        candidate: Path,
        baseline: Path,
        dev_path: Path,
        business_path: Path,
        config_path: str | Path | None,
    ) -> None: ...

    def write_evaluation_workbook(
        self, path: Path, evaluated: EvaluatedSplit, *, methodology: dict[str, Any]
    ) -> dict[str, Path]: ...


class RunStorage(Protocol):
    def model_weights_path(self, value: str | Path) -> str | Path: ...

    def point_latest_at(self, root: Path, run_dir: Path) -> None: ...

    def resolve_run_dir(self, root: Path, run_id: str, explicit: Path | None) -> Path: ...

    def runs_root(self) -> Path: ...

    def safe_path_component(self, value: str) -> str: ...

    def task_run_dir(self, root: Path, project_name: str, task_name: str, task_id: str) -> Path: ...

    def write_path(self, value: str | Path) -> Path: ...

    def mkdir(self, path: Path, *, parents: bool = False, exist_ok: bool = False) -> None: ...

    def is_file(self, path: Path) -> bool: ...

    def is_dir(self, path: Path) -> bool: ...

    def read_text(self, path: Path, *, encoding: str = "utf-8") -> str: ...

    def write_text(self, path: Path, content: str, *, encoding: str = "utf-8") -> None: ...

    def read_csv(
        self,
        path: str | Path,
        *,
        dtype: dict[str, type[str]] | None = None,
        float_precision: Literal["round_trip"] | None = None,
    ) -> pd.DataFrame: ...

    def write_csv(
        self,
        frame: pd.DataFrame,
        path: str | Path,
        *,
        index: bool = False,
        float_format: str | None = None,
    ) -> None: ...

    def archive_native_outputs(
        self, save_dir: Path, destination: Path, *, role: str, split: str
    ) -> Path: ...

    def stat(self, path: Path) -> stat_result: ...

    def resolve(self, path: Path) -> Path: ...

    def absolute(self, path: Path) -> Path: ...


class ExecutionResources(Protocol):
    def trace_operation(
        self, name: str, *, context: Mapping[str, object] | None = None
    ) -> AbstractContextManager[None]: ...

    def log(self, level: str, message: str, *args: object) -> None: ...

    def progress_callback(
        self, description: str, total: int, unit: str = "it"
    ) -> AbstractContextManager[Callable[[str | None], None]]: ...

    def log_exception(
        self,
        message: str,
        error: BaseException,
        *,
        level: str = "WARNING",
        context: Mapping[str, object] | None = None,
        include_message: bool = True,
    ) -> None: ...

    def track[Item](
        self, items: Iterable[Item], description: str, total: int | None = None, unit: str = "it"
    ) -> Iterator[Item]: ...

    def training_finished(self) -> None: ...


class TrackingSession(Protocol):
    def associate_calibration_thresholds(
        self,
        task: TaskHandle | None,
        thresholds: Mapping[str, float],
        *,
        prediction_checkpoint_sha256: str | None,
        split: str = "val",
    ) -> None: ...

    def connect_config_file(
        self, task: TaskHandle | None, name: str, path: Path, *, allow_remote_override: bool = True
    ) -> Path: ...

    def expect_artifacts(self, task: TaskHandle | None, names: list[str]) -> None: ...

    def file_digest(self, path: Path) -> str: ...

    def init_task(self, config: ClearMLConfig, stage: str) -> TaskHandle | None: ...

    def prediction_checkpoint_hash(self, predictions: Path) -> str | None: ...

    def prediction_model_identity(self, predictions: Path) -> ModelIdentity | None: ...

    def publish_evaluation(
        self,
        task: TaskHandle | None,
        evaluated: EvaluatedSplit,
        ground_truth: Path,
        predictions: Path,
        *,
        output_dir: Path,
        model_id: str | None = None,
        role: str = "prediction",
    ) -> None: ...

    def publish_table(self, task: TaskHandle | None, name: str, path: Path) -> None: ...

    def record_run_configuration(
        self, task: TaskHandle | None, values: dict[str, Any]
    ) -> dict[str, Any]: ...

    def register_ground_truth(
        self, task: TaskHandle | None, ground_truth: Path, *, output_dir: Path
    ) -> None: ...

    def register_predictions(
        self,
        task: TaskHandle | None,
        ground_truth: Path,
        predictions: Path,
        *,
        output_dir: Path,
        model_id: str | None = None,
        role: str = "prediction",
        splits: list[str] | None = None,
        model_identity: ModelIdentity | None = None,
    ) -> None: ...

    def report_comparison(
        self,
        task: TaskHandle | None,
        split: str,
        rows: pd.DataFrame,
        methodology: Mapping[str, object],
    ) -> None: ...

    def report_scalars(
        self, task: TaskHandle | None, title: str, values: Mapping[str, float]
    ) -> None: ...

    def report_table(
        self,
        task: TaskHandle | None,
        title: str,
        series: str,
        frame: pd.DataFrame,
        *,
        identities: Mapping[str, ModelIdentity] | None = None,
    ) -> None: ...

    def task_identity(self, task: TaskHandle | None) -> tuple[str, str, str]: ...

    def upload_artifact(
        self, task: TaskHandle | None, name: str, artifact_object: Path
    ) -> None: ...

    def write_prediction_provenance(
        self, predictions: Path, checkpoint: Path, model_identity: ModelIdentity | None = None
    ) -> str | None: ...

    def has_owned_native_model(self, task: TaskHandle | None) -> bool: ...


@dataclass(frozen=True)
class WorkflowDependencies:
    dataset: DatasetStore
    model: ModelRunner
    repository: ModelRepository
    evaluation: EvaluationEngine
    evaluation_writer: EvaluationWriter
    renderer: ReportRenderer
    storage: RunStorage
    resources: ExecutionResources
    tracking: TrackingSession
    publisher_factory: Callable[[FiftyOneConfig | None], Publisher]
    disabled_publisher: Publisher
