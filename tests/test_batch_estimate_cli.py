"""CLI filters and composition remain local and require explicit idle devices."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self
from uuid import uuid4

import pytest

from clearml_yolo.adapters.runtime.gpu_inventory import GPUDevice
from clearml_yolo.adapters.storage.batch_estimates import FileBatchEstimateStore
from clearml_yolo.application.training_workers import BatchCaseRequest
from clearml_yolo.entrypoints import batch_estimate as cli
from clearml_yolo.entrypoints import batch_estimate_worker
from test_batch_estimate_workflow import RecordingProbe


class RecordingCasePool:
    """Execute bounded fake probes while retaining dispatch/completion ordering."""

    def __init__(self) -> None:
        self.started: list[tuple[str, str]] = []
        self.pending: list[SimpleNamespace] = []
        self.maximum_active = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        pass

    def start(self, key: str, command: Any) -> None:
        path = Path(command.argv[-1])
        request = BatchCaseRequest.model_validate_json(path.read_text(encoding="utf-8"))
        visibility = command.environment["CUDA_VISIBLE_DEVICES"]
        assert visibility == request.profile.gpus[0].uuid
        assert all(visibility != item.gpu for item in self.pending)
        self.started.append((key, visibility))
        code = batch_estimate_worker.run(path)
        self.pending.append(SimpleNamespace(
            key=key, gpu=visibility, exit_code=code, cleanup_complete=True, diagnostic="",
        ))
        self.maximum_active = max(self.maximum_active, len(self.pending))

    def poll(self) -> tuple[Any, ...]:
        completed = tuple(reversed(self.pending))
        self.pending.clear()
        return completed


def _available_devices() -> tuple[GPUDevice, ...]:
    return tuple(
        GPUDevice(
            index=index,
            uuid=f"GPU-{index}",
            name="GPU",
            total_memory_bytes=1000,
            used_memory_bytes=0,
            utilization=0,
        )
        for index in range(3)
    )


def _install(
    monkeypatch: pytest.MonkeyPatch, *, capacity: int = 4
) -> tuple[RecordingProbe, list[tuple[int, ...]]]:
    devices = _available_devices()
    idle_checks: list[tuple[int, ...]] = []
    monkeypatch.setattr(cli, "discover_gpus", lambda: devices)
    monkeypatch.setattr(
        cli, "require_idle", lambda selected: idle_checks.append(tuple(g.index for g in selected))
    )
    probe = RecordingProbe(capacity=capacity)
    monkeypatch.setattr(cli, "_make_probe", lambda: probe)
    monkeypatch.setattr(batch_estimate_worker, "_make_probe", lambda: probe)
    monkeypatch.setattr(cli, "_make_pool", RecordingCasePool, raising=False)
    return probe, idle_checks


def test_help_has_no_gpu_or_workspace_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "discover_gpus", lambda: pytest.fail("help discovered GPUs"))
    with pytest.raises(SystemExit) as stopped:
        cli.main(["--help"])
    assert stopped.value.code == 0
    assert "--gpu-counts" in capsys.readouterr().out
    assert not (tmp_path / ".config").exists()
    assert not (tmp_path / ".tmp").exists()


def test_filters_defaults_resume_and_refresh(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    probe, checks = _install(monkeypatch)
    arguments = [
        "--imgsz",
        "960",
        "--models",
        "yolo11n,rfdetr/small",
        "--devices",
        "2,0",
        "--search-limit",
        "4",
    ]
    cli.main(arguments)
    assert checks == [(2,), (0,)]
    cases = FileBatchEstimateStore().read().cases
    assert len(cases) == 2
    assert {case.profile.world_size for case in cases} == {1}
    assert all(
        case.workload.classes == 150 and case.workload.objects_per_image == 300 for case in cases
    )
    assert all(case.settings.memory_fraction == 0.9 for case in cases)
    calls = probe.calls
    cli.main(arguments)
    assert probe.calls == calls
    output = capsys.readouterr().out
    assert "cached" in output
    assert "gpus=2\tglobal_batch=8" in output
    assert "extrapolated" in output
    assert all(profile.world_size == 1 for profile in probe.probed_profiles)
    cli.main([*arguments, "--refresh"])
    assert probe.calls == calls * 2


def test_count_and_workload_controls_are_forwarded(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch)
    cli.main(
        [
            "--imgsz",
            "640",
            "--models",
            "yolo11n",
            "--gpu-counts",
            "2",
            "--classes",
            "5",
            "--objects-per-image",
            "20",
            "--memory-budget",
            "0.85",
            "--search-limit",
            "4",
            "--trial-timeout",
            "17",
        ]
    )
    (case,) = FileBatchEstimateStore().read().cases
    assert case.profile.world_size == 1
    assert case.profile.nominal_size == (640, 640)
    assert (case.workload.classes, case.workload.objects_per_image) == (5, 20)
    assert case.settings.memory_fraction == 0.85
    assert case.settings.trial_timeout_seconds == 17


@pytest.mark.parametrize(
    "option",
    [
        ["--models", "unknown"],
        ["--devices", "0,0"],
        ["--devices", "9"],
        ["--gpu-counts", "0"],
        ["--gpu-counts", "4"],
        ["--memory-budget", "1.1"],
        ["--search-limit", "0"],
        ["--classes", "0"],
        ["--trial-timeout", "-1"],
        ["--jobs", "0"],
        ["--jobs", "-1"],
    ],
)
def test_invalid_options_fail_without_trials(
    monkeypatch: pytest.MonkeyPatch, option: list[str]
) -> None:
    probe, _ = _install(monkeypatch)
    with pytest.raises(SystemExit) as stopped:
        cli.main(["--imgsz", "960", *option])
    assert stopped.value.code == 2
    assert probe.calls == 0


def test_busy_gpu_aborts_without_native_work(monkeypatch: pytest.MonkeyPatch) -> None:
    probe, _ = _install(monkeypatch)

    def busy(*args: Any) -> None:
        raise RuntimeError("selected GPU is busy")

    monkeypatch.setattr(cli, "require_idle", busy)
    with pytest.raises(SystemExit) as stopped:
        cli.main(["--imgsz", "960", "--models", "yolo11n"])
    assert stopped.value.code == 1
    assert probe.calls == 0


def test_failed_case_is_saved_reported_and_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install(monkeypatch, capacity=0)
    with pytest.raises(SystemExit) as stopped:
        cli.main(["--imgsz", "960", "--models", "yolo11n", "--gpu-counts", "1"])
    assert stopped.value.code == 1
    assert "no_capacity" in capsys.readouterr().out
    assert FileBatchEstimateStore().read().cases[0].status == "no_capacity"


def test_counts_only_filter_output_and_global_batch_can_exceed_search_limit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    probe, checks = _install(monkeypatch)
    cli.main(["--imgsz", "640", "--models", "yolo11n", "--gpu-counts", "3", "--search-limit", "1"])
    output = capsys.readouterr().out
    assert "gpus=3\tglobal_batch=3\tper_gpu_batch=1" in output
    assert "ceiling_limited\textrapolated" in output
    assert "gpus=1" not in output
    assert checks == [(0,)]
    assert all(profile.world_size == 1 for profile in probe.probed_profiles)


def test_first_idle_identical_device_is_used_and_cached_run_ignores_busy_devices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe, checks = _install(monkeypatch)

    def idle(devices: tuple[GPUDevice, ...]) -> None:
        checks.append(tuple(device.index for device in devices))
        if devices[0].index == 0:
            raise RuntimeError("GPU 0 is busy")

    monkeypatch.setattr(cli, "require_idle", idle)
    args = ["--imgsz", "640", "--models", "yolo11n", "--gpu-counts", "2", "--search-limit", "4"]
    cli.main(args)
    assert checks == [(0,), (1,)]
    assert {profile.gpus[0].uuid for profile in probe.probed_profiles} == {"GPU-1"}
    monkeypatch.setattr(cli, "require_idle", lambda _: pytest.fail("cached run checked idle"))
    cli.main(args)


def test_mixed_hardware_measures_each_group_once(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    probe, checks = _install(monkeypatch)
    devices = _available_devices()
    devices = (devices[0], devices[1].model_copy(update={"name": "different"}), devices[2])
    monkeypatch.setattr(cli, "discover_gpus", lambda: devices)
    original_profile = probe.profile

    def profile(model: Any, imgsz: int, selected: tuple[int, ...]) -> Any:
        from clearml_yolo.core.batch_estimation import GPUHardware

        return original_profile(model, imgsz, selected).model_copy(
            update={
                "gpus": tuple(
                    GPUHardware(
                        name=devices[index].name,
                        total_memory_bytes=devices[index].total_memory_bytes,
                        uuid=devices[index].uuid,
                    )
                    for index in selected
                )
            }
        )

    monkeypatch.setattr(probe, "profile", profile)
    cli.main(["--imgsz", "640", "--models", "yolo11n", "--gpu-counts", "3", "--search-limit", "4"])
    assert checks == [(0,), (1,)]
    assert len(FileBatchEstimateStore().read().cases) == 2
    assert {p.gpus[0].name for p in probe.probed_profiles} == {"GPU", "different"}
    assert all(p.world_size == 1 for p in probe.probed_profiles)
    assert "gpus=3\tglobal_batch=12" in capsys.readouterr().out


@pytest.mark.parametrize(("jobs", "expected"), [(None, 3), (1, 1), (2, 2)])
def test_jobs_bound_independent_cases_and_preserve_model_order(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    jobs: int | None, expected: int,
) -> None:
    _install(monkeypatch)
    pool = RecordingCasePool()
    monkeypatch.setattr(cli, "_make_pool", lambda: pool)
    arguments = [
        "--imgsz", "640", "--models", "yolo11n,yolo11s,yolo11m,yolo11l",
        "--gpu-counts", "1", "--search-limit", "1",
    ]
    if jobs is not None:
        arguments += ["--jobs", str(jobs)]
    cli.main(arguments)
    assert pool.maximum_active == expected
    assert len(pool.started) == 4
    selections = [line.split("\t")[0] for line in capsys.readouterr().out.splitlines()[:-1]]
    assert selections == [f"ultralytics/yolo11{size}" for size in "nsml"]


def test_interrupted_spawn_has_already_invalidated_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(monkeypatch)
    args = ["--imgsz", "640", "--models", "yolo11n", "--search-limit", "1"]
    cli.main(args)
    assert FileBatchEstimateStore().read().cases[0].usable

    def interrupted(*_args: Any) -> None:
        assert not FileBatchEstimateStore().read().cases[0].usable
        raise KeyboardInterrupt

    monkeypatch.setattr(RecordingCasePool, "start", interrupted)
    with pytest.raises(KeyboardInterrupt):
        cli.main([*args, "--refresh"])
    assert not FileBatchEstimateStore().read().cases[0].usable


def test_next_launch_reuses_verified_models_and_retries_only_failed_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe, _ = _install(monkeypatch)
    original_run = probe.run
    failing = True
    measured: list[str] = []

    def run(profile: Any, *args: Any, **kwargs: Any) -> Any:
        measured.append(profile.model.selection)
        trial = original_run(profile, *args, **kwargs)
        if failing and profile.model.selection == "ultralytics/yolo11s":
            return trial.model_copy(update={"status": "oom"})
        return trial

    monkeypatch.setattr(probe, "run", run)
    args = [
        "--imgsz", "640", "--models", "yolo11n,yolo11s", "--devices", "0,1",
        "--search-limit", "4",
    ]
    with pytest.raises(SystemExit) as stopped:
        cli.main(args)
    assert stopped.value.code == 1
    verified = next(case for case in FileBatchEstimateStore().read().cases if case.usable)
    previous = verified.model_dump_json()
    measured.clear()
    failing = False
    cli.main([*args, "--jobs", "1"])
    assert set(measured) == {"ultralytics/yolo11s"}
    assert next(
        case for case in FileBatchEstimateStore().read().cases
        if case.profile.model.selection == "ultralytics/yolo11n"
    ).model_dump_json() == previous


def test_cache_survives_device_order_report_count_and_jobs_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe, _ = _install(monkeypatch)
    args = ["--imgsz", "640", "--models", "yolo11n,yolo11s", "--search-limit", "4"]
    cli.main([*args, "--devices", "0,1", "--jobs", "1", "--gpu-counts", "1"])
    calls = probe.calls
    monkeypatch.setattr(cli, "require_idle", lambda _: pytest.fail("cache hit checked idle GPU"))
    monkeypatch.setattr(cli, "_make_pool", lambda: pytest.fail("cache hit created worker pool"))
    cli.main([*args, "--devices", "1,0", "--jobs", "2", "--gpu-counts", "2"])
    assert probe.calls == calls


@pytest.mark.parametrize("damage", ["missing", "token", "gpu", "exit", "cleanup"])
def test_unaccepted_case_receipts_cannot_publish_success_or_fail_peers(
    monkeypatch: pytest.MonkeyPatch, damage: str,
) -> None:
    _install(monkeypatch)
    pool = RecordingCasePool()
    original_start = pool.start

    def start(key: str, command: Any) -> None:
        original_start(key, command)
        request = BatchCaseRequest.model_validate_json(
            Path(command.argv[-1]).read_text(encoding="utf-8")
        )
        if request.profile.model.selection != "ultralytics/yolo11n":
            return
        receipt = request.output / "result.json"
        if damage == "missing":
            receipt.unlink()
        elif damage in {"token", "gpu"}:
            import json

            raw = json.loads(receipt.read_text(encoding="utf-8"))
            if damage == "token":
                raw["token"] = uuid4().hex
            else:
                raw["case"]["profile"]["gpus"][0]["uuid"] = "GPU-foreign"
            receipt.write_text(json.dumps(raw), encoding="utf-8")
        elif damage == "exit":
            pool.pending[-1].exit_code = 1
        else:
            pool.pending[-1].cleanup_complete = False

    monkeypatch.setattr(pool, "start", start)
    monkeypatch.setattr(cli, "_make_pool", lambda: pool)
    with pytest.raises(SystemExit) as stopped:
        cli.main([
            "--imgsz", "640", "--models", "yolo11n,yolo11s,yolo11m", "--devices", "0,1",
            "--search-limit", "1",
        ])
    assert stopped.value.code == 1
    cases = {case.profile.model.selection: case for case in FileBatchEstimateStore().read().cases}
    assert not cases["ultralytics/yolo11n"].usable
    assert cases["ultralytics/yolo11s"].usable
    assert cases["ultralytics/yolo11m"].usable
    if damage == "cleanup":
        assert pool.started[-1][1] == "GPU-1"
