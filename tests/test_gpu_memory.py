"""CUDA telemetry uses contemporaneous reservations and survives native teardown."""

from typing import Any

import pytest

from clearml_yolo.adapters.runtime.gpu_memory import GPUMemory
from clearml_yolo.application.training_workers import ProbeRankResult


def test_sampler_subtracts_current_reservation_not_allocator_peak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import torch

    calls: list[str] = []

    def synchronize(device: Any) -> None:
        assert device == 1
        calls.append("sync")

    def info(device: Any) -> tuple[int, int]:
        calls.append("driver")
        return 300, 1000

    def reserved(device: Any) -> int:
        calls.append("reserved")
        return 600

    def peak(device: Any) -> int:
        calls.append("peak")
        return 850

    monkeypatch.setattr(torch.cuda, "synchronize", synchronize)
    monkeypatch.setattr(torch.cuda, "mem_get_info", info)
    monkeypatch.setattr(torch.cuda, "memory_reserved", reserved)
    monkeypatch.setattr(torch.cuda, "max_memory_reserved", peak)
    memory = GPUMemory(1)
    memory.observe()
    assert calls == ["sync", "driver", "reserved", "peak"]
    assert memory.peak_memory_bytes == 850
    assert memory.non_allocator_memory_bytes == 100


def test_memory_envelopes_survive_allocator_clear_and_clamp_driver_rounding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import torch

    samples = iter([(1000, 300, 550, 850), (1000, 990, 11, 0)])
    current = (0, 0, 0, 0)

    def synchronize(device: Any) -> None:
        nonlocal current
        current = next(samples)

    monkeypatch.setattr(torch.cuda, "synchronize", synchronize)
    monkeypatch.setattr(torch.cuda, "mem_get_info", lambda _: (current[1], current[0]))
    monkeypatch.setattr(torch.cuda, "memory_reserved", lambda _: current[2])
    monkeypatch.setattr(torch.cuda, "max_memory_reserved", lambda _: current[3])
    memory = GPUMemory()
    memory.observe()
    memory.observe()
    assert memory.peak_memory_bytes == 850
    assert memory.non_allocator_memory_bytes == 150


def test_worker_receipt_rejects_negative_non_allocator_measurement() -> None:
    with pytest.raises(ValueError, match="non_allocator_memory_bytes"):
        ProbeRankResult.model_validate(
            {
                "token": "fixture",
                "rank": 0,
                "status": "success",
                "non_allocator_memory_bytes": -1,
            }
        )


def test_optional_allocator_reserve_leaves_driver_headroom(monkeypatch: pytest.MonkeyPatch) -> None:
    import torch

    from clearml_yolo.adapters.runtime.gpu_memory import reserve_cuda_memory

    gib = 1024**3
    limits: list[tuple[float, int]] = []
    monkeypatch.setattr(torch.cuda, "mem_get_info", lambda device: (12 * gib, 24 * gib))
    monkeypatch.setattr(torch.cuda, "memory_reserved", lambda device: gib)
    monkeypatch.setattr(
        torch.cuda, "set_per_process_memory_fraction", lambda fraction, device: limits.append((fraction, device))
    )
    assert reserve_cuda_memory(0, 0) is None
    assert not limits
    fraction = reserve_cuda_memory(8 * gib, 0)
    assert fraction == pytest.approx(4.75 / 24)
    assert limits == [(fraction, 0)]
    with pytest.raises(RuntimeError, match="reserve"):
        reserve_cuda_memory(13 * gib, 0)
