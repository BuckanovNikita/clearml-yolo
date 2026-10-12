"""Standalone NumPy/TensorRT inference, without Torch or ClearML imports."""

import ctypes
import ctypes.util
import hashlib
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from clearml_yolo.adapters.export.preprocessing import validate_detections
from clearml_yolo.core.export import ExportMetadata

_NCHW_RANK = 4
_RGB_CHANNELS = 3
_STRIDE = 32


def _cuda_runtime() -> Any:
    candidates: list[str] = []
    found = ctypes.util.find_library("cudart")
    if found:
        candidates.append(found)
    try:
        package = importlib.util.find_spec("nvidia.cuda_runtime")
    except ModuleNotFoundError:
        package = None
    if package is not None and package.submodule_search_locations:
        for location in package.submodule_search_locations:
            candidates.extend(str(p) for p in Path(location, "lib").glob("libcudart.so*"))
    candidates.extend(("libcudart.so.12", "libcudart.so.11.0"))
    for candidate in candidates:
        try:
            library = ctypes.CDLL(candidate)
            break
        except OSError:
            continue
    else:
        raise RuntimeError("CUDA runtime library libcudart is required for standalone inference")
    library.cudaMalloc.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_size_t]
    library.cudaFree.argtypes = [ctypes.c_void_p]
    library.cudaMemcpy.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    library.cudaSetDevice.argtypes = [ctypes.c_int]
    library.cudaRuntimeGetVersion.argtypes = [ctypes.POINTER(ctypes.c_int)]
    library.cudaStreamCreate.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    library.cudaStreamDestroy.argtypes = [ctypes.c_void_p]
    library.cudaStreamSynchronize.argtypes = [ctypes.c_void_p]
    return library


def _check(status: int) -> None:
    if status:
        raise RuntimeError(f"CUDA runtime operation failed with status {status}")


def initialize_cuda(device: int) -> Any:
    """Select the explicit visible CUDA index and return the opaque runtime handle."""
    if type(device) is not int or device < 0:
        raise ValueError("CUDA device must be a nonnegative integer index")
    cuda = _cuda_runtime()
    _check(cuda.cudaSetDevice(device))
    return cuda


def cuda_runtime_version(cuda: Any) -> str:
    version = ctypes.c_int()
    _check(cuda.cudaRuntimeGetVersion(ctypes.byref(version)))
    return str(version.value)


class TensorRTRunner:
    """Metadata-bound execution on an explicit index in CUDA_VISIBLE_DEVICES.

    Each call owns its allocations and stream. This object retains the SDK runtime,
    engine and execution context and must not be called concurrently. Scheduling is
    the caller's responsibility before construction; no Torch or ClearML is loaded.
    last_buffer_bytes counts successful I/O cudaMalloc requests in the last call.
    engine_context_bytes is the SDK's required context device memory, including all
    profiles at the engine's configured weight streaming budget. Neither is a GPU peak.
    """

    def __init__(self, engine_path: Path, metadata: ExportMetadata, *, device: int = 0) -> None:
        if type(device) is not int or device < 0:
            raise ValueError("CUDA device must be a nonnegative integer index")
        engine_bytes = engine_path.read_bytes()
        if (
            metadata.engine_sha256 is None
            or hashlib.sha256(engine_bytes).hexdigest() != metadata.engine_sha256
        ):
            raise ValueError("Engine SHA256 does not match export metadata")
        self.metadata = metadata
        self.device = device
        self.trt: Any = importlib.import_module("tensorrt")
        expected_version = metadata.runtime_versions.get("tensorrt")
        if (
            not self.trt.__version__.startswith("10.13.0.")
            or expected_version != self.trt.__version__
        ):
            raise RuntimeError("TensorRT version does not match the metadata's 10.13.0 runtime")
        self.logger = self.trt.Logger(self.trt.Logger.WARNING)
        if not self.trt.init_libnvinfer_plugins(self.logger, ""):
            raise RuntimeError("TensorRT could not initialize inference plugins")
        registry = self.trt.get_plugin_registry()
        required_plugins = ("ROIAlign_TRT:2",)
        if metadata.plugins != required_plugins:
            raise ValueError("Metadata must declare the required ROIAlign_TRT:2 plugin")
        if registry.get_creator("ROIAlign_TRT", "2", "") is None:
            raise RuntimeError("TensorRT ROIAlign_TRT:2 plugin is unavailable")
        self.cuda = initialize_cuda(device)
        expected_cuda = metadata.runtime_versions.get("cuda_runtime")
        if expected_cuda is not None and expected_cuda != cuda_runtime_version(self.cuda):
            raise RuntimeError("CUDA runtime version does not match export metadata")
        self.runtime = self.trt.Runtime(self.logger)
        self.engine = self.runtime.deserialize_cuda_engine(engine_bytes)
        if self.engine is None:
            raise RuntimeError("TensorRT could not deserialize engine")
        self._validate_engine()
        self.engine_context_bytes = int(self.engine.device_memory_size_v2)
        self.last_buffer_bytes = 0
        self.context = self.engine.create_execution_context()
        if self.context is None:
            raise RuntimeError("TensorRT could not create execution context")

    def _validate_engine(self) -> None:
        names = {self.engine.get_tensor_name(i) for i in range(self.engine.num_io_tensors)}
        if names != {"images", "image_sizes", "detections", "counts"}:
            raise ValueError(f"Unexpected detector engine I/O contract: {sorted(names)}")
        dtypes = {
            "images": np.float32,
            "image_sizes": np.int64,
            "detections": np.float32,
            "counts": np.int64,
        }
        for name, dtype in dtypes.items():
            if self.trt.nptype(self.engine.get_tensor_dtype(name)) != dtype:
                raise ValueError(f"Unexpected engine dtype for {name}")
            expected_mode = (
                self.trt.TensorIOMode.INPUT
                if name in self.metadata.input_names
                else self.trt.TensorIOMode.OUTPUT
            )
            if self.engine.get_tensor_mode(name) != expected_mode:
                raise ValueError(f"Unexpected engine I/O direction for {name}")
        if self.engine.num_optimization_profiles != len(self.metadata.profiles):
            raise ValueError("Engine optimization profiles do not match metadata")
        for index, profile in enumerate(self.metadata.profiles):
            shapes = (profile.minimum, profile.optimum, profile.maximum)
            actual = tuple(tuple(s) for s in self.engine.get_tensor_profile_shape("images", index))
            if actual != shapes:
                raise ValueError("Engine image profile does not match metadata")
            sizes = tuple((s[0], 2) for s in shapes)
            actual_sizes = tuple(
                tuple(s) for s in self.engine.get_tensor_profile_shape("image_sizes", index)
            )
            if actual_sizes != sizes:
                raise ValueError("Engine image_sizes profile does not match metadata")

    def _select_profile(self, images: NDArray[np.float32], image_sizes: NDArray[np.int64]) -> int:
        if (
            images.dtype != np.float32
            or images.ndim != _NCHW_RANK
            or images.shape[1] != _RGB_CHANNELS
        ):
            raise ValueError("images must be float32 RGB NCHW")
        if not np.isfinite(images).all() or any(d % _STRIDE for d in images.shape[2:]):
            raise ValueError("images must be finite with a stride32 canvas")
        if image_sizes.dtype != np.int64 or image_sizes.shape != (images.shape[0], 2):
            raise ValueError("image_sizes must be int64 [batch,2]")
        if np.any(image_sizes <= 0) or np.any(image_sizes > np.array(images.shape[2:])):
            raise ValueError("Valid image sizes must lie inside the canvas")
        for index, profile in enumerate(self.metadata.profiles):
            if profile.accepts(images.shape):
                return index
        raise ValueError(f"Input shape {images.shape} is outside the engine profiles")

    def _host_buffers(
        self, images: NDArray[np.float32], image_sizes: NDArray[np.int64]
    ) -> dict[str, Any]:
        for name, value in (("images", images), ("image_sizes", image_sizes)):
            if not self.context.set_input_shape(name, value.shape):
                raise RuntimeError(f"TensorRT rejected {name} shape")
        host: dict[str, Any] = {
            "images": np.ascontiguousarray(images),
            "image_sizes": np.ascontiguousarray(image_sizes),
        }
        expected = {
            "detections": (images.shape[0], self.metadata.inference.max_det, 6),
            "counts": (images.shape[0],),
        }
        for name, shape in expected.items():
            if tuple(self.context.get_tensor_shape(name)) != shape:
                raise RuntimeError(f"Unexpected output shape for {name}")
            host[name] = np.empty(shape, dtype=self.trt.nptype(self.engine.get_tensor_dtype(name)))
        return host

    def _allocate(
        self, host: dict[str, Any], allocated: list[ctypes.c_void_p]
    ) -> dict[str, ctypes.c_void_p]:
        addresses: dict[str, ctypes.c_void_p] = {}
        for name, value in host.items():
            pointer = ctypes.c_void_p()
            _check(self.cuda.cudaMalloc(ctypes.byref(pointer), value.nbytes))
            allocated.append(pointer)
            self.last_buffer_bytes += int(value.nbytes)
            addresses[name] = pointer
            if not self.context.set_tensor_address(name, pointer.value):
                raise RuntimeError(f"TensorRT rejected address for {name}")
            if name in self.metadata.input_names:
                _check(self.cuda.cudaMemcpy(pointer, value.ctypes.data, value.nbytes, 1))
        return addresses

    def _release(self, allocated: list[ctypes.c_void_p], stream: ctypes.c_void_p) -> None:
        errors = []
        status = self.cuda.cudaStreamSynchronize(stream)
        if status:
            errors.append(status)
        errors.extend(status for pointer in allocated if (status := self.cuda.cudaFree(pointer)))
        status = self.cuda.cudaStreamDestroy(stream)
        if status:
            errors.append(status)
        if errors:
            message = f"CUDA resource cleanup failed with statuses {errors}"
            failure = sys.exception()
            if failure is not None:
                failure.add_note(message)
            else:
                raise RuntimeError(message)

    def __call__(
        self, images: NDArray[np.float32], image_sizes: NDArray[np.int64]
    ) -> tuple[NDArray[np.float32], NDArray[np.int64]]:
        self.last_buffer_bytes = 0
        profile = self._select_profile(images, image_sizes)
        _check(self.cuda.cudaSetDevice(self.device))
        stream = ctypes.c_void_p()
        allocated: list[ctypes.c_void_p] = []
        _check(self.cuda.cudaStreamCreate(ctypes.byref(stream)))
        try:
            if not self.context.set_optimization_profile_async(profile, stream.value):
                raise RuntimeError("TensorRT profile selection failed")
            _check(self.cuda.cudaStreamSynchronize(stream))
            host = self._host_buffers(images, image_sizes)
            addresses = self._allocate(host, allocated)
            if not self.context.execute_async_v3(stream.value):
                raise RuntimeError("TensorRT execution failed")
            _check(self.cuda.cudaStreamSynchronize(stream))
            for name in self.metadata.output_names:
                value = host[name]
                _check(self.cuda.cudaMemcpy(value.ctypes.data, addresses[name], value.nbytes, 2))
            validate_detections(
                host["detections"],
                host["counts"],
                class_count=len(self.metadata.descriptor.class_names),
                image_sizes=image_sizes,
            )
            return host["detections"], host["counts"]
        finally:
            self._release(allocated, stream)
