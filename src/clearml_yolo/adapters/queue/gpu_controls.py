"""Physical GPU controls independent of telemetry, processes, and queue storage."""

import re
from collections.abc import Callable
from uuid import UUID

from clearml_yolo.adapters.queue.locks import LocalGPULocks
from clearml_yolo.adapters.runtime.gpu_resources import GPUInventory
from clearml_yolo.core.gpu_identity import identity_label
from clearml_yolo.core.queue import GPUControlStatus, GPUFreeResult, GPUHold


def _full_uuid(selector: str) -> bool:
    if not selector.startswith("GPU-"):
        return False
    try:
        return str(UUID(selector[4:])) == selector[4:]
    except ValueError:
        return False


class GPUControls:
    """An operator declaration advances capacity without examining running work."""

    def __init__(
        self,
        pool: LocalGPULocks,
        *,
        physical_uuids: Callable[[], tuple[str, ...]] | None = None,
    ) -> None:
        self.pool = pool
        self.physical_uuids = physical_uuids or GPUInventory().physical_uuids

    def _resolve(self, selector: str) -> str:
        if re.fullmatch(r"[0-9]+", selector):
            physical = self.physical_uuids()
            index = int(selector)
            if index >= len(physical):
                raise ValueError("GPU physical index is outside the NVML inventory")
            return physical[index]
        if _full_uuid(selector):
            return selector
        if re.fullmatch(r"gpu-[0-9a-f]{12}", selector):
            matches = [
                uuid for uuid in self.pool.known_devices() if identity_label(uuid) == selector
            ]
            if len(matches) == 1:
                return matches[0]
            raise ValueError("GPU short selector is unknown or ambiguous")
        raise ValueError("GPU selector must be a nonnegative physical index or known short label")

    def list(self) -> tuple[GPUControlStatus, ...]:
        physical = self.physical_uuids()
        with self.pool.transaction():
            claims = self.pool.transaction_claims()
        holds = self.pool.holds()
        uuids = dict.fromkeys((*physical, *self.pool.known_devices()))
        return tuple(
            GPUControlStatus(
                uuid=uuid,
                physical_index=physical.index(uuid) if uuid in physical else None,
                holds=tuple(hold for hold in holds if hold.uuid == uuid),
                claim=next((claim for claim in claims if uuid in claim.devices), None),
            )
            for uuid in uuids
        )

    def disable(self, selector: str) -> GPUHold:
        return self.pool.disable(self._resolve(selector))

    def enable(self, selector: str) -> None:
        self.pool.enable(self._resolve(selector))

    def release(self, selector: str) -> GPUFreeResult:
        return self.pool.free(self._resolve(selector))
