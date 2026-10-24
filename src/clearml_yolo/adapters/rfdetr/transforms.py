"""Training-only raw RF-DETR samples before native deterministic finalization."""

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


class TrainingTransform:
    """The pinned SDK dataset/Compose objects remain opaque at this boundary."""

    def __init__(self, dataset: Any, native: Any, config: TransformConfig, seed: int) -> None:
        self.dataset = dataset
        self.native = native
        self.pipeline = training_pipeline(config, seed)
        self.config = config
        self.seed = seed
        self.indices = {image_id: index for index, image_id in enumerate(dataset.ids)}

    def raw_sample(self, index: int) -> "DetectionSample":
        image_id = self.dataset.ids[index]
        # Native private decode/annotation seams are pinned to RF-DETR VERSION.
        # They bypass __getitem__, and therefore never recursively augment donors.
        image, _ = self.dataset._decode_image(image_id)  # noqa: SLF001
        annotations = self.dataset._load_target(image_id)  # noqa: SLF001
        image, target = self.dataset.prepare(
            image, {"image_id": image_id, "annotations": annotations}
        )
        return detection_sample(image, target)

    def __call__(self, image: Image.Image, target: dict[str, Any]) -> tuple[Any, Any]:
        if self.pipeline is None:
            raise RuntimeError("Custom training requires an augmentation pipeline")
        index = self.indices[int(target["image_id"])]
        sample = self.pipeline.apply(
            detection_sample(image, target),
            index=index,
            size=len(self.dataset),
            load_sample=self.raw_sample,
            seed=worker_seed(self.seed),
        )
        image_out, target_out = self.native(
            Image.fromarray(sample.image), tensor_target(sample, target)
        )
        return image_out, target_out


def install_training_transforms(datamodule: Any, config: TransformConfig, *, seed: int) -> None:
    """Install once after setup; native repeated setup retains the existing dataset."""
    if config.mode == "native":
        return
    # These instance fields are the pinned native data module's dataset ownership seam.
    dataset = datamodule._dataset_train  # noqa: SLF001
    if dataset is None:
        raise RuntimeError("RF-DETR setup('fit') must run before installing augmentation")
    native = dataset._transforms  # noqa: SLF001
    if isinstance(native, TrainingTransform):
        if native.config == config and native.seed == seed:
            return
        native = native.native
    dataset._draft_size = None  # noqa: SLF001  # Custom geometry consumes original pixels.
    dataset._transforms = TrainingTransform(dataset, native, config, seed)  # noqa: SLF001
