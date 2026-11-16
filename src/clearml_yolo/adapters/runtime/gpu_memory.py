"""Measure CUDA allocator and non-allocator envelopes before native teardown."""

from dataclasses import dataclass


def reserve_cuda_memory(minimum_free_bytes: int, device: int = 0) -> float | None:
    """Bound this process's allocator before model load; external telemetry still monitors.

    Use the lower CUDA/whole-device free reading, retaining 256 MiB for growth.
    CUDA can omit memory visible to whole-device telemetry, notably under WSL.
    This guard cannot constrain foreign processes or native libraries, so it
    complements monitoring.
    Zero retains the ordinary full-device allocator policy without CUDA discovery.
    """
    if minimum_free_bytes == 0:
        return None
    if minimum_free_bytes < 0:
        raise ValueError("GPU memory reserve must not be negative")
    import torch

    from clearml_yolo.adapters.runtime.gpu_inventory import gpu_states

    free, total = torch.cuda.mem_get_info(device)
    current = torch.cuda.memory_reserved(device)
    properties = torch.cuda.get_device_properties(device)
    state = gpu_states().get(f"GPU-{properties.uuid}")
    if state is None:
        raise RuntimeError("Selected CUDA device lacks whole-GPU telemetry for the requested reserve")
    free = min(free, properties.total_memory - state.used)
    budget = free + current - minimum_free_bytes - 256 * 1024**2
    if budget <= current:
        raise RuntimeError("GPU has insufficient free memory for the requested reserve and driver headroom")
    fraction = min(budget / total, 1.0)
    torch.cuda.set_per_process_memory_fraction(fraction, device)
    return fraction


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
        self.peak_memory_bytes = max(self.peak_memory_bytes, torch.cuda.max_memory_reserved(self.device))
        # Driver usage already includes the idle baseline. The invocation owner
        # combines this envelope with its baseline using max, without adding both.
        self.non_allocator_memory_bytes = max(self.non_allocator_memory_bytes, total - free - reserved, 0)
