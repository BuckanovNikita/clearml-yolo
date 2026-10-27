"""Describe the selected Torchvision/timm pretrained backbone assets and read-only caches."""

import importlib
import importlib.metadata
import os
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from clearml_yolo.core.assets import AssetCache, AssetSpec

TIMM_MODELS = {
    "convnext_tiny": "convnext_tiny.fb_in22k_ft_in1k",
    "swin_tiny": "swin_tiny_patch4_window7_224.ms_in1k",
    "dinov2_small": "vit_small_patch14_dinov2.lvd142m",
    "dinov3_small": "vit_small_patch16_dinov3.lvd1689m",
}


def _torch_cache(filename: str) -> Path:
    hub = importlib.import_module("torch.hub")
    return Path(hub.get_dir()) / "checkpoints" / filename


def _hf_cache(repository: str, filename: str) -> tuple[Path, ...]:
    default = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "huggingface"
    home = Path(os.environ.get("HF_HOME") or default).expanduser()
    cache = Path(
        os.environ.get("HF_HUB_CACHE") or os.environ.get("HUGGINGFACE_HUB_CACHE") or home / "hub"
    )
    root = cache / ("models--" + repository.replace("/", "--"))
    reference = root / "refs" / "main"
    if not reference.is_file():
        return ()
    revision = reference.read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        return ()
    return (root / "snapshots" / revision / filename,)


def _description(preset: str) -> tuple[str, str, tuple[AssetCache, ...]]:
    if preset in {"resnet50_fpn", "resnet101_fpn"}:
        models = importlib.import_module("torchvision.models")
        weights = (
            models.ResNet50_Weights.DEFAULT
            if preset == "resnet50_fpn"
            else models.ResNet101_Weights.DEFAULT
        )
        return str(weights.url), importlib.metadata.version("torchvision"), ()
    timm = importlib.import_module("timm")
    native = timm.get_pretrained_cfg(TIMM_MODELS[preset])
    if native is None:
        raise ValueError(f"No native pretrained asset configuration for {preset}")
    version = importlib.metadata.version("timm") + ":" + TIMM_MODELS[preset]
    caches: list[AssetCache] = []
    if native.hf_hub_id:
        repository = str(native.hf_hub_id)
        for filename in (native.hf_hub_filename or "pytorch_model.bin", "model.safetensors"):
            for path in _hf_cache(repository, filename):
                blob = path.resolve().name
                caches.append(
                    AssetCache(
                        path=path,
                        canonical_url=f"https://huggingface.co/{repository}/resolve/main/{filename}",
                        checksum=blob if re.fullmatch(r"[0-9a-f]{64}", blob) else None,
                    )
                )
    if native.url:
        return str(native.url), version, tuple(caches)
    if not native.hf_hub_id:
        raise ValueError(f"No pretrained source registered for {preset}")
    filename = native.hf_hub_filename or "pytorch_model.bin"
    repository = str(native.hf_hub_id)
    url = f"https://huggingface.co/{repository}/resolve/main/{filename}"
    return url, version, tuple(caches)


def pretrained_asset(
    preset: str, *, backend: Literal["fasterrcnn", "fcos"] = "fasterrcnn"
) -> AssetSpec:
    url, revision, caches = _description(preset)
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
        access_requirement=(
            "If this DINOv3 repository requires access, accept its license and use HF_TOKEN "
            "or the standard Hugging Face token file, or copy the native checkpoint offline."
            if preset == "dinov3_small"
            else None
        ),
    )
