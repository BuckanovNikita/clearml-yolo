"""GPU demand and whole-device inventory without native model runtime imports."""

import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Literal, Protocol, cast

from clearml_yolo.adapters.observability.diagnostics import (
    exception_summary,
    log_exception,
    redact_text,
)
from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.core.execution import DEFAULT_MAX_USED_MEMORY_GIB, AutoGPUControl, ExecutionPhase

_CUDA_PROBE_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class GPUDevice:
    """A physical whole GPU and whether its used memory reaches the configured limit."""

    uuid: str
    busy: bool
    physical_index: int | None = None
    logical_index: int | None = None
    used_memory_bytes: int | None = None
    telemetry_error: str | None = None


class _NVML(Protocol):
    NVML_DEVICE_MIG_DISABLE: int
    NVMLError_NotSupported: type[BaseException]

    def nvmlInit(self) -> None: ...  # noqa: N802 - third-party API

    def nvmlShutdown(self) -> None: ...  # noqa: N802 - third-party API

    def nvmlDeviceGetCount(self) -> int: ...  # noqa: N802 - third-party API

    def nvmlDeviceGetHandleByIndex(self, index: int) -> Any: ...  # noqa: N802

    def nvmlDeviceGetUUID(self, handle: Any) -> str | bytes: ...  # noqa: N802

    def nvmlDeviceGetMigMode(self, handle: Any) -> tuple[int, int]: ...  # noqa: N802

    def nvmlDeviceGetMemoryInfo(self, handle: Any) -> Any: ...  # noqa: N802


def _nvml() -> _NVML:
    """Keep the opaque binding behind one typed boundary."""
    return cast(_NVML, import_module("pynvml"))


def _device_error(value: object) -> ValueError:
    return ValueError(f"Unsupported native device value: {value!r}")


def _device_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < -1:
        raise _device_error(value)
    return value


def _string_device_count(value: str) -> int:
    selection = value.strip().lower()
    if not selection or selection == "cuda":
        return 1
    if selection in {"cpu", "mps"} or (selection.startswith("mps:") and selection[4:].isdigit()):
        return 0
    cuda_prefixed = selection.startswith("cuda:")
    ordinals = selection[5:] if cuda_prefixed else selection
    parts = [part.strip() for part in ordinals.split(",")]
    if not parts or any(not part for part in parts):
        raise _device_error(value)
    for part in parts:
        if cuda_prefixed:
            if not part.isdigit():
                raise _device_error(value)
        elif part != "-1" and not part.isdigit():
            raise _device_error(value)
    return len(parts)


def device_count(value: object) -> int:
    """Derive GPU demand from one native device selector."""
    if value is None:
        return 1
    if isinstance(value, bool):
        raise _device_error(value)
    if isinstance(value, int):
        _device_id(value)
        return 1
    if isinstance(value, str):
        return _string_device_count(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if not value:
            raise _device_error(value)
        for item in value:
            _device_id(item)
        return len(value)
    raise TypeError(f"Native device must be null, a string, an integer, or a list: {value!r}")


def normalized_device(value: object) -> object:
    """Replace written GPU identities with anonymous device-count entries."""
    count = device_count(value)
    if count:
        return [-1] * count
    if isinstance(value, str):
        return value.strip()
    raise _device_error(value)


def execution_devices(count: int) -> list[int]:
    """Return the first concrete logical CUDA ordinals for a device count."""
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError(f"GPU count must be an integer: {count!r}")
    if count < 0:
        raise ValueError(f"GPU count must be nonnegative: {count}")
    return list(range(count))


def _mapping(config: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = config.get(key, {})
    if not isinstance(value, Mapping):
        raise TypeError(f"{key} configuration must be a mapping")
    return value


def _settings(config: Mapping[str, Any], path: str) -> Mapping[str, Any] | None:
    current = config
    for key in path.split("."):
        if key not in current:
            return None
        value = current[key]
        if not isinstance(value, Mapping):
            raise TypeError(f"{path} configuration must be a mapping")
        current = value
    return current


def _model_paths(config: Mapping[str, Any]) -> tuple[str, str]:
    backend = _mapping(config, "model").get("backend", "ultralytics")
    if backend == "ultralytics":
        return "ultralytics", "ultralytics_predict"
    if backend not in {"deimv2", "rfdetr", "fasterrcnn"}:
        raise ValueError(f"Unsupported model backend for GPU scheduling: {backend!r}")
    return "model.train", "model.predict"


def _model_phase(
    config: Mapping[str, Any], kind: Literal["train", "predict"], path: str
) -> ExecutionPhase:
    settings = _settings(config, path)
    return ExecutionPhase(
        kind=kind, settings_path=path, device=settings.get("device") if settings else None
    )


def _export_phase(config: Mapping[str, Any]) -> ExecutionPhase:
    settings = _mapping(config, "export")
    operation = settings.get("operation", "onnx")
    if operation not in {"onnx", "build", "verify"}:
        raise ValueError(f"Unsupported export operation: {operation!r}")
    device = settings.get("device", "cpu")
    count = device_count(device)
    implicit_device = device is None or (isinstance(device, str) and not device.strip())
    if count > 1 or (operation != "onnx" and (implicit_device or count != 1)):
        raise ValueError(f"export.{operation} requires one explicit GPU device")
    return ExecutionPhase(kind="export", settings_path="export", device=device)


def configured_phases(config: Mapping[str, Any]) -> tuple[ExecutionPhase, ...]:
    """Describe present native setting groups for provenance and automatic remapping."""
    training, prediction = _model_paths(config)
    phases: list[ExecutionPhase] = []
    if _settings(config, training) is not None:
        phases.append(_model_phase(config, "train", training))
    if _settings(config, prediction) is not None:
        phases.append(_model_phase(config, "predict", prediction))
    if "export" in config:
        phases.append(_export_phase(config))
    return tuple(phases)


def _skip(config: Mapping[str, Any], key: str) -> bool:
    value = config.get(key, False)
    if not isinstance(value, bool):
        raise TypeError(f"{key} must be boolean")
    return value


def execution_phases(command: str, config: Mapping[str, Any]) -> tuple[ExecutionPhase, ...]:
    """Describe only the command's enabled work without importing any native runtime."""
    if command in {"metrics", "report", "ground_truth", "init_config"}:
        return ()
    if command == "export":
        return (_export_phase(config),)
    training, prediction = _model_paths(config)
    if command == "train":
        return (_model_phase(config, "train", training),)
    if command in {"predict", "val", "compare"}:
        return (_model_phase(config, "predict", prediction),)
    if command == "pipeline":
        phases: list[ExecutionPhase] = []
        if not _skip(config, "skip_train"):
            phases.append(_model_phase(config, "train", training))
        inference_enabled = not _skip(config, "skip_predict") or not _skip(config, "skip_compare")
        if inference_enabled:
            phases.append(_model_phase(config, "predict", prediction))
        return tuple(phases)
    raise ValueError(f"Unknown command for GPU request: {command!r}")


def job_request(command: str, config: Mapping[str, Any]) -> int:
    """Derive the maximum enabled-phase GPU demand from lightweight setting records."""
    demands = (
        device_count(phase.device) if phase.kind == "train" else min(device_count(phase.device), 1)
        for phase in execution_phases(command, config)
    )
    return max(demands, default=0)


def _uuid(value: str | bytes) -> str:
    decoded = value.decode("ascii") if isinstance(value, bytes) else value
    if not decoded.startswith("GPU-"):
        raise RuntimeError(f"NVML returned unsupported GPU UUID {decoded!r}")
    return decoded


@trace_operation("gpu.visibility_probe")
def _probe_visible_uuids() -> tuple[str, ...]:
    try:
        result = subprocess.run(
            [sys.executable, "-B", "-m", "clearml_yolo.adapters.runtime.gpu_probe"],
            check=False,
            capture_output=True,
            text=True,
            timeout=_CUDA_PROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"CUDA visibility probe timed out after {_CUDA_PROBE_TIMEOUT_SECONDS:g} seconds"
        ) from error
    if result.returncode:
        detail = result.stderr.strip() or f"metadata probe exited {result.returncode}"
        raise RuntimeError(
            f"CUDA visibility probe failed (exit {result.returncode}): {redact_text(detail)}"
        )
    try:
        loaded = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        log_exception(
            "CUDA visibility probe returned invalid JSON",
            error,
            level="DEBUG",
            context={"line": error.lineno, "column": error.colno},
            include_message=False,
        )
        raise RuntimeError(
            "CUDA visibility probe returned invalid JSON: "
            + exception_summary(error, include_message=False)
        ) from None
    if not isinstance(loaded, list) or any(not isinstance(value, str) for value in loaded):
        raise RuntimeError("CUDA visibility probe returned an invalid UUID list")
    if any(value.startswith("MIG-") for value in loaded):
        raise RuntimeError("MIG devices are unsupported by GPU availability waiting")
    if len(set(loaded)) != len(loaded):
        raise RuntimeError("CUDA visibility probe returned duplicate GPU UUIDs")
    return tuple(loaded)


class GPUInventory:
    """Read whole-GPU telemetry and inherited CUDA visibility without pinning ordinals."""

    max_used_memory_gib: float = DEFAULT_MAX_USED_MEMORY_GIB
    _visible_uuids: tuple[str, ...] | None = None
    _required_uuids: tuple[str, ...] | None = None

    def __init__(self, *, max_used_memory_gib: float = DEFAULT_MAX_USED_MEMORY_GIB) -> None:
        self.max_used_memory_gib = AutoGPUControl(
            max_used_memory_gib=max_used_memory_gib
        ).max_used_memory_gib

    def restrict_to(self, required: tuple[str, ...]) -> None:
        """Require telemetry only for exact selected or already reserved UUIDs.

        Worker contraction can set the reserved scope without a visibility probe.
        This does not change the logical order previously discovered by visible().
        """
        if len(set(required)) != len(required):
            raise ValueError("Required GPU UUIDs must be unique")
        if self._visible_uuids is not None:
            unknown = set(required).difference(self._visible_uuids)
            if unknown:
                raise ValueError(
                    f"Required GPU UUIDs are outside CUDA visibility: {sorted(unknown)}"
                )
        self._required_uuids = required

    def physical_uuids(self) -> tuple[str, ...]:
        """Enumerate physical NVML identities without CUDA or memory telemetry."""
        return self._physical_uuids()

    def _physical_uuids(self) -> tuple[str, ...]:
        """Map physical identities independently of memory and MIG telemetry."""
        nvml = _nvml()
        initialized = False
        try:
            nvml.nvmlInit()
            initialized = True
            return tuple(
                _uuid(nvml.nvmlDeviceGetUUID(nvml.nvmlDeviceGetHandleByIndex(index)))
                for index in range(nvml.nvmlDeviceGetCount())
            )
        finally:
            if initialized:
                nvml.nvmlShutdown()

    def _memory_used(self, nvml: _NVML, handle: Any, uuid: str) -> int:
        try:
            current_mig_mode, _pending_mig_mode = nvml.nvmlDeviceGetMigMode(handle)
        except nvml.NVMLError_NotSupported:
            current_mig_mode = nvml.NVML_DEVICE_MIG_DISABLE
        if current_mig_mode != nvml.NVML_DEVICE_MIG_DISABLE:
            raise RuntimeError(f"MIG-enabled GPU {uuid} is unsupported by GPU availability waiting")
        try:
            memory = nvml.nvmlDeviceGetMemoryInfo(handle)
        except nvml.NVMLError_NotSupported as error:
            raise RuntimeError(
                f"GPU {uuid} memory telemetry is unsupported; cannot determine safe availability"
            ) from error
        # NVML exposes an opaque binding record, rather than a project-owned type.
        used = getattr(memory, "used", None)
        if isinstance(used, bool) or not isinstance(used, int) or used < 0:
            raise RuntimeError(
                f"GPU {uuid} memory telemetry returned invalid used bytes; "
                "cannot determine safe availability"
            )
        return used

    @trace_operation("gpu.inventory")
    def snapshot(self) -> tuple[GPUDevice, ...]:
        """Fail closed for required GPUs; retain unavailable excluded cards as diagnostics.

        With no visibility discovery or explicit scope, all physical GPUs are required.
        """
        nvml = _nvml()
        initialized = False
        required = self._required_uuids
        if required is None:
            required = self._visible_uuids
        logical_indexes = {uuid: index for index, uuid in enumerate(self._visible_uuids or ())}
        try:
            nvml.nvmlInit()
            initialized = True
            devices: list[GPUDevice] = []
            for index in range(nvml.nvmlDeviceGetCount()):
                handle = nvml.nvmlDeviceGetHandleByIndex(index)
                uuid = _uuid(nvml.nvmlDeviceGetUUID(handle))
                try:
                    used = self._memory_used(nvml, handle, uuid)
                except Exception as error:
                    # This adapter boundary can represent telemetry failures only
                    # when the device cannot participate in this admission decision.
                    if required is None or uuid in required:
                        raise RuntimeError(
                            f"GPU {uuid} telemetry unavailable: {exception_summary(error)}"
                        ) from error
                    devices.append(
                        GPUDevice(
                            uuid=uuid,
                            busy=True,
                            physical_index=index,
                            logical_index=logical_indexes.get(uuid),
                            telemetry_error=exception_summary(error),
                        )
                    )
                    continue
                devices.append(
                    GPUDevice(
                        uuid=uuid,
                        busy=used >= self.max_used_memory_gib * 1024**3,
                        physical_index=index,
                        logical_index=logical_indexes.get(uuid),
                        used_memory_bytes=used,
                    )
                )
            if required is not None:
                missing = set(required).difference(device.uuid for device in devices)
                if missing:
                    raise RuntimeError(
                        f"Required GPUs unavailable in NVML inventory: {sorted(missing)}"
                    )
            return tuple(devices)
        finally:
            if initialized:
                nvml.nvmlShutdown()

    @trace_operation("gpu.visibility")
    def visible(self) -> tuple[str, ...]:
        """Return supported whole-GPU UUIDs in inherited CUDA logical order."""
        visible = _probe_visible_uuids()
        physical = self.physical_uuids()
        unknown = [uuid for uuid in visible if uuid not in physical]
        if unknown:
            raise RuntimeError(
                f"CUDA visibility could not be mapped to physical GPU UUIDs: {unknown}"
            )
        self._visible_uuids = visible
        return visible
