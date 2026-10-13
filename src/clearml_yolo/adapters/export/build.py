"""TensorRT build boundary. Optional SDKs are loaded only when building."""

import importlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from clearml_yolo.adapters.export.metadata import sha256
from clearml_yolo.adapters.export.precision import fp16_weighted_graph
from clearml_yolo.adapters.export.runtime import cuda_runtime_version, initialize_cuda
from clearml_yolo.adapters.storage.filesystem import write_path
from clearml_yolo.core.export import DEFAULT_PROFILES, OptimizationProfile


@dataclass(frozen=True)
class EngineBuildResult:
    path: Path
    sha256: str
    runtime_versions: dict[str, str]
    plugins: tuple[str, ...]


def _plugin_graph(path: Path, precision: Literal["fp32", "fp16"] = "fp32") -> bytes:
    onnx = importlib.import_module("onnx")
    model = onnx.load(str(path))
    if precision == "fp16":
        fp16_weighted_graph(model, onnx)
    # The pip SDK lacks libnvinfer_vc_plugin.so used by its standard RoiAlign
    # importer. Select the same registered v2 plugin explicitly instead.
    for node in model.graph.node:
        if node.op_type != "RoiAlign":
            continue
        attrs = {a.name: onnx.helper.get_attribute_value(a) for a in node.attribute}
        node.op_type = "ROIAlign_TRT"
        node.domain = "trt.plugins"
        del node.attribute[:]
        attrs["coordinate_transformation_mode"] = int(
            attrs.get("coordinate_transformation_mode", b"half_pixel") == b"half_pixel"
        )
        attrs["mode"] = int(attrs.get("mode", b"avg") == b"avg")
        attrs["plugin_version"] = "2"
        node.attribute.extend(onnx.helper.make_attribute(k, v) for k, v in attrs.items())
    model.opset_import.append(onnx.helper.make_opsetid("trt.plugins", 1))
    return bytes(model.SerializeToString())


def _add_profiles(builder: Any, config: Any, profiles: tuple[OptimizationProfile, ...]) -> None:
    for profile in profiles:
        native = builder.create_optimization_profile()
        # The Python setter returns None on success and raises ValueError for
        # invalid bounds; unlike its C++ counterpart, it does not return a bool.
        native.set_shape("images", profile.minimum, profile.optimum, profile.maximum)
        sizes = tuple(
            (shape[0], 2) for shape in (profile.minimum, profile.optimum, profile.maximum)
        )
        native.set_shape("image_sizes", *sizes)
        if config.add_optimization_profile(native) < 0:
            raise RuntimeError("TensorRT rejected optimization profile")


def build_engine(
    onnx_path: Path,
    engine_path: Path,
    *,
    precision: Literal["fp32", "fp16"] = "fp32",
    device: int = 0,
    workspace_gib: float = 4,
    profiles: tuple[OptimizationProfile, ...] = DEFAULT_PROFILES,
) -> EngineBuildResult:
    engine_path = write_path(engine_path)
    if not math.isfinite(workspace_gib) or workspace_gib <= 0 or not profiles:
        raise ValueError("Build requires positive workspace and at least one profile")
    if precision not in ("fp32", "fp16"):
        raise ValueError("Unsupported TensorRT precision")
    if type(device) is not int or device < 0:
        raise ValueError("CUDA device must be a nonnegative integer index")
    trt: Any = importlib.import_module("tensorrt")
    if not trt.__version__.startswith("10.13.0."):
        raise RuntimeError(f"TensorRT 10.13.0 is required, got {trt.__version__}")
    cuda = initialize_cuda(device)
    logger = trt.Logger(trt.Logger.WARNING)
    if not trt.init_libnvinfer_plugins(logger, ""):
        raise RuntimeError("TensorRT could not initialize inference plugins")
    builder = trt.Builder(logger)
    flags = 1 << int(trt.NetworkDefinitionCreationFlag.STRONGLY_TYPED) if precision == "fp16" else 0
    network = builder.create_network(flags)
    parser = trt.OnnxParser(network, logger)
    if not parser.parse(_plugin_graph(onnx_path, precision)):
        errors = "\n".join(str(parser.get_error(i)) for i in range(parser.num_errors))
        raise RuntimeError(f"TensorRT could not parse the detector:\n{errors}")
    config = builder.create_builder_config()
    config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, int(workspace_gib * (1 << 30)))
    config.clear_flag(trt.BuilderFlag.TF32)
    _add_profiles(builder, config, profiles)
    serialized = builder.build_serialized_network(network, config)
    if serialized is None:
        raise RuntimeError("TensorRT engine build failed; inspect TensorRT diagnostics")
    engine_path.parent.mkdir(parents=True, exist_ok=True)
    engine_path.write_bytes(bytes(serialized))
    return EngineBuildResult(
        engine_path,
        sha256(engine_path),
        {"tensorrt": trt.__version__, "cuda_runtime": cuda_runtime_version(cuda)},
        ("ROIAlign_TRT:2",),
    )
