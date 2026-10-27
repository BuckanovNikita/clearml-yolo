"""Resolve opt-in training batches after device and dataset selection."""

from pathlib import Path
from typing import Any

from clearml_yolo.adapters.integrations.batch_lookup import resolve_batch_estimate
from clearml_yolo.adapters.integrations.batch_profiles import training_profile
from clearml_yolo.adapters.runtime.distributed import selected_gpu_indices
from clearml_yolo.adapters.runtime.gpu_inventory import GPUDevice, discover_gpus
from clearml_yolo.adapters.storage.batch_estimates import FileBatchEstimateStore
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.batch_estimation import ResolvedRecommendation, select_models
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


def batch_provenance(recommendation: ResolvedRecommendation) -> dict[str, Any]:
    values: dict[str, Any] = {
        "origin": recommendation.origin,
        "global_batch": recommendation.global_batch,
        "per_gpu_batch": recommendation.per_gpu_batch,
        "status": recommendation.status,
        "profile": recommendation.profile.model_dump(mode="json"),
        "source_estimate_keys": list(recommendation.source_estimate_keys),
        "source_statuses": list(recommendation.source_statuses),
        "sources": [
            {
                "estimate_key": key,
                "global_batch": source.global_batch,
                "per_gpu_batch": source.per_gpu_batch,
                "status": source.status,
                "created_at": source.created_at,
                "synthetic_workload": source.workload.model_dump(mode="json"),
                "profile": source.profile.model_dump(mode="json"),
                "settings": source.settings.model_dump(mode="json"),
            }
            for key, source in zip(
                recommendation.source_estimate_keys, recommendation.sources, strict=True
            )
        ],
    }
    if recommendation.origin == "measured":
        source = recommendation.sources[0]
        values.update(
            estimate_key=recommendation.source_estimate_keys[0],
            created_at=source.created_at,
            synthetic_workload=source.workload.model_dump(mode="json"),
        )
    return values


def resolve_native_batch(
    config: ModelConfig,
    prepared: PreparedDataset,
    transforms: TransformConfig | None,
) -> tuple[ModelConfig, dict[str, Any] | None]:
    if config.train.batch is not None:
        return config, None
    if not isinstance(config.train.imgsz, int):
        raise TypeError("Non-square training requires an explicit batch")
    selected = _selected(config.train.device)
    model = select_models((f"{config.backend}/{config.preset}",))[0]
    profile = training_profile(
        model,
        config.train.imgsz,
        selected,
        native=config,
        transforms=transforms,
    )
    case = resolve_batch_estimate(profile, prepared, FileBatchEstimateStore())
    resolved = config.model_copy(deep=True)
    resolved.train.batch = case.global_batch
    resolved.train.device = [device.index for device in selected]
    return resolved, batch_provenance(case)


def resolve_yolo_batch(
    architecture: str | Path,
    settings: dict[str, Any],
    prepared: PreparedDataset,
    transforms: TransformConfig | None,
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
    profile = training_profile(model, size, selected, yolo=settings, transforms=transforms)
    case = resolve_batch_estimate(profile, prepared, FileBatchEstimateStore())
    return settings | {
        "batch": case.global_batch,
        "device": [device.index for device in selected],
    }, batch_provenance(case)
