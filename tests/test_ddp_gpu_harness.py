"""Offline harness contracts: these checks do not establish physical DDP acceptance."""

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from ddp_gpu_harness import (
    Evidence,
    GPUOptions,
    physical_indexes,
    redact,
    resolve_devices,
    run_scenario,
)


@pytest.mark.parametrize("selection", ["", "0", "0,0", "-1,0", "0,abc", "GPU-abc,GPU-def"])
def test_physical_selection_rejects_ambiguous_requests(selection: str) -> None:
    with pytest.raises(ValueError, match=r"physical|nonnegative"):
        physical_indexes(selection)


@pytest.mark.parametrize("visibility", ["", "1,0", "GPU-b", "GPU-b,GPU-a"])
def test_selection_resolves_physical_index_before_cuda_mapping(
    monkeypatch: pytest.MonkeyPatch, visibility: str
) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", visibility)
    inventory = [{"index": 1, "uuid": "GPU-b"}, {"index": 0, "uuid": "GPU-a"}]
    assert resolve_devices(physical_indexes("1,0"), inventory) == ("GPU-b", "GPU-a")


@pytest.mark.parametrize(
    "inventory", [[], [{"index": 0, "uuid": "MIG-abc"}, {"index": 1, "uuid": "GPU-b"}]]
)
def test_missing_or_mig_devices_fail_instead_of_skipping(inventory: list[dict[str, Any]]) -> None:
    with pytest.raises(RuntimeError):
        resolve_devices((0, 1), inventory)


def test_preflight_failure_retains_summary_and_junit_without_launch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []

    def fail(
        evidence: Evidence, operation: str, environment: dict[str, str], **kwargs: Any
    ) -> None:
        calls.append(operation)
        raise RuntimeError("NCCL unavailable")

    monkeypatch.setattr(Evidence, "helper", fail)
    with pytest.raises(RuntimeError, match="NCCL unavailable"):
        run_scenario(
            GPUOptions("0,1", "owned-tests", tmp_path), "direct-eager", queued=False, compiled=False
        )
    root = next(tmp_path.iterdir())
    summary = json.loads((root / "summary.json").read_text())
    assert summary["status"] == "failed"
    assert "NCCL unavailable" in summary["error"]
    assert (root / "junit.xml").is_file()
    assert calls == ["preflight"]
    assert not list(root.glob("rank-*.json"))


def test_invalid_device_request_still_retains_failure(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unique nonnegative physical indexes"):
        run_scenario(
            GPUOptions("0", "owned-tests", tmp_path), "bad-selection", queued=False, compiled=False
        )
    assert json.loads(next(tmp_path.glob("*/summary.json")).read_text())["status"] == "failed"


def test_evidence_redacts_credentials_and_retains_files_on_interruption(tmp_path: Path) -> None:
    evidence = Evidence(GPUOptions("0,1", "owned-tests", tmp_path), "interrupt")

    def interrupted() -> None:
        with evidence.retained():
            (evidence.root / "owner.log").write_text(
                "https://user:secret@example.com/model\napi_key=hidden\n"
            )
            (evidence.root / "best.pt").write_bytes(b"checkpoint")
            raise KeyboardInterrupt("cancelled")

    with pytest.raises(KeyboardInterrupt):
        interrupted()
    log = (evidence.root / "owner.log").read_text()
    assert "secret" not in log
    assert "hidden" not in log
    assert (evidence.root / "best.pt").read_bytes() == b"checkpoint"
    assert json.loads((evidence.root / "summary.json").read_text())["status"] == "failed"


def test_evidence_command_failure_is_not_an_implicit_retry(tmp_path: Path) -> None:
    evidence = Evidence(GPUOptions("0,1", "owned-tests", tmp_path), "command-error")
    with pytest.raises(RuntimeError, match="Command exited 3"), evidence.retained():
        evidence.command(
            [sys.executable, "-c", "print('diagnostic'); raise SystemExit(3)"], dict(os.environ)
        )
    assert len(evidence.data["commands"]) == 1
    assert "diagnostic" in (evidence.root / "command-1.log").read_text()


def test_ordinary_collection_deselects_gpu_without_environment_effects() -> None:
    from conftest import pytest_collection_modifyitems

    gpu = SimpleNamespace(get_closest_marker=lambda name: object() if name == "ddp_gpu" else None)
    ordinary = SimpleNamespace(get_closest_marker=lambda name: None)
    removed = []
    config = SimpleNamespace(
        args=[],
        getoption=lambda name: False,
        option=SimpleNamespace(markexpr=""),
        hook=SimpleNamespace(pytest_deselected=lambda *, items: removed.extend(items)),
    )
    items = [gpu, ordinary]
    pytest_collection_modifyitems(config, items)  # type: ignore[arg-type]
    assert items == [ordinary]
    assert removed == [gpu]


def test_explicit_mark_selection_retains_gpu_missing_authorization() -> None:
    from conftest import pytest_collection_modifyitems

    config = SimpleNamespace(
        args=[], getoption=lambda name: False, option=SimpleNamespace(markexpr="ddp_gpu")
    )
    gpu = SimpleNamespace(get_closest_marker=lambda name: object() if name == "ddp_gpu" else None)
    items = [gpu]
    pytest_collection_modifyitems(config, items)  # type: ignore[arg-type]
    assert items == [gpu]


def test_cleanup_terminates_owned_survivor_preserves_unrelated_process(tmp_path: Path) -> None:
    from ddp_gpu_worker import _cleanup

    root = tmp_path / "owned"
    root.mkdir()
    owned = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        env=dict(os.environ, CY_DDP_TRACE=str(root)),
    )
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        with pytest.raises(AssertionError, match="Production cleanup left"):
            _cleanup(root)
        owned.wait(timeout=5)
        assert unrelated.poll() is None
        result = json.loads((root / "cleanup.json").read_text())
        assert [owned.pid, result["initial_survivors"][0][1]] in result["initial_survivors"]
        assert result["remaining"] == []
    finally:
        for process in (owned, unrelated):
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=5)


def test_redaction_preserves_gpu_uuid_and_local_checkpoint_hash() -> None:
    assert redact("GPU-0123 checkpoint_sha256=abc123") == "GPU-0123 checkpoint_sha256=abc123"


@pytest.mark.parametrize(
    "diagnostic",
    [
        "secret_key=credential-fixture",
        "Authorization: Bearer credential-fixture",
        "'Authorization': 'Basic credential-fixture'",
        "https://user:credential-fixture@storage.example/a.pt",
        "https://storage.example/a.pt?X-Amz-Credential=credential-fixture&X-Amz-Signature=credential-fixture&X-Amz-Expires=300",
        "https://storage.example/a.pt?sig=credential-fixture&sv=2026",
    ],
)
def test_remote_credentials_are_removed_from_diagnostics(diagnostic: str) -> None:
    assert "credential-fixture" not in redact(diagnostic)


def test_malformed_endpoint_log_preserves_original_failure_and_receipts(tmp_path: Path) -> None:
    evidence = Evidence(GPUOptions("0,1", "owned-tests", tmp_path), "bad-endpoint")
    (evidence.root / "owner.log").write_text("endpoint=http://[bad?token=credential-fixture")

    def failed_prerequisite() -> None:
        with evidence.retained():
            raise RuntimeError("prerequisite failed")

    with pytest.raises(RuntimeError, match="prerequisite failed"):
        failed_prerequisite()
    summary = json.loads((evidence.root / "summary.json").read_text())
    assert summary["status"] == "failed"
    assert "prerequisite failed" in summary["error"]
    assert (evidence.root / "junit.xml").is_file()
    assert "credential-fixture" not in (evidence.root / "owner.log").read_text()


def test_timeout_preserves_partial_output_and_failure_receipt(tmp_path: Path) -> None:
    evidence = Evidence(GPUOptions("0,1", "owned-tests", tmp_path), "timeout")

    def timed_out() -> None:
        with evidence.retained():
            evidence.command(
                [
                    sys.executable,
                    "-u",
                    "-c",
                    "import time; print('before timeout'); time.sleep(10)",
                ],
                dict(os.environ),
                timeout=0.3,
            )

    with pytest.raises(subprocess.TimeoutExpired):
        timed_out()
    assert "before timeout" in (evidence.root / "command-1.log").read_text()
    assert json.loads((evidence.root / "summary.json").read_text())["command_timeouts"]


def test_structured_redaction_retains_valid_json_and_jsonl(tmp_path: Path) -> None:
    evidence = Evidence(GPUOptions("0,1", "owned-tests", tmp_path), "redaction")
    payload = {"token": "quoted secret", "nested": {"password": "other-secret"}, "uuid": "GPU-a"}
    (evidence.root / "configuration.json").write_text(json.dumps(payload))
    (evidence.root / "events.jsonl").write_text(json.dumps(payload) + "\n")
    evidence.finish(None)
    config = json.loads((evidence.root / "configuration.json").read_text())
    event = json.loads((evidence.root / "events.jsonl").read_text())
    assert config == event
    assert config["token"] == "<redacted>"  # noqa: S105 - redaction assertion, not a credential
    assert config["nested"]["password"] == "<redacted>"  # noqa: S105
    assert config["uuid"] == "GPU-a"


@pytest.mark.parametrize(("available", "nccl"), [(False, True), (True, False)])
def test_explicit_cuda_capability_failure_never_skips(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, available: bool, nccl: bool
) -> None:
    from ddp_gpu_worker import _cuda

    distributed = SimpleNamespace(is_available=lambda: True, is_nccl_available=lambda: nccl)
    torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: available), distributed=distributed
    )
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "torch.distributed", distributed)
    with pytest.raises(AssertionError, match=r"Torch CUDA|Torch NCCL"):
        _cuda(tmp_path, {"indexes": [0, 1], "compiled": False})


def test_generated_inputs_and_native_config_compose_offline(tmp_path: Path) -> None:
    from ddp_gpu_harness import environment_for

    evidence = Evidence(GPUOptions("0,1", "owned-tests", tmp_path), "prepare-only")
    request = {
        "indexes": [0, 1],
        "project": "owned-tests",
        "compiled": False,
        "scenario": "direct-eager",
        "tag": "offline-only",
        "timeout": 1200,
    }
    (evidence.root / "request.json").write_text(json.dumps(request))
    base = environment_for(evidence)
    evidence.helper("prepare", base)
    assert not (evidence.root / "preflight.json").exists()
    for split in ("train", "val", "test"):
        assert (evidence.root / "dataset/labels" / split / f"{split}-0.txt").read_text() == ""
    source = Path(__file__).resolve().parents[1] / "src"
    code = (
        "import os; from pathlib import Path; "
        "from hydra import compose, initialize_config_dir; "
        "import clearml_yolo.entrypoints.hydra.configs; "
        "from hydra_zen import store; "
        "root=Path(os.environ['CY_HOME']); "
        "store.add_to_hydra_store(overwrite_ok=True); "
        "context=initialize_config_dir(config_dir=str(root/'config'),version_base='1.3'); "
        "context.__enter__(); config=compose(config_name='ddp'); "
        "assert 'pretrained' in config.ultralytics; context.__exit__(None,None,None)"
    )
    evidence.command(
        [sys.executable, "-c", code], dict(base, PYTHONPATH=f"{source}:{base['PYTHONPATH']}")
    )
    # Startup for a worker/probe/control command keeps Torch and ClearML unloaded.
    base["CY_DDP_TRACE"] = str(evidence.root)
    base["PYTHONPATH"] = f"{evidence.root / 'instrumentation'}:{base['PYTHONPATH']}"
    evidence.command(
        [
            sys.executable,
            "-c",
            "import sys; assert 'torch' not in sys.modules; assert 'clearml' not in sys.modules",
        ],
        base,
    )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), 0.0])
def test_execution_deadline_requires_finite_positive_value(tmp_path: Path, value: float) -> None:
    with pytest.raises(ValueError, match="Execution timeout"):
        run_scenario(
            GPUOptions("0,1", "owned-tests", tmp_path, timeout=value),
            "bad-timeout",
            queued=False,
            compiled=False,
        )
    assert json.loads(next(tmp_path.glob("*/summary.json")).read_text())["status"] == "failed"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 90.0])
def test_cleanup_deadline_preserves_finite_production_grace(tmp_path: Path, value: float) -> None:
    with pytest.raises(ValueError, match="cleanup timeout"):
        run_scenario(
            GPUOptions("0,1", "owned-tests", tmp_path, cleanup_timeout=value),
            "bad-cleanup",
            queued=False,
            compiled=False,
        )


def test_explicit_gpu_file_selection_requires_authorization() -> None:
    from conftest import pytest_collection_modifyitems

    config = SimpleNamespace(
        args=["tests/test_native_ddp_gpu.py"],
        getoption=lambda name: False,
        option=SimpleNamespace(markexpr=""),
    )
    gpu = SimpleNamespace(get_closest_marker=lambda name: object() if name == "ddp_gpu" else None)
    items = [gpu]
    pytest_collection_modifyitems(config, items)  # type: ignore[arg-type]
    assert items == [gpu]


def test_inaccessible_known_owned_process_blocks_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from ddp_gpu_instrumentation import process_birth
    from ddp_gpu_worker import _owned_processes

    pid = os.getpid()
    (tmp_path / f"process-{pid}.json").write_text(
        json.dumps({"pid": pid, "born": process_birth(pid)})
    )
    original = Path.read_bytes

    def restricted(path: Path) -> bytes:
        if path == Path(f"/proc/{pid}/environ"):
            raise PermissionError("denied owned evidence")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", restricted)
    with pytest.raises(RuntimeError, match="known owned process"):
        _owned_processes(tmp_path)
    assert json.loads((tmp_path / "cleanup-unverified.json").read_text())["pid"] == str(pid)


def test_explicit_selection_missing_opt_in_retains_failure_receipt(tmp_path: Path) -> None:
    directory = tmp_path / "receipts"
    result = subprocess.run(  # noqa: S603 - bounded local pytest selection with no GPU authorization
        [
            sys.executable,
            "-m",
            "pytest",
            str(Path(__file__).with_name("test_native_ddp_gpu.py")),
            "--ddp-artifacts",
            str(directory),
            "-x",
            "--tb=short",
            "-q",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 1
    assert "Physical DDP selection requires" in result.stdout
    summary = json.loads(next(directory.glob("*/summary.json")).read_text())
    assert summary["status"] == "failed"
    assert summary["commands"] == []
    assert not list(directory.glob("*/preflight.json"))
