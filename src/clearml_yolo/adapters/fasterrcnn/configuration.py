"""Fixed preprocessing semantics shared by native and exported Faster R-CNN."""

from clearml_yolo.core.models import Preprocessing

MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)
STRIDE = 32


def validate_preprocessing(preprocessing: Preprocessing) -> None:
    if (
        preprocessing.resize != "letterbox"
        or preprocessing.mean != MEAN
        or preprocessing.std != STD
        or preprocessing.stride != STRIDE
    ):
        raise ValueError("Checkpoint preprocessing is incompatible with native Faster R-CNN")
