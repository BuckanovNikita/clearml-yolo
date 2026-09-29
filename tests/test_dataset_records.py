import csv
import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from loguru import logger
from PIL import Image

from clearml_yolo.dataset_records import validate_ground_truth

COLUMNS = [
    "image_name",
    "image_path",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
    "split",
]


@pytest.fixture
def log_messages() -> Iterator[list[str]]:
    messages: list[str] = []
    sink = logger.add(messages.append, level="INFO", format="{level}:{message}")
    yield messages
    logger.remove(sink)


def _image(path: Path, size: tuple[int, int] = (100, 80)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size).save(path)
    return path


def _row(
    name: str,
    path: str | Path,
    label: str,
    coordinates: tuple[str | float, str | float, str | float, str | float],
    split: str,
) -> dict[str, str | Path | float]:
    x1, y1, x2, y2 = coordinates
    return {
        "image_name": name,
        "image_path": path,
        "instance_label": label,
        "bbox_x_tl": x1,
        "bbox_y_tl": y1,
        "bbox_x_br": x2,
        "bbox_y_br": y2,
        "split": split,
    }


def _background(name: str, path: str | Path, split: str) -> dict[str, str | Path | float]:
    return _row(name, path, "", ("", "", "", ""), split)


def _write_csv(
    path: Path,
    rows: list[dict[str, str | Path | float]],
    *,
    columns: list[str] | None = None,
) -> Path:
    selected_columns = columns or COLUMNS
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=selected_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _valid_dataset(tmp_path: Path) -> Path:
    train = _image(tmp_path / "images" / "train.png")
    val = _image(tmp_path / "images" / "val.png")
    return _write_csv(
        tmp_path / "ground-truth.csv",
        [
            _row("train.png", train, "cat", (0, 0, 100, 80), "train"),
            _background("val.png", val, "val"),
        ],
    )


def test_validates_relative_paths_and_preserves_canonical_records(tmp_path: Path) -> None:
    train = _image(tmp_path / "изображения" / "train image.png", (120, 90))
    val = _image(tmp_path / "изображения" / "val.png", (50, 40))
    test = _image(tmp_path / "изображения" / "test.png", (30, 20))
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [
            {
                **_row(
                    "train image.png",
                    train.relative_to(tmp_path),
                    "10",
                    (2, 3, 12, 13),
                    "train",
                ),
                "ignored": "value",
            },
            _row("train image.png", train.relative_to(tmp_path), "ёж", (0, 0, 120, 90), "train"),
            _background("val.png", val.relative_to(tmp_path), "val"),
            _row("test.png", test.relative_to(tmp_path), "10", (1, 2, 20, 19), "test"),
        ],
        columns=[*COLUMNS, "ignored"],
    )

    dataset = validate_ground_truth(source, required_splits=("test",))

    assert dataset.source == source.resolve()
    assert dataset.input_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert dataset.names == {0: "10", 1: "ёж"}
    assert dataset.input_boxes == 3
    assert dataset.errors == []
    assert [(image.name, image.path, image.split) for image in dataset.images] == [
        ("test.png", test.resolve(), "test"),
        ("train image.png", train.resolve(), "train"),
        ("val.png", val.resolve(), "val"),
    ]
    assert (dataset.images[1].width, dataset.images[1].height) == (120, 90)
    assert [box.model_dump() for box in dataset.images[1].boxes] == [
        {"label": "10", "x1": 2.0, "y1": 3.0, "x2": 12.0, "y2": 13.0},
        {"label": "ёж", "x1": 0.0, "y1": 0.0, "x2": 120.0, "y2": 90.0},
    ]
    assert dataset.images[2].boxes == []


@pytest.mark.parametrize(
    ("label", "coordinates", "reason"),
    [
        ("", (1, 2, 3, 4), "label"),
        ("cat", (1, "", 3, 4), "incomplete"),
        ("cat", (1, "nope", 3, 4), "numeric"),
        ("cat", (1, 2, "nan", 4), "finite"),
        ("cat", (3, 2, 3, 4), "positive"),
        ("cat", (-1, 2, 3, 4), "bounds"),
        ("cat", (1, 2, 101, 4), "bounds"),
    ],
)
def test_drops_each_invalid_annotation_once(
    tmp_path: Path,
    log_messages: list[str],
    label: str,
    coordinates: tuple[str | float, str | float, str | float, str | float],
    reason: str,
) -> None:
    train = _image(tmp_path / "train.png")
    val = _image(tmp_path / "val.png")
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [
            _row("train.png", train, "dog", (10, 10, 20, 20), "train"),
            _row("train.png", train, label, coordinates, "train"),
            _background("val.png", val, "val"),
        ],
    )

    dataset = validate_ground_truth(source)

    assert dataset.input_boxes == 2
    assert len(dataset.errors) == 1
    assert dataset.errors[0].row == 3
    assert dataset.errors[0].image_name == "train.png"
    assert reason in dataset.errors[0].reason.lower()
    assert len(dataset.images[0].boxes) == 1
    assert log_messages.count("INFO:Invalid bounding boxes dropped: 1\n") == 1


def test_drops_and_counts_each_identical_invalid_annotation(
    tmp_path: Path, log_messages: list[str]
) -> None:
    train = _image(tmp_path / "train.png")
    val = _image(tmp_path / "val.png")
    invalid = _row("train.png", train, "cat", (4, 2, 3, 5), "train")
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [
            _row("train.png", train, "cat", (1, 2, 3, 4), "train"),
            invalid,
            invalid,
            _background("val.png", val, "val"),
        ],
    )

    dataset = validate_ground_truth(source)

    assert dataset.input_boxes == 3
    assert [error.row for error in dataset.errors] == [3, 4]
    assert len(dataset.images[0].boxes) == 1
    assert log_messages.count("INFO:Invalid bounding boxes dropped: 2\n") == 1


def test_keeps_image_when_all_of_its_attempted_boxes_are_dropped(tmp_path: Path) -> None:
    train = _image(tmp_path / "train.png")
    invalid = _image(tmp_path / "invalid.png")
    val = _image(tmp_path / "val.png")
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [
            _row("train.png", train, "cat", (1, 2, 3, 4), "train"),
            _row("invalid.png", invalid, "dog", (4, 2, 3, 5), "train"),
            _background("val.png", val, "val"),
        ],
    )

    dataset = validate_ground_truth(source)

    records = {record.name: record for record in dataset.images}
    assert records["invalid.png"].boxes == []
    assert dataset.names == {0: "cat", 1: "dog"}


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        (
            [
                _row("same.png", "first/same.png", "cat", (1, 1, 2, 2), "train"),
                _row("same.png", "second/same.png", "cat", (1, 1, 2, 2), "train"),
            ],
            "image name",
        ),
        (
            [
                _row("a.png", "a.png", "cat", (1, 1, 2, 2), "train"),
                _row("a.png", "a.png", "dog", (1, 1, 2, 2), "val"),
            ],
            "split",
        ),
    ],
)
def test_rejects_conflicting_image_identity(
    tmp_path: Path,
    rows: list[dict[str, str | Path | float]],
    message: str,
) -> None:
    for row in rows:
        _image(tmp_path / Path(str(row["image_path"])))
    source = _write_csv(tmp_path / "ground-truth.csv", rows)

    with pytest.raises(ValueError, match=message):
        validate_ground_truth(source)


def test_rejects_an_image_name_that_is_not_the_resolved_path_basename(tmp_path: Path) -> None:
    train = _image(tmp_path / "actual.png")
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [_row("alias.png", train, "cat", (1, 2, 3, 4), "train")],
    )

    with pytest.raises(ValueError, match=r"row 2.*image_name.*alias\.png.*actual\.png"):
        validate_ground_truth(source)


def test_rejects_duplicate_annotation_rows(tmp_path: Path) -> None:
    train = _image(tmp_path / "train.png")
    row = _row("train.png", train, "cat", (1, 2, 3, 4), "train")
    source = _write_csv(tmp_path / "ground-truth.csv", [row, row])

    with pytest.raises(ValueError, match=r"[Dd]uplicate.*row 3"):
        validate_ground_truth(source)


def test_rejects_duplicate_background_rows(tmp_path: Path) -> None:
    train = _image(tmp_path / "train.png")
    row = _background("train.png", train, "train")
    source = _write_csv(tmp_path / "ground-truth.csv", [row, row])

    with pytest.raises(ValueError, match=r"[Dd]uplicate.*background.*row 3"):
        validate_ground_truth(source)


def test_rejects_mixed_background_and_annotation_rows(tmp_path: Path) -> None:
    train = _image(tmp_path / "train.png")
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [
            _background("train.png", train, "train"),
            _row("train.png", train, "cat", (1, 2, 3, 4), "train"),
        ],
    )

    with pytest.raises(ValueError, match=r"background.*annotation"):
        validate_ground_truth(source)


@pytest.mark.parametrize(
    ("columns", "rows", "message"),
    [
        (COLUMNS[:-1], [], "missing required columns.*split"),
        (COLUMNS, [], "no data rows"),
        (COLUMNS, [_background("train.png", "train.png", "dev")], "row 2.*split"),
        (COLUMNS, [_background("", "train.png", "train")], "row 2.*image_name"),
        (COLUMNS, [_background("train.png", "", "train")], "row 2.*image_path"),
    ],
)
def test_rejects_structurally_invalid_csv(
    tmp_path: Path,
    columns: list[str],
    rows: list[dict[str, str | Path | float]],
    message: str,
) -> None:
    source = _write_csv(tmp_path / "ground-truth.csv", rows, columns=columns)

    with pytest.raises(ValueError, match=message):
        validate_ground_truth(source)


def test_rejects_duplicate_csv_headers(tmp_path: Path) -> None:
    source = tmp_path / "ground-truth.csv"
    source.write_text(",".join([*COLUMNS, "image_name"]) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"[Dd]uplicate.*header.*image_name"):
        validate_ground_truth(source)


@pytest.mark.parametrize("unreadable", [False, True])
def test_rejects_missing_or_unreadable_images(tmp_path: Path, unreadable: bool) -> None:
    image = tmp_path / "broken.png"
    if unreadable:
        image.write_text("not an image", encoding="utf-8")
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [_row("broken.png", image, "cat", (1, 2, 3, 4), "train")],
    )

    with pytest.raises(ValueError, match=r"broken.png.*read"):
        validate_ground_truth(source)


def test_reads_each_repeated_image_only_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _valid_dataset(tmp_path)
    real_open = Image.open
    opened: list[str | Path] = []

    def recording_open(path: str | Path) -> Image.Image:
        opened.append(path)
        return real_open(path)

    monkeypatch.setattr(Image, "open", recording_open)

    validate_ground_truth(source)

    assert len(opened) == 2
    assert {Path(path).name for path in opened} == {"train.png", "val.png"}


def test_rejects_an_image_extension_ultralytics_would_silently_skip(tmp_path: Path) -> None:
    unsupported = tmp_path / "train.unsupported"
    _image(tmp_path / "train.png").replace(unsupported)
    val = _image(tmp_path / "val.png")
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [
            _row("train.unsupported", unsupported, "cat", (1, 2, 3, 4), "train"),
            _background("val.png", val, "val"),
        ],
    )

    with pytest.raises(ValueError, match=r"train\.unsupported.*extension.*supported"):
        validate_ground_truth(source)


def test_rejects_an_image_smaller_than_the_native_minimum(tmp_path: Path) -> None:
    train = _image(tmp_path / "tiny.png", (9, 10))
    val = _image(tmp_path / "val.png")
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [
            _row("tiny.png", train, "cat", (0, 0, 9, 10), "train"),
            _background("val.png", val, "val"),
        ],
    )

    with pytest.raises(ValueError, match=r"tiny\.png.*9 x 10.*at least 10"):
        validate_ground_truth(source)


def test_uses_native_exif_oriented_dimensions(tmp_path: Path) -> None:
    train = tmp_path / "oriented.jpg"
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (20, 30)).save(train, exif=exif)
    val = _image(tmp_path / "val.png")
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [
            _row("oriented.jpg", train, "cat", (0, 0, 30, 20), "train"),
            _background("val.png", val, "val"),
        ],
    )

    dataset = validate_ground_truth(source)

    oriented = next(image for image in dataset.images if image.name == "oriented.jpg")
    assert (oriented.width, oriented.height) == (30, 20)
    assert len(oriented.boxes) == 1


def test_warns_and_uses_decoded_dimensions_when_exif_cannot_be_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, log_messages: list[str]
) -> None:
    train = tmp_path / "broken-exif.jpg"
    Image.new("RGB", (20, 30)).save(train)
    val = _image(tmp_path / "val.png")
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [
            _row("broken-exif.jpg", train, "cat", (0, 0, 20, 30), "train"),
            _background("val.png", val, "val"),
        ],
    )

    def raise_exif_error(image: Image.Image) -> Image.Exif:
        raise OSError("corrupt EXIF metadata")

    monkeypatch.setattr(Image.Image, "getexif", raise_exif_error)

    dataset = validate_ground_truth(source)

    record = next(image for image in dataset.images if image.name == "broken-exif.jpg")
    warnings = [message for message in log_messages if message.startswith("WARNING:")]
    assert (record.width, record.height) == (20, 30)
    assert len(record.boxes) == 1
    assert len(warnings) == 1
    assert "broken-exif.jpg" in warnings[0]
    assert "EXIF" in warnings[0]
    assert "decoded dimensions" in warnings[0]


def test_rejects_numerically_duplicate_boxes_before_native_verification(tmp_path: Path) -> None:
    train = _image(tmp_path / "train.png")
    val = _image(tmp_path / "val.png")
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [
            _row("train.png", train, "cat", (1, 2, 3, 4), "train"),
            _row("train.png", train, "cat", ("1.0", "2.0", "3.0", "4.0"), "train"),
            _background("val.png", val, "val"),
        ],
    )

    with pytest.raises(ValueError, match=r"[Dd]uplicate.*box.*row 3"):
        validate_ground_truth(source)


def test_validation_does_not_modify_source_images(tmp_path: Path) -> None:
    source = _valid_dataset(tmp_path)
    paths = [tmp_path / "images" / "train.png", tmp_path / "images" / "val.png"]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}

    validate_ground_truth(source)

    assert {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths} == before


def test_requires_train_val_requested_splits_and_a_valid_training_box(
    tmp_path: Path, log_messages: list[str]
) -> None:
    train = _image(tmp_path / "train.png")
    val = _image(tmp_path / "val.png")
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [
            _row("train.png", train, "cat", (3, 2, 3, 4), "train"),
            _background("val.png", val, "val"),
        ],
    )

    with pytest.raises(ValueError, match="valid training box"):
        validate_ground_truth(source)

    assert log_messages.count("INFO:Invalid bounding boxes dropped: 1\n") == 1

    valid_source = _valid_dataset(tmp_path / "valid")
    with pytest.raises(ValueError, match="test"):
        validate_ground_truth(valid_source, required_splits=("test",))


def test_warns_for_classes_without_valid_training_examples(
    tmp_path: Path, log_messages: list[str]
) -> None:
    train = _image(tmp_path / "train.png")
    val = _image(tmp_path / "val.png")
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [
            _row("train.png", train, "cat", (1, 2, 3, 4), "train"),
            _row("train.png", train, "invalid-only", (4, 2, 3, 5), "train"),
            _row("val.png", val, "val-only", (1, 2, 3, 4), "val"),
        ],
    )

    dataset = validate_ground_truth(source)

    warnings = [message for message in log_messages if message.startswith("WARNING:")]
    assert dataset.names == {0: "cat", 1: "invalid-only", 2: "val-only"}
    assert any("invalid-only" in message for message in warnings)
    assert any("val-only" in message for message in warnings)
    assert all("cat" not in message for message in warnings)


def test_row_order_does_not_change_the_validated_dataset(tmp_path: Path) -> None:
    train = _image(tmp_path / "train.png")
    val = _image(tmp_path / "val.png")
    rows = [
        _row("train.png", train, "zebra", (10, 10, 20, 20), "train"),
        _row("train.png", train, "ant", (1, 2, 3, 4), "train"),
        _background("val.png", val, "val"),
    ]
    first = _write_csv(tmp_path / "first.csv", rows)
    second = _write_csv(tmp_path / "second.csv", list(reversed(rows)))

    first_result = validate_ground_truth(first)
    second_result = validate_ground_truth(second)

    assert first_result.names == second_result.names == {0: "ant", 1: "zebra"}
    assert first_result.images == second_result.images


def test_accepts_native_jp2_images_with_pillow_jpeg2000_format(tmp_path: Path) -> None:
    from ultralytics.data.utils import check_image

    train = _image(tmp_path / "train.jp2", (100, 80))
    val = _image(tmp_path / "val.png")
    with Image.open(train) as decoded:
        assert decoded.format == "JPEG2000"
    assert check_image(str(train)) == ("", (80, 100))
    source = _write_csv(
        tmp_path / "ground-truth.csv",
        [
            _row(train.name, train, "cat", (0, 0, 100, 80), "train"),
            _background(val.name, val, "val"),
        ],
    )

    dataset = validate_ground_truth(source)

    assert dataset.images[0].path == train.resolve()
    assert (dataset.images[0].width, dataset.images[0].height) == (100, 80)
    assert len(dataset.images[0].boxes) == 1
