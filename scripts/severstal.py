"""Prepare traceable detection fixtures from an official local Severstal download.

This command never downloads data or trains a model. Source images and annotations
remain unchanged; output CSVs reference them by absolute path. Connected components
are derived detection instances, not instance annotations supplied by Kaggle.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import struct
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
from numpy.typing import NDArray
from PIL import Image
from scipy import ndimage

type Split = Literal["train", "val", "test"]
SPLITS: tuple[Split, ...] = ("train", "val", "test")
CLASSES = frozenset({"1", "2", "3", "4"})
FEATURES = CLASSES | {"background"}
RATIOS = {"train": 0.8, "val": 0.1, "test": 0.1}
CSV_FIELDS = (
    "image_name",
    "image_path",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
    "split",
)
SOURCE_URL = "https://www.kaggle.com/competitions/severstal-steel-defect-detection"
MASK_DIMENSIONS = 2


@dataclass(frozen=True)
class Component:
    class_id: str
    component_id: int
    box: tuple[int, int, int, int]
    area: int


@dataclass(frozen=True)
class SourceImage:
    image_name: str
    image_path: Path
    height: int
    width: int
    source_sha256: str
    pixel_sha256: str
    components: tuple[Component, ...]

    @property
    def features(self) -> frozenset[str]:
        return frozenset(component.class_id for component in self.components) or frozenset(
            {"background"}
        )


def decode_rle(encoded: str, *, height: int, width: int) -> NDArray[np.bool_]:
    if height <= 0 or width <= 0:
        raise ValueError("RLE image dimensions must be positive")
    flat = np.zeros(height * width, dtype=np.bool_)
    if not encoded.strip():
        return flat.reshape((height, width), order="F")
    try:
        values = [int(value) for value in encoded.split()]
    except ValueError as error:
        raise ValueError("RLE requires integer start/length pairs") from error
    if len(values) % 2:
        raise ValueError("RLE requires complete start/length pairs")
    previous_end = 0
    for start, length in zip(values[::2], values[1::2], strict=True):
        offset = start - 1
        end = offset + length
        if offset < previous_end or length <= 0 or end > flat.size:
            raise ValueError(
                "RLE runs must be positive, sorted, nonoverlapping and within the image"
            )
        flat[offset:end] = True
        previous_end = end
    return flat.reshape((height, width), order="F")


def component_boxes(mask: NDArray[np.bool_], class_id: str) -> tuple[Component, ...]:
    if mask.ndim != MASK_DIMENSIONS or class_id not in CLASSES:
        raise ValueError("Expected a 2D mask and Severstal class 1, 2, 3 or 4")
    labels = np.zeros(mask.shape, dtype=np.int32)
    count = int(ndimage.label(mask, structure=np.ones((3, 3), dtype=np.uint8), output=labels))
    areas = np.bincount(labels.reshape(-1), minlength=count + 1)
    result: list[Component] = []
    for component_id, slices in enumerate(ndimage.find_objects(labels), start=1):
        if slices is None:
            raise ValueError("Connected-component labeling produced a missing component")
        y, x = slices
        result.append(
            Component(
                class_id, component_id, (x.start, y.start, x.stop, y.stop), int(areas[component_id])
            )
        )
    return tuple(result)


def _annotation_identity(row: Mapping[str, str | None], legacy: bool) -> tuple[str, str]:
    if legacy:
        name, separator, label = (row.get("ImageId_ClassId") or "").rpartition("_")
        if not separator:
            raise ValueError("Invalid ImageId_ClassId annotation")
    else:
        name, label = row.get("ImageId") or "", row.get("ClassId") or ""
    if not name or Path(name).name != name or "/" in name or "\\" in name:
        raise ValueError("Annotation image reference must be a filename inside train_images")
    if label not in CLASSES:
        raise ValueError(f"Unknown Severstal class {label!r} for image {name}")
    return name, label


def _annotations(path: Path, image_names: set[str]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fields = set(reader.fieldnames or ())
        legacy = "ImageId_ClassId" in fields
        expected = (
            {"ImageId_ClassId", "EncodedPixels"}
            if legacy
            else {"ImageId", "ClassId", "EncodedPixels"}
        )
        if not expected.issubset(fields) or (legacy and {"ImageId", "ClassId"} & fields):
            raise ValueError("Unsupported or ambiguous Severstal train.csv columns")
        for row in reader:
            name, label = _annotation_identity(row, legacy)
            if name not in image_names:
                raise ValueError(f"Annotation refers to missing training image {name}")
            if label in result[name]:
                raise ValueError(f"Duplicate image/class annotation: {name}/{label}")
            result[name][label] = row.get("EncodedPixels") or ""
    return dict(result)


def _read_image(path: Path, annotations: Mapping[str, str]) -> SourceImage:
    contents = path.read_bytes()
    with Image.open(io.BytesIO(contents)) as image:
        pixels = np.array(image.convert("RGB"), dtype=np.uint8)
    height, width = pixels.shape[:2]
    digest = hashlib.sha256(struct.pack("!QQ", height, width) + pixels.tobytes()).hexdigest()
    components: list[Component] = []
    for label, encoded in sorted(annotations.items()):
        try:
            mask = decode_rle(encoded, height=height, width=width)
        except ValueError as error:
            raise ValueError(f"{path.name}, class {label}: {error}") from error
        components.extend(component_boxes(mask, label))
    return SourceImage(
        path.name,
        path.resolve(),
        height,
        width,
        hashlib.sha256(contents).hexdigest(),
        digest,
        tuple(components),
    )


def read_source(source: Path) -> tuple[SourceImage, ...]:
    source = source.resolve()
    image_root = source / "train_images"
    if not image_root.is_dir() or not (source / "train.csv").is_file():
        raise FileNotFoundError("Official Severstal source requires train.csv and train_images")
    paths = sorted(
        path for path in image_root.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    if not paths:
        raise ValueError("Severstal train_images contains no supported images")
    if any(not path.is_file() or not path.resolve().is_relative_to(image_root) for path in paths):
        raise ValueError("Training image paths must be regular files inside train_images")
    annotations = _annotations(source / "train.csv", {path.name for path in paths})
    return tuple(_read_image(path, annotations.get(path.name, {})) for path in paths)


def _order_key(identity: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{identity}".encode()).hexdigest()


def _group_features(group: Sequence[SourceImage]) -> frozenset[str]:
    return frozenset(feature for record in group for feature in record.features)


def _cover_features(
    available: dict[str, tuple[SourceImage, ...]], capacity: int, *, seed: int
) -> list[str]:
    selected: list[str] = []
    missing = set(FEATURES)
    counts = Counter(feature for group in available.values() for feature in _group_features(group))
    while missing:
        candidates = [
            key
            for key, group in available.items()
            if len(group) <= capacity and missing & _group_features(group)
        ]
        if not candidates:
            raise ValueError(
                "Cannot cover all four classes and backgrounds with independent content groups"
            )
        key = min(
            candidates,
            key=lambda item: (
                -sum(
                    1 / counts[feature]
                    for feature in sorted(missing & _group_features(available[item]))
                ),
                len(available[item]),
                _order_key(item, seed),
            ),
        )
        group = available.pop(key)
        selected.append(key)
        capacity -= len(group)
        missing.difference_update(_group_features(group))
    return selected


def assign_splits(records: Sequence[SourceImage], *, seed: int = 0) -> dict[str, Split]:
    groups_mutable: dict[str, list[SourceImage]] = defaultdict(list)
    for record in sorted(records, key=lambda item: item.image_name):
        groups_mutable[record.pixel_sha256].append(record)
    groups = {key: tuple(group) for key, group in groups_mutable.items()}
    available = dict(groups)
    count = len(records)
    targets: dict[Split, int] = {"val": math.floor(count * 0.1), "test": math.floor(count * 0.1)}
    targets["train"] = count - targets["val"] - targets["test"]
    chosen: dict[Split, list[str]] = {split: [] for split in SPLITS}
    for split in ("val", "test", "train"):
        chosen[split] = _cover_features(available, targets[split], seed=seed)
    totals = Counter(feature for record in records for feature in record.features)
    counts = {split: sum(len(groups[item]) for item in chosen[split]) for split in SPLITS}
    feature_counts = {
        split: Counter(
            feature
            for item in chosen[split]
            for record in groups[item]
            for feature in record.features
        )
        for split in SPLITS
    }
    for key in sorted(
        available,
        key=lambda item: (
            min(totals[feature] for feature in _group_features(groups[item])),
            _order_key(item, seed),
        ),
    ):
        split = _choose_split(groups[key], counts, feature_counts, targets, totals)
        chosen[split].append(key)
        counts[split] += len(groups[key])
        feature_counts[split].update(
            feature for record in groups[key] for feature in record.features
        )
    return {
        record.image_name: split
        for split, keys in chosen.items()
        for key in keys
        for record in groups[key]
    }


def _choose_split(
    group: tuple[SourceImage, ...],
    counts: Mapping[Split, int],
    feature_counts: Mapping[Split, Counter[str]],
    targets: Mapping[Split, int],
    totals: Counter[str],
) -> Split:
    candidates = [split for split in SPLITS if counts[split] + len(group) <= targets[split]]
    if not candidates:
        # Indivisible duplicate-content groups may make exact ratios impossible.
        return min(
            SPLITS,
            key=lambda split: (counts[split] + len(group) - targets[split], SPLITS.index(split)),
        )
    return max(
        candidates,
        key=lambda split: (
            sum(
                (totals[feature] * RATIOS[split] - feature_counts[split][feature]) / totals[feature]
                for feature in sorted(_group_features(group))
            ),
            (targets[split] - counts[split]) / targets[split],
            -SPLITS.index(split),
        ),
    )


def select_smoke(
    records: Sequence[SourceImage],
    splits: Mapping[str, Split],
    sizes: tuple[int, int, int],
    *,
    seed: int,
) -> set[str]:
    selected: set[str] = set()
    if any(size <= 0 for size in sizes):
        raise ValueError("smoke split sizes must be positive")
    for split, size in zip(SPLITS, sizes, strict=True):
        members: dict[str, tuple[SourceImage, ...]] = {
            record.image_name: (record,) for record in records if splits[record.image_name] == split
        }
        if len(members) < size:
            raise ValueError(
                f"Requested smoke {split} size {size} exceeds available {len(members)}"
            )
        covered = _cover_features(members, size, seed=seed)
        selected.update(covered)
        remaining = sorted(members, key=lambda key: _order_key(key, seed))
        selected.update(remaining[: size - len(covered)])
    return selected


def _csv_contents(records: Iterable[SourceImage], splits: Mapping[str, Split]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for record in records:
        common = {
            "image_name": record.image_name,
            "image_path": str(record.image_path),
            "split": splits[record.image_name],
        }
        if not record.components:
            writer.writerow(common | {"instance_label": ""})
        for component in record.components:
            writer.writerow(
                common
                | {"instance_label": component.class_id}
                | dict(zip(CSV_FIELDS[3:7], component.box, strict=True))
            )
    return stream.getvalue()


def _json_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def prepare(
    source: Path, output: Path, *, seed: int = 0, smoke_sizes: tuple[int, int, int] = (160, 40, 40)
) -> dict[str, Any]:
    """Write frozen JSON evidence; its open mapping is the serialized manifest boundary."""
    source, output = source.resolve(), output.resolve()
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Preparation output and original dataset must be separate directory trees")
    destinations = [output / name for name in ("full.csv", "smoke.csv", "manifest.json")]
    if any(path.exists() for path in destinations):
        raise FileExistsError(
            "Prepared dataset already exists; verify it or choose a new output directory"
        )
    records = read_source(source)
    splits = assign_splits(records, seed=seed)
    smoke = select_smoke(records, splits, smoke_sizes, seed=seed)
    documents = {
        "full.csv": _csv_contents(records, splits),
        "smoke.csv": _csv_contents(
            (record for record in records if record.image_name in smoke), splits
        ),
    }
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "source_url": SOURCE_URL,
        "source_root": str(source),
        "annotations_sha256": hashlib.sha256((source / "train.csv").read_bytes()).hexdigest(),
        "conversion": {
            "rle": "one-based column-major",
            "connectivity": 8,
            "boxes": "half-open xyxy",
            "minimum_component_area": 1,
        },
        "seed": seed,
        "classes": sorted(CLASSES),
        "requested_split_ratios": RATIOS,
        "split_counts": dict(Counter(splits.values())),
        "smoke_counts": dict(Counter(splits[name] for name in smoke)),
        "csv_sha256": {
            name: hashlib.sha256(contents.encode()).hexdigest()
            for name, contents in documents.items()
        },
        "images": [
            asdict(record)
            | {
                "image_path": str(record.image_path),
                "split": splits[record.image_name],
                "smoke": record.image_name in smoke,
            }
            for record in records
        ],
        "limitations": [
            "Boxes are derived from semantic connected components, not native instance labels.",
            (
                "Grouping excludes exact decoded-content leakage; correlated scenes or "
                "near duplicates are not established."
            ),
        ],
    }
    manifest["sha256"] = _json_hash(manifest)
    output.mkdir(parents=True, exist_ok=True)
    for name, contents in documents.items():
        with (output / name).open("x", encoding="utf-8", newline="") as stream:
            stream.write(contents)
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    return manifest


def verify_prepared(output: Path, *, verify_images: bool = True) -> dict[str, Any]:
    """Reject changed manifests/CSVs and selected image bytes before native acceptance."""
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("Unsupported prepared Severstal manifest")
    expected = manifest.get("sha256")
    actual = _json_hash({key: value for key, value in manifest.items() if key != "sha256"})
    if expected != actual:
        raise ValueError("Prepared Severstal manifest hash mismatch")
    for name in ("full.csv", "smoke.csv"):
        if hashlib.sha256((output / name).read_bytes()).hexdigest() != manifest["csv_sha256"][name]:
            raise ValueError(f"Prepared Severstal {name} hash mismatch")
    if verify_images:
        for record in manifest["images"]:
            if (
                record["smoke"]
                and hashlib.sha256(Path(record["image_path"]).read_bytes()).hexdigest()
                != record["source_sha256"]
            ):
                raise ValueError(f"Prepared Severstal image {record['image_name']} hash mismatch")
    return cast(dict[str, Any], manifest)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("prepare")
    build.add_argument("--source", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--seed", type=int, default=0)
    build.add_argument("--smoke-sizes", nargs=3, type=int, default=(160, 40, 40))
    verify = commands.add_parser("verify")
    verify.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        sizes = cast(tuple[int, int, int], tuple(args.smoke_sizes))
        result = prepare(args.source, args.output, seed=args.seed, smoke_sizes=sizes)
    else:
        result = verify_prepared(args.output)
    print(  # noqa: T201 - maintenance CLI result
        json.dumps(
            {
                "sha256": result["sha256"],
                "split_counts": result["split_counts"],
                "smoke_counts": result["smoke_counts"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
