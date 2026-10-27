"""Bind estimator compatibility to installed recipes and concrete execution settings."""

import hashlib
import importlib.metadata
import json
import math
import platform
from pathlib import Path
from typing import Any

from clearml_yolo.adapters.assets.execution import prepare_model_assets
from clearml_yolo.adapters.runtime.gpu_inventory import GPUDevice
from clearml_yolo.adapters.yolo.config import TRAIN_KEYS, native_defaults
from clearml_yolo.core.assets import DEIM_REVISION
from clearml_yolo.core.batch_estimation import GPUHardware, ModelVariant, TrainingProfile
from clearml_yolo.core.models import ModelConfig, model_preset
from clearml_yolo.core.transforms import TransformConfig


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _implementation() -> str:
    """Editable source changes invalidate measurements before a version is released."""
    root = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256()
    for folder in (
        "core",
        "adapters/yolo",
        "adapters/deim",
        "adapters/rfdetr",
        "adapters/fcos",
        "adapters/fasterrcnn",
        "adapters/torchvision",
        "adapters/integrations",
        "adapters/runtime",
    ):
        for path in sorted((root / folder).glob("*.py")):
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return "batch-v1:" + digest.hexdigest()


def _versions(backend: str) -> dict[str, str]:
    packages = ["clearml-yolo", "torch", "torchvision", "numpy"]
    if backend == "ultralytics":
        packages += ["ultralytics", "albumentations"]
    elif backend == "rfdetr":
        packages += ["rfdetr", "pytorch-lightning", "timm", "pycocotools"]
    elif backend == "deimv2":
        packages += ["timm", "faster-coco-eval"]
    else:
        packages += ["timm", "pycocotools"]
    versions = {name: importlib.metadata.version(name) for name in packages}
    versions["python"] = platform.python_version()
    # CUDA libraries and the compiler can change allocation and kernel behavior
    # independently of Torch's package version (including editable environments).
    versions.update(
        (distribution.metadata["Name"], distribution.version)
        for distribution in importlib.metadata.distributions()
        if distribution.metadata["Name"].lower().startswith(("nvidia-", "triton"))
    )
    if backend == "deimv2":
        versions["deim-source"] = DEIM_REVISION
    return versions


def training_profile(
    model: ModelVariant,
    imgsz: int,
    devices: tuple[GPUDevice, ...],
    *,
    native: ModelConfig | None = None,
    yolo: dict[str, Any] | None = None,
    transforms: TransformConfig | None = None,
) -> TrainingProfile:
    if not devices:
        raise ValueError("Saved batch estimates require explicitly resolved CUDA devices")
    if transforms is not None and transforms.mode != "native":
        raise ValueError(
            "Custom augmentation requires an explicit batch; no standard estimate fits"
        )
    nominal = (imgsz, imgsz)
    stride = 64 if model.architecture.endswith("6u.pt") else 32
    rounded = math.ceil(imgsz / stride) * stride
    if model.backend == "ultralytics":
        values = native_defaults() | (yolo or {})
        scale = float(values["multi_scale"])
        effective = (
            (int(rounded * (1 + scale) + stride) - 1) // stride * stride
            if scale > 0 else rounded
        )
        effective = max(effective, rounded)
        optimizer = str(values["optimizer"])
        optimizers = ("AdamW", "MuSGD") if optimizer == "auto" else (optimizer,)
        ignored = {
            "device",
            "batch",
            "imgsz",
            "model",
            "data",
            "project",
            "name",
            "save_dir",
            "epochs",
            "workers",
            "exist_ok",
            "mode",
            "save",
            "save_period",
            "plots",
            "verbose",
            "patience",
            "time",
            "val",
            # CSV preparation owns the contiguous class vocabulary; the synthetic
            # target generator already uses that same zero-based convention.
            "cls_remap",
        }
        recipe = {key: value for key, value in values.items() if key in TRAIN_KEYS - ignored}
        precision = str(values["amp"])
        compilation = values["compile"]
        accumulation = f"nominal:{values['nbs']}"
        ema = True
    else:
        selected = native or model_preset(model.selection)
        values = selected.train.model_dump(mode="json")
        if native is not None and selected.train.pretrained:
            # Execution receives resolved assets; normalize only exact default asset paths.
            default, _ = prepare_model_assets(model_preset(model.selection), training=True)
            for key in ("weights", "backbone_weights"):
                if values[key] == default.train.model_dump(mode="json")[key]:
                    values[key] = None
        ignored = {"device", "batch", "imgsz", "epochs", "workers", "seed"}
        recipe = {key: value for key, value in values.items() if key not in ignored}
        if model.backend == "deimv2":
            recipe["source_revision"] = DEIM_REVISION
        optimizers = ("AdamW",)
        precision = "native-auto" if selected.train.amp else "fp32"
        compilation = False
        accumulation = f"fixed:{selected.train.grad_accum_steps}"
        ema = selected.train.use_ema
        if model.backend == "deimv2":
            effective = int(imgsz * 1.25 / 32) * 32
        elif model.backend == "rfdetr":
            # All four pinned detection presets use patch_size=16 and num_windows=2;
            # expanded native per-batch scales include offset +5.
            effective = (imgsz // 32 + 5) * 32
        else:
            effective = rounded
    return TrainingProfile(
        model=model,
        nominal_size=nominal,
        effective_size=(effective, effective),
        gpus=tuple(
            GPUHardware(name=d.name, total_memory_bytes=d.total_memory_bytes, uuid=d.uuid)
            for d in devices
        ),
        dependencies=_versions(model.backend),
        precision=precision,
        compilation=compilation,
        optimizers=optimizers,
        accumulation=accumulation,
        ema=ema,
        augmentation=_digest(recipe),
        implementation_revision=_implementation(),
    )
