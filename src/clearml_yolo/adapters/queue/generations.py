"""Append-only device generations shared across users in the host namespace."""

import hashlib
import os
import stat
import time
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from clearml_yolo.adapters.queue.storage import atomic_write
from clearml_yolo.core.queue import GPUFreeResult

_MAX_EVENT_BYTES = 4096


def device_key(uuid: str) -> str:
    return hashlib.sha256(uuid.encode()).hexdigest()


def generation_events(root: Path) -> tuple[GPUFreeResult, ...]:
    events: list[GPUFreeResult] = []
    for path in root.glob("generation-*.json"):
        status = path.lstat()
        if not stat.S_ISREG(status.st_mode) or status.st_size > _MAX_EVENT_BYTES:
            raise RuntimeError("GPU generation is not a bounded regular record")
        try:
            event = GPUFreeResult.model_validate_json(path.read_bytes())
        except ValidationError as error:
            raise RuntimeError("GPU generation record is corrupt") from error
        prefix = f"generation-{device_key(event.uuid)}-{event.generation}-"
        if (
            status.st_uid != event.actor_uid
            or stat.S_IMODE(status.st_mode) & 0o022
            or not path.name.startswith(prefix)
        ):
            raise PermissionError("GPU generation ownership or identity differs from its record")
        events.append(event)
    return tuple(events)


def current_generations(root: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for event in generation_events(root):
        result[event.uuid] = max(result.get(event.uuid, 0), event.generation)
    return result


def advance_generation(root: Path, uuid: str) -> GPUFreeResult:
    """Caller holds the host transaction; one durable event is the entire commit."""
    result = GPUFreeResult(
        uuid=uuid,
        actor_uid=os.geteuid(),
        generation=current_generations(root).get(uuid, 0) + 1,
        created_at=time.time(),
    )
    path = root / f"generation-{device_key(uuid)}-{result.generation}-{uuid4().hex}.json"
    atomic_write(path, result.model_dump_json())
    return result
