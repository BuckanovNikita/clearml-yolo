"""Read visible CUDA identities and conservative live GPU ownership telemetry."""

import csv
import io
import json
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


class GPUDevice(BaseModel):
    """CUDA profile identity with live unavailable bytes relative to its capacity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    index: int = Field(ge=0)
    uuid: str
    name: str
    total_memory_bytes: int = Field(gt=0)
    used_memory_bytes: int = Field(ge=0)
    utilization: int = Field(ge=0, le=100)


@dataclass(frozen=True)
class GPUState:
    """Raw NVML unavailable/free bytes from one row, including driver reservations."""

    used: int
    utilization: int
    pids: frozenset[int]
    free_bytes: int

    def used_for(self, total_memory_bytes: int) -> int:
        """Express unavailable bytes against CUDA capacity without mixing total bases.

        Clamp at zero when NVML free exceeds CUDA capacity; reconstructed free
        memory then conservatively saturates at that CUDA capacity.
        """
        return max(total_memory_bytes - self.free_bytes, 0)


def _attach_output(error: subprocess.CalledProcessError | subprocess.TimeoutExpired) -> None:
    for name, stream in (("stdout", error.stdout), ("stderr", error.stderr)):
        # TimeoutExpired can carry partial bytes even when text mode was requested.
        text = stream.decode(errors="replace") if isinstance(stream, bytes) else stream
        if text and text.strip():
            error.add_note(f"nvidia-smi {name}: {text.strip()}")


def _query(selector: str) -> list[list[str]]:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        raise RuntimeError("Batch estimation requires nvidia-smi GPU telemetry")
    try:
        result = subprocess.run(  # noqa: S603 - resolved executable and fixed query arguments
            [executable, selector, "--format=csv,noheader,nounits"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        # NVML reports its failure on stdout, which the exception text omits. Notes keep
        # the exception type and text, so status classification cannot change.
        _attach_output(error)
        raise
    return [[value.strip() for value in row] for row in csv.reader(io.StringIO(result.stdout))]


def _telemetry_integer(value: str, field: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise RuntimeError(
            f"GPU telemetry unavailable: nvidia-smi returned invalid {field} {value!r}; "
            "check nvidia-smi and retry when numeric telemetry is available"
        ) from error


def gpu_states() -> dict[str, GPUState]:
    inventory = _query("--query-gpu=uuid,memory.total,memory.free,utilization.gpu")
    processes = _query("--query-compute-apps=gpu_uuid,pid")
    by_gpu: dict[str, set[int]] = {}
    for uuid, pid in processes:
        by_gpu.setdefault(uuid, set()).add(_telemetry_integer(pid, "pid"))
    states = {}
    for uuid, total, free, utilization in inventory:
        total_bytes = _telemetry_integer(total, "memory.total") * 1024**2
        free_bytes = _telemetry_integer(free, "memory.free") * 1024**2
        if total_bytes <= 0 or not 0 <= free_bytes <= total_bytes:
            raise RuntimeError("GPU telemetry unavailable: inconsistent total/free memory readings")
        states[uuid] = GPUState(
            total_bytes - free_bytes,
            _telemetry_integer(utilization, "utilization.gpu"),
            frozenset(by_gpu.get(uuid, ())),
            free_bytes,
        )
    return states


def discover_gpus() -> tuple[GPUDevice, ...]:
    """Torch resolves visibility in an isolated metadata process, without model loading."""
    script = (
        "import json,torch\n"
        "records=[]\n"
        "for i in range(torch.cuda.device_count()):\n"
        " p=torch.cuda.get_device_properties(i)\n"
        " records.append(dict(index=i,uuid='GPU-'+str(p.uuid),name=p.name,"
        "total_memory_bytes=p.total_memory))\n"
        "print(json.dumps(records))\n"
    )
    result = subprocess.run(  # noqa: S603 - current interpreter and fixed metadata script
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    records = json.loads(result.stdout)
    states = gpu_states()
    devices = []
    for record in records:
        state = states.get(record["uuid"])
        if state is None:
            raise RuntimeError("Visible CUDA device lacks whole-GPU telemetry (MIG unsupported)")
        devices.append(
            GPUDevice.model_validate(
                record
                | {"used_memory_bytes": state.used_for(record["total_memory_bytes"]), "utilization": state.utilization}
            )
        )
    if not devices:
        raise RuntimeError("No visible CUDA GPUs; batch estimation requires idle GPUs")
    return tuple(devices)


def require_idle(devices: tuple[GPUDevice, ...], *, force: bool = False) -> tuple[int, ...]:
    # Utilization covers a sampling interval and can outlive the previous owned
    # CUDA context. Force permits unattributed activity, never known compute PIDs.
    deadline = time.monotonic() + 2
    while True:
        states = gpu_states()
        active = []
        for device in devices:
            state = states.get(device.uuid)
            if state is None or state.pids:
                raise RuntimeError(f"GPU {device.index} is busy or its telemetry is unavailable")
            if state.utilization and not force:
                active.append(device.index)
        if not active:
            return tuple(states[device.uuid].used_for(device.total_memory_bytes) for device in devices)
        if time.monotonic() >= deadline:
            raise RuntimeError(f"GPU {active[0]} is busy or its telemetry is unavailable")
        time.sleep(0.1)


def monitor_devices(
    devices: tuple[GPUDevice, ...],
    owned_pids: Callable[[], tuple[int, ...]],
    *,
    force: bool = False,
) -> tuple[int, ...]:
    """Reject foreign compute; force permits activity with no attributable PID."""
    states = gpu_states()
    # Native compiler/loader children may start during the query. Verify current
    # births afterwards; disappeared or replaced PIDs remain unidentifiable.
    owners = set(owned_pids())
    peaks = []
    for device in devices:
        state = states.get(device.uuid)
        if state is None:
            raise RuntimeError(f"GPU {device.index} telemetry disappeared during the trial")
        foreign = state.pids - owners
        if foreign:
            raise RuntimeError(f"GPU {device.index} measurement contaminated by foreign PIDs {sorted(foreign)}")
        if state.utilization and not state.pids and not force:
            raise RuntimeError(f"GPU {device.index} measurement contaminated: active compute has no PID telemetry")
        peaks.append(state.used_for(device.total_memory_bytes))
    return tuple(peaks)


def require_memory_reserve(devices: tuple[GPUDevice, ...], used: tuple[int, ...], reserve: int) -> None:
    """Admission and monitoring share the same optional whole-device free-byte floor."""
    for device, allocated in zip(devices, used, strict=True):
        if device.total_memory_bytes - allocated < reserve:
            raise RuntimeError(f"GPU {device.index} free memory fell below the required reserve of {reserve} bytes")
