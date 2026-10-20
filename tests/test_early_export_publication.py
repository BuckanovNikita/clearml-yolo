"""Completed export files publish before later work; partial reports remain local."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.adapters.export.metadata import sha256
from clearml_yolo.adapters.integrations import export_operations
from clearml_yolo.application.contracts import ClearMLConfig
from clearml_yolo.application.use_cases.export import export_model
from clearml_yolo.core.export import ExportMetadata
from clearml_yolo.core.export_requests import ExportRequest, ExportResult
from clearml_yolo.core.models import CheckpointDescriptor, Preprocessing, model_preset
from clearml_yolo.entrypoints.composition import build_dependencies

ArtifactReady = Callable[[str, Path], None]

def _metadata() -> ExportMetadata:
    return ExportMetadata(
        descriptor=CheckpointDescriptor(
            backend="fasterrcnn",
            preset="resnet50_fpn",
            class_names=("thing",),
            preprocessing=Preprocessing(resize="letterbox", size=608),
            checkpoint_sha256="a" * 64,
        ),
        graph_sha256="b" * 64,
    )


@pytest.mark.parametrize("later_failure", [False, True])
def test_complete_export_survives_later_producer_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, later_failure: bool
) -> None:
    dependencies = build_dependencies(model_preset("fasterrcnn/resnet50_fpn"))
    task = SimpleNamespace(id="export-owner")
    uploads: list[tuple[str, bytes]] = []
    monkeypatch.setattr(dependencies.tracking, "init_task", lambda *args, **kwargs: task)
    monkeypatch.setattr(dependencies.tracking, "record_run_configuration", lambda *args: {})
    monkeypatch.setattr(dependencies.tracking, "expect_artifacts", lambda *args: None)

    def upload(owner: Any, name: str, path: Path) -> None:
        assert owner is task
        uploads.append((name, path.read_bytes()))

    monkeypatch.setattr(dependencies.tracking, "upload_artifact", upload)

    class Exporter:
        def execute(
            self,
            request: ExportRequest,
            destination: Path,
            *,
            artifact_ready: ArtifactReady | None = None,
        ) -> ExportResult:
            assert request.operation == "build"
            assert artifact_ready is not None
            engine = destination / "model.engine"
            engine.write_bytes(b"complete engine")
            artifact_ready("export_engine", engine)
            assert uploads == [("export_engine", b"complete engine")]
            if later_failure:
                raise RuntimeError("metadata producer failed")
            metadata = destination / "model.engine.json"
            metadata.write_bytes(b"complete metadata")
            artifact_ready("export_metadata", metadata)
            return ExportResult(
                artifacts={"export_engine": engine, "export_metadata": metadata}, evidence={}
            )

    dependencies = replace(dependencies, exporter=Exporter())
    arguments = {
        "operation": "build", "device": 0, "onnx": tmp_path / "source.onnx",
    }
    if later_failure:
        with pytest.raises(RuntimeError, match="metadata producer failed"):
            export_model(arguments, ClearMLConfig(), tmp_path / "output", deps=dependencies)
        assert uploads == [("export_engine", b"complete engine")]
    else:
        export_model(arguments, ClearMLConfig(), tmp_path / "output", deps=dependencies)
        assert uploads == [
            ("export_engine", b"complete engine"), ("export_metadata", b"complete metadata"),
        ]


def test_engine_ready_callback_precedes_metadata_and_rejection_stops_producer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.export import build

    graph = tmp_path / "model.onnx"
    graph.write_bytes(b"source")
    metadata = _metadata().model_copy(update={"graph_sha256": sha256(graph)})
    events: list[str] = []

    def build_engine(source: Path, destination: Path, **kwargs: Any) -> Any:
        assert source == graph
        assert kwargs["device"] == 0
        destination.write_bytes(b"final engine")
        events.append("engine complete")
        return SimpleNamespace(
            path=destination, sha256="c" * 64, runtime_versions={}, plugins=(),
        )

    def write_metadata(value: ExportMetadata, destination: Path) -> None:
        assert value.engine_sha256 == "c" * 64
        events.append("metadata write")
        destination.write_text(value.model_dump_json(), encoding="utf-8")

    def ready(name: str, path: Path) -> None:
        assert path.is_file()
        events.append(name)

    monkeypatch.setattr(build, "build_engine", build_engine)
    monkeypatch.setattr(export_operations, "write_metadata", write_metadata)
    request = ExportRequest(operation="build", device=0, onnx=graph)
    result = export_operations.DetectorExporter._build(
        request, tmp_path, metadata, artifact_ready=ready
    )
    assert set(result.artifacts) == {"export_engine", "export_metadata"}
    assert events == ["engine complete", "export_engine", "metadata write", "export_metadata"]
    events.clear()

    def reject(name: str, path: Path) -> None:
        assert name == "export_engine"
        assert path.read_bytes() == b"final engine"
        raise RuntimeError("upload rejected")

    with pytest.raises(RuntimeError, match="upload rejected"):
        export_operations.DetectorExporter._build(
            request, tmp_path, metadata, artifact_ready=reject
        )
    assert events == ["engine complete"]


@pytest.mark.parametrize("fail_case", [False, True])
def test_verification_announces_corpus_then_only_complete_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_case: bool
) -> None:
    from clearml_yolo.adapters.export import verification
    from clearml_yolo.adapters.fasterrcnn import model

    manifest = tmp_path / "corpus.json"
    manifest.write_text('{"images": []}', encoding="utf-8")
    published: dict[str, bytes] = {}
    calls = 0

    class Detector:
        def load_state_dict(self, state: object, *, strict: bool) -> None:
            assert state == {}
            assert strict

        def to(self, device: object) -> "Detector":
            assert str(device) == "cuda:0"
            return self

        def float(self) -> "Detector":
            return self

        def eval(self) -> "Detector":
            return self

    def case(*args: object) -> dict[str, bool]:
        nonlocal calls
        assert args
        calls += 1
        assert published == {"export_corpus": manifest.read_bytes()}
        if fail_case and calls == 2:
            raise RuntimeError("case execution failed")
        return {"quality_passed": True, "preprocessing_passed": True}

    def ready(name: str, path: Path) -> None:
        assert name not in published
        published[name] = path.read_bytes()

    monkeypatch.setattr(verification, "_corpus", lambda *args: ([], manifest))
    monkeypatch.setattr(verification, "evaluator_identity", dict)
    monkeypatch.setattr(verification, "TensorRTRunner", lambda *args, **kwargs: object())
    monkeypatch.setattr(verification, "verification_cases", lambda: ((1, 608, 960), (2, 608, 960)))
    monkeypatch.setattr(verification, "_case", case)
    monkeypatch.setattr(verification, "_rejections", lambda *args: {"invalid": True})
    monkeypatch.setattr(verification, "_verify_corpus", lambda *args: None)
    monkeypatch.setattr(model, "build_model", lambda *args, **kwargs: Detector())
    monkeypatch.setattr(model, "checkpoint_state", lambda *args: {})
    request = ExportRequest(
        operation="verify", device=0, weights=tmp_path / "best.pth",
        engine=tmp_path / "model.engine", ground_truth=tmp_path / "truth.csv",
    )
    if fail_case:
        with pytest.raises(RuntimeError, match="case execution failed"):
            verification.verify_engine(request, _metadata(), tmp_path, artifact_ready=ready)
        assert set(published) == {"export_corpus"}
        assert (tmp_path / "verification.json").is_file()
    else:
        result = verification.verify_engine(request, _metadata(), tmp_path, artifact_ready=ready)
        assert result.passed
        assert len(result.evidence["cases"]) == 2
        assert set(published) == {"export_corpus", "export_verification"}
        assert published["export_verification"] == (tmp_path / "verification.json").read_bytes()
