"""Execution controls and immutable exact-device mappings for supervised jobs."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from clearml_yolo.adapters.runtime.gpu_resources import execution_phases
from clearml_yolo.core.execution import (
    AutoGPUControl,
    ExecutionPhase,
    concrete_device_selector,
    validate_concrete_phases,
)


def automatic_gpu_control(config: Mapping[str, Any]) -> AutoGPUControl:
    """Validate the per-job availability policy, including legacy enabled-only groups."""
    return AutoGPUControl.model_validate(config.get("autogpu", {}))


def execution_controls(config: Mapping[str, Any]) -> tuple[bool, bool]:
    """Read routing switches without resolving policy before Hydra's job context exists."""
    values: list[bool] = []
    for name in ("queue", "autogpu"):
        group = config.get(name, {"enabled": True})
        allowed = {"enabled", "force", "max_used_memory_gib"} if name == "autogpu" else {"enabled"}
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
    force = config.get("autogpu", {}).get("force", False)
    if type(force) is not bool:
        raise TypeError("autogpu.force must be boolean")
    if force:
        return False, False
    return values[0], values[1]


def forced_device_selection(
    command: str, config: Mapping[str, Any]
) -> dict[str, tuple[int, ...] | str]:
    """Validate forced enabled-phase selectors without CUDA or NVML discovery."""
    return validate_concrete_phases(execution_phases(command, config))


@dataclass(frozen=True)
class ExactSelection:
    """Original visibility and fixed child visibility, unaffected by lease contraction."""

    visible: tuple[str, ...]
    devices: tuple[str, ...]


def _exact_ordinals(value: object) -> tuple[int, ...]:
    selection = concrete_device_selector(value)
    return selection if isinstance(selection, tuple) else ()


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
