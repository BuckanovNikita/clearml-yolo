"""Checked Albumentations construction without arbitrary executable deserialization."""

import importlib
import inspect
import math
import warnings
from dataclasses import dataclass
from typing import Any, cast

from pydantic import JsonValue

_CLASS_KEY = "__class_fullname__"
_BOX_IDS = "_cy_instance_ids"
_CROWD = "_cy_iscrowd"
_FORBIDDEN = frozenset({"Normalize", "ToTensorV2", "ToTensor3D", "ToFloat", "FromFloat", "Lambda"})
_FORMATS = frozenset({"pascal_voc", "coco", "yolo", "albumentations"})
_RGB_CHANNELS = 3
_RESERVED_FIELDS = frozenset(
    {
        "image",
        "images",
        "bboxes",
        "keypoints",
        "mask",
        "masks",
        "volume",
        "volumes",
        "mask3d",
        "masks3d",
        "applied_transforms",
        "replay",
        _BOX_IDS,
        _CROWD,
    }
)


@dataclass(frozen=True)
class CompiledPipeline:
    # Albumentations' heterogeneous callable/registry protocol is opaque at this SDK boundary.
    transform: Any
    label_field: str
    bbox_format: str
    mosaic: Any | None


def _mapping(value: JsonValue, path: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise TypeError(f"{path} must be a JSON object")
    return value


def _supported_class(name: str, registry: dict[str, Any], path: str) -> Any:
    short_name = name.rsplit(".", maxsplit=1)[-1]
    if short_name in _FORBIDDEN:
        raise ValueError(
            f"{path}: {short_name} conflicts with backend preprocessing or executable-code "
            "restrictions; remove it from the training augmentation pipeline"
        )
    if "." in name and not name.startswith("albumentations."):
        raise ValueError(f"{path}: external transform {name!r} is unsupported")
    transform_class = registry.get(short_name)
    if transform_class is None or not transform_class.__module__.startswith("albumentations."):
        raise ValueError(f"{path}: unknown built-in Albumentations transform {name!r}")
    return transform_class


def _parameters(transform_class: Any, values: dict[str, Any], path: str) -> None:
    accepted = set(inspect.signature(transform_class).parameters) - {"self"}
    unknown = set(values) - accepted
    if unknown:
        raise ValueError(f"{path}: unsupported constructor parameters {sorted(unknown)}")
    if "p" in values:
        _number(values["p"], f"{path}.p", maximum=1)


def _number(value: JsonValue, path: str, *, maximum: float = math.inf) -> None:
    # Composition and bbox constructors lack the validation used by basic transforms.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{path} must be a number")
    if not math.isfinite(value) or not 0 <= value <= maximum:
        raise ValueError(f"{path} must be finite and between 0 and {maximum}")


def _box_values(values: dict[str, Any]) -> None:
    for field in ("min_area", "min_width", "min_height", "min_visibility", "max_accept_ratio"):
        if field in values and not (field == "max_accept_ratio" and values[field] is None):
            maximum = 1 if field == "min_visibility" else math.inf
            _number(values[field], f"transform.bbox_params.{field}", maximum=maximum)
    for field in ("check_each_transform", "clip", "filter_invalid_bboxes"):
        if field in values and not isinstance(values[field], bool):
            raise TypeError(f"transform.bbox_params.{field} must be a boolean")


def _check_targets(transform: Any, sdk: Any, path: str) -> None:
    if not isinstance(transform, sdk.BasicTransform):
        return
    try:
        if "image" not in transform.targets:
            raise ValueError(f"{path}: transform requires unsupported non-image targets")
        if (
            isinstance(transform, sdk.DualTransform)
            and type(transform).apply_to_bboxes is sdk.DualTransform.apply_to_bboxes
        ):
            raise ValueError(f"{path}: spatial transform does not support bounding box targets")
    except NotImplementedError as error:
        raise ValueError(f"{path}: abstract transform target methods are unsupported") from error
    required = set(transform.targets_as_params)
    if required - {"image", "bboxes"} and not isinstance(transform, sdk.Mosaic):
        raise ValueError(f"{path}: unsupported additional target requirements {sorted(required)}")


def _construct(node: dict[str, JsonValue], path: str, sdk: Any, registry: dict[str, Any]) -> Any:
    name = node.get(_CLASS_KEY)
    if not isinstance(name, str):
        raise TypeError(f"{path}.{_CLASS_KEY} must identify an Albumentations transform")
    transform_class = _supported_class(name, registry, path)
    values: dict[str, Any] = {key: value for key, value in node.items() if key != _CLASS_KEY}
    if values.get("num_output_channels", _RGB_CHANNELS) != _RGB_CHANNELS:
        raise ValueError(f"{path}.num_output_channels: backend input requires three RGB channels")
    children = values.get("transforms")
    if children is not None:
        if not isinstance(children, list):
            raise TypeError(f"{path}.transforms must be a list")
        values["transforms"] = [
            _construct(
                _mapping(child, f"{path}.transforms[{index}]"),
                f"{path}.transforms[{index}]",
                sdk,
                registry,
            )
            for index, child in enumerate(children)
        ]
    _parameters(transform_class, values, path)
    try:
        with warnings.catch_warnings():
            # Some upstream constructors warn then substitute defaults for invalid values.
            warnings.simplefilter("error", UserWarning)
            result = transform_class(**values)
    except (TypeError, ValueError, UserWarning) as error:
        raise ValueError(f"{path}: {error}") from error
    _check_targets(result, sdk, path)
    return result


def _check_tree(node: dict[str, JsonValue], path: str, *, root: bool = False) -> None:
    name = node.get(_CLASS_KEY)
    if (
        isinstance(name, str)
        and name.rsplit(".", maxsplit=1)[-1] == "Mosaic"
        and path != "transform.transforms[0]"
    ):
        raise ValueError(f"{path}: Mosaic is supported only as the first top-level transform")
    for field in ("additional_targets", "keypoint_params"):
        if node.get(field):
            raise ValueError(
                f"{path}.{field}: only detection images and bounding boxes are supported"
            )
    if not root and node.get("bbox_params"):
        raise ValueError(f"{path}.bbox_params: configure bounding boxes only on the root Compose")
    children = node.get("transforms")
    if isinstance(children, list):
        for index, child in enumerate(children):
            child_path = f"{path}.transforms[{index}]"
            _check_tree(_mapping(child, child_path), child_path)


def _box_configuration(root: dict[str, JsonValue], sdk: Any) -> tuple[Any, str, str]:
    original = root.get("bbox_params")
    values: dict[str, Any] = (
        dict(_mapping(original, "transform.bbox_params")) if original is not None else {}
    )
    values.setdefault("format", "pascal_voc")
    fields = values.get("label_fields")
    if fields is None or fields == []:
        fields = ["class_labels"]
    if (
        not isinstance(fields, list)
        or len(fields) != 1
        or not isinstance(fields[0], str)
        or not fields[0]
        or fields[0] in _RESERVED_FIELDS
    ):
        raise ValueError("transform.bbox_params.label_fields requires one class-label field")
    if not isinstance(values["format"], str) or values["format"] not in _FORMATS:
        raise ValueError("transform.bbox_params.format is unsupported")
    _parameters(sdk.BboxParams, values, "transform.bbox_params")
    _box_values(values)
    values["label_fields"] = [fields[0], _BOX_IDS, _CROWD]
    return sdk.BboxParams(**values), fields[0], values["format"]


def _build_pipeline(document: dict[str, JsonValue], *, seed: int) -> CompiledPipeline:
    unknown = set(document) - {"__version__", "transform"}
    if unknown:
        raise ValueError(f"Pipeline document has unsupported fields: {sorted(unknown)}")
    root = _mapping(document.get("transform"), "transform")
    name = root.get(_CLASS_KEY)
    if not isinstance(name, str) or name.rsplit(".", maxsplit=1)[-1] != "Compose":
        raise ValueError("transform must be a root Albumentations Compose saved with A.save")
    _check_tree(root, "transform", root=True)
    sdk = importlib.import_module("albumentations")
    serialization = importlib.import_module("albumentations.core.serialization")
    # Registry entries are SDK classes, inspected before construction; no user imports execute.
    registry = cast(dict[str, Any], serialization.SERIALIZABLE_REGISTRY)
    _supported_class(name, registry, "transform")
    bbox_params, label_field, bbox_format = _box_configuration(root, sdk)
    values = {key: value for key, value in root.items() if key != _CLASS_KEY}
    children = values.get("transforms")
    if not isinstance(children, list):
        raise TypeError("transform.transforms must be a list")
    constructed = [
        _construct(
            _mapping(child, f"transform.transforms[{index}]"),
            f"transform.transforms[{index}]",
            sdk,
            registry,
        )
        for index, child in enumerate(children)
    ]
    mosaic = constructed[0] if constructed and isinstance(constructed[0], sdk.Mosaic) else None
    if mosaic is not None and mosaic.metadata_key in _RESERVED_FIELDS | {label_field}:
        raise ValueError("transform.transforms[0].metadata_key conflicts with detection fields")
    _parameters(sdk.Compose, values, "transform")
    arguments: dict[str, Any] = dict(values)
    arguments.update(transforms=constructed, bbox_params=bbox_params, strict=True, seed=seed)
    try:
        with warnings.catch_warnings():
            # Keeping box metadata through image-only/empty compositions is intentional.
            warnings.filterwarnings("ignore", message="Got processor for bboxes, but no transform")
            warnings.simplefilter("error", UserWarning, append=True)
            transform = sdk.Compose(**arguments)
    except (TypeError, ValueError, UserWarning) as error:
        raise ValueError(f"transform: {error}") from error
    return CompiledPipeline(transform, label_field, bbox_format, mosaic)


def build_pipeline(document: dict[str, JsonValue], *, seed: int) -> CompiledPipeline:
    """Build only registered library classes, checking every constructor argument."""
    try:
        return _build_pipeline(document, seed=seed)
    except TypeError as error:
        # JSON field type failures are invalid configuration, not caller programming errors.
        raise ValueError(str(error)) from error
