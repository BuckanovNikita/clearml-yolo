"""Explicit YOLO measurement recipes retain native precision and reject unsupported work."""

import json
from contextlib import AbstractContextManager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self, override

import pytest

from clearml_yolo.adapters.integrations.batch_profiles import training_profile
from clearml_yolo.adapters.runtime.gpu_inventory import GPUDevice
from clearml_yolo.adapters.yolo import batch_probe
from clearml_yolo.adapters.yolo.config import native_defaults
from clearml_yolo.application.training_workers import BatchProbeRequest
from clearml_yolo.core.batch_estimation import (
    GPUHardware,
    SearchSettings,
    SyntheticWorkload,
    TrainingProfile,
    select_models,
)


def _request(root: Path, amp: bool | str) -> BatchProbeRequest:
    return BatchProbeRequest(
        token=root.name,
        profile=TrainingProfile(
            model=select_models(("yolo11n",))[0],
            nominal_size=(32, 32),
            effective_size=(32, 32),
            gpus=(GPUHardware(name="fixture", total_memory_bytes=1024),),
            dependencies={"torch": "fixture"},
            precision=str(amp),
            compilation=False,
            optimizers=("SGD",),
            accumulation="fixed:1",
            ema=True,
            augmentation="native",
            implementation_revision="precision-regression",
        ),
        workload=SyntheticWorkload(classes=1, objects_per_image=1),
        settings=SearchSettings(warmup_steps=1, measured_steps=1),
        global_batch=2,
        optimizer="SGD",
        output=root,
        yolo={"amp": amp, "optimizer": "SGD"},
    )


@pytest.mark.parametrize("compiled", [False, True])
def test_bf16_probe_optimizer_executes_bfloat16_and_updates_parameters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, compiled: bool
) -> None:
    import torch
    from ultralytics.utils import torch_utils

    observed: list[torch.dtype] = []
    contexts: list[bool | torch.dtype] = []

    class Model(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.layer = torch.nn.Linear(3, 1)

        @override
        def forward(self, batch: Any) -> Any:
            images = batch["img"] if isinstance(batch, dict) else batch
            output = self.layer(images.mean(dim=(2, 3)))
            observed.append(output.dtype)
            return self.loss(batch, output) if isinstance(batch, dict) else output

        def loss(self, _batch: object, predictions: torch.Tensor) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
            loss = predictions.float().square().mean()
            return loss, {"loss": loss.detach()}

    def cpu_context(enabled: bool | torch.dtype, device: str) -> AbstractContextManager[Any]:
        contexts.append(enabled)
        # Exercise real BF16 math while replacing only the native CUDA admission boundary.
        dtype = enabled if isinstance(enabled, torch.dtype) else torch.float16
        return torch.autocast("cpu", enabled=bool(enabled), dtype=dtype)

    monkeypatch.setattr(torch_utils, "autocast", cpu_context)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    model = Model()
    before = model.layer.weight.detach().clone()
    trainer = SimpleNamespace(
        model=model,
        optimizer=torch.optim.SGD(model.parameters(), lr=0.1),
        scaler=torch.amp.GradScaler("cpu", enabled=False),
        ema=None,
        device=torch.device("cpu"),
    )
    request = _request(tmp_path, "bf16")
    request = request.model_copy(update={"profile": request.profile.model_copy(update={"compilation": compiled})})
    batch_probe._optimize(request, trainer, accumulation=1, amp=True)

    assert observed == [torch.bfloat16, torch.bfloat16]
    assert contexts == [torch.bfloat16, torch.bfloat16]
    assert not torch.equal(before, model.layer.weight)


@pytest.mark.parametrize(
    ("amp", "enabled"), [("bf16", False), (True, True), ("fp16", True), (False, False), ("fp32", False)]
)
def test_probe_scaler_matches_native_precision_before_cuda_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, amp: bool | str, enabled: bool
) -> None:
    import torch
    from ultralytics import models
    from ultralytics.nn import tasks
    from ultralytics.utils import checks

    class Model(torch.nn.Module):
        def __init__(self, _architecture: object, **_kwargs: Any) -> None:
            super().__init__()
            self.layer = torch.nn.Linear(3, 1)

        def load(self, _weights: object) -> None:
            pass

        @override
        def to(self, *_args: Any, **kwargs: Any) -> Self:
            kwargs.pop("device", None)
            return super().to(**kwargs)

    class ScalerReachedError(Exception):
        pass

    selected: list[tuple[str, bool]] = []

    def scaler(device: str, *, enabled: bool) -> None:
        selected.append((device, enabled))
        raise ScalerReachedError

    tensor = torch.tensor

    def cpu_tensor(*args: Any, **kwargs: Any) -> torch.Tensor:
        kwargs["device"] = "cpu"
        return tensor(*args, **kwargs)

    # Keep native optimizer resolution and AMP policy; replace CUDA allocation,
    # asset construction, and scaler creation at their external SDK boundaries.
    monkeypatch.setenv("LOCAL_RANK", "0")
    monkeypatch.setattr(torch.cuda, "reset_peak_memory_stats", lambda _device: None)
    monkeypatch.setattr(torch, "tensor", cpu_tensor)
    monkeypatch.setattr(models, "YOLO", lambda _: SimpleNamespace(model=SimpleNamespace(yaml={})))
    monkeypatch.setattr(tasks, "DetectionModel", Model)
    monkeypatch.setattr(checks, "check_amp", lambda _model: True)
    monkeypatch.setattr(torch.amp, "GradScaler", scaler)
    with pytest.raises(ScalerReachedError):
        batch_probe.probe(_request(tmp_path, amp))

    assert selected == [("cuda", enabled)]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("channels_last", False),
        ("freeze", 10),
        ("pretrained", False),
        ("pretrained", "different.pt"),
        ("distill_model", "teacher.pt"),
        ("resume", True),
        ("single_cls", True),
        ("quantize", "int8"),
        ("classes", [0]),
        ("augmentations", [{"transform": "Blur"}]),
        ("model", "yolo26n.pt"),
        ("task", "segment"),
        ("cls_pw", 0.5),
    ],
)
def test_profile_and_worker_reject_explicit_controls_the_probe_does_not_execute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str, value: Any
) -> None:
    import torch

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        pytest.fail("Unsupported recipes must fail before querying or allocating CUDA memory")

    monkeypatch.setattr(torch.cuda, "reset_peak_memory_stats", forbidden)
    device = GPUDevice(
        index=0, uuid="GPU-fixture", name="fixture", total_memory_bytes=1024, used_memory_bytes=0, utilization=0
    )
    with pytest.raises(ValueError, match=key):
        training_profile(select_models(("yolo11n",))[0], 32, (device,), yolo={key: value})
    request = _request(tmp_path, False).model_copy(update={"yolo": {key: value}})
    with pytest.raises(ValueError, match=key):
        batch_probe.probe(request)


@pytest.mark.parametrize("recipe", [None, {}, {"channels_last": True, "freeze": 0, "augmentations": []}])
def test_supported_catalogue_recipes_keep_fp32_settings(recipe: dict[str, Any] | None) -> None:
    device = GPUDevice(
        index=0, uuid="GPU-fixture", name="fixture", total_memory_bytes=1024, used_memory_bytes=0, utilization=0
    )
    model = select_models(("yolo26n",))[0]
    settings = None if recipe is None else native_defaults() | recipe | {"model": model.architecture, "amp": False}
    profile = training_profile(model, 32, (device,), yolo=settings)
    assert profile.model == model
    assert profile.precision == ("True" if recipe is None else "False")


def test_bf16_probe_retains_native_device_admission(tmp_path: Path) -> None:
    import torch

    model = torch.nn.Linear(3, 1)
    before = model.weight.detach().clone()
    trainer = SimpleNamespace(
        model=model,
        optimizer=torch.optim.SGD(model.parameters(), lr=0.1),
        scaler=torch.amp.GradScaler("cpu", enabled=False),
        device=torch.device("cpu"),
    )
    with pytest.raises(RuntimeError, match="bfloat16 autocast requires CUDA"):
        batch_probe._optimize(_request(tmp_path, "bf16"), trainer, accumulation=1, amp=True)
    assert torch.equal(before, model.weight)


@pytest.mark.parametrize("augmentation", ["native", "json", "mosaic"])
def test_composed_fp32_recipes_admit_native_json_and_mosaic(tmp_path: Path, augmentation: str) -> None:
    import albumentations as alb
    from hydra import compose, initialize_config_module
    from hydra_zen import store
    from omegaconf import OmegaConf

    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401 - register product configuration
    from clearml_yolo.entrypoints.hydra.transforms import prepare_transforms

    overrides = [
        "model=ultralytics",
        "ultralytics.model=yolo26n.pt",
        "ultralytics.amp=false",
        "ultralytics.compile=false",
        "ultralytics.batch=null",
        "ultralytics.epochs=2",
    ]
    if augmentation != "native":
        transforms = (
            [alb.Mosaic(target_size=(960, 960), cell_shape=(960, 960), p=1)]
            if augmentation == "mosaic"
            else [alb.HorizontalFlip(p=1)]
        )
        path = tmp_path / "recipe.json"
        path.write_text(json.dumps(alb.to_dict(alb.Compose(transforms))), encoding="utf-8")
        overrides += ["transforms=albumentations", f"transforms.pipeline_file={path}"]
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline", overrides=overrides)
    prepared = prepare_transforms(config)
    values = OmegaConf.to_container(config.ultralytics, resolve=True)
    assert isinstance(values, dict)
    device = GPUDevice(
        index=0, uuid="GPU-fixture", name="fixture", total_memory_bytes=1024, used_memory_bytes=0, utilization=0
    )
    profile = training_profile(
        select_models(("yolo26n",))[0],
        960,
        (device,),
        yolo={str(key): value for key, value in values.items()},
        transforms=prepared,
    )
    assert profile.precision == "False"
    assert profile.compilation is False
    assert profile.model.architecture == "yolo26n.pt"
    assert profile.effective_size == (960, 960)
    assert (prepared.snapshot is None) == (augmentation == "native")
