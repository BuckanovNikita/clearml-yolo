"""Native trainer with process-local callback ownership in spawned DDP workers."""

from typing import Any, override

from ultralytics.models.yolo.detect import DetectionTrainer

from clearml_yolo.adapters.integrations.native_runtime import native_runtime


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
    def train(self) -> None:
        with native_runtime():
            super().train()  # type: ignore[no-untyped-call]  # Native loop has no annotations.
