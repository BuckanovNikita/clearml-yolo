"""CSV publication preserves image identity, splits, and original annotations."""

import hashlib
from pathlib import Path

import pytest
from PIL import Image


def write_truth(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (100, 50)).save(folder / "001.png")
    Image.new("RGB", (100, 50)).save(folder / "empty.png")
    path = folder / "gt.csv"
    path.write_text(
        "image_name,image_path,instance_label,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br,split\n"
        "001.png,001.png,01,10,5,50,25,val\n"
        "001.png,001.png,01,10,5,50,25,val\n"
        "empty.png,empty.png,,,,,,test\n"
    )
    return path


def test_snapshot_preserves_duplicates_background_and_string_labels(tmp_path: Path) -> None:
    from clearml_yolo.publishing.data import read_snapshot

    snapshot = read_snapshot(write_truth(tmp_path))
    assert snapshot.images["001.png"].split == "val"
    assert snapshot.images["empty.png"].split == "test"
    assert len(snapshot.images["001.png"].boxes) == 2
    assert snapshot.images["001.png"].boxes[0].label == "01"
    assert snapshot.images["empty.png"].boxes == []
    assert snapshot.images["001.png"].path == (tmp_path / "001.png").resolve()


def test_relocated_identical_csv_has_same_hash_but_different_paths(tmp_path: Path) -> None:
    from clearml_yolo.publishing.data import read_snapshot

    first = read_snapshot(write_truth(tmp_path / "a"))
    second = read_snapshot(write_truth(tmp_path / "b"))
    assert first.sha256 == second.sha256
    assert first.membership != second.membership


def test_snapshot_does_not_open_image_media(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.publishing.data import read_snapshot

    truth = write_truth(tmp_path)
    monkeypatch.setattr(Image, "open", lambda *a, **k: pytest.fail("cache hit opened an image"))
    assert len(read_snapshot(truth).images) == 2


def test_box_normalization_retains_absolute_extent() -> None:
    from clearml_yolo.publishing.data import normalize_box

    assert normalize_box((10, 5, 50, 25), 100, 50) == [0.1, 0.1, 0.4, 0.4]


def test_conflicting_split_is_rejected(tmp_path: Path) -> None:
    from clearml_yolo.publishing.data import read_snapshot

    path = write_truth(tmp_path)
    with path.open("a") as stream:
        stream.write("001.png,001.png,01,20,5,50,25,test\n")
    with pytest.raises(ValueError, match="identity"):
        read_snapshot(path)


def test_snapshot_hash_identifies_the_bytes_parsed_during_concurrent_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.publishing import data

    truth = write_truth(tmp_path)
    original_bytes = truth.read_bytes()
    original_box = data._box

    def replace_csv(row: dict[str, str], index: int) -> data.PublicationBox:
        truth.write_bytes(original_bytes.replace(b",val\n", b",test\n"))
        return original_box(row, index)

    monkeypatch.setattr(data, "_box", replace_csv)
    snapshot = data.read_snapshot(truth)
    assert snapshot.images["001.png"].split == "val"
    assert snapshot.sha256 == hashlib.sha256(original_bytes).hexdigest()
    assert snapshot.sha256 != data.file_hash(truth)


@pytest.mark.parametrize("mode", ["stem", "path"])
def test_prediction_names_follow_standalone_inference_mode(tmp_path: Path, mode: str) -> None:
    from clearml_yolo.publishing.data import prediction_aliases, read_predictions, read_snapshot

    snapshot = read_snapshot(write_truth(tmp_path))
    prediction_name = "001" if mode == "stem" else str(tmp_path / "001.png")
    path = tmp_path / "predictions.csv"
    path.write_text(
        "image_name,instance_label,confidence,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br\n"
        f"{prediction_name},01,0.8,10,5,50,25\n"
    )
    result = read_predictions(path, prediction_aliases(snapshot, mode))
    assert list(result) == ["001.png"]
