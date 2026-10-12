"""Inference export contracts: class separation, padding and native interpolation."""

import ctypes
import importlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
import torch


def test_export_package_is_lightweight() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json,sys; import clearml_yolo.adapters.export; "
                "import clearml_yolo.core.export; "
                "import clearml_yolo.adapters.export.build; "
                "import clearml_yolo.adapters.export.runtime; "
                "import clearml_yolo.adapters.export.preprocessing; "
                "print(json.dumps([n for n in ('torch','clearml','tensorrt') if n in sys.modules]))"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == []


def test_padded_nms_preserves_images_classes_and_empty_slots() -> None:
    tensors = importlib.import_module("clearml_yolo.adapters.export.tensors")
    boxes = torch.tensor(
        [
            [
                [[0.0, 0.0, 10.0, 10.0], [1.0, 1.0, 9.0, 9.0], [20.0, 20.0, 30.0, 30.0]],
                [[0.0, 0.0, 10.0, 10.0], [40.0, 40.0, 50.0, 50.0], [0.0, 0.0, 1.0, 1.0]],
            ],
            [
                [[0.0, 0.0, 10.0, 10.0], [1.0, 1.0, 9.0, 9.0], [20.0, 20.0, 30.0, 30.0]],
                [[0.0, 0.0, 10.0, 10.0], [40.0, 40.0, 50.0, 50.0], [0.0, 0.0, 1.0, 1.0]],
            ],
        ]
    )
    scores = torch.tensor(
        [[[0.9, 0.8, 0.6], [0.95, 0.7, -1.0]], [[-1.0, -1.0, -1.0], [-1.0, -1.0, -1.0]]]
    )
    actual_boxes, actual_scores, indices, counts = tensors.padded_nms(boxes, scores, 0.5, 5)
    assert counts.tolist() == [4, 0]
    assert actual_scores[0].tolist() == pytest.approx([0.95, 0.9, 0.7, 0.6, 0.0])
    assert indices[0, :4].tolist() == [3, 0, 4, 2]
    assert torch.count_nonzero(actual_boxes[1]) == 0
    assert torch.count_nonzero(actual_scores[1]) == 0


@pytest.mark.parametrize("size", [(44, 69), (53, 69), (10, 110), (19, 138)])
def test_antialiased_position_resize_matches_native(size: tuple[int, int]) -> None:
    position = importlib.import_module("clearml_yolo.adapters.export.positions")
    generator = torch.Generator().manual_seed(31)
    values = torch.randn((1, 4, 37, 37), generator=generator)
    actual = position.resize_bicubic_antialiased(values, size)
    expected = torch.nn.functional.interpolate(
        values,
        size=size,
        mode="bicubic",
        align_corners=False,
        antialias=True,
    )
    torch.testing.assert_close(actual, expected, atol=6e-6, rtol=6e-6)


def test_batch_clipping_uses_valid_image_sizes() -> None:
    tensors = importlib.import_module("clearml_yolo.adapters.export.tensors")
    boxes = torch.tensor([[[[-1.0, -2.0, 90.0, 80.0]]], [[[0.0, 0.0, 90.0, 80.0]]]])
    sizes = torch.tensor([[60, 40], [30, 70]], dtype=torch.int64)
    actual = tensors.clip_boxes(boxes, sizes)
    assert actual.tolist() == [[[[0.0, 0.0, 40.0, 60.0]]], [[[0.0, 0.0, 70.0, 30.0]]]]


def _metadata() -> Any:
    core = importlib.import_module("clearml_yolo.core.export")
    return core.ExportMetadata(
        descriptor={
            "backend": "fasterrcnn",
            "preset": "resnet50_fpn",
            "class_names": ("person", "bus"),
            "preprocessing": {"resize": "letterbox", "size": (608, 960)},
            "checkpoint_sha256": "a" * 64,
        },
        graph_sha256="b" * 64,
        inference={"conf": 0.05, "iou": 0.5, "max_det": 2},
        runtime_versions={"tensorrt": "10.13.0.35"},
        plugins=("ROIAlign_TRT:2",),
    )


@pytest.mark.parametrize(
    "shape",
    [
        (b, 3, h, w)
        for b in range(1, 5)
        for h, w in [(608, 960), (736, 960), (128, 1536), (256, 1920)]
    ],
)
def test_default_profiles_cover_required_shapes(shape: tuple[int, int, int, int]) -> None:
    profiles = importlib.import_module("clearml_yolo.core.export").DEFAULT_PROFILES
    assert any(profile.accepts(shape) for profile in profiles)
    assert not any(profile.accepts((1, 3, 608, 1920)) for profile in profiles)


def test_builder_accepts_python_profile_setter_returning_none() -> None:
    build = importlib.import_module("clearml_yolo.adapters.export.build")
    profiles = importlib.import_module("clearml_yolo.core.export").DEFAULT_PROFILES
    configured: list[dict[str, tuple[Any, ...]]] = []

    def create_profile() -> SimpleNamespace:
        shapes: dict[str, tuple[Any, ...]] = {}
        configured.append(shapes)

        def set_shape(name: str, *bounds: Any) -> None:
            shapes[name] = bounds

        return SimpleNamespace(set_shape=set_shape)

    added: list[Any] = []

    def add_profile(profile: Any) -> int:
        added.append(profile)
        return len(added) - 1

    build._add_profiles(
        SimpleNamespace(create_optimization_profile=create_profile),
        SimpleNamespace(add_optimization_profile=add_profile),
        profiles,
    )
    assert len(added) == len(profiles)
    for shapes, profile in zip(configured, profiles, strict=True):
        assert shapes == {
            "images": (profile.minimum, profile.optimum, profile.maximum),
            "image_sizes": ((1, 2), (2, 2), (4, 2)),
        }


@pytest.mark.parametrize(
    "bad", [(0, 3, 608, 960), (5, 3, 608, 960), (1, 4, 608, 960), (1, 3, 607, 960)]
)
def test_invalid_profiles_rejected(bad: tuple[int, int, int, int]) -> None:
    core = importlib.import_module("clearml_yolo.core.export")
    with pytest.raises(ValueError, match=r"Profile|profiles|channels"):
        core.OptimizationProfile(minimum=bad, optimum=bad, maximum=bad)


def test_metadata_roundtrip_and_hash_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helpers = importlib.import_module("clearml_yolo.adapters.export.metadata")
    runtime = importlib.import_module("clearml_yolo.adapters.export.runtime")
    path = tmp_path / "engine.bin"
    path.write_bytes(b"abc")
    assert (
        helpers.sha256(path) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    metadata = _metadata().model_copy(update={"engine_sha256": helpers.sha256(path)})
    sidecar = tmp_path / "metadata.json"
    helpers.write_metadata(metadata, sidecar)
    assert helpers.read_metadata(sidecar) == metadata
    path.write_bytes(b"altered")

    def unexpected_import(_name: str) -> Any:
        raise AssertionError("Hash mismatch must fail before importing the SDK")

    monkeypatch.setattr(runtime.importlib, "import_module", unexpected_import)
    with pytest.raises(ValueError, match="SHA256"):
        runtime.TensorRTRunner(path, metadata)


def test_runner_rejects_sdk_version_before_cuda(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helpers = importlib.import_module("clearml_yolo.adapters.export.metadata")
    runtime = importlib.import_module("clearml_yolo.adapters.export.runtime")
    path = tmp_path / "engine.bin"
    path.write_bytes(b"abc")
    metadata = _metadata().model_copy(update={"engine_sha256": helpers.sha256(path)})
    monkeypatch.setitem(sys.modules, "tensorrt", SimpleNamespace(__version__="10.14.0"))
    with pytest.raises(RuntimeError, match="version"):
        runtime.TensorRTRunner(path, metadata, device=2)


def test_numpy_letterbox_normalizes_before_resize_and_restores_boxes() -> None:
    portable = importlib.import_module("clearml_yolo.adapters.export.preprocessing")
    image = np.array([[[0, 127, 255], [255, 63, 0]]], dtype=np.uint8)
    actual, sizes = portable.preprocess([image], (32, 32))
    assert sizes.tolist() == [[16, 32]]
    assert actual.dtype == np.float32
    assert np.count_nonzero(actual[:, :, 16:]) == 0
    expected_first = (
        image[0, 0].astype(np.float32) / np.float32(255)
        - np.array([0.485, 0.456, 0.406], dtype=np.float32)
    ) / np.array([0.229, 0.224, 0.225], dtype=np.float32)
    np.testing.assert_allclose(actual[0, :, 0, 0], expected_first, atol=1e-6)
    detections = np.array([[[0, 0, 32, 16, 0.9, 2], [0, 0, 0, 0, 0, 0]]], dtype=np.float32)
    restored = portable.postprocess(
        detections, np.array([1], dtype=np.int64), [(1, 2)], sizes, class_count=2
    )
    np.testing.assert_allclose(restored[0], [[0, 0, 2, 1, 0.9, 1]])


def test_original_box_restoration_preserves_native_float32_rounding() -> None:
    portable = importlib.import_module("clearml_yolo.adapters.export.preprocessing")
    native = importlib.import_module("clearml_yolo.adapters.fasterrcnn.transform")
    detections = np.array([[[0, 0, 811, 608, 0.9, 1]]], dtype=np.float32)
    restored = portable.postprocess(
        detections,
        np.array([1], dtype=np.int64),
        [(480, 640)],
        np.array([[608, 811]], dtype=np.int64),
        class_count=1,
    )[0]
    expected = native.scale_boxes(torch.from_numpy(detections[0, :, :4]), (608, 811), (480, 640))
    np.testing.assert_array_equal(restored[:, :4], expected.numpy())
    # Both native and portable float32 scaling can place a boundary one ULP above it.
    assert restored[0, 3] == np.nextafter(np.float32(480), np.float32(np.inf))


@pytest.mark.parametrize(
    ("field", "value"), [(0, float("nan")), (4, 1.1), (5, 0), (5, 1.5), (5, 3)]
)
def test_invalid_exported_rows_rejected(field: int, value: float) -> None:
    portable = importlib.import_module("clearml_yolo.adapters.export.preprocessing")
    detections = np.array([[[0, 0, 10, 10, 0.9, 1]]], dtype=np.float32)
    detections[0, 0, field] = value
    with pytest.raises(ValueError, match=r"finite|confidences|labels"):
        portable.validate_detections(detections, np.array([1], dtype=np.int64), class_count=2)


def test_runner_failure_releases_all_allocations_and_selects_device() -> None:
    runtime = importlib.import_module("clearml_yolo.adapters.export.runtime")
    core = importlib.import_module("clearml_yolo.core.export")
    calls: list[tuple[str, Any]] = []

    class FakeCUDA:
        def cudaSetDevice(self, device: int) -> int:  # noqa: N802 - CUDA C API signature
            calls.append(("device", device))
            return 0

        def cudaStreamCreate(self, pointer: Any) -> int:  # noqa: N802
            ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p))[0] = 5
            return 0

        def cudaStreamSynchronize(self, _stream: Any) -> int:  # noqa: N802
            return 0

        def cudaMalloc(self, pointer: Any, size: int) -> int:  # noqa: N802
            ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p))[0] = 100 + size
            calls.append(("allocate", size))
            return 0

        def cudaMemcpy(self, *_args: Any) -> int:  # noqa: N802
            return 0

        def cudaFree(self, pointer: Any) -> int:  # noqa: N802
            calls.append(("free", pointer.value))
            return 0

        def cudaStreamDestroy(self, _stream: Any) -> int:  # noqa: N802
            calls.append(("destroy", None))
            return 0

    runner = runtime.TensorRTRunner.__new__(runtime.TensorRTRunner)
    tiny = core.OptimizationProfile(
        minimum=(1, 3, 32, 32), optimum=(1, 3, 32, 32), maximum=(1, 3, 32, 32)
    )
    runner.metadata = _metadata().model_copy(update={"profiles": (tiny,)})
    runner.device = 2
    runner.cuda = FakeCUDA()
    runner.trt = SimpleNamespace(nptype=lambda dtype: dtype)
    runner.engine = SimpleNamespace(
        get_tensor_dtype=lambda name: np.int64 if name == "counts" else np.float32
    )
    runner.context = SimpleNamespace(
        set_optimization_profile_async=lambda *_args: True,
        set_input_shape=lambda *_args: True,
        get_tensor_shape=lambda name: (1,) if name == "counts" else (1, 2, 6),
        set_tensor_address=lambda *_args: True,
        execute_async_v3=lambda _stream: False,
    )
    with pytest.raises(RuntimeError, match="execution failed"):
        runner(np.zeros((1, 3, 32, 32), dtype=np.float32), np.array([[16, 32]], dtype=np.int64))
    assert calls[0] == ("device", 2)
    assert len([call for call in calls if call[0] == "allocate"]) == 4
    assert len([call for call in calls if call[0] == "free"]) == 4
    assert calls[-1] == ("destroy", None)
    assert runner.last_buffer_bytes == (1 * 3 * 32 * 32 * 4) + (1 * 2 * 8) + (1 * 2 * 6 * 4) + 8


@pytest.mark.parametrize("shape", [(5, 7), (43, 19), (11, 1)])
def test_numpy_bilinear_math_matches_small_native_tensor(shape: tuple[int, int]) -> None:
    portable = importlib.import_module("clearml_yolo.adapters.export.preprocessing")
    image = np.random.default_rng(91).integers(0, 256, size=(*shape, 3), dtype=np.uint8)
    actual, sizes = portable.preprocess([image], (32, 64))
    raw = torch.from_numpy(image).permute(2, 0, 1).float() / 255
    mean = raw.new_tensor([0.485, 0.456, 0.406])[:, None, None]
    std = raw.new_tensor([0.229, 0.224, 0.225])[:, None, None]
    expected = torch.nn.functional.interpolate(
        ((raw - mean) / std)[None],
        size=tuple(sizes[0]),
        mode="bilinear",
        align_corners=False,
        antialias=False,
    )
    np.testing.assert_allclose(
        actual[:, :, : sizes[0, 0], : sizes[0, 1]], expected.numpy(), atol=1e-6, rtol=1e-6
    )


@pytest.mark.parametrize(
    "kwargs",
    [{"workspace_gib": 0}, {"workspace_gib": float("nan")}, {"profiles": ()}, {"device": -1}],
)
def test_build_invalid_controls_fail_before_sdk(
    kwargs: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build = importlib.import_module("clearml_yolo.adapters.export.build")

    def unexpected_import(_name: str) -> Any:
        raise AssertionError("Invalid controls must fail before SDK import")

    monkeypatch.setattr(build.importlib, "import_module", unexpected_import)
    with pytest.raises(ValueError, match=r"workspace|profile|device"):
        build.build_engine(tmp_path / "graph.onnx", tmp_path / "engine.bin", **kwargs)


def test_numpy_invalid_counts_and_padding_rejected() -> None:
    portable = importlib.import_module("clearml_yolo.adapters.export.preprocessing")
    rows = np.array([[[0, 0, 10, 10, 0.9, 1], [0, 0, 0, 0, 0, 0]]], dtype=np.float32)
    with pytest.raises(ValueError, match="counts"):
        portable.validate_detections(rows, np.array([3], dtype=np.int64))
    rows[0, 1, 4] = 0.1
    with pytest.raises(ValueError, match="padding"):
        portable.validate_detections(rows, np.array([1], dtype=np.int64))


def test_metadata_rejects_incompatible_normalization_contract() -> None:
    core = importlib.import_module("clearml_yolo.core.export")
    payload = _metadata().model_dump()
    payload["descriptor"]["preprocessing"]["std"] = (0, 0.224, 0.225)
    with pytest.raises(ValueError, match="deviations"):
        core.ExportMetadata.model_validate(payload)
    payload["descriptor"]["preprocessing"]["std"] = (0.229, 0.224, 0.225)
    payload["descriptor"]["preprocessing"]["resize"] = "stretch"
    with pytest.raises(ValueError, match="letterboxing"):
        core.ExportMetadata.model_validate(payload)


def test_runner_constructor_binds_profiles_device_and_context_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = importlib.import_module("clearml_yolo.adapters.export.runtime")
    helpers = importlib.import_module("clearml_yolo.adapters.export.metadata")
    engine_path = tmp_path / "engine.bin"
    engine_path.write_bytes(b"bound-engine")
    metadata = _metadata().model_copy(update={"engine_sha256": helpers.sha256(engine_path)})
    names = ("images", "image_sizes", "detections", "counts")
    profiles = metadata.profiles
    engine = SimpleNamespace(
        num_io_tensors=4,
        num_optimization_profiles=len(profiles),
        device_memory_size_v2=123456,
        get_tensor_name=lambda index: names[index],
        get_tensor_dtype=lambda name: np.int64 if name in ("image_sizes", "counts") else np.float32,
        get_tensor_mode=lambda name: "input" if name in ("images", "image_sizes") else "output",
        get_tensor_profile_shape=lambda name, index: tuple(
            shape if name == "images" else (shape[0], 2)
            for shape in (profiles[index].minimum, profiles[index].optimum, profiles[index].maximum)
        ),
        create_execution_context=object,
    )

    class FakeLogger:
        WARNING = 2

        def __init__(self, _level: int) -> None:
            pass

    sdk = SimpleNamespace(
        __version__="10.13.0.35",
        Logger=FakeLogger,
        init_libnvinfer_plugins=lambda *_args: True,
        get_plugin_registry=lambda: SimpleNamespace(get_creator=lambda *_args: object()),
        Runtime=lambda _logger: SimpleNamespace(deserialize_cuda_engine=lambda _data: engine),
        nptype=lambda dtype: dtype,
        TensorIOMode=SimpleNamespace(INPUT="input", OUTPUT="output"),
    )
    selected: list[int] = []

    def select(device: int) -> object:
        selected.append(device)
        return object()

    monkeypatch.setitem(sys.modules, "tensorrt", sdk)
    monkeypatch.setattr(runtime, "initialize_cuda", select)
    runner = runtime.TensorRTRunner(engine_path, metadata, device=2)
    assert selected == [2]
    assert runner.engine_context_bytes == 123456
    assert runner.last_buffer_bytes == 0


@pytest.mark.parametrize("shift", [(1, 1), (0, 1), (1, 0)])
def test_swin_tensor_mask_matches_native_region_goldens(shift: tuple[int, int]) -> None:
    swin = importlib.import_module("clearml_yolo.adapters.export.swin")
    native_regions = np.zeros((1, 4, 4, 1), dtype=np.float32)
    region = 0
    for height in (slice(0, -2), slice(-2, -shift[0]), slice(-shift[0], None)):
        for width in (slice(0, -2), slice(-2, -shift[1]), slice(-shift[1], None)):
            native_regions[:, height, width, :] = region
            region += 1
    windows = native_regions.reshape(1, 2, 2, 2, 2, 1).transpose(0, 1, 3, 2, 4, 5).reshape(4, 4)
    golden = np.where(windows[:, :, None] != windows[:, None, :], -100, 0).astype(np.float32)
    actual = swin.shifted_window_mask(torch.zeros((2, 4, 4, 3)), (2, 2), shift)
    assert actual is not None
    np.testing.assert_array_equal(actual.numpy(), golden)
    assert swin.shifted_window_mask(torch.zeros((1, 4, 4, 3)), (2, 2), (0, 0)) is None
