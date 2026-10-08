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
    from clearml_yolo.adapters.storage.publication_data import read_snapshot

    snapshot = read_snapshot(write_truth(tmp_path))
    assert snapshot.images["001.png"].split == "val"
    assert snapshot.images["empty.png"].split == "test"
    assert len(snapshot.images["001.png"].boxes) == 2
    assert snapshot.images["001.png"].boxes[0].label == "01"
    assert snapshot.images["empty.png"].boxes == []
    assert snapshot.images["001.png"].path == (tmp_path / "001.png").resolve()


def test_relocated_identical_csv_has_same_hash_but_different_paths(tmp_path: Path) -> None:
    from clearml_yolo.adapters.storage.publication_data import read_snapshot

    first = read_snapshot(write_truth(tmp_path / "a"))
    second = read_snapshot(write_truth(tmp_path / "b"))
    assert first.sha256 == second.sha256
    assert first.membership != second.membership


def test_snapshot_does_not_open_image_media(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.storage.publication_data import read_snapshot

    truth = write_truth(tmp_path)
    monkeypatch.setattr(Image, "open", lambda *a, **k: pytest.fail("cache hit opened an image"))
    assert len(read_snapshot(truth).images) == 2


def test_box_normalization_retains_absolute_extent() -> None:
    from clearml_yolo.adapters.storage.publication_data import normalize_box

    assert normalize_box((10, 5, 50, 25), 100, 50) == [0.1, 0.1, 0.4, 0.4]


def test_conflicting_split_is_rejected(tmp_path: Path) -> None:
    from clearml_yolo.adapters.storage.publication_data import read_snapshot

    path = write_truth(tmp_path)
    with path.open("a") as stream:
        stream.write("001.png,001.png,01,20,5,50,25,test\n")
    with pytest.raises(ValueError, match="identity"):
        read_snapshot(path)


def test_snapshot_hash_identifies_the_bytes_parsed_during_concurrent_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.storage import publication_data as data

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
    from clearml_yolo.adapters.storage.publication_data import (
        prediction_aliases,
        read_predictions,
        read_snapshot,
    )

    snapshot = read_snapshot(write_truth(tmp_path))
    prediction_name = "001" if mode == "stem" else str(tmp_path / "001.png")
    path = tmp_path / "predictions.csv"
    path.write_text(
        "image_name,instance_label,confidence,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br\n"
        f"{prediction_name},01,0.8,10,5,50,25\n"
    )
    result = read_predictions(path, prediction_aliases(snapshot, mode))
    assert list(result) == ["001.png"]


@pytest.mark.parametrize(
    "box",
    [
        (10.0, 50.0, 40.0, 50.0),
        (100.0, 5.0, 100.0, 25.0),
        (100.0, 50.0, 100.0, 50.0),
        (1482.845458984375, 1464.0, 1501.89892578125, 1464.0),
    ],
)
def test_predictions_preserve_collapsed_native_boxes_at_row_225(
    tmp_path: Path, box: tuple[float, float, float, float]
) -> None:
    from clearml_yolo.adapters.storage.publication_data import normalize_box, read_predictions

    path = tmp_path / "predictions.csv"
    path.write_text(
        "image_name,instance_label,confidence,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br\n"
        + "001.png,01,0.8,10,5,50,25\n" * 225
        + "001.png,01,0.001,"
        + ",".join(str(value) for value in box)
        + "\n"
        + "001.png,01,0.9,20,10,60,30\n"
    )
    result = read_predictions(path, {"001.png": "001.png"})["001.png"]
    assert len(result) == 227
    assert result[225].box == box
    assert result[225].label == "01"
    assert result[225].confidence == 0.001
    assert result[225].index == 225
    assert result[226].index == 226
    assert 0 in normalize_box(result[225].box, 100, 50)[2:]


@pytest.mark.parametrize(
    "coordinates",
    ["40,5,10,25", "10,25,40,5", "nan,5,40,25", "10,5,inf,25"],
)
def test_predictions_reject_reversed_or_nonfinite_boxes(tmp_path: Path, coordinates: str) -> None:
    from clearml_yolo.adapters.storage.publication_data import read_predictions

    path = tmp_path / "predictions.csv"
    path.write_text(
        "image_name,instance_label,confidence,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br\n"
        f"001.png,01,0.8,{coordinates}\n"
    )
    with pytest.raises(ValueError, match="Invalid publication box"):
        read_predictions(path, {"001.png": "001.png"})


def test_invalid_prediction_error_identifies_the_offending_record(tmp_path: Path) -> None:
    from clearml_yolo.adapters.storage.publication_data import read_predictions

    path = tmp_path / "predictions.csv"
    path.write_text(
        "image_name,instance_label,confidence,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br\n"
        "00031829_06_012835.jpg,Пятна Эмульсии,0.0024610012769699097,"
        "1540.61328125,1105.0345458984375,1563.83056640625,1124.69775390625\n"
        "invalid.jpg,01,0.8,40,5,10,25\n"
    )
    with pytest.raises(ValueError, match="Invalid publication box") as raised:
        read_predictions(
            path,
            {"00031829_06_012835.jpg": "00031829_06_012835.jpg", "invalid.jpg": "invalid.jpg"},
        )
    message = str(raised.value)
    assert "CSV data row 1 (zero-based)" in message
    assert "invalid.jpg" in message
    assert "(40.0, 5.0, 10.0, 25.0)" in message


@pytest.mark.parametrize("confidence", ["nan", "inf", "-0.1", "1.1"])
def test_collapsed_predictions_still_require_valid_confidence(
    tmp_path: Path, confidence: str
) -> None:
    from clearml_yolo.adapters.storage.publication_data import read_predictions

    path = tmp_path / "predictions.csv"
    path.write_text(
        "image_name,instance_label,confidence,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br\n"
        f"001.png,01,{confidence},10,50,40,50\n"
    )
    with pytest.raises(ValueError, match="Invalid prediction confidence"):
        read_predictions(path, {"001.png": "001.png"})


@pytest.mark.parametrize("coordinates", ["10,50,40,50", "100,5,100,25", "100,50,100,50"])
def test_ground_truth_rejects_collapsed_boxes(tmp_path: Path, coordinates: str) -> None:
    from clearml_yolo.adapters.storage.publication_data import read_snapshot

    path = tmp_path / "gt.csv"
    path.write_text(
        "image_name,image_path,instance_label,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br,split\n"
        f"001.png,001.png,01,{coordinates},val\n"
    )
    with pytest.raises(ValueError, match="Invalid publication box"):
        read_snapshot(path)
