"""Publish one verified native detector checkpoint through the invocation owner.

ClearML SDK objects are opaque inside this component. The public boundary accepts
only the task handle and the checkpoint's validated portable descriptor.
"""

import json
from pathlib import Path
from typing import Any

import yaml

from clearml_yolo.adapters.clearml.naming import resolve_model_name
from clearml_yolo.adapters.clearml.native import (
    NativeModelError,
    OwnedNativeModel,
    _deduplicated,
    _download_hash,
    _output_models,
    _package_version,
    _register_owned_model,
    _sha256,
    _validate_association,
    _verify_model,
    owned_native_model,
)
from clearml_yolo.adapters.clearml.session import register_model_barrier
from clearml_yolo.adapters.observability.capture import append_scalar
from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.storage.identity import write_checkpoint_identity
from clearml_yolo.application.ports import TaskHandle
from clearml_yolo.core.identity import ModelIdentity
from clearml_yolo.core.models import CheckpointDescriptor
from clearml_yolo.core.redaction import sanitize_configuration


@trace_operation("clearml.detector.arguments")
def record_detector_arguments(task: TaskHandle, values: dict[str, Any]) -> None:
    """Record observed native arguments without changing executable replay inputs."""
    # The SDK may mutate its connected dictionary; sanitize into a separate tree.
    owner: Any = task
    owner.connect(
        sanitize_configuration(values),
        name="General",
        ignore_remote_overrides=True,
    )


def report_metric(task: TaskHandle, name: str, value: float, step: int) -> None:
    """Forward native scalar callbacks to the single invocation-owned logger."""
    if append_scalar("Native training", name, value, step):
        return
    owner: Any = task
    owner.get_logger().report_scalar(
        title="Native training",
        series=name,
        value=value,
        iteration=step,
    )


def _metadata(
    task: Any,
    weights: Path,
    descriptor: CheckpointDescriptor,
    requested: str,
    effective: str,
) -> dict[str, dict[str, str]]:
    values = {
        "clearml_yolo_checkpoint_role": "best",
        "clearml_yolo_checkpoint_filename": weights.name,
        "clearml_yolo_checkpoint_sha256": descriptor.checkpoint_sha256,
        "clearml_yolo_training_task_id": str(task.id),
        "clearml_yolo_architecture_reference": f"{descriptor.backend}/{descriptor.preset}",
        "clearml_yolo_backend": descriptor.backend,
        "clearml_yolo_preset": descriptor.preset,
        "clearml_yolo_checkpoint_descriptor": descriptor.model_dump_json(),
        "clearml_yolo_input_imgsz": json.dumps(descriptor.preprocessing.size),
        "clearml_yolo_input_channels": "3",
        "clearml_yolo_requested_model_name": requested,
        "clearml_yolo_effective_model_name": effective,
        "clearml_yolo_version": _package_version("clearml-yolo"),
        "clearml_version": _package_version("clearml"),
        "torch_version": descriptor.dependencies.get("torch"),
    }
    return {
        key: {"value": value, "type": "str"} for key, value in values.items() if value is not None
    }


def _validate_publication(
    owner: Any,
    weights: Path,
    descriptor: CheckpointDescriptor,
    requested_name: str,
) -> None:
    if owner is None:
        raise NativeModelError("Detector publication requires an invocation-owned task")
    if not weights.is_file() or weights.stat().st_size == 0:
        raise FileNotFoundError(f"Training finished without nonempty checkpoint {weights}")
    if _sha256(weights) != descriptor.checkpoint_sha256:
        raise NativeModelError("Local detector checkpoint does not match its descriptor hash")
    if owned_native_model(owner) is not None or _output_models(owner):
        raise NativeModelError("Detector publication requires no existing output model")
    if not requested_name:
        raise NativeModelError("Detector publication requires an effective training name")


@trace_operation("clearml.detector.publish")
def publish_detector_model(
    task: TaskHandle,
    weights: Path,
    descriptor: CheckpointDescriptor,
    requested_name: str,
) -> str:
    """Create, upload, read back and register exactly one native detector model."""
    owner: Any = task
    weights = weights.resolve()
    _validate_publication(owner, weights, descriptor, requested_name)

    from clearml import OutputModel
    from clearml.model import Framework

    design = yaml.safe_dump(descriptor.model_dump(mode="json"), sort_keys=False)
    labels = {name: index for index, name in enumerate(descriptor.class_names)}
    tags = _deduplicated([*[str(tag) for tag in owner.get_tags()], "best"])
    comment = f"Best checkpoint {weights.name} produced by task {owner.id}."
    writable: Any = OutputModel(
        task=owner,
        name=requested_name,
        config_text=design,
        label_enumeration=labels,
        tags=tags,
        comment=comment,
        framework=Framework.pytorch,
    )
    writable.update_weights(
        weights_filename=str(weights),
        target_filename=weights.name,
        auto_delete_file=False,
        update_comment=False,
    )
    OutputModel.wait_for_uploads()
    if owner.flush(wait_for_uploads=True) is not True:
        raise NativeModelError("ClearML flush did not confirm detector checkpoint upload")
    owner.reload()
    model_id = str(writable.id)
    expected_outputs = {model_id}
    outputs = _output_models(owner)
    if not model_id or set(outputs) != expected_outputs:
        raise NativeModelError("Detector publication did not register exactly one output model")
    native = outputs[model_id]
    expected_url = _validate_association(owner, native)
    if _download_hash(native) != descriptor.checkpoint_sha256:
        raise NativeModelError("Downloaded detector checkpoint does not match local checkpoint")

    def write_name(name: str) -> None:
        writable.name = name

    name = resolve_model_name(owner, requested_name, model_id=model_id, write_model_name=write_name)
    writable.comment = comment
    metadata = _metadata(owner, weights, descriptor, requested_name, name)
    if writable.set_all_metadata(metadata, replace=False) is not True:
        raise NativeModelError("ClearML rejected detector output model metadata")
    owner.reload()

    def verify() -> None:
        _verify_model(
            owner,
            model_id,
            expected_outputs=expected_outputs,
            expected_url=expected_url,
            checkpoint_hash=descriptor.checkpoint_sha256,
            name=name,
            design=design,
            labels=labels,
            tags=tags,
            comment=comment,
            metadata=metadata,
        )

    verify()
    identity = ModelIdentity(
        model_name=name,
        training_task_id=str(owner.id),
        checkpoint_sha256=descriptor.checkpoint_sha256,
        model_id=model_id,
    )
    write_checkpoint_identity(weights, identity)
    _register_owned_model(
        owner,
        OwnedNativeModel(
            model_id,
            descriptor.checkpoint_sha256,
            expected_url,
            writable,
            metadata,
            verify,
            identity,
        ),
    )
    register_model_barrier(owner, verify)
    return model_id
