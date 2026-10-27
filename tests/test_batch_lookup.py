"""Null-batch lookup uses prepared vocabulary and peak target density."""

import json
from pathlib import Path
from typing import Any

import pytest

from clearml_yolo.adapters.integrations.batch_lookup import dataset_workload, resolve_batch_estimate
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.batch_estimation import GPUHardware
from test_batch_estimate_workflow import MemoryStore, sample_case


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


def test_uses_maximum_train_and_validation_density(tmp_path: Path) -> None:
    case, store = sample_case(), MemoryStore()
    store.save(case)
    prepared = _dataset(tmp_path)
    bounds = dataset_workload(prepared)
    assert bounds.classes == 2
    assert bounds.objects_per_image == 300
    recommendation = resolve_batch_estimate(case.profile, prepared, store)
    assert recommendation.origin == "measured"
    assert recommendation.sources == (case,)
    assert recommendation.global_batch == case.global_batch


@pytest.mark.parametrize(
    "updates",
    [
        {"class_names": {index: str(index) for index in range(151)}},
        {"images": [{"split": "val", "boxes": 301}]},
    ],
)
def test_real_workload_exceeding_saved_bounds_stops_with_instructions(
    tmp_path: Path,
    updates: dict[str, Any],
) -> None:
    case, store = sample_case(), MemoryStore()
    store.save(case)
    with pytest.raises(
        ValueError, match=r"cy-batch-estimate --imgsz 960 --models ultralytics/yolo11n"
    ):
        resolve_batch_estimate(case.profile, _dataset(tmp_path, **updates), store)


def test_missing_and_incompatible_cache_never_fall_back(tmp_path: Path) -> None:
    case, store = sample_case(), MemoryStore()
    prepared = _dataset(tmp_path)
    with pytest.raises(ValueError, match="explicit training batch"):
        resolve_batch_estimate(case.profile, prepared, store)
    store.save(case)
    changed = case.profile.model_copy(update={"precision": "bf16"})
    with pytest.raises(ValueError, match="explicit training batch"):
        resolve_batch_estimate(changed, prepared, store)


@pytest.mark.parametrize(
    "updates",
    [
        {"class_names": {}},
        {"class_names": {1: "cat"}},
        {"images": []},
        {"images": [{"split": "train", "boxes": "300"}]},
        {"images": [{"split": "train", "boxes": -1}]},
        {"images": [{"split": "test", "boxes": 1}]},
    ],
)
def test_invalid_manifests_cannot_shrink_workload_bounds(
    tmp_path: Path, updates: dict[str, Any]
) -> None:
    with pytest.raises(ValueError, match=r"class_names|images|boxes|no training|identifiers"):
        dataset_workload(_dataset(tmp_path, **updates))


def test_background_subset_uses_minimum_positive_probe_bound(tmp_path: Path) -> None:
    prepared = _dataset(tmp_path, images=[{"split": "train", "boxes": 0}])
    assert dataset_workload(prepared).objects_per_image == 1


def test_failed_refresh_removes_source_from_extrapolated_lookup(tmp_path: Path) -> None:
    case, store = sample_case(), MemoryStore()
    store.save(case)
    target = case.profile.model_copy(
        update={
            "gpus": (
                GPUHardware(name="GPU", total_memory_bytes=1000, uuid="assigned-0"),
                GPUHardware(name="GPU", total_memory_bytes=1000, uuid="assigned-1"),
            )
        }
    )
    prepared = _dataset(tmp_path)
    assert resolve_batch_estimate(target, prepared, store).global_batch == 8
    store.save(
        case.model_copy(
            update={
                "status": "failed",
                "global_batch": None,
                "per_gpu_batch": None,
                "trials": (),
                "diagnostic": "refresh interrupted",
            }
        )
    )
    with pytest.raises(ValueError, match="explicit training batch"):
        resolve_batch_estimate(target, prepared, store)
