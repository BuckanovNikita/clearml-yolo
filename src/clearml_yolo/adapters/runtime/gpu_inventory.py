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
    model_config = ConfigDict(extra="forbid", frozen=True)

    index: int = Field(ge=0)
    uuid: str
    name: str
    total_memory_bytes: int = Field(gt=0)
    used_memory_bytes: int = Field(ge=0)
    utilization: int = Field(ge=0, le=100)


@dataclass(frozen=True)
class GPUState:
    used: int
    utilization: int
    pids: frozenset[int]


def _query(selector: str) -> list[list[str]]:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        raise RuntimeError("Batch estimation requires nvidia-smi GPU telemetry")
    result = subprocess.run(  # noqa: S603 - resolved executable and fixed query arguments
        [executable, selector, "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
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
    inventory = _query("--query-gpu=uuid,memory.used,utilization.gpu")
    processes = _query("--query-compute-apps=gpu_uuid,pid")
    by_gpu: dict[str, set[int]] = {}
    for uuid, pid in processes:
        by_gpu.setdefault(uuid, set()).add(_telemetry_integer(pid, "pid"))
    return {
        uuid: GPUState(
            _telemetry_integer(used, "memory.used") * 1024**2,
            _telemetry_integer(utilization, "utilization.gpu"),
            frozenset(by_gpu.get(uuid, ())),
        )
        for uuid, used, utilization in inventory
    }


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
                record | {"used_memory_bytes": state.used, "utilization": state.utilization}
            )
        )
    if not devices:
        raise RuntimeError("No visible CUDA GPUs; batch estimation requires idle GPUs")
    return tuple(devices)


def require_idle(devices: tuple[GPUDevice, ...]) -> tuple[int, ...]:
    # Utilization covers a sampling interval and can outlive the previous owned
    # CUDA context. Wait briefly for an actually idle sample; never waive it.
    deadline = time.monotonic() + 2
    while True:
        states = gpu_states()
        active = []
        for device in devices:
            state = states.get(device.uuid)
            if state is None or state.pids:
                raise RuntimeError(f"GPU {device.index} is busy or its telemetry is unavailable")
            if state.utilization:
                active.append(device.index)
        if not active:
            return tuple(states[device.uuid].used for device in devices)
        if time.monotonic() >= deadline:
            raise RuntimeError(f"GPU {active[0]} is busy or its telemetry is unavailable")
        time.sleep(0.1)


def monitor_devices(
    devices: tuple[GPUDevice, ...], owned_pids: Callable[[], tuple[int, ...]]
) -> tuple[int, ...]:
    """Reject foreign or unidentifiable active compute; never terminate its workload."""
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
            raise RuntimeError(
                f"GPU {device.index} measurement contaminated by foreign PIDs {sorted(foreign)}"
            )
        if state.utilization and not state.pids:
            raise RuntimeError(
                f"GPU {device.index} measurement contaminated: active compute has no PID telemetry"
            )
        peaks.append(state.used)
    return tuple(peaks)
