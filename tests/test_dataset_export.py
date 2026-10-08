"""Native dataset exports preserve canonical images, classes, and annotations."""

import json
from pathlib import Path

import pytest
import yaml
from PIL import Image
from ultralytics.data.utils import check_det_dataset

from clearml_yolo.adapters.storage.dataset_export import DatasetFormat, export_dataset
from clearml_yolo.core.datasets import Box, ImageRecord, Split, ValidatedDataset


def _image(path: Path, color: tuple[int, int, int]) -> Path:
    Image.new("RGB", (10, 10), color).save(path)
    return path.resolve()


def _records(tmp_path: Path) -> tuple[ValidatedDataset, Path, Path]:
    source = tmp_path / "truth.csv"
    source.write_text("canonical source")
    train = _image(tmp_path / "Train.PNG", (10, 20, 30))
    val = _image(tmp_path / "validation.JPEG", (40, 50, 60))
    records = ValidatedDataset(
        source=source.resolve(),
        input_sha256="a" * 64,
        images=[
            ImageRecord(
                name=train.name,
                path=train,
                width=10,
                height=10,
                split="train",
                boxes=[Box(label="zeta", x1=0.0, y1=0.0, x2=2.0, y2=4.0)],
            ),
            ImageRecord(
                name=val.name,
                path=val,
                width=10,
                height=10,
                split="val",
                boxes=[],
            ),
        ],
        names={0: "alpha", 1: "zeta"},
        errors=[],
        input_boxes=1,
    )
    return records, train, val


@pytest.mark.parametrize("dataset_format", ["ndjson", "flat"])
def test_export_materializes_native_dataset_from_canonical_records(
    tmp_path: Path, dataset_format: DatasetFormat
) -> None:
    """Catch filename drift, links to sources, background loss, or invalid native YAML."""
    records, train_source, val_source = _records(tmp_path)
    directory = tmp_path / "prepared"
    directory.mkdir()
    train_bytes = train_source.read_bytes()
    val_bytes = val_source.read_bytes()

    data_yaml = export_dataset(records, directory, dataset_format)

    assert data_yaml == directory / "data.yaml"
    if dataset_format == "ndjson":
        train_image = directory / "images/train/Train.PNG"
        val_image = directory / "images/val/validation.JPEG"
        train_label = directory / "labels/train/Train.txt"
        val_label = directory / "labels/val/validation.txt"
    else:
        train_image = directory / "images/train/00000001.png"
        val_image = directory / "images/val/00000002.jpeg"
        train_label = directory / "labels/train/00000001.txt"
        val_label = directory / "labels/val/00000002.txt"
    assert train_image.read_bytes() == train_bytes
    assert val_image.read_bytes() == val_bytes
    assert not train_image.is_symlink()
    assert not val_image.is_symlink()
    assert train_label.read_text() == (
        "1 0.10000000000000001 0.20000000000000001 0.20000000000000001 0.40000000000000002\n"
    )
    assert val_label.read_text() == ""
    assert (directory / "images/test").is_dir()
    assert (directory / "labels/test").is_dir()

    config = yaml.safe_load(data_yaml.read_text())
    assert config == {
        "path": str(directory.resolve()),
        "train": "images/train",
        "val": "images/val",
        "names": {0: "alpha", 1: "zeta"},
    }
    checked = check_det_dataset(str(data_yaml))
    assert checked["names"] == {0: "alpha", 1: "zeta"}
    assert checked["train"] == str((directory / "images/train").resolve())
    assert checked["val"] == str((directory / "images/val").resolve())
    assert "test" not in checked

    _image(train_source, (200, 210, 220))
    assert train_image.read_bytes() == train_bytes


def test_ndjson_is_durable_manifest_consumed_into_native_layout(tmp_path: Path) -> None:
    """Catch remote URLs, absolute generated references, or NDJSON precision loss."""
    records, train_source, _ = _records(tmp_path)
    directory = tmp_path / "prepared"
    directory.mkdir()

    export_dataset(records, directory, "ndjson")

    manifest = directory / "dataset.ndjson"
    raw_lines = manifest.read_text().splitlines()
    parsed = [json.loads(line) for line in raw_lines]
    assert parsed[0] == {
        "type": "dataset",
        "task": "detect",
        "path": ".",
        "class_names": {"0": "alpha", "1": "zeta"},
    }
    assert parsed[1] == {
        "type": "image",
        "file": "Train.PNG",
        "split": "train",
        "width": 10,
        "height": 10,
        "original_image_name": "Train.PNG",
        "original_image_path": str(train_source),
        "annotations": {"boxes": [[1, 0.1, 0.2, 0.2, 0.4]]},
    }
    assert parsed[2]["file"] == "validation.JPEG"
    assert parsed[2]["annotations"] == {"boxes": []}
    assert all("url" not in record for record in parsed[1:])
    assert "0.10000000000000001" in raw_lines[1]
    assert "0.40000000000000002" in raw_lines[1]


def test_flat_export_does_not_write_ndjson(tmp_path: Path) -> None:
    """Catch accidentally routing the flat representation through an NDJSON artifact."""
    records, _, _ = _records(tmp_path)
    directory = tmp_path / "prepared"
    directory.mkdir()

    export_dataset(records, directory, "flat")

    assert not (directory / "dataset.ndjson").exists()


def test_ndjson_native_conversion_reads_local_images_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    import aiohttp
    from ultralytics.data.converter import convert_ndjson_to_yolo

    records, _, _ = _records(tmp_path)
    directory = tmp_path / "prepared"
    export_dataset(records, directory, "ndjson")
    monkeypatch.setattr(
        aiohttp.ClientSession,
        "get",
        lambda *args, **kwargs: pytest.fail("local NDJSON must not fetch an HTTP image"),
    )
    data = asyncio.run(
        convert_ndjson_to_yolo(directory / "dataset.ndjson", output_path=directory / "native")
    )
    checked = check_det_dataset(str(data))
    assert checked["names"] == {0: "alpha", 1: "zeta"}
    for split in ("train", "val"):
        images = list(Path(checked[split]).iterdir())
        assert len(images) == 1
        label = images[0].parents[2] / "labels" / split / images[0].with_suffix(".txt").name
        assert bool(label.read_text().strip()) is (split == "train")


def test_flat_same_stem_images_and_pixel_coordinates_survive_export(tmp_path: Path) -> None:
    """Numbered flat files keep distinct labels and fractional pixel corners."""
    images = []
    cases: tuple[tuple[str, Split], ...] = (("png", "train"), ("jpg", "train"), ("jpeg", "val"))
    for suffix, split in cases:
        path = tmp_path / f"same.{suffix}"
        Image.new("RGB", (641, 479)).save(path)
        images.append(
            ImageRecord(
                name=path.name,
                path=path,
                width=641,
                height=479,
                split=split,
                boxes=[Box(label="object", x1=1.125, y1=3.75, x2=639.625, y2=478.25)],
            )
        )
    records = ValidatedDataset(
        source=tmp_path / "truth.csv",
        input_sha256="b" * 64,
        images=images,
        names={0: "object"},
        errors=[],
        input_boxes=3,
    )
    directory = tmp_path / "flat"
    data = export_dataset(records, directory, "flat")
    checked = check_det_dataset(str(data))
    for split, count in (("train", 2), ("val", 1)):
        paths = list(Path(checked[split]).iterdir())
        assert len(paths) == count
        assert len({path.stem for path in paths}) == count
        for path in paths:
            label = path.parents[2] / "labels" / split / path.with_suffix(".txt").name
            class_id, cx, cy, width, height = map(float, label.read_text().split())
            assert class_id == 0
            corners = (
                (cx - width / 2) * 641,
                (cy - height / 2) * 479,
                (cx + width / 2) * 641,
                (cy + height / 2) * 479,
            )
            assert corners == pytest.approx((1.125, 3.75, 639.625, 478.25), abs=0.01)


def test_ndjson_rejects_same_split_label_stem_collisions_before_copy(tmp_path: Path) -> None:
    """Original NDJSON basenames cannot overwrite one shared YOLO label file."""
    first = _image(tmp_path / "same.JPG", (1, 2, 3))
    second = _image(tmp_path / "same.PNG", (4, 5, 6))
    val = _image(tmp_path / "val.PNG", (7, 8, 9))
    records = ValidatedDataset(
        source=tmp_path / "truth.csv",
        input_sha256="c" * 64,
        images=[
            ImageRecord(
                name=first.name,
                path=first,
                width=10,
                height=10,
                split="train",
                boxes=[Box(label="object", x1=1, y1=1, x2=5, y2=5)],
            ),
            ImageRecord(
                name=second.name,
                path=second,
                width=10,
                height=10,
                split="train",
                boxes=[Box(label="object", x1=2, y1=2, x2=6, y2=6)],
            ),
            ImageRecord(
                name=val.name,
                path=val,
                width=10,
                height=10,
                split="val",
                boxes=[],
            ),
        ],
        names={0: "object"},
        errors=[],
        input_boxes=2,
    )
    directory = tmp_path / "prepared"

    with pytest.raises(ValueError, match=r"label stem.*same"):
        export_dataset(records, directory, "ndjson")

    assert not (directory / "images").exists()
