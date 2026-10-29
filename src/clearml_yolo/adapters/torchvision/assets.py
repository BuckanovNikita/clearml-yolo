"""Describe the selected Torchvision/timm pretrained backbone assets and read-only caches."""

import importlib
import importlib.metadata
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from clearml_yolo.core.assets import AssetCache, AssetSpec, HubAsset

TIMM_MODELS = {
    "convnext_tiny": "convnext_tiny.fb_in22k_ft_in1k",
    "swin_tiny": "swin_tiny_patch4_window7_224.ms_in1k",
    "dinov2_small": "vit_small_patch14_dinov2.lvd142m",
    "dinov3_small": "vit_small_patch16_dinov3.lvd1689m",
}


def _torch_cache(filename: str) -> Path:
    hub = importlib.import_module("torch.hub")
    return Path(hub.get_dir()) / "checkpoints" / filename


def _hf_cache(hub: HubAsset, filename: str) -> tuple[Path, ...]:
    sdk = importlib.import_module("huggingface_hub")
    path = sdk.try_to_load_from_cache(
        hub.repository, filename, cache_dir=hub.cache_dir, revision=hub.revision
    )
    return (Path(path),) if isinstance(path, str) else ()


def _description(preset: str) -> tuple[str, str, tuple[AssetCache, ...], HubAsset | None]:
    if preset in {"resnet50_fpn", "resnet101_fpn"}:
        models = importlib.import_module("torchvision.models")
        weights = (
            models.ResNet50_Weights.DEFAULT
            if preset == "resnet50_fpn"
            else models.ResNet101_Weights.DEFAULT
        )
        return str(weights.url), importlib.metadata.version("torchvision"), (), None
    timm = importlib.import_module("timm")
    native = timm.get_pretrained_cfg(TIMM_MODELS[preset])
    if native is None:
        raise ValueError(f"No native pretrained asset configuration for {preset}")
    version = importlib.metadata.version("timm") + ":" + TIMM_MODELS[preset]
    # Source precedence is SDK policy (including TIMM_USE_OLD_CACHE). Keep its
    # discovery in this adapter so preparation follows normal create_model calls.
    builder = importlib.import_module("timm.models._builder")
    source, location = builder._resolve_pretrained_source(native.to_dict())  # noqa: SLF001
    if source == "url":
        return str(location), version, (), None
    if source != "hf-hub":
        raise ValueError(f"Unsupported native pretrained source for {preset}: {source}")
    native_hub = importlib.import_module("timm.models._hub")
    repository, revision = native_hub.hf_split(
        location[0] if isinstance(location, tuple) else location
    )
    filename = location[1] if isinstance(location, tuple) else "pytorch_model.bin"
    constants = importlib.import_module("huggingface_hub.constants")
    hub = HubAsset(
        repository=repository,
        revision=revision or "main",
        filename=filename,
        cache_dir=Path(constants.HF_HUB_CACHE).expanduser().resolve(),
    )
    caches: list[AssetCache] = []
    if native.hf_hub_id:
        for cached_filename in (hub.filename, "model.safetensors"):
            for path in _hf_cache(hub, cached_filename):
                blob = path.resolve().name
                caches.append(
                    AssetCache(
                        path=path,
                        canonical_url=(
                            f"https://huggingface.co/{repository}/resolve/"
                            f"{hub.revision}/{cached_filename}"
                        ),
                        checksum=blob if re.fullmatch(r"[0-9a-f]{64}", blob) else None,
                    )
                )
    if native.url:
        return str(native.url), version, tuple(caches), hub
    if not native.hf_hub_id:
        raise ValueError(f"No pretrained source registered for {preset}")
    url = f"https://huggingface.co/{repository}/resolve/{hub.revision}/{hub.filename}"
    return url, version, tuple(caches), hub


def pretrained_asset(
    preset: str, *, backend: Literal["fasterrcnn", "fcos"] = "fasterrcnn"
) -> AssetSpec:
    url, revision, caches, hub = _description(preset)
    filename = Path(urlsplit(url).path).name
    match = re.search(r"-([0-9a-f]{8,64})\.", filename)
    return AssetSpec(
        backend=backend,
        preset=preset,
        filename=filename,
        canonical_url=url,
        revision=revision,
        checksum=match.group(1) if match else None,
        override="model.train.backbone_weights",
        cache_candidates=(_torch_cache(filename),),
        equivalent_caches=caches,
        native_cache=hub.cache_dir if hub is not None else _torch_cache(filename).parent.resolve(),
        hub=hub,
        access_requirement=(
            "If this DINOv3 repository requires access, accept its license and use HF_TOKEN "
            "or the standard Hugging Face token file, or copy the native checkpoint offline."
            if preset == "dinov3_small"
            else None
        ),
    )
