"""Hydra injects capabilities only at invocation, outside the command schema."""

import inspect
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path

import pytest
from omegaconf import OmegaConf

from clearml_yolo.adapters.storage import dataset_cache
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.core.models import model_preset
from clearml_yolo.entrypoints import composition
from clearml_yolo.entrypoints.hydra.common import _execute_direct
from clearml_yolo.entrypoints.hydra.validation import validate_wrapper_keys
from workflow_dependencies import workflow_dependencies as workflow_dependencies  # noqa: PLC0414


def test_command_invocation_injects_bundle_without_changing_serializable_function(
    monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    observed: list[tuple[int, WorkflowDependencies]] = []

    def workflow(value: int, *, deps: WorkflowDependencies) -> None:
        observed.append((value, deps))

    original_signature = inspect.signature(workflow)
    monkeypatch.setattr(composition, "build_dependencies", lambda: workflow_dependencies)
    _execute_direct("metrics", OmegaConf.create({"value": 7}), workflow)

    assert observed == [(7, workflow_dependencies)]
    assert inspect.signature(workflow) == original_signature
    assert workflow.__module__ == __name__


def test_capabilities_cannot_be_supplied_as_a_hydra_override() -> None:
    def workflow(value: int, *, deps: WorkflowDependencies) -> None:
        pass

    with pytest.raises(ValueError, match=r"Unsupported wrapper settings.*deps"):
        validate_wrapper_keys(OmegaConf.create({"value": 7, "deps": {}}), workflow)


def test_ultralytics_dataset_store_refuses_the_coco_copy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[object, ...]] = []
    prepared_context: AbstractContextManager[PreparedDataset] = nullcontext()  # type: ignore[assignment]  # never entered

    def cached(*args: object, **kwargs: object) -> AbstractContextManager[PreparedDataset]:
        calls.append((*args, kwargs))
        return prepared_context

    monkeypatch.setattr(dataset_cache, "cached_dataset", cached)
    store = composition.build_dependencies().dataset
    with pytest.raises(ValueError, match="Ultralytics training requires ndjson or flat dataset_format"):
        store.cached_dataset(tmp_path / "truth.csv", tmp_path / "cache", "coco", required_splits=("val",))
    assert calls == []
    prepared = store.cached_dataset(tmp_path / "truth.csv", tmp_path / "cache", "flat", required_splits=("val",))
    assert prepared is prepared_context
    assert calls == [(tmp_path / "truth.csv", tmp_path / "cache", "flat", {"required_splits": ("val",)})]


def test_detector_dataset_store_always_prepares_the_coco_copy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        dataset_cache,
        "cached_dataset",
        lambda *args, **kwargs: calls.append((*args, kwargs)),
    )
    store = composition.build_dependencies(model_preset("rfdetr/small")).dataset
    store.cached_dataset(tmp_path / "truth.csv", None, "flat")
    assert calls == [(tmp_path / "truth.csv", None, "coco", {"required_splits": ("train", "val")})]
