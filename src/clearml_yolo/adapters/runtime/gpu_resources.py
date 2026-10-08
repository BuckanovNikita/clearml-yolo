"""GPU demand and whole-device inventory without native model runtime imports."""

import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Protocol, cast

from clearml_yolo.adapters.observability.diagnostics import (
    exception_summary,
    log_exception,
    redact_text,
)

_CUDA_PROBE_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class GPUDevice:
    """A physical whole GPU and whether an external compute process occupies it."""

    uuid: str
    busy: bool


class _NVML(Protocol):
    NVML_DEVICE_MIG_DISABLE: int
    NVMLError_NotSupported: type[BaseException]

    def nvmlInit(self) -> None: ...  # noqa: N802 - third-party API

    def nvmlShutdown(self) -> None: ...  # noqa: N802 - third-party API

    def nvmlDeviceGetCount(self) -> int: ...  # noqa: N802 - third-party API

    def nvmlDeviceGetHandleByIndex(self, index: int) -> Any: ...  # noqa: N802

    def nvmlDeviceGetUUID(self, handle: Any) -> str | bytes: ...  # noqa: N802

    def nvmlDeviceGetMigMode(self, handle: Any) -> tuple[int, int]: ...  # noqa: N802

    def nvmlDeviceGetComputeRunningProcesses(  # noqa: N802
        self, handle: Any
    ) -> Sequence[Any]: ...


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
    """Derive scheduler demand from one native Ultralytics device selector."""
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
    """Replace written GPU identities with anonymous scheduler demand entries."""
    count = device_count(value)
    if count:
        return [-1] * count
    if isinstance(value, str):
        return value.strip()
    raise _device_error(value)


def execution_devices(count: int) -> list[int]:
    """Return concrete child-local CUDA ordinals after visibility assignment."""
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


def _group_device(config: Mapping[str, Any], key: str) -> object:
    return _mapping(config, key).get("device")


def _inference_request(value: object) -> int:
    return min(device_count(value), 1)


def _skip(config: Mapping[str, Any], key: str) -> bool:
    value = config.get(key, False)
    if not isinstance(value, bool):
        raise TypeError(f"{key} must be boolean")
    return value


def job_request(command: str, config: Mapping[str, Any]) -> int:
    """Derive the up-front GPU reservation for one resolved command configuration."""
    if command == "train":
        return device_count(_group_device(config, "ultralytics"))
    if command in {"predict", "val", "compare"}:
        return _inference_request(_group_device(config, "ultralytics_predict"))
    if command == "pipeline":
        training = (
            0 if _skip(config, "skip_train") else device_count(_group_device(config, "ultralytics"))
        )
        inference_enabled = not _skip(config, "skip_predict") or not _skip(config, "skip_compare")
        inference = (
            _inference_request(_group_device(config, "ultralytics_predict"))
            if inference_enabled
            else 0
        )
        return max(training, inference)
    if command in {"metrics", "report", "ground_truth", "init_config"}:
        return 0
    raise ValueError(f"Unknown command for GPU request: {command!r}")


def _uuid(value: str | bytes) -> str:
    decoded = value.decode("ascii") if isinstance(value, bytes) else value
    if not decoded.startswith("GPU-"):
        raise RuntimeError(f"NVML returned unsupported GPU UUID {decoded!r}")
    return decoded


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
        raise RuntimeError("MIG devices are unsupported by the GPU queue")
    if len(set(loaded)) != len(loaded):
        raise RuntimeError("CUDA visibility probe returned duplicate GPU UUIDs")
    return tuple(loaded)


class GPUInventory:
    """Read whole-GPU telemetry and inherited CUDA visibility without pinning ordinals."""

    def snapshot(self) -> tuple[GPUDevice, ...]:
        """Return every physical whole GPU; unknown process telemetry fails closed."""
        nvml = _nvml()
        initialized = False
        try:
            nvml.nvmlInit()
            initialized = True
            devices: list[GPUDevice] = []
            for index in range(nvml.nvmlDeviceGetCount()):
                handle = nvml.nvmlDeviceGetHandleByIndex(index)
                uuid = _uuid(nvml.nvmlDeviceGetUUID(handle))
                try:
                    current_mig_mode, _pending_mig_mode = nvml.nvmlDeviceGetMigMode(handle)
                except nvml.NVMLError_NotSupported:
                    current_mig_mode = nvml.NVML_DEVICE_MIG_DISABLE
                if current_mig_mode != nvml.NVML_DEVICE_MIG_DISABLE:
                    raise RuntimeError(f"MIG-enabled GPU {uuid} is unsupported by the GPU queue")
                try:
                    busy = bool(nvml.nvmlDeviceGetComputeRunningProcesses(handle))
                except nvml.NVMLError_NotSupported as error:
                    raise RuntimeError(
                        f"GPU {uuid} compute process telemetry is unsupported; "
                        "cannot determine safe availability"
                    ) from error
                devices.append(GPUDevice(uuid=uuid, busy=busy))
            return tuple(devices)
        finally:
            if initialized:
                nvml.nvmlShutdown()

    def visible(self) -> tuple[str, ...]:
        """Return supported whole-GPU UUIDs in inherited CUDA logical order."""
        visible = _probe_visible_uuids()
        physical = {device.uuid: device for device in self.snapshot()}
        unknown = [uuid for uuid in visible if uuid not in physical]
        if unknown:
            raise RuntimeError(
                f"CUDA visibility could not be mapped to physical GPU UUIDs: {unknown}"
            )
        return visible
