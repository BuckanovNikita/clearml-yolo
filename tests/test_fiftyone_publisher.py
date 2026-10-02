"""Opt-in persistence checks against a real, explicitly isolated FiftyOne database."""

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from PIL import Image

from clearml_yolo.publishing.models import FiftyOneConfig, PublicationRequest
from test_publication_data import write_truth

pytestmark = pytest.mark.skipif(
    os.environ.get("CY_TEST_FIFTYONE") != "1",
    reason="Set CY_TEST_FIFTYONE=1 and FIFTYONE_DATABASE_DIR to an isolated database",
)


@pytest.fixture
def backend() -> Any:
    if not os.environ.get("FIFTYONE_DATABASE_DIR"):
        pytest.fail("Real FiftyOne tests require an explicit isolated FIFTYONE_DATABASE_DIR")
    import fiftyone as fo

    return fo


@pytest.fixture
def publisher(backend: Any) -> Iterator[Any]:
    from clearml_yolo.publishing import create_publisher

    prefix = f"cy-test-{uuid4().hex}"
    instance = create_publisher(FiftyOneConfig(dataset_prefix=prefix))
    instance.preflight()
    try:
        yield instance
    finally:
        for name in backend.list_datasets():
            if name.startswith(prefix + "-"):
                backend.delete_dataset(name)


def test_reuse_split_background_history_and_normalization(
    tmp_path: Path, publisher: Any, backend: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    truth = write_truth(tmp_path)
    first = publisher.publish(PublicationRequest(task_id="first", ground_truth=truth))
    dataset = backend.load_dataset(first.dataset_name)
    assert dataset.persistent is True
    assert len(dataset) == 2
    sample = dataset[str(tmp_path / "001.png")]
    assert sample.split == "val"
    assert sample.ground_truth.detections[0].label == "01"
    assert sample.ground_truth.detections[0].bounding_box == [0.1, 0.1, 0.4, 0.4]
    assert dataset[str(tmp_path / "empty.png")].ground_truth.detections == []
    monkeypatch.setattr(Image, "open", lambda *a, **k: pytest.fail("reimported media"))
    second = publisher.publish(PublicationRequest(task_id="second", ground_truth=truth))
    assert second.dataset_reused is True
    assert first.dataset_name == second.dataset_name
    assert first.run_key != second.run_key
    dataset.reload()
    assert set(dataset.info["cy_runs"]) == {first.run_key, second.run_key}
    assert all(run["complete"] for run in dataset.info["cy_runs"].values())


def test_identical_csv_relocated_paths_fail_without_mutation(
    tmp_path: Path, publisher: Any, backend: Any
) -> None:
    first = publisher.publish(
        PublicationRequest(task_id="first", ground_truth=write_truth(tmp_path / "a"))
    )
    with pytest.raises(ValueError, match="path identity"):
        publisher.publish(
            PublicationRequest(task_id="second", ground_truth=write_truth(tmp_path / "b"))
        )
    dataset = backend.load_dataset(first.dataset_name)
    dataset.reload()
    assert set(dataset.info["cy_runs"]) == {first.run_key}


def test_retry_replaces_only_its_own_predictions(
    tmp_path: Path, publisher: Any, backend: Any
) -> None:
    truth = write_truth(tmp_path)
    predictions = tmp_path / "predictions.csv"
    header = "image_name,instance_label,confidence,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br\n"
    predictions.write_text(header + "001.png,01,0.8,10,5,50,25\n")
    first = publisher.publish(
        PublicationRequest(task_id="first", ground_truth=truth, predictions=predictions)
    )
    second = publisher.publish(
        PublicationRequest(task_id="second", ground_truth=truth, predictions=predictions)
    )
    predictions.write_text(header)
    publisher.publish(
        PublicationRequest(task_id="first", ground_truth=truth, predictions=predictions)
    )
    dataset = backend.load_dataset(first.dataset_name)
    dataset.reload()
    sample = dataset[str(tmp_path / "001.png")]
    assert sample[first.fields["predictions"]].detections == []
    assert len(sample[second.fields["predictions"]].detections) == 1
    assert sample[second.fields["predicted"]] is True
    empty = dataset[str(tmp_path / "empty.png")]
    assert empty[second.fields["predicted"]] is None


def test_collapsed_native_predictions_are_persisted(
    tmp_path: Path, publisher: Any, backend: Any
) -> None:
    truth = write_truth(tmp_path)
    predictions = tmp_path / "predictions.csv"
    predictions.write_text(
        "image_name,instance_label,confidence,bbox_x_tl,bbox_y_tl,bbox_x_br,bbox_y_br\n"
        "001.png,01,0.001,10,50,40,50\n"
        "001.png,01,0.002,100,5,100,25\n"
        "001.png,01,0.003,100,50,100,50\n"
    )
    receipt = publisher.publish(
        PublicationRequest(task_id="collapsed", ground_truth=truth, predictions=predictions)
    )
    dataset = backend.load_dataset(receipt.dataset_name)
    sample = dataset[str(tmp_path / "001.png")]
    detections = sample[receipt.fields["predictions"]].detections
    assert [box.bounding_box for box in detections] == [
        [0.1, 1.0, 0.3, 0.0],
        [1.0, 0.1, 0.0, 0.4],
        [1.0, 1.0, 0.0, 0.0],
    ]
    assert [box.dm_index for box in detections] == [0, 1, 2]
    assert [box.confidence for box in detections] == [0.001, 0.002, 0.003]
    assert receipt.run_complete is True


def test_incomplete_import_is_repaired(
    tmp_path: Path, publisher: Any, backend: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = PublicationRequest(task_id="first", ground_truth=write_truth(tmp_path))
    original = backend.Dataset.add_sample
    attempts = 0

    def interrupted(dataset: Any, sample: Any, **kwargs: Any) -> Any:
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            raise RuntimeError("interrupted import")
        return original(dataset, sample, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(backend.Dataset, "add_sample", interrupted)
        with pytest.raises(RuntimeError, match="interrupted import"):
            publisher.publish(request)
    receipt = publisher.publish(request)
    dataset = backend.load_dataset(receipt.dataset_name)
    assert len(dataset) == 2
    assert dataset.info["cy_dataset"]["complete"] is True


def test_evaluated_fields_keep_exact_matches_and_scope(
    tmp_path: Path, publisher: Any, backend: Any
) -> None:
    from clearml_yolo.comparison.evaluation_payload import (
        EvaluationBox,
        EvaluationMatch,
        EvaluationPayload,
    )

    truth = write_truth(tmp_path)
    payload = EvaluationPayload(
        split="val",
        image_names=["001.png"],
        thresholds={"01": 0.5},
        ground_truth=[
            EvaluationBox(
                index=0, image_name="001.png", label="01", box=(10, 5, 50, 25), status="TP"
            )
        ],
        predictions=[
            EvaluationBox(
                index=8,
                image_name="001.png",
                label="01",
                box=(10, 5, 50, 25),
                confidence=0.8,
                status="TP",
            )
        ],
        matches=[
            EvaluationMatch(
                gt_index=0,
                pred_index=8,
                gt_label="01",
                pred_label="01",
                confidence=0.8,
                iou=1.0,
                status="TP",
            )
        ],
    )
    path = tmp_path / "evaluation_val.json"
    path.write_text(payload.model_dump_json())
    receipt = publisher.publish(
        PublicationRequest(task_id="evaluation", ground_truth=truth, evaluations={"val": path})
    )
    assert receipt.dataset_complete is True
    assert receipt.run_complete is True
    assert receipt.payload_paths == {
        "ground_truth": truth.resolve(),
        "evaluation_val": path.resolve(),
    }
    assert receipt.published_at.utcoffset() is not None
    from clearml_yolo.publishing.models import PublicationReceipt

    assert PublicationReceipt.model_validate_json(receipt.model_dump_json()) == receipt
    dataset = backend.load_dataset(receipt.dataset_name)
    sample = dataset[str(tmp_path / "001.png")]
    box = sample[receipt.fields["matched_predictions"]].detections[0]
    assert box.dm_status == "TP"
    assert box.dm_index == 8
    assert box.dm_gt_indices == [0]
    assert box.dm_ious == [1.0]
    assert dataset.get_field(receipt.fields["matched_predictions"] + ".detections.dm_status")
    assert sample[receipt.fields["tp"]] == 1
    empty = dataset[str(tmp_path / "empty.png")]
    assert empty.split == "test"
    assert empty[receipt.fields["evaluated"]] is False
    assert empty[receipt.fields["tp"]] is None


def test_concurrent_runs_share_one_complete_dataset(
    tmp_path: Path, publisher: Any, backend: Any
) -> None:
    truth = write_truth(tmp_path)
    requests = [PublicationRequest(task_id=f"task-{i}", ground_truth=truth) for i in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(publisher.publish, requests))
    assert len({receipt.dataset_name for receipt in receipts}) == 1
    assert sum(not receipt.dataset_reused for receipt in receipts) == 1
    dataset = backend.load_dataset(receipts[0].dataset_name)
    dataset.reload()
    assert len(dataset) == 2
    assert len(dataset.info["cy_runs"]) == 4
    assert all(run["complete"] for run in dataset.info["cy_runs"].values())


def test_run_failure_marks_incomplete_then_retry_preserves_other_run(
    tmp_path: Path, publisher: Any, backend: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.publishing import fiftyone_adapter

    truth = write_truth(tmp_path)
    first = publisher.publish(PublicationRequest(task_id="first", ground_truth=truth))
    original = fiftyone_adapter._write_run

    def interrupted(*args: Any, **kwargs: Any) -> None:
        original(*args, **kwargs)
        raise RuntimeError("interrupted run")

    request = PublicationRequest(task_id="second", ground_truth=truth)
    with monkeypatch.context() as patch:
        patch.setattr(fiftyone_adapter, "_write_run", interrupted)
        with pytest.raises(RuntimeError, match="interrupted run"):
            publisher.publish(request)
    dataset = backend.load_dataset(first.dataset_name)
    dataset.reload()
    states = dataset.info["cy_runs"]
    assert states[first.run_key]["complete"] is True
    assert sum(run["complete"] is False for run in states.values()) == 1
    second = publisher.publish(request)
    dataset.reload()
    assert dataset.info["cy_runs"][first.run_key] == states[first.run_key]
    assert dataset.info["cy_runs"][second.run_key]["complete"] is True


def test_changed_csv_creates_new_dataset_and_preserves_original(
    tmp_path: Path, publisher: Any, backend: Any
) -> None:
    truth = write_truth(tmp_path)
    source = tmp_path / "original.csv"
    source.write_bytes(truth.read_bytes())
    first = publisher.publish(PublicationRequest(task_id="first", ground_truth=truth))
    truth.write_text(truth.read_text().replace(",val\n", ",train\n"))
    second = publisher.publish(
        PublicationRequest(task_id="second", ground_truth=truth, source_ground_truth=source)
    )
    assert second.dataset_name != first.dataset_name
    assert second.dataset_reused is False
    assert second.source_ground_truth_sha256 == first.ground_truth_sha256
    assert second.ground_truth_sha256 != first.ground_truth_sha256
    assert backend.load_dataset(first.dataset_name)[str(tmp_path / "001.png")].split == "val"
    assert backend.load_dataset(second.dataset_name)[str(tmp_path / "001.png")].split == "train"
