"""CPU evidence for RF-DETR probe inputs, native loading and actual step accounting."""

import importlib
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any, override

import pytest
import torch

from clearml_yolo.adapters.rfdetr.probe import (
    SyntheticDataset,
    _config,
    _fit,
    _ProbeProgress,
    _SyntheticData,
)
from clearml_yolo.adapters.runtime.gpu_memory import GPUMemory
from clearml_yolo.application.training_workers import BatchProbeRequest
from clearml_yolo.core.batch_estimation import (
    GPUHardware,
    ModelVariant,
    SearchSettings,
    SyntheticWorkload,
    TrainingProfile,
)
from clearml_yolo.core.models import ModelConfig, TrainSettings


def _request(tmp_path: Path) -> BatchProbeRequest:
    return BatchProbeRequest(
        token=uuid.uuid4().hex,
        profile=TrainingProfile(
            model=ModelVariant(
                selection="rfdetr/nano", backend="rfdetr", preset="nano", architecture="rfdetr/nano"
            ),
            nominal_size=(64, 64),
            effective_size=(224, 224),
            gpus=(GPUHardware(name="fixture", total_memory_bytes=1024),),
            dependencies={"rfdetr": "1.11.2"},
            precision="native-auto",
            compilation=False,
            optimizers=("AdamW",),
            accumulation="fixed:2",
            ema=True,
            augmentation="native",
            implementation_revision="test",
        ),
        workload=SyntheticWorkload(),
        settings=SearchSettings(warmup_steps=1, measured_steps=2),
        global_batch=2,
        optimizer="AdamW",
        output=tmp_path,
        config=ModelConfig(
            backend="rfdetr",
            preset="nano",
            train=TrainSettings(imgsz=64, grad_accum_steps=2, workers=0, pretrained=False),
        ),
    )


def test_synthetic_native_targets_preserve_density_zero_and_bounds(tmp_path: Path) -> None:
    dataset = SyntheticDataset(_request(tmp_path), 4)
    image, target = dataset[0]
    assert len(dataset) == 4
    assert image.shape == (3, 224, 224)
    assert torch.isfinite(image).all()
    assert len(target["boxes"]) == 300
    assert torch.unique(target["labels"]).tolist() == list(range(150))
    centers, extents = target["boxes"][:, :2], target["boxes"][:, 2:]
    assert ((centers - extents / 2) >= 0).all()
    assert ((centers + extents / 2) <= 1).all()
    assert (target["area"] > 0).all()
    assert target["image_id"].item() == 0
    assert dataset[1][1]["image_id"].item() == 1
    assert torch.equal(dataset[0][0], image)


def test_probe_config_is_detached_and_rejects_incompatible_recipe(tmp_path: Path) -> None:
    request = _request(tmp_path)
    copied = _config(request)
    assert copied.train.batch == request.global_batch
    assert request.config is not None
    assert request.config.train.batch == 4
    with pytest.raises(ValueError, match="uncompiled AdamW"):
        _config(request.model_copy(update={"optimizer": "SGD"}))
    with pytest.raises(ValueError, match="nominal resolution"):
        _config(
            request.model_copy(
                update={"profile": request.profile.model_copy(update={"nominal_size": (96, 96)})}
            )
        )


def test_optimizer_counter_counts_calls_and_rejects_nonfinite_gradients() -> None:
    parameter = torch.nn.Parameter(torch.ones(1))
    optimizer = torch.optim.AdamW([parameter])
    progress = _ProbeProgress(1, (32, 32))
    trainer = SimpleNamespace(optimizers=[optimizer], scaler=None)
    progress.on_train_start(trainer, None)
    for _ in range(2):
        parameter.sum().backward()  # type: ignore[no-untyped-call]
    assert progress.optimizer_steps == 0
    progress.on_before_optimizer_step(trainer, None, optimizer)
    optimizer.step()
    assert progress.optimizer_steps == 1
    parameter.grad = torch.full_like(parameter, torch.inf)
    with pytest.raises(FloatingPointError, match="gradients"):
        progress.on_before_optimizer_step(trainer, None, optimizer)
    assert progress.optimizer_steps == 1
    progress.teardown(trainer, None, "fit")
    optimizer.step()
    assert progress.optimizer_steps == 1


def test_native_datamodule_and_lightning_accumulation_execute_exact_workload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use real native data transfer and real Lightning, with a tiny CPU model."""
    lightning = importlib.import_module("pytorch_lightning")
    native = importlib.import_module("rfdetr.training")
    configuration = importlib.import_module("rfdetr.config")
    request = _request(tmp_path)
    mc = configuration.RFDETRNanoConfig(resolution=64, pretrain_weights=None, num_classes=150)
    tc = configuration.TrainConfig(
        dataset_dir=str(tmp_path),
        output_dir=str(tmp_path),
        batch_size=2,
        grad_accum_steps=2,
        num_workers=0,
        epochs=1,
        accelerator="cpu",
        use_ema=False,
        amp_dtype=None,
        tensorboard=False,
    )
    data_type = type("CPUSyntheticData", (_SyntheticData, native.RFDETRDataModule), {})
    data = data_type(mc, tc)
    data._dataset_train = SyntheticDataset(request, 12)
    data._dataset_val = SyntheticDataset(request, 2)
    callback_type = type("CPUProbeProgress", (_ProbeProgress, lightning.Callback), {})
    teardown_started = False
    observations: list[int] = []

    class Memory(GPUMemory):
        @override
        def observe(self) -> None:
            assert not teardown_started
            self.peak_memory_bytes = 850
            self.non_allocator_memory_bytes = 100
            observations.append(progress.optimizer_steps)

    memory = Memory()
    progress = callback_type(2, (224, 224), memory=memory)

    class TinyModel:
        def __init__(self) -> None:
            super().__init__()
            self.weight = torch.nn.Parameter(torch.ones(1))

        def training_step(self, batch: Any, _batch_idx: int) -> torch.Tensor:
            samples, targets = batch
            assert len(targets) == 2
            assert targets[0]["labels"].min() == 0
            return (torch.mean(samples.tensors) * self.weight).square().sum()

        def validation_step(self, batch: Any, _batch_idx: int) -> dict[str, Any]:
            return {
                "targets": batch[1],
                "results": [{"boxes": torch.ones(1, 4), "scores": torch.ones(1)}] * len(batch[1]),
            }

        def configure_optimizers(self) -> torch.optim.AdamW:
            return torch.optim.AdamW([self.weight])

    module_type = type("TinyCPUProbe", (TinyModel, lightning.LightningModule), {})
    trainer = native.build_trainer(
        tc,
        mc,
        include_training_callbacks=False,
        accelerator="cpu",
        devices=1,
        callbacks=[progress],
        logger=False,
        enable_checkpointing=False,
        enable_progress_bar=False,
        enable_model_summary=False,
        max_steps=3,
        max_epochs=1,
        limit_train_batches=6,
        limit_val_batches=1,
        val_check_interval=6,
        check_val_every_n_epoch=1,
        num_sanity_val_steps=0,
    )
    native_teardown = trainer.strategy.teardown

    def teardown() -> None:
        nonlocal teardown_started
        teardown_started = True
        native_teardown()

    monkeypatch.setattr(trainer.strategy, "teardown", teardown)
    trainer.fit(module_type(), data)
    assert progress.optimizer_steps == 3
    assert progress.validation_steps == 1
    assert not progress._hooks
    assert teardown_started
    assert observations[0] == 0
    assert observations[-1] == 3
    assert len(observations) >= 6
    assert memory.peak_memory_bytes == 850
    assert memory.non_allocator_memory_bytes == 100


def test_nonfinite_loss_and_partial_validation_are_not_completed_steps() -> None:
    progress = _ProbeProgress(2, (32, 32))
    with pytest.raises(FloatingPointError, match="loss"):
        progress.on_train_batch_end(None, None, {"loss": torch.tensor(float("nan"))}, None, 0)
    with pytest.raises(ValueError, match="requested batch"):
        progress.on_validation_batch_end(None, None, {"targets": [{}], "results": []}, None, 0)
    assert progress.validation_steps == 0
    with pytest.raises(FloatingPointError, match="validation loss"):
        progress.on_validation_end(
            SimpleNamespace(callback_metrics={"val/loss": torch.tensor(float("nan"))}), None
        )


@pytest.mark.parametrize(("amp", "persistent"), [(True, False), (True, True), (False, False)])
def test_fit_counts_real_amp_updates_before_stopping_and_validating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, amp: bool, persistent: bool
) -> None:
    """Real Lightning/CPU GradScaler skips overflow; only the detector is replaced."""
    lightning = importlib.import_module("pytorch_lightning")
    precision = importlib.import_module("pytorch_lightning.plugins.precision")
    native = importlib.import_module("rfdetr.training")
    configuration = importlib.import_module("rfdetr.config")
    request = _request(tmp_path).model_copy(update={"settings": SearchSettings()})
    config = _config(request)
    config.train.use_ema = False
    request = request.model_copy(
        update={"profile": request.profile.model_copy(update={"ema": False})}
    )
    mc = configuration.RFDETRNanoConfig(resolution=64, pretrain_weights=None, num_classes=150)
    tc = configuration.TrainConfig(
        dataset_dir=str(tmp_path),
        output_dir=str(tmp_path),
        batch_size=2,
        grad_accum_steps=2,
        num_workers=0,
        epochs=1,
        accelerator="cpu",
        use_ema=False,
        amp_dtype=None,
        tensorboard=False,
    )
    callback_type = type("ActualAMPProbeProgress", (_ProbeProgress, lightning.Callback), {})
    progress = callback_type(2, (224, 224))
    validation_updates: list[int] = []
    modules: list[Any] = []
    trainers: list[Any] = []
    scaler = torch.amp.GradScaler("cpu", init_scale=2 if persistent else 8) if amp else None

    class TinyModel:
        def __init__(self, _model_config: Any, _train_config: Any) -> None:
            super().__init__()
            self.weight = torch.nn.Parameter(torch.ones(1))
            self.microbatches = 0
            modules.append(self)

        def training_step(self, batch: Any, _batch_idx: int) -> torch.Tensor:
            self.microbatches += 1
            return (torch.mean(batch[0].tensors) * self.weight).square().sum()

        def on_after_backward(self) -> None:
            # Inject scaled gradient overflow while keeping the actual loss finite.
            if scaler is not None and (persistent or trainers[0].global_step < 2):
                assert self.weight.grad is not None
                self.weight.grad.fill_(torch.inf)

        def validation_step(self, batch: Any, _batch_idx: int) -> dict[str, Any]:
            validation_updates.append(progress.optimizer_steps)
            assert torch.isfinite(self.weight).all()
            return {
                "targets": batch[1],
                "results": [{"boxes": torch.ones(1, 4), "scores": torch.ones(1)}] * len(batch[1]),
            }

        def configure_optimizers(self) -> torch.optim.AdamW:
            return torch.optim.AdamW([self.weight], lr=0.01)

    module_type = type("AMPFitCPUModel", (TinyModel, lightning.LightningModule), {})
    real_build_trainer = native.build_trainer

    def build_cpu_trainer(*args: Any, **kwargs: Any) -> Any:
        if scaler is not None:
            kwargs["precision"] = None
            kwargs["plugins"] = [precision.MixedPrecision("16-mixed", "cpu", scaler=scaler)]
        trainer = real_build_trainer(
            *args,
            **kwargs,
        )
        trainers.append(trainer)
        return trainer

    monkeypatch.setattr(native, "RFDETRModelModule", module_type)
    monkeypatch.setattr(native, "build_trainer", build_cpu_trainer)
    monkeypatch.setattr(
        "clearml_yolo.adapters.rfdetr.probe.training_configuration", lambda *_: (mc, tc)
    )
    monkeypatch.setattr(
        "clearml_yolo.adapters.rfdetr.probe.trainer_devices",
        lambda *_: {"accelerator": "cpu", "devices": 1},
    )
    if persistent:
        with pytest.raises(FloatingPointError, match="scale reduction"):
            _fit(request, config, progress)
        assert progress.optimizer_steps == 0
        assert validation_updates == []
        assert scaler is not None
        assert scaler.get_scale() < 1
    else:
        _fit(request, config, progress)
        assert trainers[0].global_step == (17 if amp else 15)
        assert progress.optimizer_steps == 15
        assert modules[0].microbatches == (34 if amp else 30)
        assert modules[0].weight.item() < 1
        assert validation_updates == [15]
        assert progress.validation_steps == 1
        assert trainers[0].should_stop
        assert not progress._hooks
