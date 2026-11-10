"""Training lookup consumes editable values without measurement compatibility gates."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from loguru import logger

from clearml_yolo.adapters.integrations.batch_lookup import resolve_batch_estimate
from clearml_yolo.adapters.integrations.batch_resolution import batch_provenance
from clearml_yolo.adapters.storage.batch_estimates import FileBatchEstimateStore
from clearml_yolo.adapters.storage.batch_sizes import BatchSizeStore
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.batch_estimation import GPUHardware, select_models
from test_batch_estimate_workflow import sample_case

GIB = 1024**3


def _dataset(tmp_path: Path, **updates: Any) -> PreparedDataset:
    manifest = tmp_path / "preparation.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "class_names": {0: "cat", 1: "dog"},
                "images": [
                    {"split": "train", "boxes": 10, "image_name": "training.png"},
                    {"split": "val", "boxes": 300},
                    {"split": "test", "boxes": 1000},
                ],
            }
            | updates
        )
    )
    return PreparedDataset(
        data=tmp_path / "dataset.yaml",
        ground_truth=tmp_path / "ground-truth.csv",
        manifest=manifest,
        dataset_format="ndjson",
        artifacts=[],
    )


def test_manual_positive_batch_and_source_provenance(tmp_path: Path) -> None:
    path = tmp_path / "batch-sizes.yaml"
    path.write_text('"GPU [24 GiB]":\n  960:\n    ultralytics/yolo11n: 3\n')
    gpu = GPUHardware(name="GPU", total_memory_bytes=24 * GIB)
    result = resolve_batch_estimate(select_models(("yolo11n",))[0], 960, (gpu,), BatchSizeStore(path))
    assert result.global_batch == result.per_gpu_batch == 3
    assert result.table_digest == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result.model == "ultralytics/yolo11n"
    assert result.image_size == 960
    assert result.selections[0].entry.gpu_name == "GPU"
    assert not result.selections[0].fallback


def test_mixed_gpu_lookup_uses_smallest_individually_resolved_batch_and_warns(tmp_path: Path) -> None:
    path = tmp_path / "batch-sizes.yaml"
    path.write_text(
        '"GPU [24 GiB]":\n  960:\n    ultralytics/yolo11n: 7\n"Smaller [16 GiB]":\n  960:\n    ultralytics/yolo11n: 3\n'
    )
    messages: list[str] = []
    sink = logger.add(lambda message: messages.append(str(message)))
    try:
        result = resolve_batch_estimate(
            select_models(("yolo11n",))[0],
            960,
            (
                GPUHardware(name="GPU", total_memory_bytes=24 * GIB),
                GPUHardware(name="New GPU", total_memory_bytes=20 * GIB),
            ),
            BatchSizeStore(path),
            device_indices=(2, 0),
        )
    finally:
        logger.remove(sink)
    assert result.global_batch == 6
    provenance = batch_provenance(result)
    assert provenance["global_batch"] == 6
    assert provenance["per_gpu_batch"] == 3
    assert provenance["image_size"] == 960
    assert provenance["model"] == "ultralytics/yolo11n"
    assert provenance["table_digest"] == hashlib.sha256(path.read_bytes()).hexdigest()
    sources = provenance["selected_entries"]
    assert [source["resolved_per_gpu_batch"] for source in sources] == [7, 3]
    assert [source["fallback"] for source in sources] == [False, True]
    assert [source["entry"]["gpu_name"] for source in sources] == ["GPU", "Smaller"]
    assert [source["entry"]["total_memory_bytes"] for source in sources] == [24 * GIB, 16 * GIB]
    assert [source["target_gpu"]["name"] for source in sources] == ["GPU", "New GPU"]
    assert [source["target_gpu"]["total_memory_bytes"] for source in sources] == [24 * GIB, 20 * GIB]
    assert all(source["entry"]["origin"] == "manual" for source in sources)
    assert [selection.per_gpu_batch for selection in result.selections] == [7, 3]
    assert [selection.fallback for selection in result.selections] == [False, True]
    assert len(messages) == 1
    assert "Smaller [16 GiB]" in messages[0]
    assert "cy-batch-estimate --imgsz 960 --models ultralytics/yolo11n" in messages[0]
    assert "New GPU" in messages[0]
    assert "--devices 0 --gpu-counts 1" in messages[0]


def test_missing_table_never_silently_uses_json_evidence(tmp_path: Path) -> None:
    case = sample_case()
    FileBatchEstimateStore(tmp_path / "batch-estimates.json").save(case)
    with pytest.raises(ValueError, match="explicit training batch"):
        resolve_batch_estimate(
            case.profile.model, 960, case.profile.gpus, BatchSizeStore(tmp_path / "batch-sizes.yaml")
        )


@pytest.mark.parametrize("fallback", [False, True])
def test_forced_source_warning_and_provenance_survive_table_reuse(tmp_path: Path, fallback: bool) -> None:
    case = sample_case()
    case = case.model_copy(update={"settings": case.settings.model_copy(update={"force": True})})
    store = BatchSizeStore(tmp_path / "batch-sizes.yaml")
    store.publish((case,))
    gpu = case.profile.gpus[0]
    if fallback:
        gpu = gpu.model_copy(update={"name": "Other GPU"})
    messages: list[str] = []
    sink = logger.add(lambda message: messages.append(str(message)))
    try:
        result = resolve_batch_estimate(case.profile.model, 960, (gpu,), store)
    finally:
        logger.remove(sink)
    assert any("forced/background-sensitive" in message for message in messages)
    source = batch_provenance(result)["selected_entries"][0]
    assert source["entry"]["forced"] is True
    assert source["fallback"] is fallback
