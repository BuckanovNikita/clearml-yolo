"""Fresh recipe-bound capacity evidence before native acceptance training."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from hydra import compose, initialize_config_module
from hydra_zen import store
from omegaconf import OmegaConf

from clearml_yolo.adapters.integrations.batch_probe import NativeBatchProbe
from clearml_yolo.adapters.runtime.distributed import selected_gpu_indices
from clearml_yolo.adapters.runtime.gpu_inventory import (
    GPUDevice,
    discover_gpus,
    gpu_states,
    require_idle,
    require_memory_reserve,
)
from clearml_yolo.adapters.storage.batch_estimates import FileBatchEstimateStore
from clearml_yolo.application.use_cases.batch_estimate import estimate_batches
from clearml_yolo.core.batch_estimation import SearchSettings, SyntheticWorkload, select_models, select_training_batch
from clearml_yolo.core.models import ModelConfig
from clearml_yolo.entrypoints.hydra.transforms import prepare_transforms
from severstal_helpers import file_sha256, write_json


def selected_device(value: str) -> GPUDevice:
    indices = selected_gpu_indices(value) or (0,)
    if len(indices) != 1:
        raise ValueError("Native acceptance capacity requires exactly one explicitly selected GPU")
    lookup = {device.index: device for device in discover_gpus()}
    return lookup[indices[0]]


def check_reserve(device: GPUDevice, reserve: int) -> None:
    state = gpu_states().get(device.uuid)
    if state is None:
        raise RuntimeError("GPU telemetry disappeared during native acceptance")
    require_memory_reserve((device,), (state.used_for(device.total_memory_bytes),), reserve)


def estimate_scenario(root: Path, request: dict[str, Any]) -> dict[str, Any]:
    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401 - shared product config registration

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline", overrides=request["overrides"])
    transforms = prepare_transforms(config)
    native = ModelConfig.model_validate(OmegaConf.to_container(config.model, resolve=True))
    raw = OmegaConf.to_container(config.ultralytics, resolve=True) if native.backend == "ultralytics" else None
    if raw is not None and not isinstance(raw, dict):
        raise TypeError("YOLO settings must be a mapping")
    yolo = {str(key): value for key, value in raw.items()} if raw is not None else None
    probe = NativeBatchProbe(native=native if yolo is None else None, yolo=yolo, transforms=transforms)
    selection = "yolo26n" if request["selection"] == "ultralytics" else request["selection"]
    model = select_models((selection,))[0]
    device = selected_device(request["device"])
    reserve = int(request["minimum_free_memory_bytes"])
    baseline = require_idle((device,), force=reserve > 0)
    require_memory_reserve((device,), baseline, reserve)
    size = int(yolo["imgsz"]) if yolo is not None else native.train.imgsz
    if not isinstance(size, int):
        raise TypeError("Native acceptance requires square preset resolution")
    profile = probe.profile(model, size, (device.index,))
    frame = pd.read_csv(Path(request["dataset"]) / "smoke.csv")
    labeled = frame[frame["instance_label"].notna()]
    workload = SyntheticWorkload(
        classes=int(labeled["instance_label"].nunique()),
        objects_per_image=int(labeled.groupby("image_name").size().max()),
    )
    settings = SearchSettings(
        force=reserve > 0,
        minimum_free_memory_bytes=reserve,
        memory_fraction=min(0.9, (device.total_memory_bytes - reserve) / device.total_memory_bytes),
    )
    write_json(
        root / "batch-admission.json",
        {
            "gpu": device.model_dump(mode="json"),
            "baseline_used_bytes": baseline[0],
            "minimum_free_memory_bytes": reserve,
            "workload": workload.model_dump(mode="json"),
            "profile": profile.model_dump(mode="json"),
            "settings": settings.model_dump(mode="json"),
        },
    )
    (case,) = estimate_batches(
        (profile,),
        workload,
        settings,
        probe=probe,
        store=FileBatchEstimateStore(root / "batch-estimates.json"),
        now=lambda: datetime.now(UTC).isoformat(),
        refresh=True,
    )
    batch = select_training_batch(case, 160)
    current = require_idle((device,), force=settings.force)
    require_memory_reserve((device,), current, reserve)
    if current[0] > baseline[0] + 64 * 1024**2:
        raise RuntimeError("GPU memory changed materially after estimation; a fresh case is required")
    prefix = "ultralytics" if yolo is not None else "model.train"
    overrides = [value for value in request["overrides"] if not value.startswith(f"{prefix}.batch=")]
    overrides.append(f"{prefix}.batch={batch}")
    training = config.ultralytics if yolo is not None else config.model.train
    training.batch = batch
    write_json(root / "resolved-inputs.json", OmegaConf.to_container(config, resolve=True))
    result = {
        "raw_capacity": case.global_batch,
        "chosen_batch": batch,
        "capacity_status": case.status,
        "epochs": 2,
        "overrides": overrides,
        "pretraining_used_bytes": current[0],
        "minimum_free_memory_bytes": reserve,
        "profile": case.profile.model_dump(mode="json"),
        "manifest_sha256": request["manifest_sha256"],
        "estimate_sha256": file_sha256(root / "batch-estimates.json"),
        "request_sha256": file_sha256(root / "request.json"),
        "resolved_inputs_sha256": file_sha256(root / "resolved-inputs.json"),
        "augmentation_sha256": transforms.snapshot.sha256 if transforms.snapshot is not None else None,
    }
    write_json(root / "training-inputs.json", result)
    return result
