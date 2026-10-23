"""Approved DEIM source and matching native backbone selections."""

from clearml_yolo.core.assets import DEIM_REVISION, AssetSpec

_REPOSITORY = "https://github.com/Intellindust-AI-Lab/DEIMv2"
_DISTILLED = {
    "s": ("vitt_distill.pt", "1YMTq_woOLjAcZnHSYNTsNg7f0ahj5LPs"),
    "m": ("vittplus_distill.pt", "1COHfjzq5KfnEaXTluVGEOMdhpuVcG6Jt"),
}
_DINO = {"l": ("vits16", "08c60483"), "x": ("vits16plus", "4057cbaa")}


def source_asset() -> AssetSpec:
    return AssetSpec(
        backend="deimv2",
        preset="source",
        filename=f"{DEIM_REVISION}.tar.gz",
        canonical_url=f"{_REPOSITORY}/archive/{DEIM_REVISION}.tar.gz",
        revision=DEIM_REVISION,
        override="model.source_dir",
        kind="deim-source",
    )


def backbone_asset(preset: str) -> AssetSpec:
    if preset in _DISTILLED:
        filename, identifier = _DISTILLED[preset]
        url = f"https://drive.usercontent.google.com/download?id={identifier}&export=download&confirm=t"
        checksum = None
        access = (
            "Use the official DEIMv2 README's ViT-Tiny/ViT-Tiny+ download "
            "if Google Drive requests confirmation."
        )
    else:
        name, checksum = _DINO[preset]
        filename = f"dinov3_{name}_pretrain_lvd1689m-{checksum}.pth"
        url = f"https://dl.fbaipublicfiles.com/dinov3/dinov3_{name}/{filename}"
        access = (
            "Meta DINOv3 weights require accepting the DINOv3 license and obtaining access at "
            "https://ai.meta.com/resources/models-and-libraries/dinov3-downloads/. "
            "Download the matching original .pth with your authorized link "
            "and copy it to the destination."
        )
    return AssetSpec(
        backend="deimv2",
        preset=preset,
        filename=filename,
        canonical_url=url,
        revision=DEIM_REVISION,
        checksum=checksum,
        override="model.train.backbone_weights",
        access_requirement=access,
    )
