"""Fixed preprocessing semantics shared by Torchvision detector families."""

from pathlib import Path
from typing import Any, Protocol

from clearml_yolo.core.models import ImageSize, Preprocessing

MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)
STRIDE = 32


class DetectorBuilder(Protocol):
    """Construct an SDK model while keeping family dispatch outside shared execution."""

    def __call__(
        self,
        preset: str,
        num_classes: int,
        *,
        pretrained: bool,
        backbone_weights: Path | None = None,
        image_size: ImageSize = 800,
        score_thresh: float = 0.001,
        nms_thresh: float = 0.7,
        detections_per_img: int = 300,
    ) -> Any: ...


def validate_preprocessing(preprocessing: Preprocessing) -> None:
    if (
        preprocessing.resize != "letterbox"
        or preprocessing.mean != MEAN
        or preprocessing.std != STD
        or preprocessing.stride != STRIDE
    ):
        raise ValueError(
            "Checkpoint preprocessing is incompatible with native Torchvision detectors"
        )
