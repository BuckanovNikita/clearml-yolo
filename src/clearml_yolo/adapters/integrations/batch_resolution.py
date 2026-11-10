"""Resolve opt-in training batches after device and dataset selection."""

from pathlib import Path
from typing import Any

from clearml_yolo.adapters.integrations.batch_lookup import TableRecommendation, resolve_batch_estimate
from clearml_yolo.adapters.runtime.distributed import selected_gpu_indices
from clearml_yolo.adapters.runtime.gpu_inventory import GPUDevice, discover_gpus
from clearml_yolo.adapters.storage.batch_sizes import BatchSizeStore
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.batch_estimation import GPUHardware, select_models
from clearml_yolo.core.models import Device, ModelConfig
from clearml_yolo.core.transforms import TransformConfig


def _selected(value: Device) -> tuple[GPUDevice, ...]:
    if value in ("cpu", "mps"):
        raise ValueError("batch=null requires CUDA estimates; set an explicit batch for CPU/MPS")
    inventory = discover_gpus()
    indices = selected_gpu_indices(value) or (0,)
    lookup = {device.index: device for device in inventory}
    if any(index not in lookup for index in indices):
        raise ValueError("Training device is outside the current CUDA visibility")
    return tuple(lookup[index] for index in indices)


def batch_provenance(recommendation: TableRecommendation) -> dict[str, Any]:
    return {
        "origin": "batch_sizes_table",
        "table_digest": recommendation.table_digest,
        "model": recommendation.model,
        "image_size": recommendation.image_size,
        "global_batch": recommendation.global_batch,
        "per_gpu_batch": recommendation.per_gpu_batch,
        "selected_entries": [
            {
                "target_gpu": selection.target_gpu.model_dump(mode="json"),
                "entry": selection.entry.model_dump(mode="json"),
                "fallback": selection.fallback,
                "resolved_per_gpu_batch": selection.per_gpu_batch,
            }
            for selection in recommendation.selections
        ],
    }


def _hardware(devices: tuple[GPUDevice, ...]) -> tuple[GPUHardware, ...]:
    return tuple(
        GPUHardware(name=device.name, total_memory_bytes=device.total_memory_bytes, uuid=device.uuid)
        for device in devices
    )


def resolve_native_batch(
    config: ModelConfig,
    _prepared: PreparedDataset,
    _transforms: TransformConfig | None,
) -> tuple[ModelConfig, dict[str, Any] | None]:
    if config.train.batch is not None:
        return config, None
    if not isinstance(config.train.imgsz, int):
        raise TypeError("Non-square training requires an explicit batch")
    selected = _selected(config.train.device)
    model = select_models((f"{config.backend}/{config.preset}",))[0]
    case = resolve_batch_estimate(
        model,
        config.train.imgsz,
        _hardware(selected),
        BatchSizeStore(),
        device_indices=tuple(device.index for device in selected),
    )
    resolved = config.model_copy(deep=True)
    resolved.train.batch = case.global_batch
    resolved.train.device = [device.index for device in selected]
    return resolved, batch_provenance(case)


def resolve_yolo_batch(
    architecture: str | Path,
    settings: dict[str, Any],
    _prepared: PreparedDataset,
    _transforms: TransformConfig | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if "batch" not in settings or settings["batch"] is not None:
        return settings, None
    from ultralytics.utils.torch_utils import parse_device

    size = settings["imgsz"]
    if not isinstance(size, int) or isinstance(size, bool):
        raise TypeError("Non-square training requires an explicit batch")
    # Native parsing resolves its auto-device selector without relaunching training
    # or altering CUDA visibility. Persisted replay retains the original selector.
    devices = parse_device(settings.get("device") or "")
    selected = _selected(devices or None)
    try:
        model = select_models((str(architecture),))[0]
    except ValueError as error:
        raise ValueError("Custom YOLO architectures require an explicit batch") from error
    case = resolve_batch_estimate(
        model,
        size,
        _hardware(selected),
        BatchSizeStore(),
        device_indices=tuple(device.index for device in selected),
    )
    return settings | {
        "batch": case.global_batch,
        "device": [device.index for device in selected],
    }, batch_provenance(case)
