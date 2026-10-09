"""Stateless polling selects free CUDA logical indices without reserving devices."""

import os
import time
from collections.abc import Sequence
from typing import override

import pytest
from loguru import logger

from clearml_yolo.adapters.runtime import gpu_wait
from clearml_yolo.adapters.runtime.gpu_resources import GPUDevice, GPUInventory


class _ChangingInventory(GPUInventory):
    def __init__(
        self, visible: tuple[str, ...], snapshots: Sequence[tuple[GPUDevice, ...] | BaseException]
    ) -> None:
        self.visibility = visible
        self.snapshots = iter(snapshots)

    @override
    def visible(self) -> tuple[str, ...]:
        return self.visibility

    @override
    def snapshot(self) -> tuple[GPUDevice, ...]:
        state = next(self.snapshots)
        if isinstance(state, BaseException):
            raise state
        return state


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    elapsed = [0.0]

    def sleep(delay: float) -> None:
        assert delay > 0
        elapsed[0] += delay

    monkeypatch.setattr(time, "sleep", sleep)
    monkeypatch.setattr(time, "monotonic", lambda: elapsed[0])
    return elapsed


def test_busy_gpus_are_polled_until_enough_are_free(clock: list[float]) -> None:
    inventory = _ChangingInventory(
        ("GPU-a", "GPU-b"),
        [
            (GPUDevice("GPU-a", True), GPUDevice("GPU-b", True)),
            (GPUDevice("GPU-a", False), GPUDevice("GPU-b", True)),
            (GPUDevice("GPU-a", False), GPUDevice("GPU-b", False)),
        ],
    )

    assert gpu_wait.wait_for_available_gpus(2, inventory=inventory) == (0, 1)
    assert clock[0] > 0


def test_selection_keeps_inherited_order_and_noncontiguous_logical_positions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "GPU-c,GPU-a,GPU-b")
    inventory = _ChangingInventory(
        ("GPU-c", "GPU-a", "GPU-b"),
        [(GPUDevice("GPU-a", True), GPUDevice("GPU-b", False), GPUDevice("GPU-c", False))],
    )

    assert gpu_wait.wait_for_available_gpus(2, inventory=inventory) == (0, 2)
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "GPU-c,GPU-a,GPU-b"


def test_zero_demand_bypasses_inventory_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_inventory() -> GPUInventory:
        pytest.fail("CPU/MPS requests must not discover GPU inventory")

    monkeypatch.setattr(gpu_wait, "GPUInventory", forbidden_inventory)
    assert gpu_wait.wait_for_available_gpus(0) == ()


@pytest.mark.parametrize("count", [-1, True, 1.5])
def test_invalid_count_fails_before_accessing_inventory(count: object) -> None:
    inventory = _ChangingInventory((), [])
    with pytest.raises((TypeError, ValueError), match="count"):
        gpu_wait.wait_for_available_gpus(count, inventory=inventory)  # type: ignore[arg-type]


@pytest.mark.parametrize("visible", [(), ("GPU-a",)])
def test_impossible_demand_fails_before_polling(visible: tuple[str, ...]) -> None:
    inventory = _ChangingInventory(visible, [])
    with pytest.raises(ValueError, match="visible"):
        gpu_wait.wait_for_available_gpus(2, inventory=inventory)


def test_disappearing_visible_gpu_fails_instead_of_waiting_forever(
    clock: list[float],
) -> None:
    inventory = _ChangingInventory(
        ("GPU-a", "GPU-b"),
        [
            (GPUDevice("GPU-a", True), GPUDevice("GPU-b", False)),
            (GPUDevice("GPU-b", False),),
        ],
    )
    with pytest.raises(RuntimeError, match=r"visibility.*GPU-a"):
        gpu_wait.wait_for_available_gpus(2, inventory=inventory)


def test_telemetry_failure_during_wait_propagates(clock: list[float]) -> None:
    failure = RuntimeError("compute process telemetry unavailable")
    inventory = _ChangingInventory(("GPU-a",), [(GPUDevice("GPU-a", True),), failure])
    with pytest.raises(RuntimeError, match="telemetry unavailable") as caught:
        gpu_wait.wait_for_available_gpus(1, inventory=inventory)
    assert caught.value is failure


def test_visibility_discovery_failure_propagates() -> None:
    class BrokenVisibility(_ChangingInventory):
        @override
        def visible(self) -> tuple[str, ...]:
            raise RuntimeError("visibility probe failed")

    with pytest.raises(RuntimeError, match="visibility probe failed"):
        gpu_wait.wait_for_available_gpus(1, inventory=BrokenVisibility((), []))


def test_interruption_during_wait_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def interrupted_sleep(_delay: float) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(time, "sleep", interrupted_sleep)
    inventory = _ChangingInventory(("GPU-a",), [(GPUDevice("GPU-a", True),)])
    with pytest.raises(KeyboardInterrupt):
        gpu_wait.wait_for_available_gpus(1, inventory=inventory)


def test_waiting_logs_are_periodic_without_flooding(clock: list[float]) -> None:
    messages: list[str] = []

    def sink(message: object) -> None:
        messages.append(str(message))

    handler = logger.add(sink, format="{message}", level="INFO")
    inventory = _ChangingInventory(
        ("GPU-a",), [(GPUDevice("GPU-a", True),)] * 65 + [(GPUDevice("GPU-a", False),)]
    )
    try:
        assert gpu_wait.wait_for_available_gpus(1, inventory=inventory) == (0,)
    finally:
        logger.remove(handler)
    waiting_messages = [message for message in messages if "Waiting" in message]
    assert 2 <= len(waiting_messages) <= 4
