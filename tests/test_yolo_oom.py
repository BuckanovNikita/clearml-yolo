"""The owned native loop preserves selected training batches on memory failures."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from clearml_yolo.adapters.integrations.native_trainer import OwnedDetectionTrainer


@pytest.fixture
def native_cpu_boundary(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    import torch
    from ultralytics.data import utils as dataset_utils
    from ultralytics.utils import callbacks, torch_utils

    previous_threads = torch.get_num_threads()
    monkeypatch.setattr(torch_utils, "NUM_THREADS", 2)
    # Font fetching and optional remote publishers are external to the native loop.
    monkeypatch.setattr(dataset_utils, "check_font", lambda *_args: None)
    monkeypatch.setattr(callbacks, "add_integration_callbacks", lambda _trainer: None)
    try:
        yield
    finally:
        torch.set_num_threads(previous_threads)


def _trainer(
    root: Path,
    *,
    batch: float = 2,
    epochs: int = 1,
    trainer_type: type[OwnedDetectionTrainer] = OwnedDetectionTrainer,
) -> OwnedDetectionTrainer:
    for split in ("train", "val"):
        images = root / "images" / split
        labels = root / "labels" / split
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        for index in range(2):
            Image.new("RGB", (64, 64), (80 + index * 40, 100, 150)).save(images / f"{index}.png")
            (labels / f"{index}.txt").write_text("0 0.5 0.5 0.4 0.4\n")
    data = root / "dataset.yaml"
    data.write_text(json.dumps({"path": str(root), "train": "images/train", "val": "images/val", "names": ["cat"]}))
    model = root / "tiny.yaml"
    model.write_text(
        json.dumps(
            {
                "nc": 1,
                "backbone": [[-1, 1, "Conv", [8, 3, 2]], [-1, 1, "Conv", [16, 3, 2]]],
                "head": [[[-1], 1, "Detect", ["nc"]]],
            },
        ),
    )
    return trainer_type(
        overrides={
            "model": str(model),
            "data": str(data),
            "project": str(root / "runs"),
            "name": "train",
            "device": "cpu",
            "batch": batch,
            "epochs": epochs,
            "imgsz": 64,
            "workers": 0,
            "pretrained": False,
            "amp": False,
            "compile": False,
            "plots": False,
            "mosaic": 0.0,
            "close_mosaic": 0,
            "optimizer": "SGD",
            "nbs": 2,
            "warmup_epochs": 0.0,
        },
    )


def _assert_original_failure(
    trainer: OwnedDetectionTrainer,
    failure: RuntimeError,
    *,
    backward: bool = False,
) -> None:
    from torch.utils.hooks import RemovableHandle

    attempts: list[int] = []
    selected: list[int] = []
    events: list[str] = []
    handles: list[RemovableHandle] = []

    def fail(*_inputs: Any) -> None:
        attempts.append(trainer.batch_size)
        raise failure

    def attach(current: Any) -> None:
        selected.append(current.batch_size)
        if backward:
            parameter = next(parameter for parameter in current.model.parameters() if parameter.requires_grad)
            handles.append(parameter.register_hook(fail))
        else:
            handles.append(current.model.register_forward_pre_hook(fail))

    trainer.add_callback("on_train_start", attach)
    trainer.add_callback("teardown", lambda _: events.append("teardown"))
    try:
        with pytest.raises(RuntimeError) as caught:
            trainer.train()
    finally:
        for handle in handles:
            handle.remove()

    assert caught.value is failure
    assert len(selected) == 1
    assert selected[0] > 0
    assert attempts == selected
    assert trainer.batch_size == trainer.args.batch == selected[0]
    assert trainer.device.type == trainer.args.device == "cpu"
    assert events == ["teardown"]


@pytest.mark.parametrize(
    "message",
    [
        "CUDA out of memory: injected at the CPU model boundary",
        "CUBLAS_STATUS_ALLOC_FAILED",
        "CUDNN_STATUS_INTERNAL_ERROR",
        "unable to find an engine",
        "unrelated model error",
    ],
)
@pytest.mark.usefixtures("native_cpu_boundary")
def test_training_memory_error_does_not_retry_or_reduce_batch(tmp_path: Path, message: str) -> None:
    trainer = _trainer(tmp_path)
    _assert_original_failure(trainer, RuntimeError(message))
    assert trainer.batch_size == 2


@pytest.mark.parametrize("backward", [False, True])
@pytest.mark.usefixtures("native_cpu_boundary")
def test_native_oom_preserves_exception_in_forward_and_backward(tmp_path: Path, backward: bool) -> None:
    import torch

    _assert_original_failure(_trainer(tmp_path), torch.OutOfMemoryError("injected out of memory"), backward=backward)


@pytest.mark.parametrize("requested", [-1, 0.5])
@pytest.mark.usefixtures("native_cpu_boundary")
def test_initial_autobatch_selection_still_precedes_strict_training(tmp_path: Path, requested: float) -> None:
    trainer = _trainer(tmp_path, batch=requested)
    assert trainer.batch_size == requested
    _assert_original_failure(trainer, RuntimeError("injected out of memory"))


@pytest.mark.usefixtures("native_cpu_boundary")
def test_serialized_fixed_recipe_preserves_original_memory_error(tmp_path: Path) -> None:
    import cloudpickle  # type: ignore[import-untyped]  # Native DDP serializer.

    from clearml_yolo.adapters.integrations.native_trainer import fixed_training_recipe, trainer_with_transforms

    with fixed_training_recipe(batch=2, epochs=1):
        selected = trainer_with_transforms(None)
    restored = cloudpickle.loads(cloudpickle.dumps(selected))
    _assert_original_failure(_trainer(tmp_path, trainer_type=restored), RuntimeError("injected out of memory"))


@pytest.mark.usefixtures("native_cpu_boundary")
def test_successful_native_training_updates_weights_and_completes_each_epoch_once(tmp_path: Path) -> None:
    import torch

    trainer = _trainer(tmp_path, batch=1, epochs=2)
    initial: dict[str, torch.Tensor] = {}
    epochs: list[int] = []
    batches: list[int] = []

    def snapshot(current: Any) -> None:
        initial.update({name: parameter.detach().clone() for name, parameter in current.model.named_parameters()})

    trainer.add_callback("on_train_start", snapshot)
    trainer.add_callback("on_train_epoch_start", lambda current: epochs.append(current.epoch))
    trainer.add_callback("on_train_batch_end", lambda current: batches.append(current.batch_size))
    trainer.train()

    model: Any = trainer.model
    assert epochs == [0, 1]
    assert batches == [1, 1, 1, 1]
    assert trainer.batch_size == trainer.args.batch == 1
    assert any(not torch.equal(initial[name], parameter) for name, parameter in model.named_parameters())
    assert trainer.best.is_file()
    assert trainer.best.stat().st_size > 0
