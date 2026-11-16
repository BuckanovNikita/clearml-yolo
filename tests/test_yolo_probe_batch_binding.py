"""Trial batches replace recipe selectors before native YOLO validation."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.adapters.yolo import batch_probe
from test_yolo_probe_precision import _request, restore_native_randomness  # noqa: F401 - isolate native RNG policy


@pytest.mark.parametrize("configured_batch", [None, 16, -1, 0.5])
@pytest.mark.parametrize("trial_batch", [2, 4])
def test_probe_materializes_trial_batch_through_real_native_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configured_batch: float | None, trial_batch: int
) -> None:
    import torch
    from ultralytics import models
    from ultralytics.cfg import get_cfg
    from ultralytics.engine import validator as native_validator
    from ultralytics.nn.tasks import DetectionModel

    architecture = {
        "nc": 1,
        "backbone": [[-1, 1, "Conv", [8, 3, 2]]],
        "head": [[[-1], 1, "Detect", ["nc"]]],
    }
    weights: Any = DetectionModel(architecture, nc=1, verbose=False)  # type: ignore[no-untyped-call]
    # Initialize optimizer SDK imports before replacing CUDA device admission.
    torch.optim.SGD(weights.parameters(), lr=0.01)
    device_type = torch.device

    def cpu_device(*args: Any, **kwargs: Any) -> torch.device:
        device = device_type(*args, **kwargs)
        return device_type("cpu") if device.type == "cuda" else device

    observed: list[int] = []

    def configuration(*args: Any, **kwargs: Any) -> Any:
        config = get_cfg(*args, **kwargs)
        observed.append(config.batch)
        return config

    monkeypatch.setenv("LOCAL_RANK", "0")
    monkeypatch.setattr(models, "YOLO", lambda _architecture: SimpleNamespace(model=weights))
    monkeypatch.setattr(torch, "device", cpu_device)
    monkeypatch.setattr(torch.cuda, "reset_peak_memory_stats", lambda _device: None)
    monkeypatch.setattr(torch.cuda, "synchronize", lambda _device: None)
    monkeypatch.setattr(torch.cuda, "mem_get_info", lambda _device: (1024, 2048))
    monkeypatch.setattr(torch.cuda, "memory_reserved", lambda _device: 0)
    monkeypatch.setattr(torch.cuda, "max_memory_reserved", lambda _device: 0)
    monkeypatch.setattr(native_validator, "get_cfg", configuration)
    request = _request(tmp_path, False).model_copy(
        update={
            "global_batch": trial_batch,
            "yolo": {"batch": configured_batch, "amp": False, "compile": False, "optimizer": "SGD", "nbs": 2},
        }
    )

    result = batch_probe.probe(request)

    assert observed == [request.global_batch]
    assert result.status == "success"
    assert result.actual_global_batch == request.global_batch
    assert (result.warmup_steps, result.measured_steps, result.validation_steps) == (1, 1, 1)
    assert request.yolo is not None
    assert request.yolo["batch"] == configured_batch
