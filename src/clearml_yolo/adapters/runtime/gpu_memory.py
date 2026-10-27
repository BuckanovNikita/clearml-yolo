"""Measure CUDA allocator and non-allocator envelopes before native teardown."""

from dataclasses import dataclass


@dataclass
class GPUMemory:
    device: int | None = None
    peak_memory_bytes: int = 0
    non_allocator_memory_bytes: int = 0

    def observe(self) -> None:
        """Subtract current reservations, never the historical allocator peak."""
        import torch

        torch.cuda.synchronize(self.device)
        free, total = torch.cuda.mem_get_info(self.device)
        reserved = torch.cuda.memory_reserved(self.device)
        self.peak_memory_bytes = max(
            self.peak_memory_bytes, torch.cuda.max_memory_reserved(self.device)
        )
        # Driver usage already includes the idle baseline. The invocation owner
        # combines this envelope with its baseline using max, without adding both.
        self.non_allocator_memory_bytes = max(
            self.non_allocator_memory_bytes, total - free - reserved, 0
        )
