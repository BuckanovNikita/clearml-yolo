"""RF-DETR's native Lightning fit and SDK prediction behind portable records.

The optional SDK is imported only when execution needs it. Its evolving model and
Lightning objects are intentionally opaque at this boundary; project records remain typed.
"""

import importlib
import importlib.metadata
import math
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from clearml_yolo.adapters.observability.progress import image_progress
from clearml_yolo.adapters.storage.filesystem import validate_output_tree
from clearml_yolo.application.contracts import PREDICTION_COLUMNS, PreparedDataset
from clearml_yolo.core.models import (
    BackendTrainResult,
    CheckpointMetadata,
    Device,
    ModelConfig,
    PredictSettings,
    Preprocessing,
)

VERSION = "1.11.2"
_DEFAULT_IOU = 0.7
_STRIDE = 32
_VARIANTS = {
    "nano": ("RFDETRNano", "rf-detr-nano.pth"),
    "small": ("RFDETRSmall", "rf-detr-small.pth"),
    "medium": ("RFDETRMedium", "rf-detr-medium.pth"),
    "large": ("RFDETRLarge", "rf-detr-large-2026.pth"),
}


def _sdk() -> Any:
    try:
        actual = importlib.metadata.version("rfdetr")
    except importlib.metadata.PackageNotFoundError as exc:
        raise ImportError(
            'RF-DETR requires the default "rfdetr[train]==1.11.2" dependency'
        ) from exc
    if actual != VERSION:
        raise RuntimeError(f"RF-DETR requires version {VERSION}; installed version is {actual}")
    return importlib.import_module("rfdetr")


def _device(value: Device) -> str:
    if isinstance(value, list):
        if len(value) != 1:
            raise ValueError("RF-DETR multi-device execution is unsupported by this adapter")
        value = value[0]
    if isinstance(value, int) or (isinstance(value, str) and value.isdecimal()):
        return f"cuda:{value}"
    if value is None:
        torch = importlib.import_module("torch")
        return "cuda" if torch.cuda.is_available() else "cpu"
    if "," in value:
        raise ValueError("RF-DETR multi-device execution is unsupported by this adapter")
    if value not in {"cpu", "cuda"} and not value.startswith("cuda:"):
        raise ValueError(f"RF-DETR device {value!r} is unsupported; use CPU or one CUDA device")
    return value


def _names(prepared: PreparedDataset) -> tuple[str, ...]:
    contents = yaml.safe_load(prepared.data.read_text())
    names = contents["names"]
    return tuple(names[key] for key in sorted(names)) if isinstance(names, dict) else tuple(names)


def _verify_pretrained(model: Any, weights: Path) -> None:
    torch = importlib.import_module("torch")
    # Use the pinned SDK's safe allowlist for its published checkpoint args.
    native_io = importlib.import_module("rfdetr.utilities.io")
    payload = native_io._safe_torch_load(str(weights))  # noqa: SLF001
    expected = payload["model"]
    actual = model.model.model.state_dict()
    projection = next(
        (
            key
            for key in expected
            if key.startswith("backbone.") and key.endswith("patch_embeddings.projection.weight")
        ),
        None,
    )
    # Patch projection is neither the intentionally replaced class head nor the
    # interpolated positional embedding, so this proves native initialization loaded it.
    if (
        projection is None
        or projection not in actual
        or not torch.equal(
            expected[projection].cpu(),
            actual[projection].cpu(),
        )
    ):
        raise RuntimeError(f"RF-DETR pretrained backbone was not loaded from {weights}")


class _OwnerMetrics:
    """Mixin for a task-owned Lightning Callback without importing Lightning eagerly."""

    def __init__(self, report: Callable[[str, float, int], None]) -> None:
        self.report = report
        self.metrics: dict[str, float] = {}

    def _emit(self, trainer: Any) -> None:
        for name, tensor in trainer.callback_metrics.items():
            value = float(tensor)
            if math.isfinite(value):
                self.metrics[str(name)] = value
                self.report(str(name), value, int(trainer.current_epoch))

    def on_train_epoch_end(self, trainer: Any, _module: Any) -> None:
        self._emit(trainer)

    def on_validation_end(self, trainer: Any, _module: Any) -> None:
        self._emit(trainer)


def train(
    config: ModelConfig,
    prepared: PreparedDataset,
    output: Path,
    report: Callable[[str, float, int], None],
) -> BackendTrainResult:
    output = validate_output_tree(output)
    settings = config.train
    if settings.weights is not None and not settings.weights.is_file():
        raise FileNotFoundError(settings.weights)
    if settings.backbone_weights is not None:
        raise ValueError("RF-DETR backbone_weights is unsupported; use a full native weights file")
    names = _names(prepared)
    device = _device(settings.device)
    output.mkdir(parents=True, exist_ok=True)
    sdk = _sdk()
    training = importlib.import_module("rfdetr.training")
    lightning = importlib.import_module("pytorch_lightning")
    lightning.seed_everything(settings.seed, workers=True)
    variant, _ = _VARIANTS[config.preset]
    constructor = getattr(sdk, variant)
    initial = settings.weights
    if initial is None and settings.pretrained:
        raise ValueError("Prepare the RF-DETR pretrained asset before native construction")
    model = constructor(
        pretrain_weights=str(initial.resolve()) if initial is not None else None,
        device=device,
        num_classes=len(names),
        resolution=settings.imgsz,
    )
    if initial is not None and not initial.is_file():
        raise FileNotFoundError(f"RF-DETR pretrained asset was not downloaded: {initial}")
    if initial is not None:
        _verify_pretrained(model, initial)
    model.model_config.model_name = variant
    arguments = {
        "dataset_dir": str(prepared.data.parent),
        "dataset_file": "roboflow",
        "output_dir": str(output),
        "epochs": settings.epochs,
        "batch_size": settings.batch,
        "grad_accum_steps": settings.grad_accum_steps,
        "num_workers": settings.workers,
        "lr": settings.lr,
        "weight_decay": settings.weight_decay,
        "seed": settings.seed,
        "amp_dtype": "auto" if settings.amp else None,
        "use_ema": settings.use_ema,
        "class_names": list(names),
        "tensorboard": False,
        "wandb": False,
        "mlflow": False,
        "clearml": False,
        "run_test": False,
        "compute_val_loss": True,
        "accelerator": "cpu" if device == "cpu" else "gpu",
    }
    native_config = model.get_train_config(**arguments)
    module = training.RFDETRModelModule(model.model_config, native_config)
    datamodule = training.RFDETRDataModule(model.model_config, native_config)
    devices: int | list[int] = [int(device.split(":")[1])] if ":" in device else 1
    trainer = training.build_trainer(native_config, model.model_config, devices=devices)
    callback_type = type("OwnerMetrics", (_OwnerMetrics, lightning.Callback), {})
    callback = callback_type(report)
    trainer.callbacks.append(callback)
    validate_output_tree(output)
    trainer.fit(module, datamodule)
    weights = output / "checkpoint_best_total.pth"
    if not weights.is_file():
        raise RuntimeError("RF-DETR native training did not produce checkpoint_best_total.pth")
    metadata = CheckpointMetadata(
        backend="rfdetr",
        preset=config.preset,
        class_names=names,
        preprocessing=Preprocessing(resize="stretch", size=settings.imgsz),
        dependencies={
            name: importlib.metadata.version(name)
            for name in ("torch", "torchvision", "rfdetr", "transformers", "pytorch-lightning")
        },
    )
    effective = native_config.model_dump(mode="json")
    effective["model"] = model.model_config.model_dump(mode="json")
    return BackendTrainResult(
        weights=weights,
        metadata=metadata,
        effective_args=effective,
        metrics=callback.metrics,
        artifacts=[path for path in (output / "metrics.csv",) if path.is_file()],
    )


def _prediction_frame(
    predictions: Sequence[tuple[str, Any]], names: tuple[str, ...], max_det: int
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path, detection in predictions:
        if detection.class_id is None or detection.confidence is None:
            continue
        count = 0
        for box, score, class_id in zip(
            detection.xyxy, detection.confidence, detection.class_id, strict=True
        ):
            label = int(class_id)
            if not 0 <= label < len(names):
                continue
            rows.append(
                {
                    "image_name": path,
                    "instance_label": names[label],
                    "confidence": float(score),
                    "bbox_x_tl": float(box[0]),
                    "bbox_y_tl": float(box[1]),
                    "bbox_x_br": float(box[2]),
                    "bbox_y_br": float(box[3]),
                }
            )
            count += 1
            if count >= max_det:
                break
    return pd.DataFrame(rows, columns=PREDICTION_COLUMNS)


def predict(
    config: ModelConfig,
    descriptor: CheckpointMetadata,
    weights: Path,
    image_paths: Sequence[str],
    settings: PredictSettings,
) -> pd.DataFrame:
    trained_size = descriptor.preprocessing.size
    if (
        descriptor.preprocessing.resize != "stretch"
        or descriptor.preprocessing.stride != _STRIDE
        or not isinstance(trained_size, int)
        or trained_size % _STRIDE
    ):
        raise ValueError("Checkpoint preprocessing is incompatible with native RF-DETR")
    if settings.iou != _DEFAULT_IOU or settings.half:
        raise ValueError("RF-DETR nondefault iou and half controls are unsupported")
    size = settings.imgsz or descriptor.preprocessing.size
    if not isinstance(size, int) or size % 32:
        raise ValueError("RF-DETR resolution must be square and divisible by 32")
    predictions: list[tuple[str, Any]] = []
    if image_paths:
        if not weights.is_file():
            raise FileNotFoundError(weights)
        sdk = _sdk()
        constructor = getattr(sdk, _VARIANTS[descriptor.preset][0])
        model = constructor(
            pretrain_weights=str(weights.resolve()),
            device=_device(settings.device),
            num_classes=len(descriptor.class_names),
            num_select=settings.max_det,
            # Loading at the preset default resizes the learned position grid.
            # Preserve its training grid; predict(shape=...) handles requested sizes.
            resolution=trained_size,
        )
        _verify_pretrained(model, weights)
        model.means = list(descriptor.preprocessing.mean)
        model.stds = list(descriptor.preprocessing.std)
        with image_progress(len(image_paths)) as advance:
            for offset in range(0, len(image_paths), settings.batch):
                paths = list(image_paths[offset : offset + settings.batch])
                outputs = model.predict(
                    paths, threshold=settings.conf, shape=(size, size), include_source_image=False
                )
                predictions.extend(zip(paths, outputs, strict=True))
                advance(len(paths))
    frame = _prediction_frame(predictions, descriptor.class_names, settings.max_det)
    frame.attrs.update(
        image_paths=list(image_paths),
        normalized_imgsz=[size, size],
        effective_args=settings.model_dump(mode="json")
        | {
            "backend": config.backend,
            "preset": descriptor.preset,
            "imgsz": size,
            "nms": False,
            "model": str(weights),
        },
    )
    return frame
