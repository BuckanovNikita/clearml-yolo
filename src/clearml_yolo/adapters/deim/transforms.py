"""DEIM training augmentation and local torchvision compatibility subclasses.

The upstream custom transforms implement the pre-0.22 private hook. Only these
objects are reconstructed as local subclasses; upstream classes and source stay intact.
"""

from typing import TYPE_CHECKING, Any

from PIL import Image

from clearml_yolo.adapters.augmentation.torch_data import (
    detection_sample,
    tensor_target,
    training_pipeline,
    worker_seed,
)
from clearml_yolo.core.transforms import TransformConfig

if TYPE_CHECKING:
    from clearml_yolo.adapters.augmentation.pipeline import DetectionSample

_FINALIZATION = frozenset({"Resize", "ConvertPILImage", "Normalize", "ConvertBoxes"})


def _transform(self: Any, inpt: Any, params: dict[str, Any]) -> Any:
    return self._transform(inpt, params)


def bridge_transforms(compose: Any) -> None:
    for index, transform in enumerate(compose.transforms):
        name = type(transform).__name__
        if name not in {"ConvertPILImage", "ConvertBoxes"}:
            continue
        # Identical names preserve the native Compose policy's type-name selection.
        bridge = type(name, (type(transform),), {"transform": _transform})
        if name == "ConvertPILImage":
            replacement = bridge(dtype=transform.dtype, scale=transform.scale)
        else:
            replacement = bridge(fmt=transform.fmt, normalize=transform.normalize)
        compose.transforms[index] = replacement


def custom_training_recipe(transforms: dict[str, Any], collate: dict[str, Any]) -> None:
    """Remove optional native image, epoch-policy and batch augmentation before construction."""
    # Native sanitizers impose their own minimum-size filter and do not keep all
    # per-instance fields aligned. Shared JSON processing already owns box validity.
    transforms["ops"] = [op for op in transforms["ops"] if op["type"] in _FINALIZATION]
    # The native constructor requires epoch/ops whenever policy is non-null;
    # None selects its ordinary unscheduled composition without those lookups.
    transforms["policy"] = None
    transforms["mosaic_prob"] = 0.0
    collate.update(mixup_prob=0.0, copyblend_prob=0.0, base_size_repeat=None)


class TrainingTransform:
    """Preserve DEIM's three-value transform protocol around shared augmentation."""

    def __init__(self, dataset: Any, native: Any, config: TransformConfig, seed: int) -> None:
        self.dataset = dataset
        self.native = native
        self.pipeline = training_pipeline(config, seed)
        self.seed = seed

    def raw_sample(self, index: int) -> "DetectionSample":
        image, target = self.dataset.load_item(index)
        return detection_sample(image, target)

    def __call__(
        self, image: Image.Image, target: dict[str, Any], dataset: Any
    ) -> tuple[Any, Any, Any]:
        if self.pipeline is None:
            raise RuntimeError("Custom training requires an augmentation pipeline")
        index = int(target["idx"])
        sample = self.pipeline.apply(
            detection_sample(image, target),
            index=index,
            size=len(self.dataset),
            load_sample=self.raw_sample,
            seed=worker_seed(self.seed),
        )
        image_out, target_out, dataset_out = self.native(
            Image.fromarray(sample.image),
            tensor_target(sample, target, bounding_boxes=True),
            dataset,
        )
        # The pinned final ConvertBoxes produces normalized cxcywh. Torchvision
        # Resize updates boxes but not COCO area, so restore pixel-area alignment.
        height, width = image_out.shape[-2:]
        boxes = target_out["boxes"]
        target_out["area"] = boxes[:, 2] * boxes[:, 3] * height * width
        return image_out, target_out, dataset_out
