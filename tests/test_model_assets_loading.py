"""Asset selection uses native registries and local files retain native transformations."""

import importlib
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
import torch

from clearml_yolo.adapters.assets import execution, resolver, validation
from clearml_yolo.adapters.fasterrcnn import assets as fasterrcnn_assets
from clearml_yolo.adapters.rfdetr import assets as rfdetr_assets
from clearml_yolo.core.assets import AssetCache
from clearml_yolo.core.models import PRESETS, model_preset


def _safetensors_payload(header: dict[str, object], data: bytes = b"\x00" * 4) -> bytes:
    encoded = json.dumps(header).encode()
    return len(encoded).to_bytes(8, "little") + encoded + data


@pytest.mark.parametrize(
    ("header", "data"),
    [
        ({}, b""),
        ({"__metadata__": {"description": "no tensors"}}, b""),
        ({"x": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}}, b"\x00" * 3),
        ({"x": {"dtype": "invalid", "shape": [1], "data_offsets": [0, 4]}}, b"\x00" * 4),
        ({"x": {"dtype": "F32", "shape": [2], "data_offsets": [0, 4]}}, b"\x00" * 4),
        ({"x": {"dtype": "F32", "shape": [-1], "data_offsets": [0, 4]}}, b"\x00" * 4),
        (
            {
                "x": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]},
                "y": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]},
            },
            b"\x00" * 4,
        ),
    ],
    ids=["empty-map", "metadata-only", "truncated", "dtype", "shape", "negative", "overlap"],
)
def test_malformed_safetensors_use_asset_value_error_boundary(
    tmp_path: Path, header: dict[str, object], data: bytes
) -> None:
    path = tmp_path / "model.safetensors"
    path.write_bytes(_safetensors_payload(header, data))
    spec = fasterrcnn_assets.pretrained_asset("resnet50_fpn").model_copy(
        update={"filename": path.name, "checksum": None}
    )
    with pytest.raises(ValueError, match=r"[Ss]afetensors"):
        validation.validate_asset(path, spec)


def test_valid_zero_element_tensor_is_distinct_from_no_tensors(tmp_path: Path) -> None:
    path = tmp_path / "model.safetensors"
    path.write_bytes(
        _safetensors_payload({"x": {"dtype": "F32", "shape": [0], "data_offsets": [0, 0]}}, b"")
    )
    validation._safetensors(path)


def test_malformed_safetensors_cache_falls_through_to_valid_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path / "project"))
    cache = tmp_path / "model.safetensors"
    cache.write_bytes(
        _safetensors_payload({"x": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}})
    )
    spec = fasterrcnn_assets.pretrained_asset("resnet50_fpn").model_copy(
        update={
            "filename": cache.name,
            "checksum": None,
            "cache_candidates": (cache,),
            "native_cache": None,
        }
    )
    destination = resolver.asset_destination(spec)
    destination.parent.mkdir(parents=True)
    destination.write_bytes(
        _safetensors_payload({"x": {"dtype": "invalid", "shape": [1], "data_offsets": [0, 4]}})
    )
    monkeypatch.setattr(resolver, "_download", lambda *args: pytest.fail("valid offline cache"))

    record = resolver.resolve_asset(spec)

    assert record.path == cache
    assert destination.read_bytes() != cache.read_bytes(), "Invalid user cache remains untouched"


@pytest.fixture
def native_threads() -> Iterator[None]:
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        yield
    finally:
        torch.set_num_threads(previous)


@pytest.mark.parametrize("preset", PRESETS["fasterrcnn"])
def test_every_fasterrcnn_asset_is_the_selected_native_backbone(preset: str) -> None:
    spec = fasterrcnn_assets.pretrained_asset(preset)
    assert spec.canonical_url.startswith("https://")
    assert spec.override == "model.train.backbone_weights"
    assert spec.filename
    assert spec.revision
    if preset == "swin_tiny":
        assert spec.canonical_url == (
            "https://github.com/SwinTransformer/storage/releases/download/"
            "v1.0.0/swin_tiny_patch4_window7_224.pth"
        )
    elif preset == "dinov3_small":
        assert spec.canonical_url.startswith("https://huggingface.co/timm/")
        assert spec.access_requirement


@pytest.mark.parametrize("preset", PRESETS["rfdetr"])
def test_rf_registry_supplies_full_native_weights_with_checksum(preset: str) -> None:
    spec = rfdetr_assets.pretrained_asset(preset)
    assert spec.canonical_url.startswith("https://storage.googleapis.com/rfdetr/")
    assert spec.checksum_algorithm == "md5"
    assert spec.checksum is not None
    assert len(spec.checksum) == 32
    assert spec.override == "model.train.weights"


@pytest.mark.usefixtures("native_threads")
@pytest.mark.parametrize("preset", PRESETS["fasterrcnn"])
def test_native_backbones_load_local_files_without_downloading(
    preset: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.fasterrcnn.model import FeaturePyramid, _resnet_backbone

    if preset.endswith("_fpn"):
        models = importlib.import_module("torchvision.models")
        native = getattr(models, preset.removesuffix("_fpn"))(weights=None)
    else:
        timm = importlib.import_module("timm")
        native = timm.create_model(fasterrcnn_assets.TIMM_MODELS[preset], pretrained=False)
    first = next(native.parameters())
    with torch.no_grad():
        first.fill_(0.125)
    expected = first.detach().clone()
    path = tmp_path / "native.pth"
    torch.save(native.state_dict(), path)
    del native
    hub = importlib.import_module("torch.hub")
    monkeypatch.setattr(
        hub, "download_url_to_file", lambda *args, **kwargs: pytest.fail("native network download")
    )
    if preset.endswith("_fpn"):
        actual = _resnet_backbone(preset, pretrained=True, weights=path).body
    else:
        actual = FeaturePyramid(preset, pretrained=True, weights=path).body
    assert torch.equal(next(actual.parameters()).detach(), expected)


@pytest.mark.parametrize("selection", ["rfdetr/nano", "fasterrcnn/swin_tiny"])
def test_explicit_weights_and_nontraining_never_resolve_pretrained(
    selection: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = model_preset(selection)
    monkeypatch.setattr(
        execution,
        "resolve_assets",
        lambda specs: () if not specs else pytest.fail("unexpected asset request"),
    )
    _, records = execution.prepare_model_assets(config, training=False)
    assert records == ()
    weights = tmp_path / "explicit.pth"
    weights.write_bytes(b"user-owned native file")
    config.train.weights = weights
    prepared, records = execution.prepare_model_assets(config, training=True)
    assert prepared.train.weights == weights
    assert records == ()
    weights.unlink()
    with pytest.raises(FileNotFoundError, match="Explicit model weights"):
        execution.prepare_model_assets(config, training=True)


def test_valid_library_cache_is_reused_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path / "project"))
    cache = tmp_path / "library" / "weight.pth"
    cache.parent.mkdir()
    torch.save({"weight": torch.ones(1)}, cache)
    spec = fasterrcnn_assets.pretrained_asset("resnet50_fpn").model_copy(
        update={"checksum": None, "cache_candidates": (cache,), "native_cache": None}
    )
    monkeypatch.setattr(resolver, "_download", lambda *args: pytest.fail("existing cache"))
    record = resolver.resolve_asset(spec)
    assert record.path == cache
    assert not resolver.asset_destination(spec).parent.exists()


def test_hf_safetensors_cache_keeps_the_loading_suffix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hashlib

    monkeypatch.setenv("CY_HOME", str(tmp_path / "project"))
    payload = _safetensors_payload({"x": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}})
    digest = hashlib.sha256(payload).hexdigest()
    blob = tmp_path / digest
    blob.write_bytes(payload)
    cached = tmp_path / "model.safetensors"
    cached.symlink_to(blob)
    spec = fasterrcnn_assets.pretrained_asset("resnet50_fpn").model_copy(
        update={
            "cache_candidates": (),
            "native_cache": None,
            "equivalent_caches": (
                AssetCache(
                    path=cached,
                    canonical_url="https://huggingface.co/timm/example/resolve/main/model.safetensors",
                    checksum=digest,
                ),
            ),
        }
    )
    record = resolver.resolve_asset(spec)
    assert record.path == cached
    assert record.path.suffix == ".safetensors"
    assert record.canonical_url.endswith("model.safetensors")
