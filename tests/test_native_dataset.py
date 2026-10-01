"""Native YAML inputs are copied before native caches or repairs can touch them."""

import importlib
import stat
from pathlib import Path

import pytest
import yaml
from PIL import Image


def test_native_dataset_stages_images_labels_and_preserves_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module("clearml_yolo.native_dataset")
    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    source = tmp_path / "source"
    for split in ("train", "val"):
        images = source / "images" / split
        labels = source / "labels" / split
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        Image.new("RGB", (32, 32)).save(images / "sample.jpg")
        (labels / "sample.txt").write_text("0 0.5 0.5 0.5 0.5\n")
    config = source / "data.yaml"
    config.write_text(yaml.safe_dump({"path": str(source), "train": "images/train",
                                    "val": "images/val", "names": {0: "object"}}))
    original = {path: path.read_bytes() for path in source.rglob("*") if path.is_file()}
    with module.native_dataset(config) as staged:
        assert staged.is_relative_to(tmp_path / "workspace/.cache")
        settings = yaml.safe_load(staged.read_text())
        copied = next((Path(settings["path"]) / "images/train").glob("*.jpg"))
        from ultralytics.data.dataset import YOLODataset

        YOLODataset(img_path=str(copied.parent), data=settings, imgsz=32,
                    augment=False, cache="disk", batch_size=1)
        assert copied.with_suffix(".npy").is_file()
        assert (Path(settings["path"]) / "labels/train.cache").is_file()
        copied.write_bytes(b"native repair")
        assert (Path(settings["path"]) / "labels/train" / copied.with_suffix(".txt").name).is_file()
    assert {path: path.read_bytes() for path in source.rglob("*") if path.is_file()} == original
    replayed = tmp_path / "resolved.yaml"
    replayed.write_bytes(config.read_bytes())
    with module.native_dataset(replayed) as reused:
        assert reused == staged
        assert copied.read_bytes() == b"native repair"


@pytest.mark.parametrize("input_form", ["cwd-relative", "manifest-relative", "repeated"])
def test_native_staging_preserves_upstream_image_membership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, input_form: str
) -> None:
    from ultralytics.data.base import BaseDataset

    from clearml_yolo.native_dataset import _stage

    monkeypatch.chdir(tmp_path)
    images = tmp_path / "source/images"
    images.mkdir(parents=True)
    Image.new("RGB", (32, 32), "red").save(images / "first.jpg")
    Image.new("RGB", (32, 32), "blue").save(images / "second.jpg")
    manifest = tmp_path / "source/lists/train.txt"
    manifest.parent.mkdir()
    entry: str | list[str]
    if input_form == "repeated":
        entry = [str(images), str(images)]
    else:
        prefix = "source/images" if input_form == "cwd-relative" else "./../images"
        manifest.write_text(f"{prefix}/second.jpg\n{prefix}/first.jpg\n")
        entry = str(manifest)
    # Use the native reader as the compatibility oracle without constructing a training loader.
    reader = BaseDataset.__new__(BaseDataset)
    reader.prefix = ""
    reader.fraction = 1.0
    native = reader.get_img_files(entry)
    output = tmp_path / "staged"
    _stage({"train": entry, "names": {0: "object"}}, output)
    copies = sorted((output / "images/train").glob("*.jpg"))
    assert [path.read_bytes() for path in copies] == [Path(path).read_bytes() for path in native]


def test_read_only_sources_produce_owner_writable_native_copies(tmp_path: Path) -> None:
    from clearml_yolo.native_dataset import _stage

    images = tmp_path / "source/images/train"
    labels = tmp_path / "source/labels/train"
    images.mkdir(parents=True)
    labels.mkdir(parents=True)
    image = images / "sample.jpg"
    label = labels / "sample.txt"
    Image.new("RGB", (32, 32)).save(image)
    label.write_text("0 0.5 0.5 0.5 0.5\n")
    image.chmod(0o444)
    label.chmod(0o444)
    output = tmp_path / "staged"
    _stage({"train": str(images), "names": {0: "object"}}, output)
    copied_image = next((output / "images/train").iterdir())
    copied_label = next((output / "labels/train").iterdir())
    assert copied_image.stat().st_mode & stat.S_IWUSR
    assert copied_label.stat().st_mode & stat.S_IWUSR
    assert stat.S_IMODE(image.stat().st_mode) == 0o444
    assert stat.S_IMODE(label.stat().st_mode) == 0o444


def test_native_manifest_cache_distinguishes_working_directory_membership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.native_dataset import native_dataset

    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    manifest = tmp_path / "train.txt"
    manifest.write_text("images/sample.jpg\n")
    config = tmp_path / "data.yaml"
    config.write_text(yaml.safe_dump({"path": str(tmp_path), "train": str(manifest),
                                    "val": str(manifest), "names": {0: "object"}}))
    entries: list[Path] = []
    for name, color in (("first", "red"), ("second", "blue")):
        launch = tmp_path / name
        images = launch / "images"
        images.mkdir(parents=True)
        source = images / "sample.jpg"
        Image.new("RGB", (32, 32), color).save(source)
        monkeypatch.chdir(launch)
        with native_dataset(config) as staged:
            copied = next((staged.parent / "images/train").iterdir())
            assert copied.read_bytes() == source.read_bytes()
            entries.append(staged)
    assert entries[0] != entries[1]


@pytest.mark.parametrize("explicit_directory", [False, True])
def test_ndjson_conversion_honors_the_selected_native_dataset_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, explicit_directory: bool
) -> None:
    from ultralytics.data import converter
    from ultralytics.utils import SETTINGS

    from clearml_yolo.native_dataset import native_dataset

    workspace = tmp_path / "workspace"
    monkeypatch.setenv("CY_HOME", str(workspace))
    selected = (
        tmp_path / "explicit" if explicit_directory else workspace / ".cache/ultralytics/datasets"
    )
    images = tmp_path / "source/images"
    images.mkdir(parents=True)
    Image.new("RGB", (32, 32)).save(images / "sample.jpg")
    config = tmp_path / "source/data.yaml"
    config.write_text(yaml.safe_dump({"path": str(config.parent), "train": "images",
                                    "val": "images", "names": {0: "object"}}))

    async def convert(
        data: str | Path, output_path: str | Path | None,
        fraction: float | list[float | int], *, split: str,
    ) -> Path:
        assert data == "https://example.com/data.ndjson"
        assert output_path == selected
        assert fraction == 0.5
        assert split == "val"
        return config

    monkeypatch.setattr(converter, "convert_ndjson_to_yolo", convert)
    original = SETTINGS["datasets_dir"]
    configured = str(selected) if explicit_directory else SETTINGS.defaults["datasets_dir"]
    # Change process memory only; the real SDK settings file remains untouched.
    dict.__setitem__(SETTINGS, "datasets_dir", configured)
    try:
        with native_dataset("https://example.com/data.ndjson", fraction=0.5) as staged:
            assert staged.is_file()
    finally:
        dict.__setitem__(SETTINGS, "datasets_dir", original)
