"""Canonical CSVs preserve contexts and upload once at owner completion."""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from clearml_yolo import clearml_results as results
from clearml_yolo.clearml_session import ClearMLConfig, invocation
from clearml_yolo.model_identity import ModelIdentity
from test_clearml_session import FakeTask
from test_clearml_session import fake_clearml as owner_fixture

owner = owner_fixture


def _inputs(root: Path) -> tuple[Path, Path]:
    truth = root / "truth.csv"
    predictions = root / "predictions.csv"
    pd.DataFrame(
        {
            "image_name": ["val.jpg", "test.jpg"],
            "instance_label": ["01", "猫"],
            "split": ["val", "test"],
            "bbox_x_tl": [0, 0],
            "bbox_y_tl": [0, 0],
            "bbox_x_br": [10, 10],
            "bbox_y_br": [10, 10],
        }
    ).to_csv(truth, index=False)
    pd.DataFrame(
        {
            "image_name": ["val.jpg", "test.jpg"],
            "instance_label": ["01", "猫"],
            "confidence": [0.8, 0.5],
            "bbox_x_tl": [0, 0],
            "bbox_y_tl": [0, 0],
            "bbox_x_br": [10, 10],
            "bbox_y_br": [10, 10],
        }
    ).to_csv(predictions, index=False)
    return truth, predictions


def test_prediction_bundle_is_deferred_and_contexts_are_distinct(
    owner: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = owner
    truth, predictions = _inputs(tmp_path)
    with invocation(ClearMLConfig(), "pipeline"):
        results.register_predictions(task, truth, predictions, output_dir=tmp_path, model_id="m1")
        results.register_predictions(task, truth, predictions, output_dir=tmp_path, model_id="m1")
        results.register_predictions(
            task, truth, predictions, output_dir=tmp_path, model_id="m2", role="comparison_baseline"
        )
        assert task.uploads == []
    assert [item["name"] for item in task.uploads] == ["gt_csv", "predicts_csv"]
    frame = pd.read_csv(task.uploads[1]["artifact_object"], dtype={"instance_label": str})
    assert set(frame["model_id"]) == {"m1", "m2"}
    assert set(frame["split"]) == {"val", "test"}
    assert len(frame) == 8  # GT and prediction per model/split.
    assert set(frame["instance_label"]) == {"01", "猫"}
    assert set(frame["evaluation_status"]) == {"not_evaluated"}
    assert frame["is_below_threshold"].isna().all()


def test_gt_only_does_not_invent_prediction_artifact(
    owner: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = owner
    truth, _ = _inputs(tmp_path)
    with invocation(ClearMLConfig(), "train"):
        results.register_ground_truth(task, truth, output_dir=tmp_path)
    assert [item["name"] for item in task.uploads] == ["gt_csv"]
    frame = pd.read_csv(task.uploads[0]["artifact_object"])
    assert frame["source_row_id"].is_unique


def test_worker_does_not_read_inputs_or_create_shards(tmp_path: Path) -> None:
    results.register_predictions(
        None, tmp_path / "missing_gt", tmp_path / "missing_pred", output_dir=tmp_path
    )
    assert list(tmp_path.iterdir()) == []


def test_prediction_provenance_detects_modified_csv(tmp_path: Path) -> None:
    _, predictions = _inputs(tmp_path)
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"model")
    expected = results.write_prediction_provenance(predictions, checkpoint)
    assert results.prediction_checkpoint_hash(predictions) == expected
    predictions.write_text(predictions.read_text() + "\n")
    with pytest.raises(ValueError, match="provenance"):
        results.prediction_checkpoint_hash(predictions)


def test_raw_predictions_outside_split_population_remain_exported(
    owner: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = owner
    truth, predictions = _inputs(tmp_path)
    source = pd.read_csv(predictions)
    extra = source.iloc[[0]].assign(image_name="outside.jpg")
    pd.concat([source, extra], ignore_index=True).to_csv(predictions, index=False)
    with invocation(ClearMLConfig(), "predict"):
        results.register_predictions(task, truth, predictions, output_dir=tmp_path)
    frame = pd.read_csv(task.uploads[1]["artifact_object"])
    predicted = frame[frame["row_type"] == "predict"]
    assert set(predicted["image_name"]) == {"val.jpg", "test.jpg", "outside.jpg"}
    outside = predicted[predicted["image_name"] == "outside.jpg"].iloc[0]
    assert outside["evaluation_status"] == "not_evaluated"
    assert pd.isna(outside["is_below_threshold"])


def test_source_identity_survives_context_csv_and_manifest(
    owner: tuple[type[Any], FakeTask], tmp_path: Path,
) -> None:
    _, task = owner
    truth, predictions = _inputs(tmp_path)
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"trained model")
    identity = ModelIdentity(
        model_name="=001 Unicode model", training_task_id="00000000000000000000000000000001",
        checkpoint_sha256=results.file_digest(checkpoint),
    )
    results.write_prediction_provenance(predictions, checkpoint, identity)
    assert results.prediction_model_identity(predictions) == identity
    with invocation(ClearMLConfig(), "metrics"):
        results.register_predictions(task, truth, predictions, output_dir=tmp_path)
    frame = pd.read_csv(
        task.uploads[1]["artifact_object"], dtype={"training_task_id": str, "model_name": str},
    )
    assert set(frame["model_name"]) == {identity.model_name}
    assert set(frame["training_task_id"]) == {identity.training_task_id}
    manifest = (tmp_path / "result_publication/contexts.json").read_text()
    assert identity.training_task_id is not None
    assert identity.training_task_id in manifest
    assert str(task.id) != identity.training_task_id


def test_prediction_identity_rejects_changed_checkpoint_association(tmp_path: Path) -> None:
    import json

    _, predictions = _inputs(tmp_path)
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"trained model")
    identity = ModelIdentity(
        model_name="model", checkpoint_sha256=results.file_digest(checkpoint),
    )
    results.write_prediction_provenance(predictions, checkpoint, identity)
    sidecar = predictions.with_suffix(".csv.provenance.json")
    data = json.loads(sidecar.read_text())
    data["model_identity"]["checkpoint_sha256"] = "0" * 64
    sidecar.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="checkpoint association"):
        results.prediction_model_identity(predictions)
