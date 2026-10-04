"""Invocation-scoped GPU ownership and the native training completion boundary."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from clearml_yolo.gpu_queue import WorkerClaim

_CLAIM: ContextVar[WorkerClaim | None] = ContextVar("cy_gpu_claim", default=None)
_SCHEDULED: ContextVar[bool] = ContextVar("cy_scheduled", default=False)


@contextmanager
def reservation(claim: WorkerClaim | None) -> Iterator[None]:
    token = _CLAIM.set(claim)
    scheduled_token = _SCHEDULED.set(True)
    try:
        yield
    finally:
        _CLAIM.reset(token)
        _SCHEDULED.reset(scheduled_token)


def scheduled() -> bool:
    return _SCHEDULED.get()


def assigned_devices() -> tuple[str, ...]:
    claim = _CLAIM.get()
    return claim.devices if claim is not None else ()


def training_finished() -> None:
    """Contract only after the caller has verified training and reaped native workers."""
    claim = _CLAIM.get()
    if claim is None:
        return
    from clearml_yolo.clearml_session import active_task, record_run_configuration
    from clearml_yolo.native_runtime import release_training_memory

    release_training_memory()
    devices = claim.shrink()
    record_run_configuration(
        active_task(), {"gpu_scheduler": {"phase": "inference", "reserved_uuids": list(devices)}}
    )
