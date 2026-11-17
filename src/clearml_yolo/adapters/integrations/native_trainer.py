"""Native trainer with process-local callback ownership in spawned DDP workers.

Ultralytics serializes the trainer class into fresh DDP interpreters, so frozen inputs (the
custom transform snapshot and an optional fixed batch/epoch recipe) travel as class
attributes of a task-local subclass, never as unknown native arguments or global state.
Construction and training both run inside ``native_runtime`` because workers may load native
settings that enable ClearML; no SDK settings file is written. A fixed recipe fails training
when native code changes the batch, or exceeds or repeats an epoch.

Native OOM recovery is exhausted at every training-batch start, so an OOM re-raises the
original error instead of halving the batch; initial AutoBatch selection is unaffected.
Output directories are validated after native save-dir resolution and before any weights or
``args.yaml`` are written.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, override

from ultralytics.cfg import get_save_dir
from ultralytics.models.yolo.detect import DetectionTrainer
from ultralytics.utils.torch_utils import unwrap_model

from clearml_yolo.adapters.integrations.native_runtime import (
    final_training_evaluation,
    native_runtime,
)
from clearml_yolo.adapters.storage.filesystem import validate_output_tree
from clearml_yolo.core.transforms import TransformConfig

_fixed_recipe: ContextVar[tuple[int, int] | None] = ContextVar("fixed_training_recipe", default=None)


@contextmanager
def fixed_training_recipe(*, batch: int, epochs: int) -> Iterator[None]:
    """Opt into a fixed native execution recipe, including serialized worker classes."""
    if batch < 1 or epochs < 1:
        raise ValueError("Fixed training batch and epochs must be positive")
    token = _fixed_recipe.set((batch, epochs))
    try:
        yield
    finally:
        _fixed_recipe.reset(token)


class OwnedDetectionTrainer(DetectionTrainer):
    """Retain native loops while scoping callbacks before trainer initialization.

    Ultralytics serializes this class for its fresh DDP interpreters. Their native
    settings may enable ClearML, so construction and training both need the worker
    guard; no SDK settings file or import-time mutation carries that switch.
    """

    transform_config = TransformConfig()
    required_recipe: tuple[int, int] | None = None
    _last_checked_epoch = -1

    def _check_fixed_recipe(self) -> None:
        if self.required_recipe is not None:
            batch, epochs = self.required_recipe
            if self.batch_size != batch or self.epochs != epochs:
                raise RuntimeError("Native training changed the fixed batch or epoch recipe")

    @override
    def _build_train_pipeline(self) -> None:
        self._check_fixed_recipe()
        super()._build_train_pipeline()  # type: ignore[no-untyped-call]

    @override
    def run_callbacks(self, event: str) -> None:
        if event == "on_train_batch_start":
            # Installed Ultralytics exhausts OOM recovery at three retries. Arm
            # that gate after initial AutoBatch/setup so its catch re-raises the
            # original error before halving the selected batch or rebuilding.
            # Successful epoch completion resets the native counter normally.
            self._oom_retries = 3
        if self.required_recipe is not None and event == "on_train_epoch_start":
            self._check_fixed_recipe()
            if not 0 <= self.epoch < self.required_recipe[1]:
                raise RuntimeError("Native training exceeded the fixed epoch recipe")
            if self.epoch <= self._last_checked_epoch:
                raise RuntimeError("Native training repeated an epoch in a fixed recipe")
            self._last_checked_epoch = self.epoch
        super().run_callbacks(event)

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
    def final_eval(self) -> None:
        with final_training_evaluation():
            super().final_eval()  # type: ignore[no-untyped-call]  # Native validation has no annotations.

    @override
    def train(self) -> None:
        with native_runtime():
            validate_output_tree(self.save_dir)
            super().train()  # type: ignore[no-untyped-call]  # Native loop has no annotations.


def trainer_with_transforms(transforms: TransformConfig | None) -> type[OwnedDetectionTrainer]:
    """Capture frozen configuration in the class serialized by native DDP cloudpickle."""
    recipe = _fixed_recipe.get()
    if (transforms is None or transforms.mode == "native") and recipe is None:
        return OwnedDetectionTrainer
    if transforms is not None and transforms.mode != "native" and transforms.snapshot is None:
        raise ValueError("Custom trainer requires a resolved transform snapshot")
    captured = transforms.model_copy(deep=True) if transforms is not None else TransformConfig()

    # A task-local class is serialized by value, so fresh ranks inherit the snapshot
    # without adding unknown native arguments or changing global trainer classes.
    class CustomDetectionTrainer(OwnedDetectionTrainer):
        transform_config = captured
        required_recipe = recipe

    return CustomDetectionTrainer
