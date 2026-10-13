"""NVML/CUDA telemetry behind the queue application's inventory port."""

from clearml_yolo.adapters.runtime.gpu_resources import GPUInventory
from clearml_yolo.core.queue import GPUObservation


class QueueGPUInventory:
    def __init__(self, *, max_used_memory_gib: float = 2.0) -> None:
        self.source = GPUInventory(max_used_memory_gib=max_used_memory_gib)
        self.visible: tuple[str, ...] | None = None

    def snapshot(self) -> tuple[GPUObservation, ...]:
        if self.visible is None:
            self.visible = self.source.visible()
        physical = {card.uuid: card for card in self.source.snapshot()}
        if any(uuid not in physical for uuid in self.visible):
            raise RuntimeError("Queue GPU visibility changed before admission")
        return tuple(
            GPUObservation(uuid=uuid, available=not physical[uuid].busy, logical_index=index)
            for index, uuid in enumerate(self.visible)
        )
