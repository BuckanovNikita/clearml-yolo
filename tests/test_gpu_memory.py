"""CUDA telemetry uses contemporaneous reservations and survives native teardown."""

from types import SimpleNamespace
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

    from clearml_yolo.adapters.runtime import gpu_inventory
    from clearml_yolo.adapters.runtime.gpu_memory import reserve_cuda_memory

    gib = 1024**3
    limits: list[tuple[float, int]] = []
    monkeypatch.setattr(torch.cuda, "mem_get_info", lambda device: (12 * gib, 24 * gib))
    monkeypatch.setattr(torch.cuda, "memory_reserved", lambda device: gib)
    monkeypatch.setattr(
        torch.cuda, "get_device_properties", lambda device: SimpleNamespace(uuid="selected", total_memory=24 * gib)
    )
    monkeypatch.setattr(
        gpu_inventory, "gpu_states", lambda: {"GPU-selected": gpu_inventory.GPUState(12 * gib, 0, frozenset(), free_bytes=12 * gib)}
    )
    monkeypatch.setattr(
        torch.cuda, "set_per_process_memory_fraction", lambda fraction, device: limits.append((fraction, device))
    )
    assert reserve_cuda_memory(0, 0) is None
    assert not limits
    fraction = reserve_cuda_memory(8 * gib)
    assert fraction == pytest.approx(4.75 / 24)
    assert limits == [(fraction, 0)]
    with pytest.raises(RuntimeError, match="reserve"):
        reserve_cuda_memory(13 * gib, 0)


@pytest.mark.parametrize(("cuda_free_gib", "whole_used_gib", "expected_budget_gib"), [(20, 10, 5.75), (12, 4, 3.75)])
def test_allocator_reserve_uses_lower_free_reading_for_visible_device(
    monkeypatch: pytest.MonkeyPatch, cuda_free_gib: int, whole_used_gib: int, expected_budget_gib: float
) -> None:
    import torch

    from clearml_yolo.adapters.runtime import gpu_inventory
    from clearml_yolo.adapters.runtime.gpu_memory import reserve_cuda_memory

    gib = 1024**3
    limits: list[tuple[float, int]] = []

    def properties(device: int) -> SimpleNamespace:
        assert device == 1
        return SimpleNamespace(uuid="visible-selected", total_memory=24 * gib)

    def memory_info(device: int) -> tuple[int, int]:
        assert device == 1
        return cuda_free_gib * gib, 24 * gib

    def reserved(device: int) -> int:
        assert device == 1
        return 0

    monkeypatch.setattr(torch.cuda, "mem_get_info", memory_info)
    monkeypatch.setattr(torch.cuda, "memory_reserved", reserved)
    monkeypatch.setattr(torch.cuda, "get_device_properties", properties)
    monkeypatch.setattr(
        gpu_inventory,
        "gpu_states",
        lambda: {
            "GPU-other": gpu_inventory.GPUState(23 * gib, 0, frozenset(), free_bytes=gib),
            "GPU-visible-selected": gpu_inventory.GPUState(whole_used_gib * gib, 0, frozenset(), free_bytes=(24 - whole_used_gib) * gib),
        },
    )
    monkeypatch.setattr(
        torch.cuda, "set_per_process_memory_fraction", lambda fraction, device: limits.append((fraction, device))
    )
    fraction = reserve_cuda_memory(8 * gib, 1)
    assert fraction == pytest.approx(expected_budget_gib / 24)
    assert limits == [(fraction, 1)]


@pytest.mark.parametrize("whole_used_gib", [None, 23, 15.75])
def test_allocator_reserve_refuses_missing_or_insufficient_whole_device_memory(
    monkeypatch: pytest.MonkeyPatch, whole_used_gib: float | None
) -> None:
    import torch

    from clearml_yolo.adapters.runtime import gpu_inventory
    from clearml_yolo.adapters.runtime.gpu_memory import reserve_cuda_memory

    gib = 1024**3
    limits: list[float] = []
    monkeypatch.setattr(torch.cuda, "mem_get_info", lambda device: (20 * gib, 24 * gib))
    monkeypatch.setattr(torch.cuda, "memory_reserved", lambda device: 0)
    monkeypatch.setattr(
        torch.cuda, "get_device_properties", lambda device: SimpleNamespace(uuid="selected", total_memory=24 * gib)
    )
    states = (
        {}
        if whole_used_gib is None
        else {"GPU-selected": gpu_inventory.GPUState(int(whole_used_gib * gib), 0, frozenset(), free_bytes=int((24 - whole_used_gib) * gib))}
    )
    monkeypatch.setattr(gpu_inventory, "gpu_states", lambda: states)
    monkeypatch.setattr(torch.cuda, "set_per_process_memory_fraction", lambda fraction, device: limits.append(fraction))
    with pytest.raises(RuntimeError, match="reserve"):
        reserve_cuda_memory(8 * gib, 0)
    assert not limits


def test_disabled_or_invalid_allocator_reserve_never_queries_hardware(monkeypatch: pytest.MonkeyPatch) -> None:
    import torch

    from clearml_yolo.adapters.runtime import gpu_inventory
    from clearml_yolo.adapters.runtime.gpu_memory import reserve_cuda_memory

    def unexpected(*args: object) -> Any:
        pytest.fail("Disabled or invalid reserve queried hardware")

    monkeypatch.setattr(torch.cuda, "mem_get_info", unexpected)
    monkeypatch.setattr(torch.cuda, "get_device_properties", unexpected)
    monkeypatch.setattr(gpu_inventory, "gpu_states", unexpected)
    assert reserve_cuda_memory(0, 0) is None
    with pytest.raises(ValueError, match="negative"):
        reserve_cuda_memory(-1, 0)


@pytest.mark.parametrize(
    ("cuda_total_mib", "cuda_free_mib", "budget_mib"),
    [(32579.75, 18000, 7936), (32768, 18000, 7936), (32579.75, 12288, 3840)],
)
def test_allocator_reserve_does_not_mix_cuda_and_nvml_memory_totals(
    monkeypatch: pytest.MonkeyPatch, cuda_total_mib: float, cuda_free_mib: int, budget_mib: int
) -> None:
    import torch

    from clearml_yolo.adapters.runtime import gpu_inventory
    from clearml_yolo.adapters.runtime.gpu_memory import reserve_cuda_memory

    mib = 1024**2
    total = int(cuda_total_mib * mib)
    limits: list[tuple[float, int]] = []

    def query(selector: str) -> list[list[str]]:
        return [] if selector.startswith("--query-compute-apps=") else [["GPU-selected", "32607", "16384", "0"]]

    monkeypatch.setattr(gpu_inventory, "_query", query)
    monkeypatch.setattr(torch.cuda, "mem_get_info", lambda device: (cuda_free_mib * mib, total))
    monkeypatch.setattr(torch.cuda, "memory_reserved", lambda device: 0)
    monkeypatch.setattr(
        torch.cuda, "get_device_properties", lambda device: SimpleNamespace(uuid="selected", total_memory=total)
    )
    monkeypatch.setattr(
        torch.cuda, "set_per_process_memory_fraction", lambda fraction, device: limits.append((fraction, device))
    )
    fraction = reserve_cuda_memory(8 * 1024**3, 0)
    assert fraction == pytest.approx(budget_mib / cuda_total_mib)
    assert limits == [(fraction, 0)]
