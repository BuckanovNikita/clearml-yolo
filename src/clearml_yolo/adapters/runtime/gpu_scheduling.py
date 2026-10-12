"""Execution controls and immutable exact-device mappings for supervised jobs."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from clearml_yolo.adapters.runtime.gpu_resources import device_count, execution_phases
from clearml_yolo.core.execution import AutoGPUControl, ExecutionPhase


def automatic_gpu_control(config: Mapping[str, Any]) -> AutoGPUControl:
    """Validate the per-job availability policy, including legacy enabled-only groups."""
    return AutoGPUControl.model_validate(config.get("autogpu", {}))


def execution_controls(config: Mapping[str, Any]) -> tuple[bool, bool]:
    """Read routing switches without resolving policy before Hydra's job context exists."""
    values: list[bool] = []
    for name in ("queue", "autogpu"):
        group = config.get(name, {"enabled": True})
        allowed = {"enabled", "max_used_memory_gib"} if name == "autogpu" else {"enabled"}
        if (
            not isinstance(group, Mapping)
            or set(group) - allowed
            or (name == "queue" and "enabled" not in group)
        ):
            raise TypeError(f"{name} must contain only {', '.join(sorted(allowed))}")
        enabled = group.get("enabled", True)
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


def _phase_ids(phase: ExecutionPhase, visible: tuple[str, ...]) -> tuple[str, ...]:
    ordinals = _exact_ordinals(phase.device)
    if phase.kind != "train" and len(ordinals) > 1:
        raise ValueError("Queued manual inference requires one exact GPU ordinal")
    if any(ordinal >= len(visible) for ordinal in ordinals):
        raise ValueError("Exact GPU ordinal exceeds inherited CUDA visibility")
    return tuple(visible[ordinal] for ordinal in ordinals)


def exact_request(
    command: str, config: Mapping[str, Any], visible: tuple[str, ...]
) -> ExactSelection:
    """Reserve every enabled phase identity, keeping downstream inference first."""
    phases = execution_phases(command, config)
    ordered: list[str] = []
    for phase in sorted(phases, key=lambda item: item.kind == "train"):
        for uuid in _phase_ids(phase, visible):
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
    for phase in execution_phases(command, config):
        identities = _phase_ids(phase, selection.visible)
        if any(
            identity not in admitted or identity not in selection.devices for identity in identities
        ):
            raise ValueError(
                "ClearML replay requires a GPU identity outside the admitted selection"
            )
        if identities:
            result[phase.settings_path] = [
                selection.devices.index(identity) for identity in identities
            ]
    return result
