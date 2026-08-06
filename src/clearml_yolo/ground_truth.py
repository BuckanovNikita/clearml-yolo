"""Convert a YOLO detection dataset into the ground-truth CSV digital-metrics expects.

Ultralytics stores annotations as one text file per image with normalised centre
coordinates, while digital-metrics wants a single table of absolute pixel corners keyed
by image name. Dataset roots, split entries and label locations are resolved with
ultralytics' own helpers so a plain ``data=`` yaml behaves exactly as it does in training.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from PIL import Image
from ultralytics.data.utils import IMG_FORMATS, check_det_dataset, img2label_paths

from clearml_yolo.progress import track

GROUND_TRUTH_COLUMNS = [
    "image_name",
    "image_path",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
    "split",
]
SPLITS = ("train", "val", "test")
DETECTION_LABEL_FIELDS = 5

GroundTruthRow = dict[str, str | float]
YoloBox = tuple[str, float, float, float, float]


def _manifest_images(manifest: Path) -> list[str]:
    """Read an image list file, resolving relative entries against its own directory."""
    images: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if not entry:
            continue
        image = Path(entry)
        if not image.is_absolute():
            image = manifest.parent / entry.removeprefix("./")
        if not image.exists():
            raise FileNotFoundError(f"{manifest}: listed image {entry!r} does not exist")
        images.append(str(image))
    return images


def _collect_images(entry: str | list[str], split: str) -> list[Path]:
    """Expand a resolved split entry into a sorted list of image paths."""
    found: list[str] = []
    for source in entry if isinstance(entry, list) else [entry]:
        path = Path(source)
        if path.is_dir():
            found.extend(str(candidate) for candidate in path.rglob("*"))
        elif path.suffix.lower() == ".txt" and path.is_file():
            found.extend(_manifest_images(path))
        else:
            raise FileNotFoundError(
                f"Split {split!r} points at {source!r}, which is neither an existing image "
                "directory nor a .txt image list"
            )
    return [
        Path(image)
        for image in sorted(set(found))
        if image.rpartition(".")[-1].lower() in IMG_FORMATS
    ]


def _parse_label_file(label_path: Path, names: dict[int, str]) -> list[YoloBox]:
    """Read one YOLO label file as ``(class name, cx, cy, w, h)`` tuples."""
    boxes: list[YoloBox] = []
    for number, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), start=1):
        fields = line.split()
        if not fields:
            continue
        if len(fields) != DETECTION_LABEL_FIELDS:
            raise ValueError(
                f"{label_path}:{number} has {len(fields)} fields, expected "
                f"{DETECTION_LABEL_FIELDS} (class cx cy w h); segment labels are not supported"
            )
        try:
            class_index = int(fields[0])
            center_x, center_y, box_width, box_height = (float(field) for field in fields[1:])
        except ValueError as error:
            raise ValueError(f"{label_path}:{number} is not a YOLO label: {line!r}") from error
        if box_width <= 0 or box_height <= 0:
            raise ValueError(
                f"{label_path}:{number} has a non-positive box size ({box_width} x "
                f"{box_height}); such a box has no top-left/bottom-right corner"
            )
        if class_index not in names:
            raise ValueError(
                f"{label_path}:{number} references class {class_index}, but the dataset "
                f"defines classes {min(names)}..{max(names)}"
            )
        boxes.append((names[class_index], center_x, center_y, box_width, box_height))
    return boxes


def _image_size(image: Path) -> tuple[int, int]:
    try:
        with Image.open(image) as opened:
            width, height = opened.size
    except OSError as error:
        raise ValueError(f"Cannot read the pixel size of {image}") from error
    return int(width), int(height)


def _split_rows(
    images: list[Path], split: str, names: dict[int, str]
) -> tuple[list[GroundTruthRow], int]:
    """Build the CSV rows of one split, counting images that carry no annotation."""
    rows: list[GroundTruthRow] = []
    background_images = 0
    labels = img2label_paths([str(image) for image in images])
    for image, label in track(
        list(zip(images, labels, strict=True)), f"Reading split {split!r}", unit="img"
    ):
        label_path = Path(label)
        boxes = _parse_label_file(label_path, names) if label_path.is_file() else []
        if not boxes:
            background_images += 1
            continue
        width, height = _image_size(image)
        for class_name, center_x, center_y, box_width, box_height in boxes:
            rows.append(
                {
                    "image_name": image.name,
                    "image_path": str(image),
                    "instance_label": class_name,
                    "bbox_x_tl": min(max((center_x - box_width / 2) * width, 0.0), width),
                    "bbox_y_tl": min(max((center_y - box_height / 2) * height, 0.0), height),
                    "bbox_x_br": min(max((center_x + box_width / 2) * width, 0.0), width),
                    "bbox_y_br": min(max((center_y + box_height / 2) * height, 0.0), height),
                    "split": split,
                }
            )
    return rows, background_images


def _carve_test_split(
    val_images: list[Path], test_fraction: float, seed: int
) -> tuple[list[Path], list[Path]]:
    """Move a deterministic fraction of the val images into a test split.

    The draw is over image names rather than paths, so two annotations of one image can
    never end up on both sides: digital-metrics reads that as calibration leaking into
    evaluation and refuses to score.
    """
    val_names = sorted({image.name for image in val_images})
    requested = round(len(val_names) * test_fraction)
    test_size = min(requested, len(val_names) - 1)
    if test_size < requested:
        logger.warning(
            "test_fraction {} would leave the val split empty; moving {} of {} images instead",
            test_fraction,
            test_size,
            len(val_names),
        )
    if test_size <= 0:
        return val_images, []

    order = np.random.default_rng(seed).permutation(len(val_names))
    test_names = {val_names[int(index)] for index in order[:test_size]}
    kept = [image for image in val_images if image.name not in test_names]
    moved = [image for image in val_images if image.name in test_names]
    logger.info("Carved {} of {} val images into a test split", len(moved), len(val_images))
    return kept, moved


def _reject_duplicate_image_names(images: dict[str, list[Path]]) -> None:
    """Refuse datasets where one file name stands for more than one image.

    digital-metrics keys everything on ``image_name``: two files sharing a name have
    their annotations merged inside a split, and across splits the CSV is rejected
    outright as calibration leaking into evaluation.
    """
    path_of_name: dict[str, Path] = {}
    collisions: list[str] = []
    for paths in images.values():
        for path in paths:
            owner = path_of_name.setdefault(path.name, path)
            if owner != path:
                collisions.append(f"{path.name} ({owner} and {path})")
    if collisions:
        raise ValueError(
            f"{len(collisions)} image name(s) refer to more than one file, which "
            f"digital-metrics cannot tell apart: {', '.join(collisions[:5])}"
        )


def build_ground_truth(
    data_yaml: str | Path,
    output: str | Path,
    *,
    test_fraction: float = 0.5,
    seed: int = 0,
) -> Path:
    """Write the ground truth of a YOLO dataset yaml as a digital-metrics CSV.

    Datasets that ship only train and val get a test split carved out of val, since
    thresholds are calibrated on val and reported on test.
    """
    if not 0.0 <= test_fraction < 1.0:
        raise ValueError(f"test_fraction must be within [0.0, 1.0), got {test_fraction}")

    yaml_path = Path(data_yaml).expanduser()
    dataset = check_det_dataset(str(yaml_path.resolve()) if yaml_path.exists() else str(data_yaml))
    names: dict[int, str] = {int(index): str(name) for index, name in dataset["names"].items()}

    images: dict[str, list[Path]] = {}
    for split in SPLITS:
        entry = dataset.get(split)
        found = _collect_images(entry, split) if entry else []
        if found:
            images[split] = found

    if not images:
        raise ValueError(f"{data_yaml} resolved to no images at all; nothing to convert")

    if "test" in images:
        logger.info("Dataset already defines a test split, leaving the val split untouched")
    elif "val" in images:
        if dataset.get("test"):
            logger.warning("The declared test split holds no images; carving one out of val")
        images["val"], carved = _carve_test_split(images["val"], test_fraction, seed)
        if carved:
            images["test"] = carved

    _reject_duplicate_image_names(images)

    rows: list[GroundTruthRow] = []
    background_images = 0
    for split, paths in images.items():
        split_rows, backgrounds = _split_rows(paths, split, names)
        rows.extend(split_rows)
        background_images += backgrounds
        logger.info("Split {!r}: {} images, {} annotations", split, len(paths), len(split_rows))

    frame = pd.DataFrame(rows, columns=GROUND_TRUTH_COLUMNS)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)

    logger.info(
        "Wrote {} ground-truth rows over {} classes to {} ({} images carry no annotation)",
        len(frame),
        frame["instance_label"].nunique(),
        output_path,
        background_images,
    )
    return output_path
