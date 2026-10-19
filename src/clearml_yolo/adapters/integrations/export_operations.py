"""Compose optional detector/export adapters after command admission."""

from importlib.metadata import version
from pathlib import Path

from clearml_yolo.adapters.export.metadata import read_metadata, sha256, write_metadata
from clearml_yolo.adapters.fasterrcnn.configuration import validate_preprocessing
from clearml_yolo.adapters.storage.checkpoint import read_checkpoint_descriptor
from clearml_yolo.adapters.storage.filesystem import write_path
from clearml_yolo.application.ports import ArtifactReady
from clearml_yolo.core.export import ExportMetadata, InferencePolicy
from clearml_yolo.core.export_requests import ExportRequest, ExportResult, gpu_device_index
from clearml_yolo.core.models import ModelConfig


class DetectorExporter:
    def __init__(self, model: ModelConfig) -> None:
        self.model = model

    def execute(
        self,
        request: ExportRequest,
        destination: Path,
        *,
        artifact_ready: ArtifactReady | None = None,
    ) -> ExportResult:
        if self.model.backend != "fasterrcnn":
            raise ValueError("cy-export supports only Faster R-CNN models")
        destination = write_path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        if request.operation == "onnx":
            return self._onnx(request, destination, artifact_ready=artifact_ready)
        source = request.onnx if request.operation == "build" else request.engine
        if source is None:
            raise ValueError("Export operation requires its source artifact")
        metadata_path = request.metadata or source.with_name(source.name + ".json")
        metadata = read_metadata(metadata_path)
        if metadata.descriptor.preset != self.model.preset:
            raise ValueError("Selected preset disagrees with export metadata")
        validate_preprocessing(metadata.descriptor.preprocessing)
        if request.operation == "build":
            return self._build(request, destination, metadata, artifact_ready=artifact_ready)
        if request.precision != metadata.precision:
            raise ValueError("Requested verification precision disagrees with engine metadata")
        if request.weights is None:
            raise ValueError("Verification requires native weights")
        descriptor = read_checkpoint_descriptor(request.weights, expected=self.model)
        if descriptor != metadata.descriptor:
            raise ValueError("Verification checkpoint disagrees with export source descriptor")
        from clearml_yolo.adapters.export.verification import verify_engine

        return verify_engine(request, metadata, destination, artifact_ready=artifact_ready)

    def _onnx(
        self,
        request: ExportRequest,
        destination: Path,
        *,
        artifact_ready: ArtifactReady | None = None,
    ) -> ExportResult:
        if request.weights is None:
            raise ValueError("ONNX export requires weights")
        descriptor = read_checkpoint_descriptor(request.weights, expected=self.model)
        if descriptor is None:
            raise ValueError("ONNX export requires a checkpoint with a validated descriptor")
        validate_preprocessing(descriptor.preprocessing)
        from clearml_yolo.adapters.export.onnx import export_onnx
        from clearml_yolo.adapters.fasterrcnn.model import build_model, checkpoint_state

        policy = InferencePolicy(
            conf=self.model.predict.conf,
            iou=self.model.predict.iou,
            max_det=self.model.predict.max_det,
        )
        detector = build_model(
            descriptor.preset,
            len(descriptor.class_names),
            pretrained=False,
            image_size=(608, 960),
            score_thresh=policy.conf,
            nms_thresh=policy.iou,
            detections_per_img=policy.max_det,
        )
        detector.load_state_dict(checkpoint_state(request.weights), strict=True)
        graph = export_onnx(detector, destination / "model.onnx")
        if artifact_ready is not None:
            artifact_ready("export_onnx", graph.path)
        metadata = ExportMetadata(
            descriptor=descriptor,
            graph_sha256=sha256(graph.path),
            inference=policy,
            runtime_versions={
                name: version(name) for name in ("torch", "torchvision", "timm", "onnx")
            },
        )
        metadata_path = destination / "model.onnx.json"
        write_metadata(metadata, metadata_path)
        if artifact_ready is not None:
            artifact_ready("export_metadata", metadata_path)
        return ExportResult(
            artifacts={"export_onnx": graph.path, "export_metadata": metadata_path},
            evidence=metadata.model_dump(mode="json") | {"operation": "onnx"},
        )

    @staticmethod
    def _build(
        request: ExportRequest,
        destination: Path,
        metadata: ExportMetadata,
        *,
        artifact_ready: ArtifactReady | None = None,
    ) -> ExportResult:
        if request.onnx is None or sha256(request.onnx) != metadata.graph_sha256:
            raise ValueError("ONNX graph hash disagrees with export metadata")
        from clearml_yolo.adapters.export.build import build_engine

        built = build_engine(
            request.onnx,
            destination / "model.engine",
            precision=request.precision,
            workspace_gib=request.workspace_gib,
            profiles=metadata.profiles,
            device=gpu_device_index(request.device),
        )
        if artifact_ready is not None:
            artifact_ready("export_engine", built.path)
        bound = metadata.model_copy(
            update={
                "engine_sha256": built.sha256,
                "precision": request.precision,
                "runtime_versions": metadata.runtime_versions | built.runtime_versions,
                "plugins": built.plugins,
            }
        )
        metadata_path = destination / "model.engine.json"
        write_metadata(bound, metadata_path)
        if artifact_ready is not None:
            artifact_ready("export_metadata", metadata_path)
        return ExportResult(
            artifacts={"export_engine": built.path, "export_metadata": metadata_path},
            evidence=bound.model_dump(mode="json") | {"operation": "build"},
        )
