"""Foreign GPU workloads remain protected even when a trial has native children."""

import time

import pytest

from clearml_yolo.adapters.runtime import gpu_inventory as gpu
from clearml_yolo.adapters.runtime import process_tree


def _device() -> gpu.GPUDevice:
    return gpu.GPUDevice(
        index=0,
        uuid="GPU-test",
        name="test",
        total_memory_bytes=100,
        used_memory_bytes=10,
        utilization=0,
    )


@pytest.mark.parametrize("pids", [frozenset({10}), frozenset({10, 11})])
def test_measurements_accept_owned_ranks_and_compiler_children(
    monkeypatch: pytest.MonkeyPatch, pids: frozenset[int]
) -> None:
    monkeypatch.setattr(gpu, "gpu_states", lambda: {"GPU-test": gpu.GPUState(50, 75, pids)})
    assert gpu.monitor_devices((_device(),), lambda: (10, 11)) == (50,)


@pytest.mark.parametrize(
    ("state", "message"),
    [
        (gpu.GPUState(50, 75, frozenset({10, 12})), "foreign PIDs"),
        (gpu.GPUState(50, 75, frozenset()), "no PID telemetry"),
    ],
)
def test_unowned_or_unidentifiable_activity_rejects_trial(
    monkeypatch: pytest.MonkeyPatch, state: gpu.GPUState, message: str
) -> None:
    monkeypatch.setattr(gpu, "gpu_states", lambda: {"GPU-test": state})
    with pytest.raises(RuntimeError, match=message):
        gpu.monitor_devices((_device(),), lambda: (10, 11))


def test_idle_preflight_waits_for_utilization_sampling_to_settle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    states = iter([gpu.GPUState(10, 20, frozenset()), gpu.GPUState(10, 0, frozenset())])
    monkeypatch.setattr(gpu, "gpu_states", lambda: {"GPU-test": next(states)})
    monkeypatch.setattr(time, "sleep", lambda _: None)
    assert gpu.require_idle((_device(),)) == (10,)


def test_idle_baseline_uses_fresh_telemetry_in_selected_device_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    peer = _device().model_copy(update={"index": 1, "uuid": "GPU-peer"})
    monkeypatch.setattr(
        gpu,
        "gpu_states",
        lambda: {
            "GPU-test": gpu.GPUState(40, 0, frozenset()),
            "GPU-peer": gpu.GPUState(70, 0, frozenset()),
        },
    )
    assert gpu.require_idle((peer, _device())) == (70, 40)


def test_idle_preflight_never_waits_on_or_accepts_foreign_compute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gpu, "gpu_states", lambda: {"GPU-test": gpu.GPUState(10, 0, frozenset({42}))}
    )
    monkeypatch.setattr(time, "sleep", lambda _: pytest.fail("Must reject foreign process"))
    with pytest.raises(RuntimeError, match="busy"):
        gpu.require_idle((_device(),))


def test_idle_preflight_remains_bounded_when_unidentified_activity_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticks = iter([0, 1, 2])
    monkeypatch.setattr(time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(time, "sleep", lambda _: None)
    monkeypatch.setattr(gpu, "gpu_states", lambda: {"GPU-test": gpu.GPUState(10, 30, frozenset())})
    with pytest.raises(RuntimeError, match="busy"):
        gpu.require_idle((_device(),))


@pytest.mark.parametrize("replacement", [True, False])
def test_telemetry_cannot_reuse_a_previously_owned_pid_after_its_identity_changes(
    monkeypatch: pytest.MonkeyPatch, replacement: bool
) -> None:
    table = {
        101: process_tree._Process(101, 1, 101, 1, "S"),
        202: process_tree._Process(202, 101, 202, 2, "S"),
    }
    monkeypatch.setattr(process_tree, "_read_process", table.get)
    tree = process_tree.LinuxProcessTree(101, "private-token", identities={202: 2})
    monkeypatch.setattr(tree, "_table", lambda: dict(table))
    monkeypatch.setattr(tree, "_marked", lambda _: False)
    monkeypatch.setattr(
        gpu, "gpu_states", lambda: {"GPU-test": gpu.GPUState(50, 75, frozenset({202}))}
    )
    assert gpu.monitor_devices((_device(),), tree.live_pids) == (50,)

    def changed_telemetry() -> dict[str, gpu.GPUState]:
        if replacement:
            table[202] = process_tree._Process(202, 1, 202, 3, "S")
        else:
            del table[202]
        return {"GPU-test": gpu.GPUState(50, 75, frozenset({202}))}

    monkeypatch.setattr(gpu, "gpu_states", changed_telemetry)
    with pytest.raises(RuntimeError, match=r"foreign PIDs \[202\]"):
        gpu.monitor_devices((_device(),), tree.live_pids)


@pytest.mark.parametrize("field", ["memory.used", "utilization.gpu", "pid"])
def test_malformed_numeric_telemetry_is_an_actionable_unavailable_failure(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    values = {"memory.used": "50", "utilization.gpu": "75", "pid": "42"}
    values[field] = "[Generic operating system error]"
    queries = iter([
        [["GPU-test", values["memory.used"], values["utilization.gpu"]]],
        [["GPU-test", values["pid"]]],
    ])
    monkeypatch.setattr(gpu, "_query", lambda _: next(queries))
    with pytest.raises(RuntimeError, match=f"GPU telemetry unavailable.*{field}"):
        gpu.gpu_states()
