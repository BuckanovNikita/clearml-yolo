"""Writable native input copies, isolated from user-owned images and annotations."""

import asyncio
import glob
import hashlib
import json
import os
import shutil
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import yaml
from filelock import FileLock

from clearml_yolo.filesystem import cy_home, write_path


def _native_images(entry: str | list[str]) -> list[Path]:
    """Match native ordering, duplicates and manifest-relative path semantics."""
    from ultralytics.data.utils import IMG_FORMATS

    files: list[str] = []
    for source in entry if isinstance(entry, list) else [entry]:
        path = Path(source)
        if path.is_dir():
            pattern = str(Path(glob.escape(source)) / "**" / "*.*")
            # Match native glob behavior, including hidden-file and wildcard semantics.
            files.extend(glob.glob(pattern, recursive=True))  # noqa: PTH207
        elif path.is_file():
            parent = str(path.parent) + os.sep
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            # Native manifests anchor only './'; other relative paths use the process cwd.
            files.extend(line.replace("./", parent, 1) if line.startswith("./") else line
                         for line in lines)
        else:
            raise FileNotFoundError(f"Native dataset source does not exist: {path}")
    images = sorted(name.replace("/", os.sep) for name in files
                    if name.rpartition(".")[-1].lower() in IMG_FORMATS)
    if not images:
        raise FileNotFoundError("Native dataset split contains no supported images")
    return [Path(image) for image in images]


def _manifest_sources(settings: dict[str, Any]) -> dict[str, list[str]]:
    """Include effective manifest membership, whose bare paths depend on the launch cwd."""
    sources: dict[str, list[str]] = {}
    for split in ("train", "val", "test"):
        entry = settings.get(split)
        if not entry:
            continue
        for source in entry if isinstance(entry, list) else [entry]:
            if Path(source).is_file():
                sources[str(source)] = [str(image.resolve()) for image in _native_images(source)]
    return sources


def _copy_writable(source: Path, destination: Path) -> None:
    shutil.copy2(source, destination)
    # Source files can be read-only; native repairs must still be possible on owned copies.
    destination.chmod(stat.S_IMODE(destination.stat().st_mode) | stat.S_IWUSR)


def _stage(settings: dict[str, Any], directory: Path) -> Path:
    from ultralytics.data.utils import img2label_paths

    exported = {key: value for key, value in settings.items()
                if key not in {"yaml_file", "download", "train", "val", "test", "path"}}
    exported["path"] = str(directory)
    for split in ("train", "val", "test"):
        if not settings.get(split):
            continue
        images = directory / "images" / split
        labels = directory / "labels" / split
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        for index, source in enumerate(_native_images(settings[split])):
            # Native fraction takes a sorted prefix; retain the source order and avoid collisions.
            name = f"{index:012d}-{source.name}"
            _copy_writable(source, images / name)
            label = Path(img2label_paths([str(source)])[0])
            if label.is_file():
                _copy_writable(label, labels / Path(name).with_suffix(".txt"))
        exported[split] = f"images/{split}"
    output = directory / "data.yaml"
    output.write_text(yaml.safe_dump(exported, sort_keys=False), encoding="utf-8")
    return output


@contextmanager
def native_dataset(
    data: str | Path, *, fraction: float | list[float | int] = 1.0, split: str = "val"
) -> Iterator[Path]:
    """Hold the cache lock throughout native writes; source inputs remain read-only.

    Native repairs and .cache/.npy generation are permitted only on these real copies.
    Like the CSV cache, unchanged dataset references assume immutable source images.
    """
    from ultralytics.data.converter import convert_ndjson_to_yolo
    from ultralytics.data.utils import check_det_dataset
    from ultralytics.utils import SETTINGS
    from ultralytics.utils.checks import normalize_platform_uri

    # The installed normalization helper has no annotations; constrain its adapter interface.
    normalize = cast(Callable[[str | Path], str | Path], normalize_platform_uri)
    data = normalize(data)
    if str(data).split("?", 1)[0].endswith(".ndjson") or str(data).startswith("ul://"):
        selected = SETTINGS["datasets_dir"]
        converted_root = write_path(
            cy_home() / ".cache/ultralytics/datasets"
            if selected == SETTINGS.defaults["datasets_dir"] else selected
        )
        data = asyncio.run(convert_ndjson_to_yolo(
            data, output_path=converted_root,
            fraction=fraction, split=split,
        ))
    settings: dict[str, Any] = check_det_dataset(str(data), split=split)
    identity_values = {
        "settings": {key: value for key, value in settings.items() if key != "yaml_file"},
        "manifest_sources": _manifest_sources(settings),
    }
    identity = hashlib.sha256(
        json.dumps(identity_values, sort_keys=True, default=str).encode()
    ).hexdigest()
    root = write_path(cy_home() / ".cache" / "clearml-yolo" / "native-datasets")
    root.mkdir(parents=True, exist_ok=True)
    destination = root / identity
    with FileLock(str(root / f".{identity}.lock")):
        if not (destination / "data.yaml").is_file():
            partial = root / f".{identity}-{uuid4().hex}"
            try:
                _stage(settings, partial)
                # The exported root must name the final directory, not the staging directory.
                output = partial / "data.yaml"
                values = yaml.safe_load(output.read_text(encoding="utf-8"))
                values["path"] = str(destination)
                output.write_text(yaml.safe_dump(values, sort_keys=False), encoding="utf-8")
                partial.rename(destination)
            finally:
                if partial.exists():
                    shutil.rmtree(partial)
        yield destination / "data.yaml"
