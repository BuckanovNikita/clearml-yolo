"""Foreign GPU workloads remain protected even when a trial has native children."""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

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


def test_driver_reserved_memory_is_unavailable_to_reserve_monitor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Real NVML reports total = used + reserved + free, not just used + free.
    values = {
        "uuid": "GPU-test",
        "memory.total": "24576",
        "memory.used": "10240",
        "memory.free": "5120",
        "utilization.gpu": "0",
    }

    def query(selector: str) -> list[list[str]]:
        if selector.startswith("--query-compute-apps="):
            return []
        return [[values[field] for field in selector.partition("=")[2].split(",")]]

    monkeypatch.setattr(gpu, "_query", query)
    device = _device().model_copy(update={"total_memory_bytes": 24 * 1024**3})
    unavailable = gpu.monitor_devices((device,), lambda: ())
    with pytest.raises(RuntimeError, match="reserve"):
        gpu.require_memory_reserve((device,), unavailable, 8 * 1024**3)
    assert unavailable == (19 * 1024**3,)


def test_queried_processes_remain_bound_to_their_gpu_uuid(monkeypatch: pytest.MonkeyPatch) -> None:
    def query(selector: str) -> list[list[str]]:
        if selector.startswith("--query-compute-apps="):
            return [["GPU-test", "10"], ["GPU-test", "11"], ["GPU-peer", "12"]]
        # Inventory order need not match either the process list or selection.
        return [["GPU-peer", "100", "70", "0"], ["GPU-test", "100", "80", "0"]]

    monkeypatch.setattr(gpu, "_query", query)
    device = _device().model_copy(update={"total_memory_bytes": 100 * 1024**2})
    peer = device.model_copy(update={"index": 1, "uuid": "GPU-peer"})
    # A foreign process on an unselected GPU cannot contaminate the selected GPU.
    assert gpu.monitor_devices((device,), lambda: (10, 11)) == (20 * 1024**2,)
    with pytest.raises(RuntimeError, match=r"foreign PIDs \[12\]"):
        gpu.monitor_devices((device, peer), lambda: (10, 11))
    assert gpu.monitor_devices((device, peer), lambda: (10, 11, 12)) == (20 * 1024**2, 30 * 1024**2)
    with pytest.raises(RuntimeError, match="busy"):
        gpu.require_idle((device,), force=True)


@pytest.mark.parametrize("free_mib", [0, 100])
def test_valid_memory_endpoints_preserve_exact_reserve_boundary(monkeypatch: pytest.MonkeyPatch, free_mib: int) -> None:
    def query(selector: str) -> list[list[str]]:
        return [] if selector.startswith("--query-compute-apps=") else [["GPU-test", "100", str(free_mib), "0"]]

    monkeypatch.setattr(gpu, "_query", query)
    device = _device().model_copy(update={"total_memory_bytes": 100 * 1024**2})
    unavailable = gpu.monitor_devices((device,), lambda: ())
    # Empty and full devices both produce valid telemetry, including zero-reserve
    # use. Admission accepts equality and rejects even one byte more than free.
    gpu.require_memory_reserve((device,), unavailable, free_mib * 1024**2)
    with pytest.raises(RuntimeError, match="reserve"):
        gpu.require_memory_reserve((device,), unavailable, free_mib * 1024**2 + 1)


@pytest.mark.parametrize("pids", [frozenset({10}), frozenset({10, 11})])
def test_measurements_accept_owned_ranks_and_compiler_children(
    monkeypatch: pytest.MonkeyPatch, pids: frozenset[int]
) -> None:
    monkeypatch.setattr(gpu, "gpu_states", lambda: {"GPU-test": gpu.GPUState(50, 75, pids, free_bytes=50)})
    assert gpu.monitor_devices((_device(),), lambda: (10, 11)) == (50,)


@pytest.mark.parametrize(
    ("state", "message"),
    [
        (gpu.GPUState(50, 75, frozenset({10, 12}), free_bytes=50), "foreign PIDs"),
        (gpu.GPUState(50, 75, frozenset(), free_bytes=50), "no PID telemetry"),
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
    states = iter([gpu.GPUState(10, 20, frozenset(), free_bytes=90), gpu.GPUState(10, 0, frozenset(), free_bytes=90)])
    monkeypatch.setattr(gpu, "gpu_states", lambda: {"GPU-test": next(states)})
    delays: list[float] = []
    monkeypatch.setattr(time, "sleep", delays.append)
    assert gpu.require_idle((_device(),)) == (10,)
    assert delays == [0.1]


def test_idle_baseline_uses_fresh_telemetry_in_selected_device_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    peer = _device().model_copy(update={"index": 1, "uuid": "GPU-peer"})
    monkeypatch.setattr(
        gpu,
        "gpu_states",
        lambda: {
            "GPU-test": gpu.GPUState(40, 0, frozenset(), free_bytes=60),
            "GPU-peer": gpu.GPUState(70, 0, frozenset(), free_bytes=30),
        },
    )
    assert gpu.require_idle((peer, _device())) == (70, 40)


def test_idle_preflight_never_waits_on_or_accepts_foreign_compute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gpu, "gpu_states", lambda: {"GPU-test": gpu.GPUState(10, 0, frozenset({42}), free_bytes=90)})
    monkeypatch.setattr(time, "sleep", lambda _: pytest.fail("Must reject foreign process"))
    with pytest.raises(RuntimeError, match="busy"):
        gpu.require_idle((_device(),))


def test_idle_preflight_remains_bounded_when_unidentified_activity_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    elapsed = 0.0
    delays: list[float] = []

    def sleep(seconds: float) -> None:
        nonlocal elapsed
        assert 0 < seconds <= 0.1
        elapsed += seconds
        delays.append(seconds)

    monkeypatch.setattr(time, "monotonic", lambda: elapsed)
    monkeypatch.setattr(time, "sleep", sleep)
    monkeypatch.setattr(gpu, "gpu_states", lambda: {"GPU-test": gpu.GPUState(10, 30, frozenset(), free_bytes=90)})
    with pytest.raises(RuntimeError, match="GPU 0 is busy"):
        gpu.require_idle((_device(),))
    assert 2 <= elapsed < 2.1
    assert delays


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
    monkeypatch.setattr(gpu, "gpu_states", lambda: {"GPU-test": gpu.GPUState(50, 75, frozenset({202}), free_bytes=50)})
    assert gpu.monitor_devices((_device(),), tree.live_pids) == (50,)

    def changed_telemetry() -> dict[str, gpu.GPUState]:
        if replacement:
            table[202] = process_tree._Process(202, 1, 202, 3, "S")
        else:
            del table[202]
        return {"GPU-test": gpu.GPUState(50, 75, frozenset({202}), free_bytes=50)}

    monkeypatch.setattr(gpu, "gpu_states", changed_telemetry)
    with pytest.raises(RuntimeError, match=r"foreign PIDs \[202\]"):
        gpu.monitor_devices((_device(),), tree.live_pids)


@pytest.mark.parametrize("field", ["memory.total", "memory.free", "utilization.gpu", "pid"])
def test_malformed_numeric_telemetry_is_an_actionable_unavailable_failure(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    values = {"memory.total": "100", "memory.free": "50", "utilization.gpu": "75", "pid": "42"}
    values[field] = "[Generic operating system error]"
    queries = iter(
        [
            [["GPU-test", values["memory.total"], values["memory.free"], values["utilization.gpu"]]],
            [["GPU-test", values["pid"]]],
        ]
    )
    monkeypatch.setattr(gpu, "_query", lambda _: next(queries))
    with pytest.raises(RuntimeError, match=f"GPU telemetry unavailable.*{field}"):
        gpu.gpu_states()


@pytest.mark.parametrize(("total", "free"), [("0", "0"), ("-1", "0"), ("100", "-1"), ("100", "101")])
def test_inconsistent_memory_telemetry_is_unavailable(monkeypatch: pytest.MonkeyPatch, total: str, free: str) -> None:
    queries = iter([[["GPU-test", total, free, "0"]], []])
    monkeypatch.setattr(gpu, "_query", lambda _: next(queries))
    with pytest.raises(RuntimeError, match="inconsistent total/free"):
        gpu.gpu_states()


def test_force_allows_unattributed_activity_but_keeps_live_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gpu, "gpu_states", lambda: {"GPU-test": gpu.GPUState(70, 65, frozenset(), free_bytes=30)})
    assert gpu.require_idle((_device(),), force=True) == (70,)
    assert gpu.monitor_devices((_device(),), lambda: (), force=True) == (70,)


@pytest.mark.parametrize("missing", [False, True])
def test_force_still_rejects_foreign_compute_and_missing_telemetry(
    monkeypatch: pytest.MonkeyPatch,
    missing: bool,
) -> None:
    states = {} if missing else {"GPU-test": gpu.GPUState(70, 65, frozenset({42}), free_bytes=30)}
    monkeypatch.setattr(gpu, "gpu_states", lambda: states)
    with pytest.raises(RuntimeError, match=r"busy|unavailable"):
        gpu.require_idle((_device(),), force=True)
    with pytest.raises(RuntimeError, match=r"foreign PIDs|telemetry disappeared"):
        gpu.monitor_devices((_device(),), lambda: (10,), force=True)


def _fake_nvidia_smi(directory: Path, body: str) -> None:
    directory.mkdir()
    script = directory / "nvidia-smi"
    script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    script.chmod(0o755)


def _metadata_child(monkeypatch: pytest.MonkeyPatch, directory: Path, body: str) -> None:
    """Replace only the child interpreter's CUDA boundary, never its product script."""
    module = directory / "fake-cuda"
    module.mkdir()
    (module / "torch.py").write_text(body, encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(module))
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")


def test_discovery_executes_isolated_metadata_script_and_joins_visible_uuid_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    _metadata_child(
        monkeypatch,
        tmp_path,
        "from types import SimpleNamespace\n"
        "import sys\n"
        "print('metadata diagnostic', file=sys.stderr)\n"
        "devices = [SimpleNamespace(uuid='second', name='Second CUDA device', total_memory=209715200),\n"
        "           SimpleNamespace(uuid='first', name='First CUDA device', total_memory=104857600)]\n"
        "cuda = SimpleNamespace(device_count=lambda: len(devices), get_device_properties=devices.__getitem__)\n",
    )
    _fake_nvidia_smi(
        tmp_path / "bin",
        'case "$1" in\n'
        "  --query-gpu=*) printf 'GPU-first, 120, 50, 0\\nGPU-second, 210, 150, 7\\n' ;;\n"
        "  --query-compute-apps=*) exit 0 ;;\n"
        "  *) exit 2 ;;\nesac",
    )
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    assert [device.model_dump() for device in gpu.discover_gpus()] == [
        {
            "index": 0,
            "uuid": "GPU-second",
            "name": "Second CUDA device",
            "total_memory_bytes": 209715200,
            "used_memory_bytes": 52428800,
            "utilization": 7,
        },
        {
            "index": 1,
            "uuid": "GPU-first",
            "name": "First CUDA device",
            "total_memory_bytes": 104857600,
            "used_memory_bytes": 52428800,
            "utilization": 0,
        },
    ]
    assert capfd.readouterr() == ("", "")


def test_discovery_preserves_metadata_child_exit_and_captured_diagnostics(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _metadata_child(
        monkeypatch,
        tmp_path,
        "import sys\nprint('metadata context')\n"
        "print('CUDA metadata unavailable', file=sys.stderr)\nraise SystemExit(23)\n",
    )
    with pytest.raises(subprocess.CalledProcessError) as caught:
        gpu.discover_gpus()
    assert caught.value.returncode == 23
    assert caught.value.stdout == "metadata context\n"
    assert caught.value.stderr == "CUDA metadata unavailable\n"


@pytest.mark.parametrize(("device_count", "message"), [(0, "No visible CUDA GPUs"), (1, "lacks whole-GPU telemetry")])
def test_discovery_explains_absent_visible_devices_or_nvml_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, device_count: int, message: str
) -> None:
    _metadata_child(
        monkeypatch,
        tmp_path,
        "from types import SimpleNamespace\n"
        f"cuda = SimpleNamespace(device_count=lambda: {device_count}, "
        "get_device_properties=lambda index: SimpleNamespace(uuid='missing', name='test', total_memory=104857600))\n",
    )
    _fake_nvidia_smi(tmp_path / "bin", "exit 0")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    with pytest.raises(RuntimeError, match=message):
        gpu.discover_gpus()


def test_discovery_bounds_and_reaps_stalled_metadata_child(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pid_file = tmp_path / "metadata.pid"
    _metadata_child(
        monkeypatch,
        tmp_path,
        "import os, time\nfrom pathlib import Path\n"
        f"Path({str(pid_file)!r}).write_text(str(os.getpid()))\ntime.sleep(60)\n",
    )
    run = subprocess.run

    def bounded(command: list[str], *, timeout: float, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        # Assert a bounded external-process policy, then accelerate only the clock
        # for this real sleeping child. Do not replace execution or termination.
        assert timeout is not None
        assert 0 < timeout <= 60
        return run(command, timeout=0.5, **kwargs)

    monkeypatch.setattr(subprocess, "run", bounded)
    with pytest.raises(subprocess.TimeoutExpired):
        gpu.discover_gpus()
    pid = int(pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_failed_query_keeps_its_type_and_attaches_nvml_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # NVML prints its failure on stdout; the exception text alone omits it.
    _fake_nvidia_smi(
        tmp_path / "bin",
        "echo 'Failed to initialize NVML: Generic operating system error'\necho 'driver unreachable' >&2\nexit 12",
    )
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    with pytest.raises(subprocess.CalledProcessError) as caught:
        gpu.gpu_states()
    assert type(caught.value) is subprocess.CalledProcessError
    assert caught.value.returncode == 12
    assert "NVML" not in str(caught.value)
    notes = "\n".join(caught.value.__notes__)
    assert "Failed to initialize NVML: Generic operating system error" in notes
    assert "driver unreachable" in notes


@pytest.mark.parametrize("output", [b"partial NVML output\n", "partial NVML output\n"], ids=["bytes", "text"])
def test_timed_out_query_keeps_its_type_and_attaches_partial_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, output: bytes | str
) -> None:
    _fake_nvidia_smi(tmp_path / "bin", "exit 0")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))

    def timeout(command: list[str], **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(command, 15, output=output, stderr=None)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        gpu.gpu_states()
    assert type(caught.value) is subprocess.TimeoutExpired
    assert caught.value.__notes__ == ["nvidia-smi stdout: partial NVML output"]


def test_failed_query_with_empty_streams_adds_no_notes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _fake_nvidia_smi(tmp_path / "bin", "exit 3")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    with pytest.raises(subprocess.CalledProcessError) as caught:
        gpu.gpu_states()
    assert not hasattr(caught.value, "__notes__")


def test_reserve_accepts_recorded_nvml_free_despite_lower_cuda_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mib = 1024**2

    def query(selector: str) -> list[list[str]]:
        return [] if selector.startswith("--query-compute-apps=") else [["GPU-test", "32607", "10261", "0"]]

    monkeypatch.setattr(gpu, "_query", query)
    device = _device().model_copy(update={"total_memory_bytes": 34_162_343_936})
    unavailable = gpu.monitor_devices((device,), lambda: ())
    gpu.require_memory_reserve((device,), unavailable, 10 * 1024**3)
    assert unavailable == (22_318 * mib + 786_432,)


@pytest.mark.parametrize(
    ("nvml_total_mib", "cuda_total_mib", "free_mib", "raw_used_mib", "used_mib", "passes_floor"),
    [
        (32607, 32579.75, 10261, 22346, 22318.75, True),
        (32607, 32579.75, 10240, 22367, 22339.75, True),
        (32607, 32579.75, 10239, 22368, 22340.75, False),
        (32579, 32607, 10261, 22318, 22346, True),
        (32579, 32607, 10239, 22340, 22368, False),
    ],
)
def test_discovery_admission_and_monitoring_use_coherent_free_memory(
    monkeypatch: pytest.MonkeyPatch,
    nvml_total_mib: int,
    cuda_total_mib: float,
    free_mib: int,
    raw_used_mib: int,
    used_mib: float,
    passes_floor: bool,
) -> None:
    mib = 1024**2
    record = {"index": 0, "uuid": "GPU-test", "name": "test", "total_memory_bytes": int(cuda_total_mib * mib)}

    def query(selector: str) -> list[list[str]]:
        return (
            []
            if selector.startswith("--query-compute-apps=")
            else [["GPU-test", str(nvml_total_mib), str(free_mib), "0"]]
        )

    monkeypatch.setattr(gpu, "_query", query)
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, json.dumps([record]))
    )
    state = gpu.gpu_states()["GPU-test"]
    assert state.used == raw_used_mib * mib
    assert state.free_bytes == free_mib * mib
    devices = gpu.discover_gpus()
    assert devices[0].total_memory_bytes == int(cuda_total_mib * mib)
    assert devices[0].used_memory_bytes == int(used_mib * mib)
    for unavailable in (gpu.require_idle(devices), gpu.monitor_devices(devices, lambda: ())):
        assert unavailable == (int(used_mib * mib),)
        gpu.require_memory_reserve(devices, unavailable, free_mib * mib)
        with pytest.raises(RuntimeError, match="reserve"):
            gpu.require_memory_reserve(devices, unavailable, free_mib * mib + 1)
        if passes_floor:
            gpu.require_memory_reserve(devices, unavailable, 10 * 1024**3)
        else:
            with pytest.raises(RuntimeError, match="reserve"):
                gpu.require_memory_reserve(devices, unavailable, 10 * 1024**3)


def test_normalized_memory_saturates_at_cuda_capacity_in_caller_order(monkeypatch: pytest.MonkeyPatch) -> None:
    mib = 1024**2
    devices = (
        _device().model_copy(update={"uuid": "GPU-peer", "total_memory_bytes": 100 * mib}),
        _device().model_copy(update={"total_memory_bytes": 200 * mib}),
    )

    def query(selector: str) -> list[list[str]]:
        return (
            []
            if selector.startswith("--query-compute-apps=")
            else [["GPU-test", "150", "70", "0"], ["GPU-peer", "200", "150", "0"]]
        )

    monkeypatch.setattr(gpu, "_query", query)
    for unavailable in (gpu.require_idle(devices), gpu.monitor_devices(devices, lambda: ())):
        assert unavailable == (0, 130 * mib)
        gpu.require_memory_reserve((devices[0],), (unavailable[0],), 100 * mib)
        with pytest.raises(RuntimeError, match="reserve"):
            gpu.require_memory_reserve((devices[0],), (unavailable[0],), 100 * mib + 1)
