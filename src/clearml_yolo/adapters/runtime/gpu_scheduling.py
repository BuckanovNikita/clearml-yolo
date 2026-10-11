"""Execution controls and immutable exact-device mappings for supervised jobs."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from clearml_yolo.adapters.runtime.gpu_resources import device_count


def execution_controls(config: Mapping[str, Any]) -> tuple[bool, bool]:
    values: list[bool] = []
    for name in ("queue", "autogpu"):
        group = config.get(name, {"enabled": True})
        if not isinstance(group, Mapping) or set(group) != {"enabled"}:
            raise TypeError(f"{name} must contain only enabled")
        enabled = group["enabled"]
        if type(enabled) is not bool:
            raise TypeError(f"{name}.enabled must be boolean")
        values.append(enabled)
    return values[0], values[1]


@dataclass(frozen=True)
class ExactSelection:
    """Original visibility and fixed child visibility, unaffected by lease contraction."""

    visible: tuple[str, ...]
    devices: tuple[str, ...]


def _exact_ordinals(value: object) -> tuple[int, ...]:
    if device_count(value) == 0:
        return ()
    values: tuple[int, ...]
    if type(value) is int:
        values = (value,)
    elif isinstance(value, str):
        text = value.strip()
        text = text.removeprefix("cuda:")
        parts = text.split(",")
        if any(not part.strip().isdigit() for part in parts):
            raise ValueError("Queued manual selection requires exact nonnegative GPU ordinals")
        values = tuple(int(part.strip()) for part in parts)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        values = tuple(value)
    else:
        raise ValueError("Queued manual selection requires exact nonnegative GPU ordinals")
    if any(type(item) is not int or item < 0 for item in values) or len(set(values)) != len(values):
        raise ValueError("Queued manual selection requires unique exact nonnegative GPU ordinals")
    return values


def _enabled_groups(command: str, config: Mapping[str, Any]) -> tuple[str, ...]:
    if command == "train":
        return ("ultralytics",)
    if command in {"predict", "val", "compare"}:
        return ("ultralytics_predict",)
    if command == "pipeline":
        groups: list[str] = []
        if not config.get("skip_train", False):
            groups.append("ultralytics")
        if not config.get("skip_predict", False) or not config.get("skip_compare", False):
            groups.append("ultralytics_predict")
        return tuple(groups)
    return ()


def _group_ids(group: str, config: Mapping[str, Any], visible: tuple[str, ...]) -> tuple[str, ...]:
    native = config.get(group, {})
    if not isinstance(native, Mapping):
        raise TypeError(f"{group} must be a mapping")
    ordinals = _exact_ordinals(native.get("device"))
    if group == "ultralytics_predict" and len(ordinals) > 1:
        raise ValueError("Queued manual inference requires one exact GPU ordinal")
    if any(ordinal >= len(visible) for ordinal in ordinals):
        raise ValueError("Exact GPU ordinal exceeds inherited CUDA visibility")
    return tuple(visible[ordinal] for ordinal in ordinals)


def exact_request(
    command: str, config: Mapping[str, Any], visible: tuple[str, ...]
) -> ExactSelection:
    """Reserve every enabled phase identity, keeping downstream inference first."""
    groups = _enabled_groups(command, config)
    ordered: list[str] = []
    for group in ("ultralytics_predict", "ultralytics"):
        if group in groups:
            for uuid in _group_ids(group, config, visible):
                if uuid not in ordered:
                    ordered.append(uuid)
    return ExactSelection(visible, tuple(ordered))


def exact_device_ordinals(
    command: str,
    config: Mapping[str, Any],
    selection: ExactSelection,
    admitted: tuple[str, ...],
) -> dict[str, list[int]]:
    """Validate replay identities and return fixed child CUDA ordinal replacements."""
    result: dict[str, list[int]] = {}
    for group in _enabled_groups(command, config):
        identities = _group_ids(group, config, selection.visible)
        if any(
            identity not in admitted or identity not in selection.devices for identity in identities
        ):
            raise ValueError(
                "ClearML replay requires a GPU identity outside the admitted selection"
            )
        if identities:
            result[group] = [selection.devices.index(identity) for identity in identities]
    return result
