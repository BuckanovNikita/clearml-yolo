"""Pure class vocabulary, threshold and split-membership rules."""

import math
from collections.abc import Mapping

import pandas as pd


def validate_thresholds(
    thresholds: Mapping[str, float | int], required_classes: list[str]
) -> dict[str, float]:
    """Return exact numeric thresholds after validating every required class."""
    missing = sorted(set(required_classes) - set(thresholds))
    if missing:
        raise ValueError(f"Confidence thresholds are missing required class(es): {missing}")

    normalized = {str(name): float(value) for name, value in thresholds.items()}
    nonfinite = sorted(name for name, value in normalized.items() if not math.isfinite(value))
    if nonfinite:
        raise ValueError(f"Confidence thresholds must be finite for class(es): {nonfinite}")
    outside = sorted(name for name, value in normalized.items() if not 0.0 <= value <= 1.0)
    if outside:
        raise ValueError(f"Confidence thresholds must be within [0, 1] for class(es): {outside}")
    return normalized


def classes_from_ground_truth(ground_truth: pd.DataFrame) -> list[str]:
    """Return the real class vocabulary, excluding empty-image placeholders."""
    if "instance_label" not in ground_truth.columns:
        raise ValueError("Ground truth is missing the 'instance_label' column")
    return sorted({str(value) for value in ground_truth["instance_label"].dropna().unique()})


def validate_split_membership(ground_truth: pd.DataFrame) -> None:
    """Reject leakage when one logical image appears in both validation and test."""
    required = {"image_name", "split"}
    missing = sorted(required - set(ground_truth.columns))
    if missing:
        raise ValueError(f"Ground truth is missing membership column(s): {missing}")
    val_images = set(ground_truth.loc[ground_truth["split"] == "val", "image_name"])
    test_images = set(ground_truth.loc[ground_truth["split"] == "test", "image_name"])
    overlap = sorted(str(value) for value in val_images & test_images)
    if overlap:
        raise ValueError(
            "A logical image cannot belong to both val and test; overlapping image_name(s): "
            f"{overlap}"
        )
