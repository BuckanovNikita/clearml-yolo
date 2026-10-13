"""Admission explanations reflect the telemetry and registry used to decide."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from clearml_yolo.adapters.runtime.gpu_queue import GPUQueue
from clearml_yolo.adapters.runtime.gpu_resources import GPUDevice
from test_gpu_queue import MutableInventory


def test_five_of_eight_admits_immediately_and_records_immutable_decision(tmp_path: Path) -> None:
    visible = tuple(f"GPU-{index}" for index in range(8))
    queue = GPUQueue(tmp_path, MutableInventory(*(GPUDevice(uuid, False) for uuid in visible)))
    ticket = queue.register(5, visible)
    try:
        assert ticket.try_acquire() == visible[:5]
        decision = ticket.diagnostics
        assert decision is not None
        assert (decision.requested_count, decision.visible_count, decision.eligible_count) == (
            5,
            8,
            8,
        )
        assert decision.admitted == visible[:5]
        with pytest.raises(FrozenInstanceError):
            decision.eligible_count = 0  # type: ignore[misc]
    finally:
        ticket.close()


def test_reported_memory_sample_admits_five_through_real_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.runtime import gpu_resources
    from clearml_yolo.adapters.runtime.gpu_resources import GPUInventory
    from test_gpu_resources import _FakeNVML, _install_nvml

    visible = tuple(f"GPU-{index}" for index in range(8))
    _install_nvml(
        monkeypatch,
        _FakeNVML(
            uuids=visible,
            used_memory=tuple(value * 1024**2 for value in (1215, 3, 409, 3, 3, 3, 3, 3)),
        ),
    )
    monkeypatch.setattr(gpu_resources, "_probe_visible_uuids", lambda: visible)
    inventory = GPUInventory()
    ticket = GPUQueue(tmp_path, inventory).register(5, inventory.visible())
    try:
        assert ticket.try_acquire() == visible[:5]
        assert ticket.diagnostics is not None
        assert ticket.diagnostics.eligible_count == 8
    finally:
        ticket.close()


def test_fifo_and_reservations_are_distinct_and_release_admits_five(tmp_path: Path) -> None:
    visible = tuple(f"GPU-{index}" for index in range(8))
    inventory = MutableInventory(*(GPUDevice(uuid, False) for uuid in visible))
    queue = GPUQueue(tmp_path, inventory)
    owner = queue.register(4, visible)
    head = queue.register(5, visible)
    follower = queue.register(1, visible)
    try:
        assert owner.try_acquire() == visible[:4]
        assert head.try_acquire() is None
        assert follower.try_acquire() is None
        decision = follower.diagnostics
        assert decision is not None
        assert decision.eligible_count == 4
        assert decision.queue_position == 2
        assert decision.fifo_blocked_by == head.id
        assert not decision.insufficient_capacity
        assert all(card.eligible for card in decision.cards[4:])
        assert all(card.reserved_by == owner.id for card in decision.cards[:4])
        assert head.diagnostics is not None
        assert head.diagnostics.insufficient_capacity
        owner.close()
        assert head.try_acquire() == visible[:5]
        assert follower.try_acquire() == (visible[5],)
    finally:
        owner.close()
        head.close()
        follower.close()


def test_exact_selection_distinguishes_hidden_and_excluded_cards(tmp_path: Path) -> None:
    inventory = MutableInventory(*(GPUDevice(f"GPU-{index}", False) for index in range(4)))
    queue = GPUQueue(tmp_path, inventory)
    ticket = queue.register(1, ("GPU-3",), cuda_visible=("GPU-3", "GPU-1"))
    try:
        assert ticket.try_acquire() == ("GPU-3",)
        decision = ticket.diagnostics
        assert decision is not None
        cards = {card.device.uuid: card for card in decision.cards}
        assert decision.visible_count == 2
        assert cards["GPU-3"].logical_index == 0
        assert cards["GPU-3"].eligible
        assert cards["GPU-1"].logical_index == 1
        assert not cards["GPU-1"].in_selection
        assert cards["GPU-0"].logical_index is None
    finally:
        ticket.close()


def test_refresh_tracks_reasons_not_small_memory_changes(tmp_path: Path) -> None:
    from clearml_yolo.entrypoints.hydra.execution import DecisionReporter

    inventory = MutableInventory(GPUDevice("GPU-0", True))
    ticket = GPUQueue(tmp_path, inventory).register(1, ("GPU-0",))
    try:
        assert ticket.try_acquire() is None
        decision = ticket.diagnostics
        assert decision is not None
        reporter = DecisionReporter()
        assert reporter.message(decision, now=0) is not None
        assert reporter.message(decision, now=1) is None
        changed = replace(decision, cards=(replace(decision.cards[0], reserved_by="42"),))
        assert reporter.message(changed, now=1) is None
        assert reporter.message(changed, now=5) is not None
        assert reporter.message(changed, now=34) is None
        assert reporter.message(changed, now=35) is not None
    finally:
        ticket.close()


def test_per_card_output_uses_cuda_indexes_and_simultaneous_blockers(tmp_path: Path) -> None:
    from clearml_yolo.entrypoints.hydra.execution import format_decision

    inventory = MutableInventory(
        GPUDevice("GPU-hidden", False, physical_index=0, used_memory_bytes=0),
        GPUDevice("GPU-idle", False, physical_index=1, used_memory_bytes=3 * 1024**2),
        GPUDevice("GPU-excluded", False, physical_index=2, used_memory_bytes=0),
        GPUDevice("GPU-loaded", False, physical_index=3, used_memory_bytes=0),
    )
    visible = ("GPU-loaded", "GPU-idle", "GPU-excluded")
    queue = GPUQueue(tmp_path, inventory)
    owner = queue.register(1, visible)
    waiting = queue.register(2, visible[:2], cuda_visible=visible)
    try:
        assert owner.try_acquire() == ("GPU-loaded",)
        inventory.devices = (
            *inventory.devices[:3],
            GPUDevice("GPU-loaded", True, physical_index=3, used_memory_bytes=2 * 1024**3),
        )
        assert waiting.try_acquire() is None
        decision = waiting.diagnostics
        assert decision is not None
        message = format_decision(decision)
        assert "requested 2, visible 3, eligible 1, memory < 2 GiB" in message
        assert (
            "GPU 0 (physical GPU 3): memory 2.000 GiB at/above threshold 2 GiB; "
            "reserved by ticket 1" in message
        )
        assert "GPU 1: eligible" in message
        assert "GPU 2: outside the exact selection" in message
        assert "Physical GPU 0: outside CUDA visibility" in message
        assert "Insufficient eligible capacity" in message
        assert "FIFO" not in message
        assert all(uuid not in message for uuid in visible)
    finally:
        owner.close()
        waiting.close()


def test_decision_uses_one_unlocked_telemetry_sample_and_remains_detached(tmp_path: Path) -> None:
    from clearml_yolo.entrypoints.hydra.execution import format_decision

    inventory = MutableInventory(GPUDevice("GPU-0", True))
    queue = GPUQueue(tmp_path, inventory)
    calls: list[bool] = []
    original = inventory.snapshot

    def snapshot() -> tuple[GPUDevice, ...]:
        calls.append(queue._registry_lock.is_locked)
        return original()

    inventory.snapshot = snapshot  # type: ignore[method-assign]
    ticket = queue.register(1, ("GPU-0",))
    try:
        assert ticket.try_acquire() is None
        decision = ticket.diagnostics
        assert decision is not None
        assert calls == [False]
        inventory.devices = (GPUDevice("GPU-0", False),)
        assert "at/above threshold" in format_decision(decision)
        assert calls == [False]
        assert ticket.try_acquire() == ("GPU-0",)
        assert decision.insufficient_capacity
    finally:
        ticket.close()


def test_measured_memory_fluctuations_do_not_refresh_until_heartbeat(tmp_path: Path) -> None:
    from clearml_yolo.entrypoints.hydra.execution import DecisionReporter

    inventory = MutableInventory(GPUDevice("GPU-0", True, used_memory_bytes=3 * 1024**3))
    ticket = GPUQueue(tmp_path, inventory).register(1, ("GPU-0",))
    try:
        assert ticket.try_acquire() is None
        initial = ticket.diagnostics
        assert initial is not None
        reporter = DecisionReporter()
        assert reporter.message(initial, now=0) is not None
        inventory.devices = (replace(inventory.devices[0], used_memory_bytes=3 * 1024**3 + 50),)
        assert ticket.try_acquire() is None
        changed = ticket.diagnostics
        assert changed is not None
        assert reporter.message(changed, now=10) is None
        assert reporter.message(changed, now=29) is None
        assert reporter.message(changed, now=30) is not None
    finally:
        ticket.close()
