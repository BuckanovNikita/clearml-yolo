"""Ultralytics must recognise every kind of albumentations transform, DDP children included."""

from __future__ import annotations

import py_compile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import albumentations as A
import numpy as np
import pytest
from ultralytics.data.augment import Albumentations
from ultralytics.utils import dist

from clearml_yolo.ultralytics_patch import DDP_PREAMBLE, apply_patches


class RenamedFlip(A.DualTransform):  # type: ignore[misc]
    """A spatial transform whose class name ultralytics has never heard of."""

    def apply(self, img: np.ndarray, **params: Any) -> np.ndarray:
        return np.ascontiguousarray(img[:, ::-1])

    def apply_to_bboxes(self, bboxes: np.ndarray, **params: Any) -> np.ndarray:
        return bboxes


@pytest.fixture(scope="module", autouse=True)
def patched() -> None:
    apply_patches()


def _bbox_aware(transforms: list[Any]) -> bool:
    node = Albumentations(p=1.0, transforms=transforms)
    assert node.transform is not None
    has_params = node.transform.processors.get("bboxes") is not None
    # The flag drives whether __call__ passes bboxes at all, so it has to agree.
    assert node.contains_spatial == has_params
    return has_params


def test_geometry_nested_in_a_oneof_is_recognised() -> None:
    """The class name is "OneOf", which is in no spatial set anywhere."""
    assert _bbox_aware([A.OneOf([A.Rotate(p=1.0), A.Affine(p=1.0)], p=1.0)])


def test_geometry_nested_two_levels_deep_is_recognised() -> None:
    assert _bbox_aware([A.Sequential([A.OneOf([A.Rotate(p=1.0)], p=1.0)], p=1.0)])


def test_an_unfamiliar_spatial_transform_is_recognised() -> None:
    assert _bbox_aware([RenamedFlip(p=1.0)])


def test_a_pixel_only_pipeline_stays_without_bbox_params() -> None:
    """Passing bboxes through a pipeline that cannot move them only adds validation."""
    assert not _bbox_aware([A.RandomBrightnessContrast(p=1.0)])


def test_a_oneof_of_pixel_transforms_stays_without_bbox_params() -> None:
    assert not _bbox_aware([A.OneOf([A.Blur(p=1.0), A.ToGray(p=1.0)], p=1.0)])


def test_a_recognised_top_level_transform_is_untouched() -> None:
    assert _bbox_aware([A.HorizontalFlip(p=0.5)])


def test_ultralytics_own_defaults_still_work() -> None:
    """transforms=None means ultralytics' built-in pixel-only list."""
    node = Albumentations(p=1.0)

    assert node.transform is not None
    assert not node.contains_spatial


def test_the_rebuilt_pipeline_keeps_its_transforms_in_order() -> None:
    transforms = [A.Blur(p=1.0), A.OneOf([A.Rotate(p=1.0)], p=1.0), A.ToGray(p=1.0)]

    node = Albumentations(p=1.0, transforms=transforms)

    assert node.transform is not None
    assert [type(t).__name__ for t in node.transform.transforms] == [
        "Blur",
        "OneOf",
        "ToGray",
    ]


def test_the_rebuilt_pipeline_moves_boxes_with_the_pixels() -> None:
    """The whole point: a nested flip must take the box with it."""
    node = Albumentations(p=1.0, transforms=[A.OneOf([A.HorizontalFlip(p=1.0)], p=1.0)])
    assert node.transform is not None

    result = node.transform(
        image=np.zeros((100, 100, 3), dtype=np.uint8),
        bboxes=np.array([[0.2, 0.5, 0.2, 0.2]], dtype=np.float32),
        class_labels=np.array([0]),
    )

    assert result["bboxes"][0][0] == pytest.approx(0.8)


def test_applying_the_patches_twice_does_not_stack_them() -> None:
    apply_patches()
    apply_patches()

    assert _bbox_aware([A.OneOf([A.Rotate(p=1.0)], p=1.0)])


def test_the_ddp_child_module_imports_the_patch(tmp_path: Path) -> None:
    """DDP children are fresh interpreters that import a pristine ultralytics, so the
    generated module has to pull the patch in itself."""
    # Only `args` and the class path are read, and BaseTrainer is far too heavy to build.
    trainer: Any = SimpleNamespace(
        args=SimpleNamespace(model="yolo11n.pt", epochs=1, augmentations=None)
    )

    generated = Path(dist.generate_ddp_file(trainer))
    try:
        content = generated.read_text(encoding="utf-8")
        assert content.startswith(DDP_PREAMBLE)
        py_compile.compile(str(generated), cfile=str(tmp_path / "child.pyc"), doraise=True)
    finally:
        generated.unlink()
