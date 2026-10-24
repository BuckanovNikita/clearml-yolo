"""Native trainer with process-local callback ownership in spawned DDP workers."""

from typing import Any, override

from ultralytics.cfg import get_save_dir
from ultralytics.models.yolo.detect import DetectionTrainer
from ultralytics.utils.torch_utils import unwrap_model

from clearml_yolo.adapters.integrations.native_runtime import native_runtime
from clearml_yolo.adapters.storage.filesystem import validate_output_tree
from clearml_yolo.core.transforms import TransformConfig


class OwnedDetectionTrainer(DetectionTrainer):
    """Retain native loops while scoping callbacks before trainer initialization.

    Ultralytics serializes this class for its fresh DDP interpreters. Their native
    settings may enable ClearML, so construction and training both need the worker
    guard; no SDK settings file or import-time mutation carries that switch.
    """

    transform_config = TransformConfig()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        with native_runtime():
            super().__init__(*args, **kwargs)

    @override
    def build_dataset(self, img_path: str, mode: str = "train", batch: int | None = None) -> Any:
        if mode != "train" or self.transform_config.mode == "native":
            return super().build_dataset(img_path, mode, batch)
        from clearml_yolo.adapters.yolo.augmentation import AugmentedYOLODataset

        # The SDK annotates model as its initial path, then replaces it with a module.
        model: Any = self.model
        runtime_model: Any = unwrap_model(model)
        stride = max(int(runtime_model.stride.max()), 32)
        return AugmentedYOLODataset(
            img_path=img_path,
            imgsz=self.args.imgsz,
            batch_size=batch,
            augment=True,
            hyp=self.args,
            rect=self.args.rect,
            cache=self.args.cache or None,
            single_cls=self.args.single_cls,
            stride=stride,
            pad=0.0,
            prefix="train: ",
            task=self.args.task,
            classes=self.args.classes,
            data=self.data,
            fraction=1.0,
            transforms=self.transform_config,
        )

    @override
    def check_resume(self, overrides: dict[str, Any]) -> None:
        # BaseTrainer invokes this after effective configuration is resolved and
        # before creating weights/ or writing args.yaml. Preserve native routing,
        # including its directory increment and supported resume normalization.
        super().check_resume(overrides)  # type: ignore[no-untyped-call]
        validate_output_tree(get_save_dir(self.args))

    @override
    def train(self) -> None:
        with native_runtime():
            validate_output_tree(self.save_dir)
            super().train()  # type: ignore[no-untyped-call]  # Native loop has no annotations.


def trainer_with_transforms(transforms: TransformConfig | None) -> type[OwnedDetectionTrainer]:
    """Capture frozen configuration in the class serialized by native DDP cloudpickle."""
    if transforms is None or transforms.mode == "native":
        return OwnedDetectionTrainer
    if transforms.snapshot is None:
        raise ValueError("Custom trainer requires a resolved transform snapshot")
    captured = transforms.model_copy(deep=True)

    # A task-local class is serialized by value, so fresh ranks inherit the snapshot
    # without adding unknown native arguments or changing global trainer classes.
    class CustomDetectionTrainer(OwnedDetectionTrainer):
        transform_config = captured

    return CustomDetectionTrainer
