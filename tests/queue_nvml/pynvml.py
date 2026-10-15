"""File-backed NVML double for real queue subprocess tests; never installed."""

import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
from typing import cast

NVML_DEVICE_MIG_DISABLE = 0


class NVMLError_NotSupported(RuntimeError):  # noqa: N801, N818 - third-party binding
    pass


def _memory() -> dict[str, int | None]:
    return cast(
        dict[str, int | None],
        json.loads(Path(os.environ["CY_TEST_QUEUE_MEMORY"]).read_text(encoding="utf-8")),
    )


def nvmlInit() -> None:  # noqa: N802
    pass


def nvmlShutdown() -> None:  # noqa: N802
    pass


def nvmlDeviceGetCount() -> int:  # noqa: N802
    return len(_memory())


def nvmlDeviceGetHandleByIndex(index: int) -> int:  # noqa: N802
    return index


def nvmlDeviceGetUUID(handle: int) -> str:  # noqa: N802
    return tuple(_memory())[handle]


def nvmlDeviceGetMigMode(_handle: int) -> tuple[int, int]:  # noqa: N802
    return 0, 0


def nvmlDeviceGetMemoryInfo(handle: int) -> SimpleNamespace:  # noqa: N802
    if barrier := os.environ.get("CY_TEST_QUEUE_MEMORY_BARRIER"):
        gate = Path(barrier)
        gate.with_suffix(".ready").touch()
        deadline = time.monotonic() + 10
        while not gate.with_suffix(".continue").exists():
            if time.monotonic() >= deadline:
                raise TimeoutError("Queue test memory barrier was not released")
            time.sleep(0.01)
    used = _memory()[nvmlDeviceGetUUID(handle)]
    if used is None:
        raise NVMLError_NotSupported("Memory reading unavailable")
    return SimpleNamespace(used=used)
