"""Lookup changes execution copies while retaining explicit batches and replay intent."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.adapters.clearml import session
from clearml_yolo.adapters.integrations import batch_resolution as resolution
from clearml_yolo.adapters.runtime.gpu_inventory import GPUDevice
from clearml_yolo.core.batch_estimation import GPUHardware, SyntheticWorkload, select_recommendation
from clearml_yolo.core.models import ModelConfig
from test_batch_estimate_workflow import MemoryStore, sample_case
from test_batch_lookup import _dataset


def test_explicit_batches_do_not_discover_gpus(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def forbidden() -> Any:
        pytest.fail("Numeric batches must retain direct native device behavior")

    monkeypatch.setattr(resolution, "discover_gpus", forbidden)
    config = ModelConfig.model_validate({"backend": "fcos", "preset": "resnet50_fpn"})
    prepared = _dataset(tmp_path)
    assert resolution.resolve_native_batch(config, prepared, None) == (config, None)
    for values in ({}, {"batch": 16}, {"batch": -1}, {"batch": 0.8}):
        result, provenance = resolution.resolve_yolo_batch("yolo11n.pt", values, prepared, None)
        assert result is values
        assert provenance is None


@pytest.mark.parametrize("device", ["cpu", "mps"])
def test_native_null_on_non_cuda_device_fails_before_gpu_discovery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, device: str
) -> None:
    def forbidden() -> Any:
        pytest.fail("Explicit non-CUDA selection must not query unavailable GPU telemetry")

    monkeypatch.setattr(resolution, "discover_gpus", forbidden)
    config = ModelConfig.model_validate(
        {
            "backend": "fcos",
            "preset": "resnet50_fpn",
            "train": {"batch": None, "device": device},
        }
    )
    with pytest.raises(ValueError, match="explicit batch for CPU/MPS"):
        resolution.resolve_native_batch(config, _dataset(tmp_path), None)


def test_native_null_resolves_a_copy_after_dataset_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = sample_case()
    device = GPUDevice(
        index=0,
        uuid="GPU-test",
        name="GPU",
        total_memory_bytes=1000,
        used_memory_bytes=0,
        utilization=0,
    )
    monkeypatch.setattr(resolution, "discover_gpus", lambda: (device,))
    observed = []

    def profile(*args: Any, **kwargs: Any) -> Any:
        assert kwargs["native"].train.batch is None
        return case.profile

    def lookup(profile: Any, dataset: Any, store: Any) -> Any:
        observed.append(dataset)
        return select_recommendation((case,), case.profile, SyntheticWorkload())

    monkeypatch.setattr(resolution, "training_profile", profile)
    monkeypatch.setattr(resolution, "resolve_batch_estimate", lookup)
    config = ModelConfig.model_validate(
        {
            "backend": "fcos",
            "preset": "resnet50_fpn",
            "train": {"batch": None},
        }
    )
    prepared = _dataset(tmp_path)
    result, provenance = resolution.resolve_native_batch(config, prepared, None)
    assert result is not config
    assert config.train.batch is None
    assert result.train.batch == case.global_batch
    assert result.train.device == [0]
    assert observed == [prepared]
    assert provenance is not None
    assert provenance["global_batch"] == case.global_batch
    assert provenance["origin"] == "measured"
    assert provenance["estimate_key"] == provenance["source_estimate_keys"][0]


def test_queue_assigned_allocation_uses_extrapolated_batch_and_retains_null(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    case, store = sample_case(), MemoryStore()
    store.save(case)
    devices = tuple(
        GPUDevice(
            index=index,
            uuid=f"queue-assigned-{index}",
            name="GPU",
            total_memory_bytes=1000,
            used_memory_bytes=0,
            utilization=0,
        )
        for index in range(3)
    )
    monkeypatch.setattr(resolution, "discover_gpus", lambda: devices)
    monkeypatch.setattr(resolution, "FileBatchEstimateStore", lambda: store)

    def profile(*args: Any, **kwargs: Any) -> Any:
        selected = args[2]
        assert [device.index for device in selected] == [2, 0]
        return case.profile.model_copy(
            update={
                "gpus": tuple(
                    GPUHardware(
                        name=device.name,
                        total_memory_bytes=device.total_memory_bytes,
                        uuid=device.uuid,
                    )
                    for device in selected
                )
            }
        )

    monkeypatch.setattr(resolution, "training_profile", profile)
    config = ModelConfig.model_validate(
        {
            "backend": "fcos",
            "preset": "resnet50_fpn",
            "train": {"batch": None, "device": [2, 0]},
        }
    )
    resolved, provenance = resolution.resolve_native_batch(config, _dataset(tmp_path), None)
    assert config.train.batch is None
    assert resolved.train.batch == 8
    assert resolved.train.device == [2, 0]
    assert provenance is not None
    assert provenance["origin"] == "extrapolated"
    assert provenance["global_batch"] == 8
    assert provenance["per_gpu_batch"] == 4
    assert provenance["source_statuses"] == ["validated"]
    assert "estimate_key" not in provenance
    assert [gpu["uuid"] for gpu in provenance["profile"]["gpus"]] == [
        "queue-assigned-2",
        "queue-assigned-0",
    ]
    assert len(provenance["sources"]) == 1
    assert provenance["sources"][0]["global_batch"] == 4
    assert len(provenance["sources"][0]["profile"]["gpus"]) == 1


def test_replay_null_is_not_replaced_by_previous_effective_general_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session, "_is_worker", lambda: False)
    task = SimpleNamespace(get_parameters=lambda **_: {"General/batch": 32, "General/epochs": 9})
    state = session._InvocationState(task=task, stages=["train"], current_stage="train")
    token = session._ACTIVE_INVOCATION.set(state)
    try:
        values = session.replay_training_parameters(task, {"batch": None, "epochs": 3})
    finally:
        session._ACTIVE_INVOCATION.reset(token)
    assert values == {"batch": None, "epochs": 9}
