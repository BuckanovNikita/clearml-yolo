"""Real Ultralytics training with only its accelerator boundaries adapted to CPU DDP."""

import hashlib
import time
from copy import copy
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, override
from unittest.mock import patch

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel
from torch.utils.data.distributed import DistributedSampler
from ultralytics.engine import validator as validator_module
from ultralytics.models.yolo.detect import DetectionTrainer, DetectionValidator
from ultralytics.utils.torch_utils import unwrap_model


class _CpuDistributedDataParallel(DistributedDataParallel):
    """Keep upstream's DDP class checks and arguments, replacing its CPU device IDs."""

    def __init__(self, module: Any, *args: Any, **kwargs: Any) -> None:
        if kwargs.get("device_ids") == [None]:
            kwargs["device_ids"] = None
        super().__init__(module, *args, **kwargs)


class _CpuDetectionValidator(DetectionValidator):
    def __init__(self, *args: Any, evidence: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.evidence = evidence

    @override
    def __call__(self, trainer: Any = None, model: Any = None, **kwargs: Any) -> Any:
        key = "validation_calls" if trainer is not None else "final_validation_calls"
        self.evidence[key] += 1
        if trainer is not None:
            return super().__call__(trainer=trainer, model=model, **kwargs)
        # Upstream stores constructor aliases as unexported runtime module globals.
        runtime_validator: Any = validator_module
        backend = runtime_validator.AutoBackend

        def cpu_backend(*args: Any, **options: Any) -> Any:
            options["device"] = torch.device("cpu")
            return backend(*args, **options)

        # Ranked final validation assumes an accelerator even for args.device='cpu'.
        # Preserve its ranked loop and gathers while adapting just device selection.
        with (
            patch.object(
                validator_module,
                "get_torch_device_backend",
                return_value=SimpleNamespace(current_device=lambda: 0),
            ),
            patch.object(validator_module, "AutoBackend", cpu_backend),
        ):
            return super().__call__(trainer=trainer, model=model, **kwargs)


class CpuDetectionTrainer(DetectionTrainer):
    """Exercise the inherited trainer, sampler, loss, optimizer, EMA and final eval."""

    def __init__(
        self, *, root: Path, scenario: str, evidence: dict[str, Any], callbacks: dict[str, Any]
    ) -> None:
        self.root = root
        self.scenario = scenario
        self.evidence = evidence
        self.initial_parameters = ""
        self.previous_parameters = ""
        self.epoch_samples: list[str] = []
        self.epoch_optimizer_steps = 0
        dist.init_process_group("gloo", timeout=timedelta(seconds=30))
        super().__init__(overrides=self._overrides(), _callbacks=callbacks)
        self.world_size = dist.get_world_size()
        self.ddp = False  # Already launched by torchrun; do not spawn another launcher.
        torch.set_num_threads(1)
        self.evidence.update(
            world_size=self.world_size, backend=dist.get_backend(), device=str(self.device)
        )

    def _overrides(self) -> dict[str, Any]:
        return {
            "model": str(self.root / "yolov8n.yaml"),
            "data": str(self.root / "data.yaml"),
            "device": "cpu",
            "epochs": 2,
            "imgsz": 64,
            "batch": 8,
            "nbs": 8,
            "optimizer": "SGD",
            "lr0": 0.01,
            "momentum": 0.9,
            "weight_decay": 0.0005,
            "warmup_epochs": 0,
            "amp": False,
            "compile": False,
            "workers": 0,
            "plots": False,
            "pretrained": False,
            "rect": False,
            "deterministic": True,
            "close_mosaic": 0,
            "save": True,
            "val": True,
            "project": str(self.root / "train"),
            "name": "run",
            "exist_ok": True,
            "hsv_h": 0.0,
            "hsv_s": 0.0,
            "hsv_v": 0.0,
            "degrees": 0.0,
            "translate": 0.0,
            "scale": 0.0,
            "shear": 0.0,
            "perspective": 0.0,
            "flipud": 0.0,
            "fliplr": 0.0,
            "mosaic": 0.0,
            "mixup": 0.0,
            "cutmix": 0.0,
            "copy_paste": 0.0,
            "erasing": 0.0,
            "auto_augment": None,
            "augmentations": [],
        }

    @override
    def _setup_ddp(self) -> None:
        assert dist.is_initialized()
        assert dist.get_backend() == "gloo"
        assert self.device.type == "cpu"
        assert self.world_size == dist.get_world_size()

    @override
    def _setup_train(self) -> None:
        with patch.object(
            torch.nn.parallel, "DistributedDataParallel", _CpuDistributedDataParallel
        ):
            super()._setup_train()  # type: ignore[no-untyped-call]

    @override
    def get_validator(self) -> Any:
        return _CpuDetectionValidator(
            self.test_loader,
            save_dir=self.save_dir,
            args=copy(self.args),
            _callbacks=self.callbacks,
            evidence=self.evidence,
        )

    @override
    def preprocess_batch(self, batch: Any) -> Any:
        self.epoch_samples.extend(Path(path).name for path in batch["im_file"])
        return super().preprocess_batch(batch)

    @override
    def optimizer_step(self) -> None:
        super().optimizer_step()  # type: ignore[no-untyped-call]
        self.epoch_optimizer_steps += 1

    def _parameters_sha256(self) -> str:
        digest = hashlib.sha256()
        # Upstream annotates model as its pre-setup path, then replaces it with a module.
        model: Any = self.model
        for name, parameter in unwrap_model(model).named_parameters():
            if parameter.requires_grad:
                digest.update(name.encode())
                digest.update(parameter.detach().cpu().contiguous().numpy().tobytes())
        return digest.hexdigest()

    @override
    def run_callbacks(self, event: str) -> None:
        super().run_callbacks(event)
        if event == "on_train_start":
            self.evidence["ddp"] = isinstance(self.model, DistributedDataParallel)
            self.evidence["distributed_sampler"] = isinstance(
                self.train_loader.sampler, DistributedSampler
            )
            self.initial_parameters = self._parameters_sha256()
            self.evidence["initial_parameters_sha256"] = self.initial_parameters
            self.previous_parameters = self.initial_parameters
            model: Any = self.model
            self.evidence["parameter_count"] = sum(
                parameter.numel() for parameter in model.parameters()
            )
        elif event == "on_train_epoch_start":
            self.epoch_samples = []
            self.epoch_optimizer_steps = 0
            rank = dist.get_rank()
            if self.epoch == 1 and self.scenario == f"rank{rank}_error":
                raise RuntimeError(f"Injected rank {rank} failure at epoch 1")
        elif event == "on_train_epoch_end":
            digest = self._parameters_sha256()
            self.evidence["epochs"].append(
                {
                    "epoch": self.epoch,
                    "samples": list(self.epoch_samples),
                    "losses": self.label_loss_items(self.tloss),  # type: ignore[no-untyped-call]
                    "parameters_sha256": digest,
                    "parameters_changed": digest != self.previous_parameters,
                    "optimizer_steps": self.epoch_optimizer_steps,
                }
            )
            self.previous_parameters = digest
        elif event == "on_fit_epoch_end" and self.epoch == 0 and dist.get_rank() == 0:
            (self.root / "first-epoch-ready").touch()
            deadline = time.monotonic() + 30
            while not (self.root / "release-first-epoch").exists():
                if time.monotonic() >= deadline:
                    raise TimeoutError("Owner did not release the first epoch telemetry gate")
                time.sleep(0.05)
