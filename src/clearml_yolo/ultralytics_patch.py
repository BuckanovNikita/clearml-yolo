"""Teach ultralytics to recognise every kind of albumentations transform.

Ultralytics decides whether to hand its ``A.Compose`` a ``bbox_params`` by looking each
transform's class *name* up in a hardcoded set of 39 strings. Anything outside that set —
a transform nested in ``A.OneOf``, a subclass of your own, a class albumentations has
added since the list was written — counts as pixel-only, so it moves the image while the
boxes stay behind and the labels quietly stop matching.

The patch replaces the name lookup with the question the names were standing in for: does
this pipeline contain an albumentations ``DualTransform`` at any nesting depth. It also
threads itself into the DDP children, which ultralytics launches from a generated module
that would otherwise import a pristine ultralytics and undo the fix on every rank.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

# Prepended to the module ultralytics generates for its DDP children. Patching in the
# parent is not enough: `torch.distributed.run` starts fresh interpreters that import
# ultralytics themselves and know nothing about anything we changed.
DDP_PREAMBLE = "from clearml_yolo.ultralytics_patch import apply_patches\napply_patches()\n"

_applied = False


def _moves_pixels(transforms: list[Any]) -> bool:
    """Whether any transform in the tree operates on more than the image.

    ``DualTransform`` is albumentations' own answer to this question, and unlike a name
    it stays right for transforms that did not exist when ultralytics was written.
    """
    import albumentations as A

    return any(
        _moves_pixels(list(transform.transforms))
        if isinstance(transform, A.BaseCompose)
        else isinstance(transform, A.DualTransform)
        for transform in transforms
    )


def _patch_spatial_transform_detection() -> None:
    import albumentations as A
    import torch
    from ultralytics.data import augment

    build = augment.Albumentations.__init__

    def build_with_bbox_params(
        self: Any, p: float = 1.0, transforms: list[Any] | None = None
    ) -> None:
        build(self, p=p, transforms=transforms)
        if self.transform is None or self.contains_spatial:
            return

        pipeline = list(self.transform.transforms)
        if not _moves_pixels(pipeline):
            return

        self.contains_spatial = True
        self.transform = A.Compose(
            pipeline,
            bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"]),
        )
        # Mirrors ultralytics: albumentations >= 1.4.21 needs the seed for deterministic
        # transforms across DDP ranks, and older releases have no such method.
        if hasattr(self.transform, "set_random_seed"):
            self.transform.set_random_seed(torch.initial_seed())
        logger.info(
            "Rebuilt the albumentations pipeline with bbox_params: {} move pixels but "
            "ultralytics recognised none of them by name.",
            [type(transform).__name__ for transform in pipeline],
        )

    augment.Albumentations.__init__ = build_with_bbox_params  # type: ignore[method-assign]


def _patch_ddp_child_module() -> None:
    from ultralytics.utils import dist

    generate = dist.generate_ddp_file

    def generate_patched_ddp_file(trainer: Any) -> str:
        path = Path(generate(trainer))
        path.write_text(DDP_PREAMBLE + path.read_text(encoding="utf-8"), encoding="utf-8")
        return str(path)

    dist.generate_ddp_file = generate_patched_ddp_file


def apply_patches() -> None:
    """Patch ultralytics in this interpreter. Safe to call more than once."""
    global _applied
    if _applied:
        return
    _applied = True

    _patch_spatial_transform_detection()
    _patch_ddp_child_module()
