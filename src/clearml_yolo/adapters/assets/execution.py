"""Prepare an execution copy while leaving canonical model selectors unchanged."""

from clearml_yolo.adapters.assets.resolver import resolve_assets
from clearml_yolo.adapters.assets.sources import existing_source, extract_resolved_source
from clearml_yolo.adapters.deim.assets import backbone_asset, source_asset
from clearml_yolo.adapters.deim.source import validate_checkout
from clearml_yolo.adapters.fasterrcnn.assets import pretrained_asset as fasterrcnn_asset
from clearml_yolo.adapters.rfdetr.assets import pretrained_asset as rfdetr_asset
from clearml_yolo.core.assets import AssetSpec, ResolvedAsset
from clearml_yolo.core.models import ModelConfig


def _validate_explicit(config: ModelConfig, training: bool) -> None:
    if config.source_dir is not None:
        validate_checkout(config.source_dir)
    if training:
        for weights in (config.train.weights, config.train.backbone_weights):
            if weights is not None and not weights.expanduser().is_file():
                raise FileNotFoundError(f"Explicit model weights do not exist: {weights}")


def _requests(config: ModelConfig, training: bool) -> tuple[AssetSpec, ...]:
    assets: list[AssetSpec] = []
    if config.backend == "deimv2" and config.source_dir is None:
        assets.append(source_asset())
    if not training or not config.train.pretrained or config.train.weights is not None:
        return tuple(assets)
    if config.backend == "rfdetr":
        if config.train.backbone_weights is not None:
            raise ValueError("RF-DETR backbone_weights is unsupported; use model.train.weights")
        assets.append(rfdetr_asset(config.preset))
    elif config.train.backbone_weights is None:
        assets.append(
            backbone_asset(config.preset)
            if config.backend == "deimv2"
            else fasterrcnn_asset(
                config.preset, backend="fcos" if config.backend == "fcos" else "fasterrcnn"
            )
        )
    return tuple(assets)


def _execution_copy(config: ModelConfig, training: bool) -> ModelConfig:
    model = config.model_copy(deep=True)
    if model.source_dir is not None:
        model.source_dir = model.source_dir.expanduser().resolve()
    if training:
        if model.train.weights is not None:
            model.train.weights = model.train.weights.expanduser().absolute()
        if model.train.backbone_weights is not None:
            model.train.backbone_weights = model.train.backbone_weights.expanduser().absolute()
    return model


def prepare_model_assets(
    config: ModelConfig,
    *,
    training: bool,
) -> tuple[ModelConfig, tuple[ResolvedAsset, ...]]:
    """Resolve only assets needed now, retaining all selected nulls in the caller's model."""
    if config.backend == "ultralytics":
        return config.model_copy(deep=True), ()
    _validate_explicit(config, training)
    specs = _requests(config, training)
    existing: list[ResolvedAsset] = []
    pending: list[AssetSpec] = []
    for spec in specs:
        cached = existing_source(spec) if spec.kind == "deim-source" else None
        if cached is None:
            pending.append(spec)
        else:
            existing.append(cached)
    records = (*existing, *resolve_assets(tuple(pending)))
    model = _execution_copy(config, training)
    for record in records:
        if record.override == "model.source_dir":
            model.source_dir = extract_resolved_source(record)
        elif record.override == "model.train.weights":
            model.train.weights = record.path
        elif record.override == "model.train.backbone_weights":
            model.train.backbone_weights = record.path
    return model, records
