"""NVML/CUDA telemetry behind the queue application's inventory port."""

from clearml_yolo.adapters.runtime.gpu_resources import GPUInventory
from clearml_yolo.core.queue import GPUObservation


class QueueGPUInventory:
    def __init__(self) -> None:
        self.source = GPUInventory()
        self.visible: tuple[str, ...] | None = None

    def snapshot(self) -> tuple[GPUObservation, ...]:
        if self.visible is None:
            self.visible = self.source.visible()
        # Missing memory for one card must not hide healthy capacity on other cards.
        self.source.restrict_to(())
        physical = {card.uuid: card for card in self.source.snapshot(memory_only=True)}
        if any(uuid not in physical for uuid in self.visible):
            raise RuntimeError("Queue GPU visibility changed before admission")
        return tuple(
            GPUObservation(uuid=uuid, available=not physical[uuid].busy, logical_index=index)
            for index, uuid in enumerate(self.visible)
        )


def allocation_available(devices: tuple[str, ...]) -> bool:
    """Read physical memory again at startup, without a CUDA context or process scan."""
    source = GPUInventory()
    source.restrict_to(())
    try:
        physical = {card.uuid: card for card in source.snapshot(memory_only=True)}
    except (OSError, RuntimeError):
        return False
    return all(uuid in physical and not physical[uuid].busy for uuid in devices)
