"""Explicit dependency fixtures and adapter-seam patching for workflow tests."""

from collections.abc import Callable
from dataclasses import replace
from types import ModuleType
from typing import Any

import pytest

from clearml_yolo.application.ports import Publisher, WorkflowDependencies
from clearml_yolo.core.publication import FiftyOneConfig
from clearml_yolo.entrypoints.composition import build_dependencies


class PublisherFactory:
    """Keep the injected bundle immutable while allowing a factory test double."""

    def __init__(self, create: Callable[[FiftyOneConfig | None], Publisher]) -> None:
        self.create = create

    def __call__(self, config: FiftyOneConfig | None) -> Publisher:
        return self.create(config)


@pytest.fixture
def workflow_dependencies() -> WorkflowDependencies:
    dependencies = build_dependencies()
    return replace(dependencies, publisher_factory=PublisherFactory(dependencies.publisher_factory))


# These are adapter capabilities formerly imported into the workflow modules.
_CAPABILITIES = {
    "dataset": {
        "apply_dataset_policy",
        "build_ground_truth",
        "cached_dataset",
        "dataset_cache_root",
    },
    "model": {
        "execution_settings",
        "predict_on_images",
        "prediction_settings",
        "reinfer_split",
        "requested_settings",
        "resolution_of",
        "stage_settings",
        "trained_imgsz",
        "write_native_yaml",
    },
    "repository": {
        "fetch_best_confidences",
        "latest_completed_task_id",
        "read_checkpoint_identity",
        "resolve_task_model",
        "resolve_weights_with_identity",
    },
    "evaluation": {
        "calibrate_thresholds",
        "filter_invalid_prediction_boxes",
        "prepare_ground_truth",
        "prepare_predictions",
        "compute_evaluation",
    },
    "renderer": {
        "annotate_workbook",
        "read_dashboard",
        "workbook_identities",
        "write_comparison_workbook",
    },
    "storage": {
        "model_weights_path",
        "point_latest_at",
        "resolve_run_dir",
        "runs_root",
        "safe_path_component",
        "task_run_dir",
        "write_path",
    },
    "resources": {"training_finished", "log_exception", "track"},
    "tracking": {
        "init_task",
        "record_run_configuration",
        "register_ground_truth",
        "connect_config_file",
        "file_digest",
        "prediction_checkpoint_hash",
        "prediction_model_identity",
        "publish_evaluation",
        "register_predictions",
        "write_prediction_provenance",
        "report_table",
        "report_scalars",
        "report_comparison",
        "expect_artifacts",
        "upload_artifact",
        "publish_table",
        "task_identity",
        "associate_calibration_thresholds",
    },
}

_UNSET = object()


def patch_workflow(
    monkeypatch: pytest.MonkeyPatch,
    dependencies: WorkflowDependencies,
    target: object,
    name: Any,
    value: Any = _UNSET,
    *,
    raising: bool = True,
) -> None:
    """Patch an explicit port when an old test names an application-imported adapter."""
    module_name = target.__name__ if isinstance(target, ModuleType) else ""
    selected_name = name
    selected_value = value
    if isinstance(target, str):
        module_name, _, selected_name = target.rpartition(".")
        selected_value = name
    if module_name.startswith("clearml_yolo.application.use_cases."):
        if selected_name == "create_publisher":
            monkeypatch.setattr(dependencies.publisher_factory, "create", selected_value)
            return
        if selected_name == "owned_native_model":
            monkeypatch.setattr(
                dependencies.tracking,
                "has_owned_native_model",
                lambda task: selected_value(task) is not None,
            )
            return
        for group, methods in _CAPABILITIES.items():
            if selected_name in methods:
                monkeypatch.setattr(
                    getattr(dependencies, group), selected_name, selected_value, raising=raising
                )
                if module_name.endswith(".train") and selected_name == "record_run_configuration":
                    monkeypatch.setattr(
                        "clearml_yolo.adapters.integrations.training.record_run_configuration",
                        selected_value,
                    )
                return
        concrete = {
            "native_ddp_relay": "clearml_yolo.adapters.integrations.training.native_ddp_relay",
            "finalize_native_model": (
                "clearml_yolo.adapters.integrations.training.finalize_native_model"
            ),
        }
        if selected_name in concrete:
            monkeypatch.setattr(concrete[selected_name], selected_value, raising=raising)
            return
    if isinstance(target, str):
        monkeypatch.setattr(target, name, raising=raising)
    else:
        monkeypatch.setattr(target, name, value, raising=raising)
