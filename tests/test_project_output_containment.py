"""Project adapter writes fail before touching external files or native runtimes."""

import importlib
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest

from clearml_yolo.core.export import ExportMetadata


@pytest.mark.parametrize("route", ["destination", "archive_leaf"])
def test_native_archive_rejects_external_destination_and_leaf_before_truncation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    from clearml_yolo.adapters.storage.native_archive import archive_native_outputs

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("CY_HOME", str(workspace))
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "native_outputs_candidate_test.zip"
    target.write_bytes(b"preserved external archive")
    destination = outside if route == "destination" else workspace
    if route == "archive_leaf":
        (workspace / target.name).symlink_to(target)
    with pytest.raises(ValueError, match="CY_HOME"):
        archive_native_outputs(tmp_path / "input", destination, role="candidate", split="test")
    assert target.read_bytes() == b"preserved external archive"
    assert list(outside.iterdir()) == [target]


@pytest.mark.parametrize(
    "operation", ["candidate", "reports", "comparison", "metadata", "engine", "onnx"]
)
def test_adapter_outputs_reject_external_routes_before_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    from clearml_yolo.adapters.export import build, metadata, onnx
    from clearml_yolo.adapters.reporting.comparison_workbook import write_comparison_workbook
    from clearml_yolo.adapters.reporting.evaluation_workbook import write_candidate_workbook
    from clearml_yolo.adapters.reporting.reports import build_reports

    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    output = tmp_path / "external" / "existing"
    output.parent.mkdir()
    output.write_bytes(b"preserve external file")

    def reject_native_import(name: str) -> None:
        raise AssertionError(f"Native import before output validation: {name}")

    if operation in {"engine", "onnx"}:
        monkeypatch.setattr(importlib, "import_module", reject_native_import)
    model_metadata = ExportMetadata.model_validate(
        {
            "descriptor": {
                "backend": "fasterrcnn",
                "preset": "resnet50_fpn",
                "class_names": ["object"],
                "preprocessing": {"resize": "letterbox", "size": [608, 960]},
                "checkpoint_sha256": "a" * 64,
            },
            "graph_sha256": "b" * 64,
        }
    )
    actions: dict[str, Callable[[], object]] = {
        "candidate": lambda: write_candidate_workbook(output, pd.DataFrame(), {}),
        "reports": lambda: build_reports(
            tmp_path / "input.xlsx", tmp_path / "baseline.xlsx", output, output, None
        ),
        "comparison": lambda: write_comparison_workbook(pd.DataFrame(), pd.DataFrame(), {}, output),
        "metadata": lambda: metadata.write_metadata(model_metadata, output),
        "engine": lambda: build.build_engine(tmp_path / "input.onnx", output),
        "onnx": lambda: onnx.export_onnx(object(), output),
    }
    with pytest.raises(ValueError, match="CY_HOME"):
        actions[operation]()
    assert output.read_bytes() == b"preserve external file"
    assert list(output.parent.iterdir()) == [output]


def test_prediction_provenance_rejects_external_sibling_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.clearml.results import write_prediction_provenance

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("CY_HOME", str(workspace))
    predictions = workspace / "predictions.csv"
    predictions.write_text("image_name\nimage.jpg\n")
    outside = tmp_path / "outside.json"
    outside.write_text("preserved")
    predictions.with_suffix(".csv.provenance.json").symlink_to(outside)
    with pytest.raises(ValueError, match="CY_HOME"):
        write_prediction_provenance(predictions, tmp_path / "input.pt")
    assert outside.read_text() == "preserved"


def test_result_csv_ignores_preexisting_pending_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.clearml.results import _atomic_csv

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("CY_HOME", str(workspace))
    outside = tmp_path / "outside.csv"
    outside.write_text("preserved")
    output = workspace / "predictions.csv"
    pending = output.with_suffix(".pending")
    pending.symlink_to(outside)
    _atomic_csv(pd.DataFrame({"x": [1]}), output)
    assert outside.read_text() == "preserved"
    assert not output.is_symlink()
    assert output.read_text() == "x\n1\n"
    assert pending.is_symlink()


@pytest.mark.parametrize("operation", ["yaml", "manifest"])
def test_native_generated_leaf_rejects_external_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    from clearml_yolo.adapters.yolo.config import write_native_yaml
    from clearml_yolo.adapters.yolo.inference import _write_manifest

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("CY_HOME", str(workspace))
    outside = tmp_path / "outside"
    outside.write_text("preserved")
    output = workspace / ("native.yaml" if operation == "yaml" else "images.txt")
    output.symlink_to(outside)
    actions: dict[str, Callable[[], object]] = {
        "yaml": lambda: write_native_yaml(output, {}, "train"),
        "manifest": lambda: _write_manifest(["input.jpg"], workspace),
    }
    with pytest.raises(ValueError, match="CY_HOME"):
        actions[operation]()
    assert outside.read_text() == "preserved"
