"""Native trainer with process-local callback ownership in spawned DDP workers."""

from typing import Any, override

from ultralytics.cfg import get_save_dir
from ultralytics.models.yolo.detect import DetectionTrainer

from clearml_yolo.adapters.integrations.native_runtime import native_runtime
from clearml_yolo.adapters.storage.filesystem import validate_output_tree


class OwnedDetectionTrainer(DetectionTrainer):
    """Retain native loops while scoping callbacks before trainer initialization.

    Ultralytics serializes this class for its fresh DDP interpreters. Their native
    settings may enable ClearML, so construction and training both need the worker
    guard; no SDK settings file or import-time mutation carries that switch.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        with native_runtime():
            super().__init__(*args, **kwargs)

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
