"""Detection input identities survive storage, execution, evaluation and publication."""

import csv
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from PIL import Image


def _truth(directory: Path, *, absolute: bool = False) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "truth.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
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
        for split in ("train", "val"):
            image = directory / f"{split}.png"
            Image.new("RGB", (16, 16)).save(image)
            writer.writerow(
                [
                    image.name,
                    str(image) if absolute else image.name,
                    "NA",
                    0,
                    0,
                    10,
                    10,
                    split,
                ]
            )
    return path


def test_cache_distinguishes_resolved_relative_images(tmp_path: Path) -> None:
    from clearml_yolo.adapters.storage.dataset_cache import cached_dataset

    left, right = _truth(tmp_path / "left"), _truth(tmp_path / "right")
    assert left.read_bytes() == right.read_bytes()
    with cached_dataset(left, tmp_path / "cache") as first:
        first_root = first.data.parent
    with cached_dataset(right, tmp_path / "cache") as second:
        assert second.data.parent != first_root
        truth = pd.read_csv(second.ground_truth)
        assert all(str(tmp_path / "right") in path for path in truth.image_path)


def test_cache_reuses_same_absolute_references(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import clearml_yolo.adapters.storage.dataset_cache as cache

    left = _truth(tmp_path / "left", absolute=True)
    right = tmp_path / "copy.csv"
    right.write_bytes(left.read_bytes())
    with cache.cached_dataset(left, tmp_path / "cache") as first:
        first_root = first.data.parent
    monkeypatch.setattr(cache, "prepare_dataset", lambda *_a, **_kw: pytest.fail("cache miss"))
    with cache.cached_dataset(right, tmp_path / "cache") as second:
        assert second.data.parent == first_root


def test_ground_truth_retains_lexical_paths_and_resolves_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.storage.file_io import read_ground_truth

    source = _truth(tmp_path / "source")
    other = tmp_path / "working"
    _truth(other)
    monkeypatch.chdir(other)
    loaded = read_ground_truth(source)
    assert loaded.source.image_path.tolist() == ["train.png", "val.png"]
    assert loaded.execution.image_path.tolist() == [
        str(source.parent / "train.png"),
        str(source.parent / "val.png"),
    ]
    assert loaded.source.index.equals(loaded.execution.index)
    assert loaded.source.instance_label.tolist() == ["NA", "NA"]


def test_detection_csv_preserves_literals_backgrounds_and_exact_floats(tmp_path: Path) -> None:
    from clearml_yolo.adapters.storage.file_io import read_detection_csv

    labels = ["NA", "NULL", "nan", "None", "0001", "树", ""]
    threshold = math.nextafter(0.37, 1.0)
    path = tmp_path / "rows.csv"
    pd.DataFrame(
        {"image_name": labels, "instance_label": labels, "confidence": [threshold] * len(labels)}
    ).to_csv(path, index=False)
    rows = read_detection_csv(path)
    assert rows.instance_label.iloc[:-1].tolist() == labels[:-1]
    assert pd.isna(rows.instance_label.iloc[-1])
    assert rows.confidence.tolist() == [threshold] * len(labels)
    assert rows.index.tolist() == list(range(len(labels)))


@pytest.mark.parametrize("mode", ["stem", "path"])
def test_comparison_config_rejects_noncanonical_modes(mode: str) -> None:
    from clearml_yolo.application.contracts import InferenceConfig

    with pytest.raises(ValueError, match="name"):
        InferenceConfig.model_validate(
            {
                "conf": 0.1,
                "iou": 0.7,
                "imgsz": 32,
                "batch": 1,
                "device": "cpu",
                "image_name": mode,
            }
        )


def test_prediction_provenance_binds_naming_mode_and_detects_changed_csv(tmp_path: Path) -> None:
    from clearml_yolo.adapters.clearml.results import (
        prediction_image_name,
        write_prediction_provenance,
    )

    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"model")
    predictions = tmp_path / "predictions.csv"
    predictions.write_text("image_name,instance_label\na,NA\n")
    write_prediction_provenance(predictions, checkpoint, prediction_image_name="stem")
    assert prediction_image_name(predictions) == "stem"
    payload = json.loads(predictions.with_suffix(".csv.provenance.json").read_text())
    assert payload["prediction_image_name"] == "stem"
    predictions.write_text("image_name,instance_label\nb,NA\n")
    with pytest.raises(ValueError, match="CSV bytes"):
        prediction_image_name(predictions)


def test_evaluation_rejects_unknown_prediction_membership() -> None:
    from clearml_yolo.core.evaluation.policy import validate_prediction_identity

    truth = pd.DataFrame({"image_name": ["a.jpg"]})
    validate_prediction_identity(truth, pd.DataFrame({"image_name": ["a.jpg"]}))
    for name in ("a", "/tmp/a.jpg", "unknown.jpg"):
        with pytest.raises(ValueError, match="canonical"):
            validate_prediction_identity(truth, pd.DataFrame({"image_name": [name]}))


@pytest.mark.parametrize("label", ["NA", "NULL", "nan", "None", "0001", "树"])
def test_literal_class_csv_keeps_perfect_ap_and_threshold_boundary(
    tmp_path: Path, label: str
) -> None:
    from clearml_yolo.adapters.evaluation.scoring import compute_evaluation
    from clearml_yolo.adapters.storage.file_io import read_detection_csv

    threshold = math.nextafter(0.37, 1.0)
    truth_path = tmp_path / "truth.csv"
    predictions_path = tmp_path / "predictions.csv"
    truth = pd.DataFrame(
        {
            "image_name": ["image.jpg", "empty.jpg"],
            "instance_label": [label, None],
            "bbox_x_tl": [0.0, None],
            "bbox_y_tl": [0.0, None],
            "bbox_x_br": [10.0, None],
            "bbox_y_br": [10.0, None],
            "split": ["test", "test"],
        }
    )
    prediction = truth.iloc[[0]].drop(columns="split").assign(confidence=threshold)
    truth.to_csv(truth_path, index=False)
    prediction.to_csv(predictions_path, index=False)
    loaded_truth, loaded_predictions = (
        read_detection_csv(truth_path),
        read_detection_csv(predictions_path),
    )
    kwargs: dict[str, Any] = {
        "split": "test",
        "classes": [label],
        "thresholds": {label: threshold},
        "required_classes": None,
        "iou_threshold": 0.5,
        "matching_strategy": "iou_prior",
        "ap_method": "interp",
        "skip_cohen_kappa": True,
    }
    evaluated = compute_evaluation(loaded_truth, loaded_predictions, loaded_predictions, **kwargs)
    assert evaluated.metrics[label].ap50 == 1.0
    assert evaluated.metrics[label].tp == 1
    assert evaluated.image_names == ["image.jpg", "empty.jpg"]
    for name in ("image", str(tmp_path / "image.jpg"), "unknown.jpg"):
        unsupported = loaded_predictions.assign(image_name=name)
        with pytest.raises(ValueError, match="canonical"):
            compute_evaluation(loaded_truth, unsupported, unsupported, **kwargs)


@pytest.mark.parametrize("mode", ["stem", "path"])
def test_hydra_comparison_validation_rejects_raw_export_naming(mode: str) -> None:
    from omegaconf import OmegaConf

    from clearml_yolo.application.use_cases.compare import compare
    from clearml_yolo.entrypoints.hydra.validation import validate_wrapper_keys

    config = OmegaConf.create({"inference": {"reuse_existing": True, "image_name": mode}})
    with pytest.raises(ValueError, match="require image_name='name'"):
        validate_wrapper_keys(config, compare)


def test_historical_provenance_without_naming_mode_remains_usable(tmp_path: Path) -> None:
    from clearml_yolo.adapters.clearml.results import (
        prediction_image_name,
        write_prediction_provenance,
    )
    from clearml_yolo.core.evaluation.policy import validate_prediction_identity

    predictions = tmp_path / "predictions.csv"
    predictions.write_text("image_name,instance_label\na.jpg,NA\n")
    write_prediction_provenance(predictions, tmp_path / "unavailable.pt")
    sidecar = predictions.with_suffix(".csv.provenance.json")
    payload = json.loads(sidecar.read_text())
    del payload["prediction_image_name"]
    sidecar.write_text(json.dumps(payload))
    assert prediction_image_name(predictions) is None
    validate_prediction_identity(
        pd.DataFrame({"image_name": ["a.jpg"]}),
        pd.DataFrame({"image_name": ["a.jpg"]}),
        image_name=prediction_image_name(predictions),
    )


@pytest.mark.parametrize("mode", [None, 1, {}, "unknown"])
def test_malformed_provenance_naming_mode_fails_clearly(tmp_path: Path, mode: object) -> None:
    from clearml_yolo.adapters.clearml.results import (
        prediction_image_name,
        write_prediction_provenance,
    )

    predictions = tmp_path / "predictions.csv"
    predictions.write_text("image_name,instance_label\na.jpg,NA\n")
    write_prediction_provenance(predictions, tmp_path / "unavailable.pt")
    sidecar = predictions.with_suffix(".csv.provenance.json")
    payload = json.loads(sidecar.read_text())
    payload["prediction_image_name"] = mode
    sidecar.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="invalid prediction_image_name"):
        prediction_image_name(predictions)


def test_bom_with_first_image_path_column_keeps_cache_resolution_and_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import clearml_yolo.adapters.storage.dataset_cache as cache
    from clearml_yolo.adapters.storage.file_io import read_detection_csv, read_ground_truth
    from clearml_yolo.adapters.storage.publication_data import read_snapshot

    left, right = _truth(tmp_path / "left"), _truth(tmp_path / "right")
    for source in (left, right):
        frame = read_detection_csv(source)
        columns = ["image_path", *(name for name in frame.columns if name != "image_path")]
        frame[columns].to_csv(source, index=False, encoding="utf-8-sig")
    assert left.read_bytes() == right.read_bytes()
    roots: list[Path] = []
    for source in (left, right):
        with cache.cached_dataset(source, tmp_path / "cache") as prepared:
            roots.append(prepared.data.parent)
        assert read_ground_truth(source).execution.image_path.iloc[0] == str(
            source.parent / "train.png"
        )
        snapshot = read_snapshot(source)
        assert snapshot.images["train.png"].path == source.parent / "train.png"
        assert snapshot.images["train.png"].boxes[0].label == "NA"
    assert roots[0] != roots[1]
    monkeypatch.setattr(cache, "prepare_dataset", lambda *_a, **_kw: pytest.fail("cache miss"))
    for source, root in zip((left, right), roots, strict=True):
        with cache.cached_dataset(source, tmp_path / "cache") as prepared:
            assert prepared.data.parent == root


def test_cache_hits_ignore_image_contents_and_mtime_until_explicit_invalidation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os
    import shutil

    import clearml_yolo.adapters.storage.dataset_cache as cache

    source = _truth(tmp_path / "source")
    with cache.cached_dataset(source, tmp_path / "cache") as prepared:
        root = prepared.data.parent
        manifest = json.loads(prepared.manifest.read_text())
        copied = Path(manifest["images"][0]["generated_path"])
        original_copy = copied.read_bytes()
    image_path = source.parent / "train.png"
    image_path.write_bytes(b"new content requires explicit invalidation")
    os.utime(image_path, (1, 1))
    original_read_bytes = Path.read_bytes

    def read_without_source_image(path: Path) -> bytes:
        if path == image_path:
            pytest.fail("cache hit must not hash source image content")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_without_source_image)
    monkeypatch.setattr(cache, "prepare_dataset", lambda *_a, **_kw: pytest.fail("cache miss"))
    monkeypatch.setattr(shutil, "copyfile", lambda *_a, **_kw: pytest.fail("copied source image"))
    monkeypatch.setattr(Image, "open", lambda *_a, **_kw: pytest.fail("decoded source image"))
    with cache.cached_dataset(source, tmp_path / "cache") as cached:
        assert cached.data.parent == root
        assert copied.read_bytes() == original_copy
