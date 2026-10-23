"""Dataset references preserve CSV provenance without changing local input semantics."""

import hashlib
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import store
from pydantic import ValidationError

from clearml_yolo.application.contracts import ClearMLDatasetRef, ResolvedGroundTruth
from clearml_yolo.application.ground_truth import normalize_ground_truth, resolve_ground_truth
from clearml_yolo.application.ports import WorkflowDependencies
from workflow_dependencies import (
    workflow_dependencies as workflow_dependencies,  # noqa: PLC0414 - fixture export
)


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"dataset_id": ""},
        {"project_name": "p"},
        {"name": "n"},
        {"dataset_id": "id", "name": "n"},
        {"dataset_id": "id", "version": "1.0"},
        {"project_name": "p", "name": " "},
        {"project_name": "p", "name": "n", "version": 1.2},
        {"dataset_id": "id", "filename": "other.csv"},
    ],
)
def test_invalid_references_fail_before_effects(value: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        normalize_ground_truth(value)


@pytest.mark.parametrize(
    "value", [{"dataset_id": "id"}, {"project_name": "p", "name": "n", "version": "1.2.0"}]
)
def test_reference_mapping_becomes_typed_request(value: dict[str, str]) -> None:
    assert normalize_ground_truth(value) == ClearMLDatasetRef(**value)


def test_local_warning_only_at_original_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    warnings: list[tuple[Any, ...]] = []
    monkeypatch.setattr(workflow_dependencies.resources, "log", lambda *args: warnings.append(args))
    monkeypatch.setattr(
        workflow_dependencies.ground_truth_repository,
        "resolve",
        lambda _: pytest.fail("local path triggered dataset lookup"),
    )
    source = tmp_path / "original.csv"
    original = resolve_ground_truth(source, task=None, deps=workflow_dependencies)
    assert original.path == source
    derived = replace(original, path=tmp_path / "cleaned.csv")
    assert resolve_ground_truth(derived, task=None, deps=workflow_dependencies) is derived
    assert len(warnings) == 1
    assert warnings[0][0] == "WARNING"
    assert "ClearML" in warnings[0][1]


def test_legacy_dependency_constructor_keeps_local_input_support(
    workflow_dependencies: WorkflowDependencies,
) -> None:
    existing_fields = (
        "dataset",
        "model",
        "repository",
        "evaluation",
        "evaluation_writer",
        "renderer",
        "storage",
        "resources",
        "tracking",
        "publisher_factory",
        "disabled_publisher",
        "exporter",
    )
    legacy = WorkflowDependencies(
        *(getattr(workflow_dependencies, name) for name in existing_fields)
    )
    assert legacy.ground_truth_repository is None
    assert resolve_ground_truth("local.csv", task=None, deps=legacy).path == Path("local.csv")
    with pytest.raises(ValueError, match="does not provide ClearML ground-truth resolution"):
        resolve_ground_truth({"dataset_id": "id"}, task=None, deps=legacy)


def test_remote_source_records_identity_and_preserves_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    resolved = ResolvedGroundTruth(
        path=tmp_path / "dataset.csv",
        dataset_id="exact-id",
        project_name="p",
        name="n",
        version="1.0.0",
        csv_sha256="digest",
    )
    calls: list[ClearMLDatasetRef] = []
    records: list[dict[str, Any]] = []

    def fetch(reference: ClearMLDatasetRef) -> ResolvedGroundTruth:
        calls.append(reference)
        return resolved

    monkeypatch.setattr(workflow_dependencies.ground_truth_repository, "resolve", fetch)
    monkeypatch.setattr(
        workflow_dependencies.tracking,
        "record_run_configuration",
        lambda task, values: records.append(values),
    )
    monkeypatch.setattr(
        workflow_dependencies.resources, "log", lambda *args: pytest.fail("remote source warning")
    )
    requested = {"project_name": "p", "name": "n"}
    result = resolve_ground_truth(
        requested, task=SimpleNamespace(id="task"), deps=workflow_dependencies
    )
    assert resolve_ground_truth(result, task=None, deps=workflow_dependencies) is result
    assert len(calls) == 1
    assert requested == {"project_name": "p", "name": "n"}
    assert records[0]["ground_truth_source"]["dataset_id"] == "exact-id"
    assert records[0]["ground_truth_source"]["csv_sha256"] == "digest"
    assert records[0]["ground_truth_source"]["requested"] == requested
    assert "ground_truth" not in records[0]


@pytest.mark.parametrize(
    ("reference", "selector"),
    [
        (ClearMLDatasetRef(dataset_id="id"), {"dataset_id": "id"}),
        (
            ClearMLDatasetRef(project_name="p", name="n", version="1.0.0"),
            {"dataset_project": "p", "dataset_name": "n", "dataset_version": "1.0.0"},
        ),
        (
            ClearMLDatasetRef(project_name="p", name="n"),
            {"dataset_project": "p", "dataset_name": "n"},
        ),
    ],
)
def test_adapter_downloads_root_csv_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reference: ClearMLDatasetRef,
    selector: dict[str, str],
) -> None:
    from clearml_yolo.adapters.clearml.datasets import ClearMLGroundTruthRepository

    content = b"image_name,image_path,instance_label\n001,../images/a.jpg,NA\n"
    csv = tmp_path / "dataset.csv"
    csv.write_bytes(content)
    downloads: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []

    def local_copy(**kwargs: Any) -> str:
        downloads.append(kwargs)
        return str(tmp_path)

    dataset = SimpleNamespace(
        id="id",
        project="p",
        name="n",
        version="1.0.0",
        is_final=lambda: True,
        list_files=lambda: ["dataset.csv"],
        get_local_copy=local_copy,
    )

    def get_dataset(**kwargs: Any) -> SimpleNamespace:
        queries.append(kwargs)
        return dataset

    monkeypatch.setitem(
        sys.modules,
        "clearml",
        SimpleNamespace(Dataset=SimpleNamespace(get=get_dataset)),
    )
    result = ClearMLGroundTruthRepository().resolve(reference)
    assert result.path == csv
    assert csv.read_bytes() == content
    assert result.csv_sha256 == hashlib.sha256(content).hexdigest()
    assert queries == [selector | {"only_completed": True, "auto_create": False}]
    assert downloads == [
        {"files": ["dataset.csv"], "raise_on_error": True, "use_soft_links": False}
    ]


@pytest.mark.parametrize(
    ("final", "files"),
    [
        (False, ["dataset.csv"]),
        (True, ["nested/dataset.csv"]),
        (True, ["dataset.csv", "images/a.jpg"]),
        (True, ["dataset.csv", "notes.txt"]),
    ],
)
def test_invalid_dataset_inventory_or_state_fails_before_download(
    monkeypatch: pytest.MonkeyPatch,
    final: bool,
    files: list[str],
) -> None:
    from clearml_yolo.adapters.clearml.datasets import ClearMLGroundTruthRepository

    dataset = SimpleNamespace(
        is_final=lambda: final,
        list_files=lambda: files,
        get_local_copy=lambda **_: pytest.fail("invalid dataset downloaded"),
    )
    monkeypatch.setitem(
        sys.modules, "clearml", SimpleNamespace(Dataset=SimpleNamespace(get=lambda **_: dataset))
    )
    with pytest.raises((ValueError, FileNotFoundError)):
        ClearMLGroundTruthRepository().resolve(ClearMLDatasetRef(dataset_id="id"))


@pytest.mark.parametrize(
    "command", ["train", "predict", "val", "metrics", "compare", "pipeline", "export"]
)
def test_hydra_accepts_reference_without_sdk_resolution(command: str) -> None:
    # Import the command registrations explicitly so this file also runs standalone.
    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name=command, overrides=["ground_truth={dataset_id:id}"])
    assert normalize_ground_truth(config.ground_truth) == ClearMLDatasetRef(dataset_id="id")


def test_download_failure_preserves_cause(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.adapters.clearml.datasets import ClearMLGroundTruthRepository

    def failed_download(**_: object) -> str:
        raise OSError("fixture download failed")

    dataset = SimpleNamespace(
        is_final=lambda: True,
        list_files=lambda: ["dataset.csv"],
        get_local_copy=failed_download,
    )
    monkeypatch.setitem(
        sys.modules, "clearml", SimpleNamespace(Dataset=SimpleNamespace(get=lambda **_: dataset))
    )
    with pytest.raises(OSError, match="fixture download failed"):
        ClearMLGroundTruthRepository().resolve(ClearMLDatasetRef(dataset_id="id"))


@pytest.mark.parametrize("ground_truth", [None, {"dataset_id": "id"}])
def test_export_missing_weights_precedes_task_and_dataset_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ground_truth: dict[str, str] | None,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    from clearml_yolo.application.contracts import ClearMLConfig
    from clearml_yolo.application.use_cases.export import export_model

    monkeypatch.setattr(
        workflow_dependencies.tracking,
        "init_task",
        lambda *args, **kwargs: pytest.fail("Invalid export created a task"),
    )
    monkeypatch.setattr(
        workflow_dependencies.ground_truth_repository,
        "resolve",
        lambda *args: pytest.fail("Invalid export fetched a dataset"),
    )
    with pytest.raises(ValueError, match="requires weights"):
        export_model(
            {}, ClearMLConfig(), tmp_path, ground_truth=ground_truth, deps=workflow_dependencies
        )
