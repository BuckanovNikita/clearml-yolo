"""Worker command producers emit importable entrypoints with intact request arguments."""

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from clearml_yolo.adapters.fiftyone import bounded
from clearml_yolo.adapters.integrations import batch_probe, distributed_training
from clearml_yolo.adapters.runtime.workers import WorkerCommand
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.application.training_workers import BatchCaseRequest, BatchProbeRequest, TrainingWorkerRequest
from clearml_yolo.core.batch_estimation import SearchSettings, SyntheticWorkload
from clearml_yolo.core.models import model_preset
from clearml_yolo.entrypoints.batch_estimate import _case_command
from test_batch_case_worker import request_for
from test_batch_estimate_workflow import sample_profile
from test_batch_profiles import sample_devices


class LaunchCapturedError(Exception):
    """Stop at the process boundary without starting native work."""


def _assert_entrypoint(argv: Sequence[str]) -> None:
    assert list(argv[:2]) == [sys.executable, "-m"]
    result = subprocess.run(  # noqa: S603 - module comes from a product command producer
        [
            sys.executable,
            "-B",
            "-c",
            "import importlib,sys; module=importlib.import_module(sys.argv[1]); assert callable(module.main)",
            argv[2],
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_case_command_preserves_request_and_loads_its_entrypoint(tmp_path: Path) -> None:
    request = request_for(tmp_path)
    command = _case_command(request)
    _assert_entrypoint(command.argv)
    restored = BatchCaseRequest.model_validate_json(Path(command.argv[3]).read_text(encoding="utf-8"))
    assert restored == request
    assert command.environment["CUDA_VISIBLE_DEVICES"] == str(request.profile.gpus[0].uuid)


def test_probe_launch_loads_emitted_entrypoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[WorkerCommand] = []

    def capture(commands: Sequence[WorkerCommand], **_kwargs: Any) -> None:
        emitted.extend(commands)
        raise LaunchCapturedError

    monkeypatch.setattr(batch_probe, "run_workers", capture)
    monkeypatch.setattr(batch_probe, "temporary_root", lambda: tmp_path)
    monkeypatch.setattr(batch_probe, "configure_weights_directory", lambda: tmp_path)
    monkeypatch.setattr(batch_probe, "require_idle", lambda *_args, **_kwargs: (0,))
    monkeypatch.setattr(batch_probe, "_port", lambda: "12345")
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    profile = sample_profile()
    token = uuid4().hex
    with pytest.raises(LaunchCapturedError):
        batch_probe.NativeBatchProbe()._path(
            profile, SyntheticWorkload(), SearchSettings(), 4, "AdamW", token, sample_devices()[:1]
        )
    assert len(emitted) == 1
    command = emitted[0]
    _assert_entrypoint(command.argv)
    request = BatchProbeRequest.model_validate_json(Path(command.argv[3]).read_text(encoding="utf-8"))
    assert request.token == token
    assert request.profile == profile
    assert request.global_batch == 4
    assert command.environment["LOCAL_RANK"] == "0"


def test_training_launch_loads_emitted_entrypoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[WorkerCommand] = []

    def capture(commands: Sequence[WorkerCommand], **_kwargs: Any) -> None:
        emitted.extend(commands)
        raise LaunchCapturedError

    monkeypatch.setattr(distributed_training, "run_workers", capture)
    monkeypatch.setattr(distributed_training, "_port", lambda: "12345")
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    prepared = PreparedDataset(
        data=tmp_path / "data.yaml",
        ground_truth=tmp_path / "truth.csv",
        manifest=tmp_path / "manifest.json",
        dataset_format="coco",
        artifacts=[],
    )
    config = model_preset("fasterrcnn/resnet50_fpn")
    config.train.batch = 4
    with pytest.raises(LaunchCapturedError):
        distributed_training.train_distributed(config, prepared, tmp_path, lambda *_args: None, devices=(0, 1))
    assert len(emitted) == 2
    assert emitted[0].argv[2] == emitted[1].argv[2]
    _assert_entrypoint(emitted[0].argv)
    for rank, command in enumerate(emitted):
        request = TrainingWorkerRequest.model_validate_json(Path(command.argv[3]).read_text(encoding="utf-8"))
        assert request.config == config
        assert request.prepared == prepared
        assert request.world_size == 2
        assert command.argv[4] == str(rank)
        assert command.environment["LOCAL_RANK"] == str(rank)


def test_fiftyone_command_preserves_protocol_paths_and_loads_entrypoint(tmp_path: Path) -> None:
    paths = tuple(tmp_path / name for name in ("request.json", "result.json", "phase"))
    command = bounded._worker_command(*paths)
    _assert_entrypoint(command)
    assert command[3:] == [str(path) for path in paths]
