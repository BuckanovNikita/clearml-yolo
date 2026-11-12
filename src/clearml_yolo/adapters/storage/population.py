"""Read original prepared dataset populations without resolving image paths."""

from pathlib import Path

from clearml_yolo.adapters.storage.file_io import read_detection_csv


def population_counts(path: Path) -> dict[str, dict[str, int]] | None:
    """Count foreground annotations by observed split, preserving lexical labels."""
    frame = read_detection_csv(path)
    if not {"split", "instance_label"} <= set(frame.columns):
        return None
    if frame["split"].isna().any() or frame["split"].astype(str).str.strip().eq("").any():
        return None
    result: dict[str, dict[str, int]] = {}
    for split, rows in frame.dropna(subset=["split"]).groupby("split", sort=True):
        labels = rows["instance_label"].dropna()
        result[str(split)] = {str(label): int(count) for label, count in labels.value_counts().items()}
    return result or None
