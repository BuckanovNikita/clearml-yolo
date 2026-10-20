"""Pure opt-in projection for ClearML's controller-side task hashing callback.

The returned document is only cache identity, never executable configuration. Importing
this module does not register a callback or import the ClearML SDK. Controllers that
already have a callback must explicitly compose it with ``normalize_task_hash``.
"""

import json
import math
import re
from copy import deepcopy
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Literal, override

import yaml
from yaml.nodes import MappingNode

from clearml_yolo.adapters.clearml.parameters import NATIVE_EXECUTION_KEYS

_POLICY_KEY = "_clearml_yolo_cache_policy"
_POLICY_VERSION = 1
_MAX_DOCUMENT_DEPTH = 80
_DATASET_PREFIX = "clearml-yolo-dataset://"
_COMMANDS = frozenset(
    {
        "train",
        "pipeline",
        "predict",
        "val",
        "metrics",
        "compare",
        "report",
        "export",
        "ground_truth",
    }
)
_NATIVE_ROUTING = NATIVE_EXECUTION_KEYS - {"device", "data"}
_RUN_ROUTING = frozenset(
    {
        "run_id",
        "run_dir",
        "output",
        "output_dir",
        "dataset_cache_dir",
        "model_label",
        "baseline_label",
        "candidate_label",
        "display_names",
    }
)
_PIPELINE_SKIP_FLAGS = frozenset(
    {"skip_train", "skip_predict", "skip_metrics", "skip_compare", "skip_report"}
)
_TRACKING_ROUTING = frozenset({"project_name", "task_name", "tags", "output_uri"})
_PUBLICATION_RECEIPT = frozenset(
    {"dataset_name", "run_key", "dataset_reused", "sample_count", "fields", "evaluation_keys"}
)
_DeviceConsumer = Literal["native", "typed_native", "single", "cpu", "gpu"]


class _UnsafeProjectionError(ValueError):
    """Parsing or raw markers could make distinct executable inputs collide."""


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate configuration key")
        result[key] = value
    return result


class _UniqueSafeLoader(yaml.SafeLoader):
    @override
    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[Any, Any]:
        keys: set[str | int] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if type(key) not in {str, int} or key in keys:
                raise ValueError("Unsupported or duplicate configuration key")
            keys.add(key)
        return super().construct_mapping(node, deep=deep)


def _supported_tree(value: Any, ancestors: frozenset[int] = frozenset()) -> bool:
    if value is None or type(value) in {str, bool, int}:
        return True
    if type(value) is float:
        return math.isfinite(value)
    if (
        not isinstance(value, (dict, list))
        or id(value) in ancestors
        or len(ancestors) > _MAX_DOCUMENT_DEPTH
    ):
        return False
    parents = ancestors | {id(value)}
    if isinstance(value, list):
        return all(_supported_tree(item, parents) for item in value)
    return all(
        type(key) in {str, int} and _supported_tree(item, parents) for key, item in value.items()
    )


def _document(value: Any, *, dataset: bool = False) -> dict[str, Any] | None:
    # Unsupported documents retain their bytes. In particular, legacy HOCON must
    # not be interpreted by YAML, whose scalar and assignment semantics differ.
    if not isinstance(value, str):
        return None
    try:
        parsed = (
            yaml.load(value, Loader=_UniqueSafeLoader)  # noqa: S506 - strict SafeLoader subclass
            if dataset
            else json.loads(value, object_pairs_hook=_unique_pairs)
        )
    except (ValueError, yaml.YAMLError, RecursionError):
        return None
    if (
        not isinstance(parsed, dict)
        or any(not isinstance(key, str) for key in parsed)
        or not _supported_tree(parsed)
    ):
        return None
    if not dataset and _ambiguous_json_escape(value):
        raise _UnsafeProjectionError("The SDK and JSON parser disagree on string escapes")
    return parsed


def _ambiguous_json_escape(document: str) -> bool:
    # The SDK's vendored HOCON reader leaves these JSON escapes literal. Scan
    # active escapes only: a doubled backslash before `u` is an ordinary string.
    inside_string = False
    index = 0
    while index < len(document):
        character = document[index]
        if character == '"':
            inside_string = not inside_string
        elif character == "\\" and inside_string:
            index += 1
            if index < len(document) and document[index] in "u/bf":
                return True
        index += 1
    return False


def _device(value: Any, consumer: _DeviceConsumer = "single") -> Any:
    if isinstance(value, dict):
        raise _UnsafeProjectionError("Device dictionaries are not executable selectors")
    requested = value
    native = consumer in {"native", "typed_native"}
    if isinstance(value, str):
        if (value == "cpu" and consumer != "gpu") or (value == "mps" and native):
            return {"type": value}
        value = _selector_parts(value) if native else [value]
    if consumer == "cpu":
        return requested
    if type(value) is int:
        value = [value]
    if not isinstance(value, list) or not value or (not native and len(value) != 1):
        return requested
    if (
        isinstance(requested, list)
        and consumer != "native"
        and any(type(item) is not int for item in requested)
    ):
        return requested
    ordinals = [_ordinal(item, native=native) for item in value]
    if None in ordinals or len(set(ordinals)) != len(ordinals):
        return requested
    return {"type": "cuda", "count": len(ordinals)}


def _selector_parts(value: str) -> list[str]:
    # Ultralytics removes ASCII spaces and numeric-list brackets, but does not
    # decode JSON string elements or strip tabs/newlines.
    value = value.replace(" ", "")
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return value.split(",")


def _ordinal(value: Any, *, native: bool) -> int | None:
    # Leading-zero strings are accepted by YOLO, but rejected by torch.device
    # in Faster R-CNN. Unknown/mixed backends use only their common safe subset.
    pattern = r"(?:cuda:)?[0-9]+" if native else r"(?:cuda:)?(?:0|[1-9][0-9]*)"
    if isinstance(value, str) and re.fullmatch(pattern, value):
        try:
            value = int(value.removeprefix("cuda:"))
        except ValueError:
            return None
    return value if type(value) is int and value >= 0 else None


def _dataset_binding(run: dict[str, Any] | None) -> tuple[str, str] | None:
    record = run.get("prepared_dataset") if run is not None else None
    if not isinstance(record, dict):
        return None
    root, identity = record.get("root"), record.get("cache_identity")
    if isinstance(root, str) and root.startswith(_DATASET_PREFIX):
        raise _UnsafeProjectionError("Prepared dataset roots must not contain cache markers")
    if not isinstance(root, str) or not isinstance(identity, str):
        return None
    if not re.fullmatch(r"[0-9a-f]{64}", identity):
        return None
    path = PureWindowsPath(root) if PureWindowsPath(root).drive else PurePosixPath(root)
    if not path.is_absolute() or ".." in path.parts or path == path.parent:
        return None
    return root, identity


def _dataset_path(value: Any, binding: tuple[str, str] | None) -> Any:
    if isinstance(value, str) and value.startswith(_DATASET_PREFIX):
        raise _UnsafeProjectionError("Input paths must not contain generated cache markers")
    if not isinstance(value, str) or binding is None:
        return value
    root, identity = binding
    path_type = PureWindowsPath if PureWindowsPath(root).drive else PurePosixPath
    path, parent = path_type(value), path_type(root)
    if not path.is_absolute() or ".." in path.parts or not path.is_relative_to(parent):
        return value
    relative = path.relative_to(parent).as_posix()
    return f"{_DATASET_PREFIX}{identity}/{relative}"


def _native(
    values: Any, binding: tuple[str, str] | None, consumer: _DeviceConsumer = "single"
) -> None:
    if not isinstance(values, dict):
        return
    for key in _NATIVE_ROUTING:
        values.pop(key, None)
    if "device" in values:
        values["device"] = _device(values["device"], consumer)
    if "data" in values:
        values["data"] = _dataset_path(values["data"], binding)


def _reference_uses_project(reference: Any) -> bool:
    if not isinstance(reference, dict):
        # Missing selectors use the default promoted-model search.
        return True
    if reference.get("source", "clearml") == "local":
        return False
    return not reference.get("task_id") and not reference.get("project_name")


def _project_is_input(run: dict[str, Any], command: str) -> bool:
    if command == "compare":
        return any(
            _reference_uses_project(run.get(key)) for key in ("baseline_model", "candidate_model")
        )
    if command == "pipeline" and run.get("skip_compare") is not True:
        comparison = run.get("compare")
        return not isinstance(comparison, dict) or _reference_uses_project(
            comparison.get("baseline_model")
        )
    return False


def _remove_routing(run: dict[str, Any], command: str) -> None:
    routing = _RUN_ROUTING
    if command == "pipeline" and any(run.get(key) for key in _PIPELINE_SKIP_FLAGS):
        # Skipping producers makes existing files beneath this destination inputs.
        routing = routing - {"run_dir", "run_id"}
    for key in routing:
        run.pop(key, None)
    tracking = run.get("clearml")
    if isinstance(tracking, dict):
        fields = _TRACKING_ROUTING
        if _project_is_input(run, command):
            fields = fields - {"project_name"}
        for key in fields:
            tracking.pop(key, None)


def _run_consumer(run: dict[str, Any] | None, command: str) -> _DeviceConsumer:
    # Comparison checkpoints can carry a different backend from model.backend.
    if run is None or command == "compare":
        return "single"
    model = run.get("model", {})
    if isinstance(model, dict) and model.get("backend", "ultralytics") == "ultralytics":
        return "native"
    return "single"


def _run_document(run: dict[str, Any], binding: tuple[str, str] | None, command: str) -> None:
    consumer = _run_consumer(run, command)
    _remove_routing(run, command)
    for key in ("ultralytics", "ultralytics_predict"):
        _native(run.get(key), binding, consumer)
    _run_provenance(run, binding)
    model = run.get("model")
    if isinstance(model, dict):
        for key in ("train", "predict"):
            _device_field(model.get(key), "typed_native" if consumer == "native" else consumer)
    _inference(run.get("inference"), binding)
    for key in ("compare", "comparison"):
        comparison = run.get(key)
        if isinstance(comparison, dict):
            _inference(comparison.get("inference"), binding)
    export = run.get("export")
    if isinstance(export, dict):
        _device_field(export, "gpu" if export.get("operation") in ("build", "verify") else "cpu")
    _normalization(run.get("training_normalization"), binding, consumer)
    prediction = run.get("prediction_result")
    if isinstance(prediction, dict):
        _normalization(prediction.get("native_normalization"), binding, consumer)


def _run_provenance(run: dict[str, Any], binding: tuple[str, str] | None) -> None:
    prepared = run.get("prepared_dataset")
    if isinstance(prepared, dict) and binding is not None:
        prepared["root"] = _dataset_path(prepared["root"], binding)
    training = run.get("training_data_overrides")
    if isinstance(training, dict) and isinstance(training.get("data"), dict):
        for key in ("requested", "effective"):
            if key in training["data"]:
                training["data"][key] = _dataset_path(training["data"][key], binding)
    receipt = run.get("fiftyone_result")
    if isinstance(receipt, dict):
        for key in _PUBLICATION_RECEIPT:
            receipt.pop(key, None)
        if not receipt:
            run.pop("fiftyone_result")


def _inference(values: Any, binding: tuple[str, str] | None) -> None:
    if isinstance(values, dict):
        _device_field(values)
        _native(values.get("ultralytics"), binding)


def _device_field(values: Any, consumer: _DeviceConsumer = "single") -> None:
    if isinstance(values, dict) and "device" in values:
        values["device"] = _device(values["device"], consumer)


def _normalization(values: Any, binding: tuple[str, str] | None, consumer: _DeviceConsumer) -> None:
    if not isinstance(values, dict):
        return
    for key in _NATIVE_ROUTING:
        values.pop(key, None)
    for key in ("device", "data"):
        change = values.get(key)
        if isinstance(change, dict):
            for side in ("requested", "effective"):
                if side in change:
                    change[side] = (
                        _device(change[side], consumer)
                        if key == "device"
                        else _dataset_path(change[side], binding)
                    )


def _hyperparameters(
    values: Any, binding: tuple[str, str] | None, consumer: _DeviceConsumer
) -> None:
    if not isinstance(values, dict):
        return
    for key in _NATIVE_ROUTING:
        values.pop(f"General/{key}", None)
    if "General/device" in values:
        values["General/device"] = _device(values["General/device"], consumer)
    if "General/data" in values:
        values["General/data"] = _dataset_path(values["General/data"], binding)


def _ordered_tree(value: Any) -> Any:
    if isinstance(value, dict):
        # YAML class IDs may be integers. Preserve their types without conflating
        # class 0 with an unknown literal string key "0" during JSON conversion.
        keys = sorted(value, key=lambda key: (type(key).__name__, str(key)))
        return {key: _ordered_tree(value[key]) for key in keys}
    if isinstance(value, list):
        return [_ordered_tree(item) for item in value]
    return value


def _dataset_document(document: dict[str, Any], binding: tuple[str, str]) -> str:
    for key in ("path", "train", "val", "test"):
        value = document.get(key)
        if isinstance(value, list):
            document[key] = [_dataset_path(item, binding) for item in value]
        elif key in document:
            document[key] = _dataset_path(value, binding)
    return yaml.safe_dump(_ordered_tree(document), sort_keys=False, allow_unicode=True)


def normalize_task_hash(representation: dict[str, Any]) -> dict[str, Any]:
    """Detach and normalize a recognized task's cache identity, retaining unknown data.

    Register this explicitly with ``ClearmlJob.register_hashing_callback`` in the
    controller before cache lookup. Canonical ``run`` documents use JSON; legacy
    HOCON, malformed documents and unproven input paths remain cache-sensitive.
    """
    result = deepcopy(representation)
    script = result.get("script")
    if not isinstance(script, dict):
        return result
    entrypoint = script.get("entry_point")
    if not isinstance(entrypoint, str) or entrypoint not in {
        f"-m clearml_yolo.entrypoints.{command}" for command in _COMMANDS
    }:
        return result
    configs = result.get("configs")
    if isinstance(configs, dict):
        # This view never controls execution, even when opaque/unsafe executable
        # inputs require the conservative projection fallback below.
        configs.pop("run_overrides", None)
    # Projected identities are terminal values. Never reinterpret their markers
    # as executable selectors, and preserve any caller-owned version-key collision.
    if _POLICY_KEY in result:
        return result
    unprojected = deepcopy(result)
    try:
        command = entrypoint.rpartition(".")[2]
        run = _document(configs.get("run")) if isinstance(configs, dict) else None
        binding = _dataset_binding(run)
        consumer = _run_consumer(run, command)
        if run is not None and isinstance(configs, dict):
            _run_document(run, binding, command)
            configs["run"] = json.dumps(
                run, sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=False
            )
        if isinstance(configs, dict) and binding is not None:
            dataset = _document(configs.get("dataset"), dataset=True)
            if dataset is not None:
                configs["dataset"] = _dataset_document(dataset, binding)
        _hyperparameters(result.get("hyper_params"), binding, consumer)
    except _UnsafeProjectionError:
        # Reject the entire projection: partial edits could conflate executable
        # inputs whose raw markers or SDK parsing differ from normalized values.
        return unprojected
    result[_POLICY_KEY] = _POLICY_VERSION
    return result
