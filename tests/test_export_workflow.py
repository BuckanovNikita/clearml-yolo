"""Export provenance, publication and corpus checks without model or GPU execution."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
from PIL import Image

from clearml_yolo.adapters.export.metadata import sha256, write_metadata
from clearml_yolo.adapters.export.verification import _corpus, _verify_corpus, verification_cases
from clearml_yolo.adapters.integrations.export_operations import DetectorExporter
from clearml_yolo.application.contracts import ClearMLConfig
from clearml_yolo.application.use_cases.export import export_model
from clearml_yolo.core.export import ExportMetadata
from clearml_yolo.core.export_requests import ExportRequest, ExportResult
from clearml_yolo.core.models import CheckpointDescriptor, Preprocessing, model_preset
from clearml_yolo.entrypoints.composition import build_dependencies


@pytest.mark.parametrize("passed", [True, False])
def test_verification_evidence_uploads_before_failed_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, passed: bool
) -> None:
    dependencies = build_dependencies(model_preset("fasterrcnn/resnet50_fpn"))
    checkpoint = tmp_path / "downloaded.pth"
    checkpoint.write_bytes(b"owned checkpoint")
    report = tmp_path / "report.json"
    report.write_text('{"passed": false}')
    task = SimpleNamespace(id="export-owner")
    calls: list[tuple[str, Any]] = []
    configurations: list[dict[str, Any]] = []

    def init_task(config: ClearMLConfig, *, stage: str) -> Any:
        calls.append((stage, config.project_name))
        return task

    def record(owner: Any, payload: dict[str, Any]) -> None:
        assert owner is task
        configurations.append(payload)

    def upload(owner: Any, name: str, path: Path) -> None:
        assert owner is task
        assert path.is_file()
        calls.append(("upload", name))

    class Exporter:
        def execute(self, request: ExportRequest, destination: Path) -> ExportResult:
            assert destination == tmp_path / "output"
            assert destination.is_dir()
            assert request.weights == checkpoint
            return ExportResult(
                artifacts={"export_verification": report},
                evidence={"operation": "verify", "passed": passed},
                passed=passed,
            )

    dependencies = replace(dependencies, exporter=Exporter())
    monkeypatch.setattr(dependencies.tracking, "init_task", init_task)
    monkeypatch.setattr(dependencies.tracking, "record_run_configuration", record)
    monkeypatch.setattr(dependencies.tracking, "upload_artifact", upload)
    monkeypatch.setattr(
        dependencies.tracking,
        "expect_artifacts",
        lambda owner, names: calls.append(("expect", names)),
    )
    monkeypatch.setattr(
        dependencies.repository, "resolve_weights_with_identity", lambda weights: (checkpoint, None)
    )
    arguments: dict[str, Any] = {
        "export": {"operation": "verify", "device": 0, "engine": tmp_path / "model.engine"},
        "clearml": ClearMLConfig(project_name="export-tests"),
        "output_dir": tmp_path / "output",
        "weights": "remote-checkpoint-id",
        "ground_truth": tmp_path / "truth.csv",
        "deps": dependencies,
    }
    if passed:
        assert export_model(**arguments).passed
    else:
        with pytest.raises(ValueError, match="verification failed"):
            export_model(**arguments)
    assert calls == [
        ("export", "export-tests"),
        ("expect", ["export_verification"]),
        ("upload", "export_verification"),
    ]
    assert configurations == [
        {"source_model": {"checkpoint_sha256": sha256(checkpoint)}},
        {"export_result": {"operation": "verify", "passed": passed}},
    ]


def test_missing_inputs_fail_before_task_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dependencies = build_dependencies(model_preset("fasterrcnn/resnet50_fpn"))
    monkeypatch.setattr(
        dependencies.tracking,
        "init_task",
        lambda *args, **kwargs: pytest.fail("Input validation must precede task creation"),
    )
    with pytest.raises(ValueError, match="requires weights"):
        export_model({}, ClearMLConfig(), tmp_path, deps=dependencies)


def test_changed_graph_is_rejected_before_tensor_rt_loading(tmp_path: Path) -> None:
    graph = tmp_path / "model.onnx"
    graph.write_bytes(b"changed graph")
    descriptor = CheckpointDescriptor(
        backend="fasterrcnn",
        preset="resnet50_fpn",
        class_names=("thing",),
        preprocessing=Preprocessing(resize="letterbox", size=608),
        checkpoint_sha256="a" * 64,
    )
    write_metadata(
        ExportMetadata(descriptor=descriptor, graph_sha256="b" * 64),
        graph.with_name(graph.name + ".json"),
    )
    exporter = DetectorExporter(model_preset("fasterrcnn/resnet50_fpn"))
    request = ExportRequest(operation="build", device=0, onnx=graph)
    with pytest.raises(ValueError, match="graph hash disagrees"):
        exporter.execute(request, tmp_path / "output")


@pytest.mark.parametrize("changed", ["image", "ground_truth"])
def test_quality_corpus_bytes_are_frozen_across_verification(tmp_path: Path, changed: str) -> None:
    image = tmp_path / "image.png"
    Image.new("RGB", (16, 12)).save(image)
    truth = tmp_path / "truth.csv"
    pd.DataFrame(
        [[image.name, str(image), "thing", 1, 2, 10, 9, "test"]],
        columns=[
            "image_name",
            "image_path",
            "instance_label",
            "bbox_x_tl",
            "bbox_y_tl",
            "bbox_x_br",
            "bbox_y_br",
            "split",
        ],
    ).to_csv(truth, index=False)
    request = ExportRequest(
        operation="verify",
        device=0,
        weights=tmp_path / "best.pth",
        engine=tmp_path / "model.engine",
        ground_truth=truth,
    )
    images, manifest = _corpus(request, tmp_path)
    assert len(images) == 1
    _verify_corpus(request, manifest)
    if changed == "image":
        Image.new("RGB", (16, 12), color="white").save(image)
    else:
        truth.write_text(truth.read_text().replace("thing", "other"))
    with pytest.raises(ValueError, match="changed during verification"):
        _verify_corpus(request, manifest)


def test_verification_covers_contract_endpoints_and_profile_switches() -> None:
    cases = verification_cases()
    assert set(cases[:16]) == {
        (batch, height, width)
        for batch in (1, 2, 3, 4)
        for height, width in ((608, 960), (736, 960), (128, 1536), (256, 1920))
    }
    assert cases[16:] == tuple(
        case for batch in (1, 2, 4) for case in ((batch, 672, 960), (batch, 192, 1728))
    )
