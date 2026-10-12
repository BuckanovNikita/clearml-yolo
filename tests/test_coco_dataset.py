"""COCO preparation preserves CSV geometry, empty images and class identity."""

import csv
import json
from pathlib import Path

from PIL import Image

from clearml_yolo.adapters.storage.dataset_cache import cached_dataset


def test_coco_cache_preserves_source_bytes_geometry_and_empty_images(tmp_path: Path) -> None:
    source = tmp_path / "truth.csv"
    rows = []
    original = {}
    for index, split in enumerate(("train", "val", "test")):
        path = tmp_path / f"{index}.png"
        Image.new("RGB", (48, 32), (index, 10, 20)).save(path)
        original[path] = path.read_bytes()
        rows.append([path.name, str(path), "0001", 1.25, 2.5, 30.75, 25.0, split])
    empty = tmp_path / "empty.png"
    Image.new("RGB", (48, 32)).save(empty)
    original[empty] = empty.read_bytes()
    rows.append([empty.name, str(empty), "", "", "", "", "", "train"])
    with source.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "image_name",
                "image_path",
                "instance_label",
                "bbox_x_tl",
                "bbox_y_tl",
                "bbox_x_br",
                "bbox_y_br",
                "split",
            ]
        )
        writer.writerows(rows)
    source_bytes = source.read_bytes()
    with cached_dataset(source, tmp_path / "cache", "coco") as prepared:
        root = prepared.data.parent
        train = json.loads((root / "train/_annotations.coco.json").read_text())
        assert train["categories"] == [{"id": 0, "name": "0001"}]
        assert len(train["images"]) == 2
        assert len(train["annotations"]) == 1
        assert train["annotations"][0]["bbox"] == [1.25, 2.5, 29.5, 22.5]
        assert train["annotations"][0]["category_id"] == 0
        assert (root / "valid/_annotations.coco.json").is_file()
        assert (root / "test/_annotations.coco.json").is_file()
        for record in json.loads(prepared.manifest.read_text())["images"]:
            assert (
                Path(record["generated_path"]).read_bytes() == original[Path(record["image_path"])]
            )
        initial_timestamp = prepared.manifest.stat().st_mtime_ns
    with cached_dataset(source, tmp_path / "cache", "coco") as hit:
        assert hit.data.parent == root
        assert hit.manifest.stat().st_mtime_ns == initial_timestamp
    with cached_dataset(source, tmp_path / "cache", "flat") as different:
        assert different.data.parent != root
    assert source.read_bytes() == source_bytes
    assert all(path.read_bytes() == data for path, data in original.items())
