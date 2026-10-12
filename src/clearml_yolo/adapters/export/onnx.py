"""Dynamic detector ONNX export with optional SDK imports at execution only."""

import copy
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_MAX_BATCH = 4
_RGB_CHANNELS = 3
_STRIDE = 32


@dataclass(frozen=True)
class ONNXExportResult:
    """The portable graph contract; labels retain native foreground IDs starting at one."""

    path: Path
    sample_shape: tuple[int, int, int, int]
    opset: int = 17
    input_names: tuple[str, ...] = ("images", "image_sizes")
    output_names: tuple[str, ...] = ("detections", "counts")


def export_onnx(
    model: Any,
    destination: Path,
    sample_shape: tuple[int, int, int, int] = (1, 3, 608, 960),
) -> ONNXExportResult:
    """Export normalized, zero-padded RGB canvases and valid resized image sizes.

    RPN, proposal filtering, ROIAlign, box decoding and class-aware NMS stay inside
    the graph. All batch loops are replaced with tensors; no fixed batch is traced.
    The caller owns preprocessing and inverse coordinate scaling at the boundary.
    The source model, training mode and device remain unchanged.
    """
    batch, channels, height, width = sample_shape
    if not 1 <= batch <= _MAX_BATCH or channels != _RGB_CHANNELS or min(height, width) < _STRIDE:
        raise ValueError("Export requires batch 1-4, three RGB channels and dimensions >=32")
    if height % _STRIDE or width % _STRIDE:
        raise ValueError("Export canvas height and width must be divisible by 32")
    torch = importlib.import_module("torch")
    onnx = importlib.import_module("onnx")
    tensor_adapter = importlib.import_module("clearml_yolo.adapters.export.tensors")
    source = copy.deepcopy(model).cpu().float().eval()
    native_models = importlib.import_module("clearml_yolo.adapters.fasterrcnn.model")
    if (
        isinstance(source.backbone, native_models.FeaturePyramid)
        and source.backbone.preset == "dinov2_small"
    ):
        positions = importlib.import_module("clearml_yolo.adapters.export.positions")
        source.backbone.body = positions.ExportViTIntermediates(source.backbone.body)
    elif (
        isinstance(source.backbone, native_models.FeaturePyramid)
        and source.backbone.preset == "dinov3_small"
    ):
        positions = importlib.import_module("clearml_yolo.adapters.export.positions")
        if tuple(source.backbone.body.patch_embed.patch_size) != (16, 16):
            raise ValueError("DINOv3 export requires its native patch16 embedding")
        # Every admitted canvas is stride32, hence also patch16 divisible. Native
        # padding is a no-op here; disabling it avoids math.ceil in timm's dynamic
        # intermediate-grid reshape while preserving all permitted-input numerics.
        source.backbone.body.patch_embed.dynamic_img_pad = False
        source.backbone.body.rope = positions.ExportDinoRotary(source.backbone.body.rope)
    elif (
        isinstance(source.backbone, native_models.FeaturePyramid)
        and source.backbone.preset == "swin_tiny"
    ):
        swin = importlib.import_module("clearml_yolo.adapters.export.swin")
        swin.adapt_swin_blocks(source.backbone.body)
    adapter = tensor_adapter.TensorizedDetector(source).eval()
    images = torch.zeros(sample_shape, dtype=torch.float32)
    sizes = torch.tensor([[height, width]] * batch, dtype=torch.int64)
    destination.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        adapter,
        (images, sizes),
        str(destination),
        dynamo=False,
        opset_version=17,
        input_names=["images", "image_sizes"],
        output_names=["detections", "counts"],
        dynamic_axes={
            "images": {0: "batch", 2: "height", 3: "width"},
            "image_sizes": {0: "batch"},
            "detections": {0: "batch"},
            "counts": {0: "batch"},
        },
    )
    graph = onnx.load(str(destination))
    onnx.checker.check_model(graph)
    return ONNXExportResult(destination, sample_shape)
