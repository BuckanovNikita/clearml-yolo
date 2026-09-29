"""Export validated detection records into local Ultralytics datasets.

NDJSON preserves original per-split filenames. Preparation builds one native YAML
layout directly so consumers never repeat Ultralytics' NDJSON conversion.
"""

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from clearml_yolo.dataset_records import ImageRecord, ValidatedDataset

DatasetFormat = Literal["ndjson", "flat"]

_SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class _ExportBox:
    class_id: int
    cx: float
    cy: float
    width: float
    height: float


@dataclass(frozen=True)
class _ExportImage:
    file: str
    split: str
    width: int
    height: int
    original_image_name: str
    original_image_path: Path
    boxes: tuple[_ExportBox, ...]


def _format_coordinate(value: float) -> str:
    return format(value, ".17g")


def exported_image_filename(image: ImageRecord, index: int, dataset_format: DatasetFormat) -> str:
    """Return the stable native filename for one validated image."""
    suffix = image.path.suffix.lower()
    if not suffix:
        raise ValueError(f"Image path has no file extension: {image.path}")
    if dataset_format == "flat":
        return f"{index:08d}{suffix}"
    if dataset_format != "ndjson":
        raise ValueError(
            f"Unsupported dataset format {dataset_format!r}; expected 'ndjson' or 'flat'"
        )
    if image.name in {"", ".", ".."} or Path(image.name).name != image.name:
        raise ValueError(f"NDJSON image name must be a safe basename: {image.name!r}")
    if "/" in image.name or "\\" in image.name:
        raise ValueError(f"NDJSON image name must be a safe basename: {image.name!r}")
    return image.name


def _export_image(
    image: ImageRecord,
    index: int,
    class_ids: dict[str, int],
    dataset_format: DatasetFormat,
) -> _ExportImage:
    filename = exported_image_filename(image, index, dataset_format)
    boxes = tuple(
        _ExportBox(
            class_id=class_ids[box.label],
            cx=((box.x1 + box.x2) / 2) / image.width,
            cy=((box.y1 + box.y2) / 2) / image.height,
            width=(box.x2 - box.x1) / image.width,
            height=(box.y2 - box.y1) / image.height,
        )
        for box in image.boxes
    )
    return _ExportImage(
        file=f"images/{image.split}/{filename}",
        split=image.split,
        width=image.width,
        height=image.height,
        original_image_name=image.name,
        original_image_path=image.path,
        boxes=boxes,
    )


def _export_images(
    records: ValidatedDataset, dataset_format: DatasetFormat
) -> tuple[_ExportImage, ...]:
    class_ids = {name: class_id for class_id, name in records.names.items()}
    images = tuple(
        _export_image(image, index, class_ids, dataset_format)
        for index, image in enumerate(records.images, start=1)
    )
    if dataset_format == "ndjson":
        label_owners: dict[tuple[str, str], str] = {}
        for image in images:
            stem = Path(image.file).stem
            key = (image.split, stem.casefold())
            owner = label_owners.get(key)
            if owner is not None:
                raise ValueError(
                    f"NDJSON label stem collision in split {image.split!r}: "
                    f"{owner!r} and {Path(image.file).name!r} share stem {stem!r}"
                )
            label_owners[key] = Path(image.file).name
    return images


def _box_json(box: _ExportBox) -> str:
    values = " ".join(
        (
            str(box.class_id),
            _format_coordinate(box.cx),
            _format_coordinate(box.cy),
            _format_coordinate(box.width),
            _format_coordinate(box.height),
        )
    )
    return "[" + values.replace(" ", ",") + "]"


def _image_json(image: _ExportImage) -> str:
    metadata = {
        "type": "image",
        "file": Path(image.file).name,
        "split": image.split,
        "width": image.width,
        "height": image.height,
        "original_image_name": image.original_image_name,
        "original_image_path": str(image.original_image_path),
    }
    prefix = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
    boxes = ",".join(_box_json(box) for box in image.boxes)
    return prefix[:-1] + f',"annotations":{{"boxes":[{boxes}]}}}}'


def _write_ndjson(path: Path, names: dict[int, str], images: tuple[_ExportImage, ...]) -> None:
    header = {"type": "dataset", "task": "detect", "path": ".", "class_names": names}
    lines = [json.dumps(header, ensure_ascii=False, separators=(",", ":"))]
    lines.extend(_image_json(image) for image in images)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _prepare_directories(directory: Path) -> None:
    for split in _SPLITS:
        (directory / "images" / split).mkdir(parents=True, exist_ok=True)
        (directory / "labels" / split).mkdir(parents=True, exist_ok=True)


def _destination(directory: Path, image: _ExportImage) -> tuple[Path, Path]:
    relative = Path(image.file)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"NDJSON image file must be a safe relative path: {image.file!r}")
    if relative.parts[:2] != ("images", image.split) or image.split not in _SPLITS:
        raise ValueError(f"NDJSON image path does not match split {image.split!r}: {image.file!r}")
    image_path = directory / relative
    label_path = directory / "labels" / image.split / relative.with_suffix(".txt").name
    return image_path, label_path


def _label_text(boxes: tuple[_ExportBox, ...]) -> str:
    lines = [
        " ".join(
            (
                str(box.class_id),
                _format_coordinate(box.cx),
                _format_coordinate(box.cy),
                _format_coordinate(box.width),
                _format_coordinate(box.height),
            )
        )
        for box in boxes
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def _materialize(directory: Path, images: tuple[_ExportImage, ...]) -> None:
    _prepare_directories(directory)
    for image in images:
        image_path, label_path = _destination(directory, image)
        shutil.copyfile(image.original_image_path, image_path)
        label_path.write_text(_label_text(image.boxes), encoding="utf-8")


def _write_yaml(directory: Path, names: dict[int, str], images: tuple[_ExportImage, ...]) -> Path:
    data_path = directory / "data.yaml"
    data: dict[str, object] = {
        "path": str(directory.resolve()),
        "names": names,
    }
    present_splits = {image.split for image in images}
    for split in _SPLITS:
        if split in present_splits:
            data[split] = f"images/{split}"
    data_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    return data_path


def export_dataset(
    records: ValidatedDataset, directory: Path, dataset_format: DatasetFormat
) -> Path:
    """Export canonical records and return the native YAML consumed by Ultralytics."""
    directory.mkdir(parents=True, exist_ok=True)
    images = _export_images(records, dataset_format)
    if dataset_format == "ndjson":
        manifest = directory / "dataset.ndjson"
        _write_ndjson(manifest, records.names, images)
    elif dataset_format != "flat":
        raise ValueError(
            f"Unsupported dataset format {dataset_format!r}; expected 'ndjson' or 'flat'"
        )
    _materialize(directory, images)
    return _write_yaml(directory, records.names, images)
