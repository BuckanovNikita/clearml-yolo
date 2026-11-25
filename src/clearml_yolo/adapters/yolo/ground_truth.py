"""Convert a YOLO detection dataset into the ground-truth CSV digital-metrics expects.

Ultralytics stores annotations as one text file per image with normalised centre
coordinates, while digital-metrics wants a single table of absolute pixel corners keyed
by image name. Dataset roots, split entries and label locations are resolved with
ultralytics' own helpers so a plain ``data=`` yaml behaves exactly as it does in training.
"""

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from loguru import logger
from PIL import Image
from ultralytics.data.utils import IMG_FORMATS, check_det_dataset, exif_size, img2label_paths
from ultralytics.nn.autobackend import check_class_names

from clearml_yolo.adapters.observability.progress import track
from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.storage.filesystem import write_path
from clearml_yolo.application.contracts import validate_test_fraction

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
NORMALIZED_MIN = -0.01
NORMALIZED_MAX = 1.01

# Characters Ultralytics 8.4.184 strips from data.yaml before its second PyYAML attempt.
_UNREADABLE_YAML_CHARACTERS = re.compile(r"[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\uD7FF\uE000-\uFFFD\U00010000-\U0010ffff]+")

GroundTruthRow = dict[str, str | float | None]
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
    return [Path(image) for image in sorted(set(found)) if image.rpartition(".")[-1].lower() in IMG_FORMATS]


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
        coordinates = (center_x, center_y, box_width, box_height)
        if any(not math.isfinite(value) or not NORMALIZED_MIN <= value <= NORMALIZED_MAX for value in coordinates):
            raise ValueError(f"{label_path}:{number} has nonfinite or out-of-bounds normalized coordinates")
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
            width, height = exif_size(opened)
    except OSError as error:
        raise ValueError(f"Cannot read the pixel size of {image}") from error
    return int(width), int(height)


def _split_rows(images: list[Path], split: str, names: dict[int, str]) -> tuple[list[GroundTruthRow], int]:
    """Build the CSV rows of one split, counting images that carry no annotation."""
    rows: list[GroundTruthRow] = []
    background_images = 0
    labels = img2label_paths([str(image) for image in images])
    for image, label in track(list(zip(images, labels, strict=True)), f"Reading split {split!r}", unit="img"):
        label_path = Path(label)
        boxes = _parse_label_file(label_path, names) if label_path.is_file() else []
        if not boxes:
            background_images += 1
            rows.append(
                {
                    "image_name": image.name,
                    "image_path": str(image),
                    "instance_label": None,
                    "bbox_x_tl": None,
                    "bbox_y_tl": None,
                    "bbox_x_br": None,
                    "bbox_y_br": None,
                    "split": split,
                }
            )
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


def _carve_test_split(val_images: list[Path], test_fraction: float, seed: int) -> tuple[list[Path], list[Path]]:
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


def _yaml_1_1_data(yaml_file: Path) -> object:
    """Load data.yaml exactly as Ultralytics 8.4.184 ``YAML.load`` does (ultralytics/utils/__init__.py).

    That version prefers libyaml (``CSafeLoader``), which accepts some text the pure-Python
    ``SafeLoader`` rejects (a tab after ``0:``), retries once without the characters below after
    any failure, and turns top-level ``'None'`` strings into ``None``.
    """
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    text = yaml_file.read_text(encoding="utf-8", errors="ignore")
    try:
        data = yaml.load(text, Loader=loader)  # noqa: S506 - loader is CSafeLoader or SafeLoader
    # BLE001: 8.4.184 retries after any exception; PyYAML raises plain ValueError on impossible dates.
    except Exception:  # noqa: BLE001
        try:
            data = yaml.load(_UNREADABLE_YAML_CHARACTERS.sub("", text), Loader=loader)  # noqa: S506 - as above
        except Exception as error:  # as above; re-raised with its cause
            raise ValueError(
                f"{yaml_file} is not YAML 1.1, so CY cannot confirm that its class names read the same "
                "under every Ultralytics version"
            ) from error
    if isinstance(data, dict) and "None" in data.values():
        data = {key: None if value == "None" else value for key, value in data.items()}
    return {} if data is None else data


def _unusable_names(yaml_file: Path, reason: str) -> ValueError:
    return ValueError(
        f"YAML 1.1 reads no usable class names in {yaml_file} ({reason}), so CY cannot confirm that its "
        "class names read the same under every Ultralytics version"
    )


def _yaml_1_1_class_count(yaml_file: Path, data: dict[object, object]) -> int | None:
    """Return ``nc`` as Ultralytics 8.4.184 ``check_det_dataset`` coerces it, or ``None`` without ``nc``."""
    if "nc" not in data:
        return None
    count = data["nc"]
    if isinstance(count, int):
        return count
    try:
        number = float(count)  # type: ignore[arg-type] # 8.4.184 tries any value; TypeError is refused below
        if number != int(number):
            raise ValueError(number)  # noqa: TRY301 - 8.4.184 refuses a fractional count in the same handler
        return int(number)
    # OverflowError: int(inf), which 8.4.184 lets escape and so also refuses.
    except (OverflowError, TypeError, ValueError) as error:
        raise _unusable_names(yaml_file, f"'nc: {count}' is not an integer") from error


def _yaml_1_1_class_names(yaml_file: Path, installed_count: int) -> dict[int, str]:
    """Return the class names Ultralytics 8.4.184 derives from data.yaml, from ``names`` or from ``nc``.

    Each refusal here mirrors one in Ultralytics 8.4.184 (``YAML.load``, ``check_det_dataset``,
    ``check_class_names``), so it never stops a file that version accepts. A class count that
    differs from the installed reader's is refused before the ``class_<i>`` names are built.
    """
    data = _yaml_1_1_data(yaml_file)
    if not isinstance(data, dict):
        raise _unusable_names(yaml_file, "not a mapping")
    names = data.get("names")
    if names is not None and not isinstance(names, list | dict):
        raise _unusable_names(yaml_file, f"'names' is {type(names).__name__}, not list or dict")
    if names is None and "nc" not in data:
        raise _unusable_names(yaml_file, "neither 'names' nor 'nc'")
    count = _yaml_1_1_class_count(yaml_file, data)
    if names is not None and count is not None and len(names) != count:
        raise _unusable_names(yaml_file, f"'names' length {len(names)} and 'nc: {count}' differ")
    if names is None:
        if count != installed_count:
            raise ValueError(
                f"Ultralytics reads {installed_count} classes in {yaml_file} where YAML 1.1 reads 'nc' as "
                f"{count}; write 'nc' as a decimal integer without leading zeros so every Ultralytics "
                "version reads the same class count"
            )
        names = [f"class_{index}" for index in range(installed_count)]
    try:
        return check_class_names(names)
    except (KeyError, TypeError, ValueError) as error:
        raise _unusable_names(yaml_file, f"{type(error).__name__}: {error}") from error


def _reject_reader_dependent_names(yaml_file: Path, names: dict[int, str]) -> None:
    """Refuse class names whose text depends on the YAML reader of the installed Ultralytics.

    Ultralytics 8.4.184 reads data.yaml with PyYAML (YAML 1.1); 8.4.218 uses its own YAML 1.2
    core reader. An unquoted ``yes`` or ``1e3`` then becomes the label ``'yes'`` or ``'1000.0'``
    instead of ``'True'`` or ``'1e3'``, and ``nc: 010`` gives 10 classes instead of 8; a CSV
    rebuilt from the same file would silently stop matching models trained on the old one.
    """
    expected = _yaml_1_1_class_names(yaml_file, len(names))
    if expected == names:
        return
    differences = ", ".join(
        f"{index} {names.get(index)!r} (YAML 1.1: {expected.get(index)!r})"
        for index in sorted(expected.keys() | names.keys())
        if names.get(index) != expected.get(index)
    )
    raise ValueError(
        f"Ultralytics reads class names in {yaml_file} unlike YAML 1.1: {differences}; "
        "write these names in quotes so every Ultralytics version reads the same text"
    )


@trace_operation("yolo.ground_truth.build")
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
    validate_test_fraction(test_fraction)

    yaml_path = Path(data_yaml).expanduser()
    dataset = check_det_dataset(str(yaml_path.resolve()) if yaml_path.exists() else str(data_yaml))
    names: dict[int, str] = {int(index): str(name) for index, name in dataset["names"].items()}
    _reject_reader_dependent_names(Path(dataset["yaml_file"]), names)

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
    output_path = write_path(output)
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
