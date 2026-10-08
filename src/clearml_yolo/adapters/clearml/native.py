"""Verify and enrich the one model registered by Ultralytics' ClearML callback."""

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import yaml

from clearml_yolo.adapters.clearml.naming import resolve_model_name
from clearml_yolo.adapters.clearml.session import (
    ArtifactUploadError,
    invocation_resource,
    register_model_barrier,
    sanitize_configuration,
)
from clearml_yolo.adapters.storage.identity import write_checkpoint_identity
from clearml_yolo.core.identity import ModelIdentity


class NativeModelError(ArtifactUploadError):
    """Native best-model registration, upload, or metadata verification failed."""


@dataclass
class OwnedNativeModel:
    """Only a verified native model created by this invocation can be enriched."""

    model_id: str
    checkpoint_sha256: str
    checkpoint_url: str
    writable: Any
    expected_metadata: dict[str, dict[str, str]]
    verify: Callable[[], None]
    identity: ModelIdentity


@dataclass
class _OwnedModelState:
    model: OwnedNativeModel | None = None


def owned_native_model(task: Any) -> OwnedNativeModel | None:
    """Return this invocation's verified best model; never recover or create a model."""
    state = invocation_resource(task, "clearml_native_owned_model", _OwnedModelState)
    return state.model


def _register_owned_model(task: Any, model: OwnedNativeModel) -> None:
    state = invocation_resource(task, "clearml_native_owned_model", _OwnedModelState)
    if state.model is not None and state.model.model_id != model.model_id:
        raise NativeModelError("Invocation already owns a different native best model")
    state.model = model


def _package_version(distribution: str) -> str | None:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata_value(model: Any, key: str) -> str | None:
    metadata = model.get_all_metadata()
    item = metadata.get(key) if isinstance(metadata, dict) else None
    if not isinstance(item, dict):
        return None
    value = item.get("value")
    return str(value) if value is not None else None


def _output_models(task: Any) -> dict[str, Any]:
    models = task.get_models()
    output = models.get("output", ()) if isinstance(models, Mapping) else ()
    unique: dict[str, Any] = {}
    for model in output:
        model_id = str(model.id)
        if model_id:
            unique[model_id] = model
    return unique


def _best_output(task: Any) -> tuple[Any, set[str]]:
    outputs = _output_models(task)
    if len(outputs) != 1:
        raise NativeModelError(
            f"Native training must register exactly one unique output model; found {len(outputs)}"
        )
    candidates = []
    for model in outputs.values():
        basename = Path(unquote(urlsplit(str(model.url)).path)).name
        explicit_best = _metadata_value(model, "clearml_yolo_checkpoint_role") == "best"
        if explicit_best or basename == "best.pt":
            candidates.append(model)
    if len(candidates) != 1:
        raise NativeModelError("Native output model does not identify one best.pt checkpoint")
    return candidates[0], set(outputs)


def _validate_association(task: Any, native: Any) -> str:
    model_id = str(native.id)
    if not model_id:
        raise NativeModelError("Native output model has no ID")
    if str(native.original_task) != str(task.id) or str(native.task) != str(task.id):
        raise NativeModelError("Native output model is not associated with the training task")
    if str(native.project) != str(task.project):
        raise NativeModelError("Native output model is not associated with the training project")
    url = str(native.url or "")
    basename = Path(unquote(urlsplit(url).path)).name
    if not url or basename in {"uploading_file", "failed_uploading"}:
        raise NativeModelError("Native best-model upload did not produce a valid URL")
    return url


def _download_hash(native: Any) -> str:
    local = native.get_local_copy(
        extract_archive=False,
        raise_on_error=True,
        force_download=True,
    )
    path = Path(str(local))
    if not path.is_file() or path.stat().st_size == 0:
        raise NativeModelError("Native best model did not download to a nonempty file")
    return _sha256(path)


def _label_enumeration(model: Any) -> dict[str, int]:
    names = model.names
    if isinstance(names, dict):
        source = [(str(label), int(index)) for index, label in names.items()]
    elif isinstance(names, (list, tuple)):
        source = [(str(label), index) for index, label in enumerate(names)]
    else:
        raise NativeModelError("Trained model does not expose label names")
    labels = dict(source)
    if not labels or len(labels) != len(source) or any(not label for label in labels):
        raise NativeModelError("Trained model labels must be unique and nonempty")
    return labels


def _design_text(model: Any) -> tuple[str, int | None]:
    definition = getattr(getattr(model, "model", None), "yaml", None)
    if not isinstance(definition, dict) or not definition:
        raise NativeModelError("Trained model does not expose a nonempty architecture design")
    channels = definition.get("channels", definition.get("ch"))
    known_channels = channels if isinstance(channels, int) and channels > 0 else None
    sanitized = sanitize_configuration(definition)
    return yaml.safe_dump(sanitized, sort_keys=False, allow_unicode=True), known_channels


def _deduplicated(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _metadata(
    task: Any,
    checkpoint: Path,
    checkpoint_hash: str,
    architecture: Any,
    trainer: Any,
    channels: int | None,
) -> dict[str, dict[str, str]]:
    values = {
        "clearml_yolo_checkpoint_role": "best",
        "clearml_yolo_checkpoint_filename": checkpoint.name,
        "clearml_yolo_checkpoint_sha256": checkpoint_hash,
        "clearml_yolo_training_task_id": str(task.id),
        "clearml_yolo_architecture_reference": str(sanitize_configuration(str(architecture))),
        "clearml_yolo_version": _package_version("clearml-yolo"),
        "clearml_version": _package_version("clearml"),
        "ultralytics_version": _package_version("ultralytics"),
        "torch_version": _package_version("torch"),
    }
    imgsz = getattr(trainer.args, "imgsz", None)
    if imgsz is not None:
        values["clearml_yolo_input_imgsz"] = (
            json.dumps(imgsz, separators=(",", ":"))
            if isinstance(imgsz, (list, tuple, dict))
            else str(imgsz)
        )
    if channels is not None:
        values["clearml_yolo_input_channels"] = str(channels)
    task_inputs = task.input_models_id or ()
    input_values = task_inputs.values() if isinstance(task_inputs, Mapping) else task_inputs
    input_ids = _deduplicated([str(value) for value in input_values])
    if len(input_ids) == 1:
        values["clearml_yolo_input_model_id"] = input_ids[0]
    return {
        key: {"value": value, "type": "str"} for key, value in values.items() if value is not None
    }


def _verify_model(
    task: Any,
    model_id: str,
    expected_outputs: set[str],
    expected_url: str,
    checkpoint_hash: str,
    name: str,
    design: str,
    labels: dict[str, int],
    tags: list[str],
    comment: str,
    metadata: dict[str, dict[str, str]],
) -> None:
    from clearml import Model
    from clearml.model import Framework

    outputs = _output_models(task)
    if set(outputs) != expected_outputs:
        raise NativeModelError("Native output model set changed during metadata enrichment")
    fresh = Model(model_id=model_id)
    if str(fresh.id) != model_id:
        raise NativeModelError("Fresh model lookup returned a different model ID")
    if _validate_association(task, fresh) != expected_url:
        raise NativeModelError("Native output model URL changed during metadata enrichment")
    if _download_hash(fresh) != checkpoint_hash:
        raise NativeModelError("Downloaded native best model does not match local trainer.best")
    fields = {
        "name": (fresh.name, name),
        "comment": (fresh.comment, comment),
        "framework": (fresh.framework, Framework.pytorch),
        "config_text": (fresh.config_text, design),
        "labels": (fresh.labels, labels),
        "tags": (set(fresh.tags), set(tags)),
    }
    mismatched = [field for field, (actual, expected) in fields.items() if actual != expected]
    if mismatched:
        raise NativeModelError(
            "Native output model metadata fields failed verification: " + ", ".join(mismatched)
        )
    _verify_custom_metadata(fresh, metadata)


def _verify_custom_metadata(model: Any, metadata: dict[str, dict[str, str]]) -> None:
    stored_metadata = model.get_all_metadata()
    if not isinstance(stored_metadata, Mapping):
        raise NativeModelError("Native output model custom metadata failed verification")
    if any(
        stored_metadata.get(key, {}).get(field) != expected
        for key, value in metadata.items()
        for field, expected in value.items()
    ):
        raise NativeModelError("Native output model custom metadata failed verification")


def _name_native_model(
    task: Any,
    model_id: str,
    requested_name: str,
    design: str,
    labels: dict[str, int],
    tags: list[str],
    comment: str,
) -> tuple[Any, str]:
    from clearml import OutputModel
    from clearml.model import Framework

    writable: Any = None

    def write_name(name: str) -> None:
        nonlocal writable
        if writable is None:
            writable = OutputModel(
                task=task,
                base_model_id=model_id,
                name=name,
                config_text=design,
                label_enumeration=labels,
                tags=tags,
                comment=comment,
                framework=Framework.pytorch,
            )
        else:
            writable.name = name
        if str(writable.id) != model_id:
            raise NativeModelError("ClearML did not reopen the native output model for enrichment")

    name = resolve_model_name(task, requested_name, model_id=model_id, write_model_name=write_name)
    return writable, name


def finalize_native_model(task: Any, model: Any, trainer: Any, architecture: Any) -> str:
    """Enrich Ultralytics' native best record and register its completion barrier."""
    if task is None:
        raise NativeModelError("Native model finalization requires the invocation-owned task")
    checkpoint = Path(trainer.best)
    if not checkpoint.is_file() or checkpoint.stat().st_size == 0:
        raise FileNotFoundError(f"Training finished without nonempty best checkpoint {checkpoint}")

    from clearml import OutputModel

    OutputModel.wait_for_uploads()
    if task.flush(wait_for_uploads=True) is not True:
        raise NativeModelError("ClearML flush did not confirm native best-model upload")
    task.reload()
    native, expected_outputs = _best_output(task)
    expected_url = _validate_association(task, native)
    checkpoint_hash = _sha256(checkpoint)
    if _download_hash(native) != checkpoint_hash:
        raise NativeModelError("Downloaded native best model does not match local trainer.best")

    labels = _label_enumeration(model)
    design, channels = _design_text(model)
    requested_name = str(trainer.args.name)
    if not requested_name:
        raise NativeModelError("Native best model requires the effective training name")
    model_id = str(native.id)
    tags = _deduplicated([*[str(tag) for tag in task.get_tags()], "best"])
    comment = f"Best checkpoint {checkpoint.name} produced by task {task.id}."
    writable, name = _name_native_model(
        task, model_id, requested_name, design, labels, tags, comment
    )
    metadata = _metadata(task, checkpoint, checkpoint_hash, architecture, trainer, channels)
    metadata.update(
        clearml_yolo_requested_model_name={"value": requested_name, "type": "str"},
        clearml_yolo_effective_model_name={"value": name, "type": "str"},
    )
    writable.comment = comment
    if writable.set_all_metadata(metadata, replace=False) is not True:
        raise NativeModelError("ClearML rejected native output model metadata")
    task.reload()
    if set(_output_models(task)) != expected_outputs:
        raise NativeModelError("Native output model set changed during metadata enrichment")

    def verify() -> None:
        _verify_model(
            task,
            model_id,
            expected_outputs,
            expected_url,
            checkpoint_hash,
            name,
            design,
            labels,
            tags,
            comment,
            metadata,
        )

    verify()
    identity = ModelIdentity(
        model_name=name,
        training_task_id=str(task.id),
        checkpoint_sha256=checkpoint_hash,
        model_id=model_id,
    )
    write_checkpoint_identity(checkpoint, identity)
    _register_owned_model(
        task,
        OwnedNativeModel(
            model_id,
            checkpoint_hash,
            expected_url,
            writable,
            metadata,
            verify,
            identity,
        ),
    )
    register_model_barrier(task, verify)
    return model_id


def _calibration_metadata(
    thresholds: Mapping[str, float], checkpoint_sha256: str
) -> dict[str, dict[str, str]]:
    if not thresholds:
        raise NativeModelError("Calibration requires nonempty confidence thresholds")
    values: dict[str, float] = {}
    for name, raw_value in thresholds.items():
        if not name.strip():
            raise NativeModelError("Calibration thresholds require nonempty string class names")
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            raise NativeModelError("Calibration thresholds must be numeric values")
        value = float(raw_value)
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise NativeModelError("Calibration thresholds must be finite values in [0, 1]")
        values[name] = value
    metadata = {
        "clearml_yolo_confidence_thresholds": {
            "value": json.dumps(values, ensure_ascii=False, sort_keys=True, allow_nan=False),
            "type": "str",
        },
        "clearml_yolo_calibration_split": {"value": "val", "type": "str"},
        "clearml_yolo_calibration_checkpoint_sha256": {"value": checkpoint_sha256, "type": "str"},
    }
    metadata.update(
        {
            f"clearml_yolo_confidence_threshold/{name}": {"value": repr(value), "type": "float"}
            for name, value in values.items()
        }
    )
    return metadata


def associate_calibration_thresholds(
    task: Any,
    thresholds: Mapping[str, float],
    *,
    prediction_checkpoint_sha256: str | None,
    split: str = "val",
) -> None:
    """Attach thresholds only when verified prediction provenance matches owned best bytes.

    The caller must obtain the hash from the prediction checkpoint provenance, rather
    than calculating it from a supplied path during calibration. Standalone metrics
    has no owned handle and must not call this hook.
    """
    owned = owned_native_model(task)
    if owned is None:
        raise NativeModelError("Calibration metadata requires an invocation-owned native model")
    if split != "val":
        raise NativeModelError("Owned model thresholds must be calibrated on val")
    if not prediction_checkpoint_sha256:
        raise NativeModelError("Calibration prediction checkpoint provenance is missing")
    if prediction_checkpoint_sha256 != owned.checkpoint_sha256:
        raise NativeModelError(
            "Calibration prediction checkpoint does not match the owned best model"
        )
    metadata = _calibration_metadata(thresholds, prediction_checkpoint_sha256)
    owned.verify()
    if owned.writable.set_all_metadata(metadata, replace=False) is not True:
        raise NativeModelError("ClearML rejected native output model calibration metadata")

    from clearml import Model

    fresh = Model(model_id=owned.model_id)
    if str(fresh.id) != owned.model_id:
        raise NativeModelError("Calibration readback returned a different native model ID")
    if _validate_association(task, fresh) != owned.checkpoint_url:
        raise NativeModelError("Native output model URL changed during calibration enrichment")
    if _download_hash(fresh) != owned.checkpoint_sha256:
        raise NativeModelError("Calibration model checkpoint bytes failed verification")
    _verify_custom_metadata(fresh, metadata)
    # The original closure references this dictionary, so the final completion
    # barrier now verifies threshold metadata as well as the native model fields.
    owned.expected_metadata.update(metadata)
    owned.verify()
