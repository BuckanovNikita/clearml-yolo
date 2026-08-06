"""Re-run a previous model's weights over the *current* test split.

Comparing a new model against the baseline's stored dashboards compares numbers
computed on a different set of images; the only apples-to-apples baseline is the
old checkpoint scored on today's images, by the same inference code the new model
went through (``clearml_yolo.inference.predict_on_images``, which the predict
stage also calls).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd
from loguru import logger
from pydantic import BaseModel

from clearml_yolo.inference import predict_on_images

Predictor = Callable[..., pd.DataFrame]
ClassNameLoader = Callable[[str | Path], dict[int, str]]

_REQUIRED_COLUMNS = ("split", "image_path", "instance_label")
_MAX_REPORTED_PATHS = 5
# Numeric-looking identifiers (COCO stems, "0001") would come back as int64 and stop
# joining to the ground truth, so the cached frame must reload as the model produced it.
_CACHED_TEXT_COLUMNS = {"image_name": str, "instance_label": str}


class VocabularyReport(BaseModel):
    """How the checkpoint's class vocabulary lines up with the split's ground truth."""

    model_classes: list[str]
    unknown_to_model: list[str]
    unknown_to_ground_truth: list[str]


def _model_class_names(weights: str | Path) -> dict[int, str]:
    from ultralytics.models import YOLO

    # A ClearML-registered model carries no label enumeration (empty `labels`,
    # `config_text` and `get_labels_enumeration()`), so the checkpoint's own mapping
    # is the only source that cannot silently mislabel every detection.
    names: dict[int, str] = YOLO(str(weights)).names
    return names


def _select_split(ground_truth: pd.DataFrame, split: str) -> pd.DataFrame:
    missing_columns = [name for name in _REQUIRED_COLUMNS if name not in ground_truth.columns]
    if missing_columns:
        raise ValueError(
            f"Ground truth is missing the column(s) {missing_columns}; re-inference needs "
            f"the current split's own images. Got columns: {sorted(ground_truth.columns)}"
        )

    rows = ground_truth[ground_truth["split"] == split]
    if rows.empty:
        available = sorted({str(value) for value in ground_truth["split"].unique()})
        raise ValueError(
            f"Split {split!r} has no ground-truth rows; available splits: {available}"
        )
    return rows


def _existing_image_paths(split_rows: pd.DataFrame, split: str) -> list[str]:
    paths = [str(path) for path in split_rows["image_path"].unique()]
    missing = [path for path in paths if not Path(path).is_file()]
    if missing:
        # Dropping unreadable images instead would shrink the scored set and surface
        # later as a recall drop that reads like a model regression.
        shown = missing[:_MAX_REPORTED_PATHS]
        suffix = "" if len(missing) <= _MAX_REPORTED_PATHS else f" (+{len(missing) - len(shown)})"
        raise ValueError(
            f"{len(missing)} of {len(paths)} images of split {split!r} do not exist on disk: "
            f"{shown}{suffix}"
        )
    return paths


def _vocabulary_report(
    model_names: dict[int, str], split_labels: pd.Series[str]
) -> VocabularyReport:
    model_classes = [model_names[index] for index in sorted(model_names)]
    ground_truth_classes = {str(label) for label in split_labels.unique()}
    return VocabularyReport(
        model_classes=model_classes,
        unknown_to_model=sorted(ground_truth_classes - set(model_classes)),
        unknown_to_ground_truth=sorted(set(model_classes) - ground_truth_classes),
    )


def reinfer_split(
    weights: str | Path,
    ground_truth: pd.DataFrame,
    split: str,
    output: Path,
    *,
    conf: float,
    iou: float,
    imgsz: int,
    batch: int,
    device: str | None,
    image_name: str,
    reuse_existing: bool = True,
    predictor: Predictor = predict_on_images,
    class_names: ClassNameLoader = _model_class_names,
) -> tuple[pd.DataFrame, VocabularyReport]:
    """Score ``weights`` on the images of ``split`` in ``ground_truth``.

    The images come from the current ground truth, never from the baseline task's
    stored predictions — that substitution is the bug this whole comparison exists to
    remove. Inference settings must be the ones the new model was predicted with.

    ``predictor`` and ``class_names`` are the two seams that keep everything except
    the inference itself testable without a GPU: the class vocabulary cannot be
    recovered from the predictions (only detected classes appear there), so the
    checkpoint's name map is loaded separately.

    Raises:
        ValueError: If the split is empty, the required columns are absent, or any of
            the split's images is missing on disk.
    """
    split_rows = _select_split(ground_truth, split)
    image_paths = _existing_image_paths(split_rows, split)

    if reuse_existing and output.is_file():
        predictions = pd.read_csv(output, dtype=_CACHED_TEXT_COLUMNS)
        logger.info(
            "Reusing {} cached baseline predictions for split {!r} from {}",
            len(predictions),
            split,
            output,
        )
    else:
        predictions = predictor(
            weights,
            image_paths,
            conf=conf,
            iou=iou,
            imgsz=imgsz,
            batch=batch,
            device=device,
            image_name=image_name,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        predictions.to_csv(output, index=False)
        logger.info(
            "Re-inferred {} baseline predictions over {} images of split {!r} into {}",
            len(predictions),
            len(image_paths),
            split,
            output,
        )

    vocabulary = _vocabulary_report(class_names(weights), split_rows["instance_label"])
    if vocabulary.unknown_to_model:
        logger.warning(
            "Checkpoint {} cannot predict {} class(es) present in split {!r}: {}",
            Path(weights).name,
            len(vocabulary.unknown_to_model),
            split,
            vocabulary.unknown_to_model,
        )
    return predictions, vocabulary
