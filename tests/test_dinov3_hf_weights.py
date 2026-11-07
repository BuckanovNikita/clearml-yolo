"""Official HF representations preserve native tensor and asset provenance contracts."""

import hashlib
import importlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType

import pytest
import torch
from safetensors.torch import save_file

from clearml_yolo.adapters.assets import execution
from clearml_yolo.adapters.assets.resolver import AssetResolutionError
from clearml_yolo.adapters.deim import hf_weights
from clearml_yolo.adapters.deim.assets import backbone_asset, huggingface_backbone_asset
from clearml_yolo.core.assets import AssetSpec, ResolvedAsset
from clearml_yolo.core.models import model_preset

type Conversion = tuple[str, dict[str, torch.Tensor], dict[str, torch.Tensor]]
type SourceRecord = tuple[str, ResolvedAsset]


def _native(tensors: dict[str, torch.Tensor]) -> torch.nn.Module:
    model = torch.nn.Module()
    for key, value in tensors.items():
        parent = model
        *parts, name = key.split(".")
        for part in parts:
            if part not in parent._modules:
                parent.add_module(part, torch.nn.Module())
            child = parent._modules[part]
            assert child is not None
            parent = child
        parent.register_buffer(name, value.clone())
    return model


@pytest.fixture(params=["l", "x"])
def conversion(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Conversion:
    """A small real Torch module exercises strict loading independently of native source IO."""
    preset = str(request.param)
    source = {
        "embeddings.cls_token": torch.ones(1, 1, 2),
        "embeddings.register_tokens": torch.ones(1, 4, 2),
        "embeddings.patch_embeddings.weight": torch.ones(2, 3, 1, 1),
        "embeddings.patch_embeddings.bias": torch.ones(2),
        "embeddings.mask_token": torch.ones(1, 1, 2),
        "norm.weight": torch.ones(2),
        "norm.bias": torch.ones(2),
    }
    state = {
        "cls_token": torch.zeros(1, 1, 2),
        "storage_tokens": torch.zeros(1, 4, 2),
        "patch_embed.proj.weight": torch.zeros(2, 3, 1, 1),
        "patch_embed.proj.bias": torch.zeros(2),
        "mask_token": torch.zeros(1, 2),
        "norm.weight": torch.zeros(2),
        "norm.bias": torch.zeros(2),
        "rope_embed.periods": torch.tensor([3.0, 7.0]),
    }
    for name in ("norm1.weight", "norm1.bias", "norm2.weight", "norm2.bias"):
        source["layer.0." + name] = torch.arange(2, dtype=torch.float32)
        state["blocks.0." + name] = torch.zeros(2)
    for index in (1, 2):
        source[f"layer.0.layer_scale{index}.lambda1"] = torch.full((2,), float(index))
        state[f"blocks.0.ls{index}.gamma"] = torch.zeros(2)
    for projection in ("q", "k", "v", "o"):
        source[f"layer.0.attention.{projection}_proj.weight"] = torch.full((2, 2), float(ord(projection)))
        if projection != "k":
            source[f"layer.0.attention.{projection}_proj.bias"] = torch.full((2,), float(ord(projection)))
    state.update(
        {
            "blocks.0.attn.proj.weight": torch.zeros(2, 2),
            "blocks.0.attn.proj.bias": torch.zeros(2),
            "blocks.0.attn.qkv.weight": torch.zeros(6, 2),
            "blocks.0.attn.qkv.bias": torch.zeros(6),
            "blocks.0.attn.qkv.bias_mask": torch.zeros(6),
        }
    )
    mlps = (
        [("up_proj", "fc1"), ("down_proj", "fc2")]
        if preset == "l"
        else [("gate_proj", "w1"), ("up_proj", "w2"), ("down_proj", "w3")]
    )
    for upstream, target in mlps:
        shape = (2, 4) if upstream == "down_proj" else (4, 2)
        source[f"layer.0.mlp.{upstream}.weight"] = torch.full(shape, 2.5)
        source[f"layer.0.mlp.{upstream}.bias"] = torch.full((shape[0],), 1.5)
        state[f"blocks.0.mlp.{target}.weight"] = torch.zeros(shape)
        state[f"blocks.0.mlp.{target}.bias"] = torch.zeros(shape[0])
    monkeypatch.setattr(hf_weights, "_LAYERS", 1)
    monkeypatch.setattr(hf_weights, "_native_model", lambda *_: _native(state))
    return preset, source, state


def test_mapping_preserves_attention_order_mlp_and_nonlearned_buffers(
    conversion: Conversion,
) -> None:
    preset, source, expected = conversion
    model = _native(expected)
    result = hf_weights.native_state(source, preset, model)
    for index, projection in enumerate(("q", "k", "v")):
        assert torch.equal(
            result["blocks.0.attn.qkv.weight"].chunk(3)[index],
            source[f"layer.0.attention.{projection}_proj.weight"],
        )
    assert torch.equal(result["blocks.0.attn.qkv.bias"], torch.tensor([113.0, 113.0, 0.0, 0.0, 118.0, 118.0]))
    assert torch.equal(result["blocks.0.attn.qkv.bias_mask"], torch.tensor([1.0, 1.0, 0.0, 0.0, 1.0, 1.0]))
    assert torch.equal(result["rope_embed.periods"], expected["rope_embed.periods"])
    assert all(torch.equal(value, model.state_dict()[key]) for key, value in result.items())


@pytest.mark.parametrize("failure", ["missing", "extra", "nan", "shape", "dtype"])
def test_conversion_rejects_incomplete_or_incompatible_source(conversion: Conversion, failure: str) -> None:
    preset, source, expected = conversion
    key = "embeddings.cls_token"
    if failure == "missing":
        del source[key]
    elif failure == "extra":
        source["unexpected"] = torch.ones(1)
    elif failure == "nan":
        source[key].fill_(float("nan"))
    elif failure == "shape":
        source[key] = torch.ones(1, 1, 3)
    else:
        source[key] = source[key].double()
    with pytest.raises(ValueError, match="DINOv3"):
        hf_weights.native_state(source, preset, _native(expected))


@pytest.fixture
def source_record(conversion: Conversion, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SourceRecord:
    preset, source, _ = conversion
    path = tmp_path / "model.safetensors"
    save_file(source, path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    spec = huggingface_backbone_asset(preset).model_copy(update={"checksum": digest})
    monkeypatch.setattr(hf_weights, "huggingface_backbone_asset", lambda _: spec)
    monkeypatch.setenv("CY_HOME", str(tmp_path / "home"))
    record = ResolvedAsset(
        canonical_url=spec.canonical_url,
        path=path,
        sha256=digest,
        override=spec.override,
        revision=spec.revision,
    )
    return preset, record


def test_original_meta_cache_wins_without_hf_access(
    source_record: SourceRecord, monkeypatch: pytest.MonkeyPatch
) -> None:
    preset, source = source_record

    def resolve(spec: AssetSpec, *, local_only: bool = False) -> ResolvedAsset:
        assert local_only
        assert spec == backbone_asset(preset)
        return source

    monkeypatch.setattr(hf_weights, "resolve_asset", resolve)
    assert hf_weights.resolve_backbone(preset, Path("unused")) is source


def test_fallback_preserves_source_and_derived_provenance_and_reuses_cache(
    source_record: SourceRecord, monkeypatch: pytest.MonkeyPatch
) -> None:
    preset, source = source_record

    def resolve(spec: AssetSpec, *, local_only: bool = False) -> ResolvedAsset:
        if local_only:
            raise AssetResolutionError("Original Meta checkpoint unavailable")
        assert spec.hub is not None
        return source

    monkeypatch.setattr(hf_weights, "resolve_asset", resolve)
    result = hf_weights.resolve_backbone(preset, Path("source"))
    assert result.derivation is not None
    assert result.derivation.source_sha256 == source.sha256
    assert result.derivation.source_revision == source.revision
    assert result.path.name != backbone_asset(preset).filename
    assert result.canonical_url == source.canonical_url + "#hf-dinov3-to-deim-v1"
    assert result.sha256 != source.sha256
    before = result.path.stat().st_mtime_ns
    assert hf_weights.resolve_backbone(preset, Path("source")) == result
    assert result.path.stat().st_mtime_ns == before


def test_unauthorized_hf_failure_is_not_hidden(source_record: SourceRecord, monkeypatch: pytest.MonkeyPatch) -> None:
    preset, _ = source_record

    def resolve(spec: AssetSpec, *, local_only: bool = False) -> ResolvedAsset:
        raise AssetResolutionError("Meta unavailable" if local_only else "HF access required")

    monkeypatch.setattr(hf_weights, "resolve_asset", resolve)
    with pytest.raises(AssetResolutionError, match="HF access required"):
        hf_weights.resolve_backbone(preset, Path("source"))


def test_corrupt_source_fails_before_native_construction(
    source_record: SourceRecord, monkeypatch: pytest.MonkeyPatch
) -> None:
    preset, source = source_record
    source.path.write_bytes(b"corrupt")
    monkeypatch.setattr(hf_weights, "_native_model", lambda *_: pytest.fail("invalid source consumed"))
    with pytest.raises(ValueError, match="checksum"):
        hf_weights._publish(source, preset, Path("source"))


@pytest.mark.parametrize("failure", ["checkpoint", "receipt", "tensor-and-hash", "metadata"])
def test_corrupt_derived_cache_is_rebuilt_from_verified_source(source_record: SourceRecord, failure: str) -> None:
    preset, source = source_record
    result = hf_weights._publish(source, preset, Path("source"))
    receipt = result.path.with_suffix(".json")
    if failure == "checkpoint":
        result.path.write_bytes(b"corrupt")
    elif failure == "receipt":
        receipt.write_text("{}")
    elif failure == "metadata":
        receipt.write_text(result.model_copy(update={"canonical_url": "wrong"}).model_dump_json())
    else:
        state = torch.load(result.path, weights_only=True)
        state["cls_token"].add_(1)
        torch.save(state, result.path)
        receipt.write_text(
            result.model_copy(update={"sha256": hashlib.sha256(result.path.read_bytes()).hexdigest()}).model_dump_json()
        )
    repaired = hf_weights._publish(source, preset, Path("source"))
    assert repaired == result


@pytest.mark.parametrize(
    "payload",
    [
        # An allowlisted OrderedDict reduce with a non-iterable argument raises TypeError.
        b"\x80\x02ccollections\nOrderedDict\nK\x05R.",
        # A memo lookup of an unset index raises KeyError.
        b"\x80\x02h\x05.",
        # STOP on an empty stack raises IndexError.
        b"\x80\x02.",
    ],
    ids=["type-error", "key-error", "index-error"],
)
def test_unreadable_derived_checkpoint_with_matching_receipt_is_rebuilt(
    source_record: SourceRecord, payload: bytes
) -> None:
    """Weights-only unpickling errors outside the usual types still trigger reconversion."""
    preset, source = source_record
    result = hf_weights._publish(source, preset, Path("source"))
    result.path.write_bytes(payload)
    result.path.with_suffix(".json").write_text(
        result.model_copy(update={"sha256": hashlib.sha256(payload).hexdigest()}).model_dump_json()
    )
    repaired = hf_weights._publish(source, preset, Path("source"))
    assert repaired == result


def test_concurrent_conversion_publishes_one_valid_checkpoint(source_record: SourceRecord) -> None:
    preset, source = source_record
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: hf_weights._publish(source, preset, Path("source")), range(2)))
    assert results[0] == results[1]
    assert not list(results[0].path.parent.glob(".conversion-*"))


@pytest.mark.parametrize("selection", ["deimv2/l", "deimv2/x"])
def test_selected_execution_uses_fallback_without_mutating_canonical_config(
    selection: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = model_preset(selection)
    config.source_dir = tmp_path
    record = ResolvedAsset(
        canonical_url="https://example.test/source#conversion",
        path=tmp_path / "converted.pth",
        sha256="verified",
        override="model.train.backbone_weights",
    )
    monkeypatch.setattr(execution, "validate_checkout", lambda _: None)
    monkeypatch.setattr(
        execution,
        "resolve_assets",
        lambda specs: () if not specs else pytest.fail("original URL requested"),
    )
    monkeypatch.setattr(execution, "resolve_backbone", lambda preset, source: record)
    prepared, records = execution.prepare_model_assets(config, training=True)
    assert prepared.train.backbone_weights == record.path
    assert records == (record,)
    assert config.train.backbone_weights is None


@pytest.mark.parametrize("mode", ["inference", "random", "weights", "backbone_weights"])
def test_explicit_or_unrequested_initialization_never_uses_fallback(
    mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = model_preset("deimv2/l")
    config.source_dir = tmp_path
    checkpoint = tmp_path / "explicit.pth"
    checkpoint.touch()
    if mode == "random":
        config.train.pretrained = False
    elif mode == "weights":
        config.train.weights = checkpoint
    elif mode == "backbone_weights":
        config.train.backbone_weights = checkpoint
    monkeypatch.setattr(execution, "validate_checkout", lambda _: None)
    monkeypatch.setattr(execution, "resolve_assets", lambda specs: ())
    monkeypatch.setattr(execution, "resolve_backbone", lambda *_: pytest.fail("unrequested HF fallback"))
    _, records = execution.prepare_model_assets(config, training=mode != "inference")
    assert records == ()


def test_source_revision_mismatch_is_rejected(source_record: SourceRecord) -> None:
    preset, source = source_record
    with pytest.raises(ValueError, match="provenance"):
        hf_weights._publish(source.model_copy(update={"revision": "another"}), preset, Path("source"))


def test_native_construction_preserves_cpu_rng_without_seeding_cuda(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = ModuleType("test_deim.core")
    backbone = ModuleType("test_deim.backbone.dinov3")
    monkeypatch.setattr(backbone, "DinoVisionTransformer", lambda **_: torch.nn.Linear(2, 2), raising=False)
    monkeypatch.setattr(hf_weights, "load_source", lambda _: (core, core))
    original = importlib.import_module
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: backbone if name == backbone.__name__ else original(name),
    )
    monkeypatch.setattr(torch.cuda, "manual_seed_all", lambda _: pytest.fail("CUDA RNG seeded"))
    before = torch.random.get_rng_state().clone()
    hf_weights._native_model("l", Path("source"))
    assert torch.equal(before, torch.random.get_rng_state())
