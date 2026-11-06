"""Convert pinned official HF DINOv3 tensors into verified native DEIM checkpoints."""

import hashlib
import importlib
import pickle  # noqa: S403 -- catch only UnpicklingError from safe weights_only Torch loading
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

from filelock import FileLock

from clearml_yolo.adapters.assets.resolver import AssetResolutionError, resolve_asset
from clearml_yolo.adapters.assets.validation import validate_asset
from clearml_yolo.adapters.deim.assets import backbone_asset, huggingface_backbone_asset
from clearml_yolo.adapters.deim.source import load_source
from clearml_yolo.adapters.storage.filesystem import cy_home, write_path
from clearml_yolo.core.assets import DEIM_REVISION, AssetDerivation, ResolvedAsset

if TYPE_CHECKING:
    from torch import Tensor, nn

_CONVERTER = "hf-dinov3-to-deim-v1"
_LAYERS = 12
_MODEL_NAMES = {"l": "dinov3_vits16", "x": "dinov3_vits16plus"}


def _native_model(preset: str, source_dir: Path) -> "nn.Module":
    torch = importlib.import_module("torch")
    core, _solver = load_source(source_dir)
    backbone = importlib.import_module(core.__name__.removesuffix(".core") + ".backbone.dinov3")
    # Conversion must neither initialize CUDA nor consume the training RNG stream.
    with torch.random.fork_rng(devices=[]), torch.device("cpu"):
        torch.random.default_generator.manual_seed(0)
        return cast("nn.Module", backbone.DinoVisionTransformer(name=_MODEL_NAMES[preset]).eval())


def native_state(
    source: Mapping[str, "Tensor"], preset: str, native: "nn.Module"
) -> dict[str, "Tensor"]:
    """Map every source tensor once; restore only architecture-defined nonlearned state."""
    torch = importlib.import_module("torch")
    remaining = dict(source)
    result: dict[str, Tensor] = {}

    def take(name: str) -> "Tensor":
        try:
            tensor = remaining.pop(name)
        except KeyError as error:
            raise ValueError(f"Missing or repeated DINOv3 source tensor: {name}") from error
        if tensor.device.type != "cpu" or not bool(torch.isfinite(tensor).all()):
            raise ValueError(f"DINOv3 conversion requires finite CPU tensors: {name}")
        return tensor.clone()

    for origin, target in (
        ("embeddings.cls_token", "cls_token"),
        ("embeddings.register_tokens", "storage_tokens"),
        ("embeddings.patch_embeddings.weight", "patch_embed.proj.weight"),
        ("embeddings.patch_embeddings.bias", "patch_embed.proj.bias"),
        ("norm.weight", "norm.weight"),
        ("norm.bias", "norm.bias"),
    ):
        result[target] = take(origin)
    result["mask_token"] = take("embeddings.mask_token").squeeze(1)
    mlp = (
        (("up_proj", "fc1"), ("down_proj", "fc2"))
        if preset == "l"
        else (("gate_proj", "w1"), ("up_proj", "w2"), ("down_proj", "w3"))
    )
    for layer in range(_LAYERS):
        origin, target = f"layer.{layer}.", f"blocks.{layer}."
        for name in ("norm1.weight", "norm1.bias", "norm2.weight", "norm2.bias"):
            result[target + name] = take(origin + name)
        pairs = [
            ("layer_scale1.lambda1", "ls1.gamma"),
            ("layer_scale2.lambda1", "ls2.gamma"),
            ("attention.o_proj.weight", "attn.proj.weight"),
            ("attention.o_proj.bias", "attn.proj.bias"),
            *(
                (f"mlp.{hf}.{kind}", f"mlp.{deim}.{kind}")
                for hf, deim in mlp
                for kind in ("weight", "bias")
            ),
        ]
        for hf, deim in pairs:
            result[target + deim] = take(origin + hf)
        result[target + "attn.qkv.weight"] = torch.cat(
            [take(origin + f"attention.{projection}_proj.weight") for projection in ("q", "k", "v")]
        )
        query, value = [
            take(origin + f"attention.{projection}_proj.bias") for projection in ("q", "v")
        ]
        result[target + "attn.qkv.bias"] = torch.cat((query, torch.zeros_like(query), value))
        result[target + "attn.qkv.bias_mask"] = torch.cat(
            (torch.ones_like(query), torch.zeros_like(query), torch.ones_like(query))
        )
    expected = native.state_dict()
    result["rope_embed.periods"] = expected["rope_embed.periods"].clone()
    _validate_mapping(remaining, result, expected)
    native.load_state_dict(result, strict=True)
    return result


def _validate_mapping(
    remaining: Mapping[str, "Tensor"],
    result: Mapping[str, "Tensor"],
    expected: Mapping[str, "Tensor"],
) -> None:
    if remaining:
        raise ValueError(f"Unconsumed DINOv3 source tensors: {sorted(remaining)}")
    if result.keys() != expected.keys():
        raise ValueError("Converted DINOv3 tensor keys differ from the pinned native architecture")
    for name, value in result.items():
        if value.shape != expected[name].shape or value.dtype != expected[name].dtype:
            raise ValueError(f"Converted DINOv3 tensor shape/dtype mismatch: {name}")


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _reload(path: Path, expected: Mapping[str, "Tensor"], native: "nn.Module") -> None:
    torch = importlib.import_module("torch")
    try:
        loaded = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as error:
        # Weights-only unpickling raises open-ended types (TypeError, KeyError,
        # IndexError, AssertionError and others from allowlisted reducers and opcodes).
        # Normalize them so _cached rebuilds a stale checkpoint; staging stays loud.
        raise ValueError(f"Unreadable converted DINOv3 checkpoint: {path}") from error
    if not isinstance(loaded, dict) or loaded.keys() != expected.keys():
        raise ValueError("Invalid converted DINOv3 tensor inventory")
    if any(
        not isinstance(loaded[key], torch.Tensor)
        or loaded[key].dtype != value.dtype
        or not torch.equal(loaded[key], value)
        for key, value in expected.items()
    ):
        raise ValueError("Converted DINOv3 tensors do not match the pinned source")
    native.load_state_dict(loaded, strict=True)


def _cached(
    path: Path,
    receipt: Path,
    expected: Mapping[str, "Tensor"],
    native: "nn.Module",
    derivation: AssetDerivation,
) -> ResolvedAsset | None:
    try:
        record = ResolvedAsset.model_validate_json(receipt.read_text(encoding="utf-8"))
        if (
            record.path != path
            or record.derivation != derivation
            or record.sha256 != _sha256(path)
            or record.canonical_url != derivation.source_url + "#" + _CONVERTER
            or record.revision != DEIM_REVISION
            or record.override != "model.train.backbone_weights"
            or record.content_kind != "file"
        ):
            return None
        _reload(path, expected, native)
    except (OSError, ValueError, RuntimeError, EOFError, pickle.UnpicklingError):
        return None
    return record


def _publish(
    source: ResolvedAsset,
    preset: str,
    source_dir: Path,
) -> ResolvedAsset:
    from safetensors.torch import load_file

    torch = importlib.import_module("torch")
    spec = huggingface_backbone_asset(preset)
    # Generic Hub requests also serve alternate representations. This conversion
    # has one frozen source representation and therefore rechecks its full pin.
    digest = validate_asset(source.path, spec)
    if digest != source.sha256 or source.revision != spec.revision or source.revision is None:
        raise ValueError("DINOv3 source provenance differs from its pinned content")
    derivation = AssetDerivation(
        source_url=source.canonical_url,
        source_revision=source.revision,
        source_sha256=digest,
        converter=_CONVERTER,
        native_revision=DEIM_REVISION,
    )
    identity = hashlib.sha256(derivation.model_dump_json().encode()).hexdigest()[:24]
    directory = write_path(
        cy_home() / ".cache" / "clearml-yolo" / "models" / "deimv2" / preset / identity
    )
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_CONVERTER}.pth"
    receipt = path.with_suffix(".json")
    with FileLock(str(path) + ".lock", timeout=1260):
        native = _native_model(preset, source_dir)
        tensors = load_file(source.path, device="cpu")
        if _sha256(source.path) != digest:
            raise ValueError("DINOv3 source changed during conversion")
        expected = native_state(tensors, preset, native)
        cached = _cached(path, receipt, expected, native, derivation)
        if cached is not None:
            return cached
        with tempfile.TemporaryDirectory(prefix=".conversion-", dir=directory) as staging:
            checkpoint = Path(staging) / path.name
            with checkpoint.open("wb") as stream:
                torch.save(expected, stream)
            _reload(checkpoint, expected, native)
            record = ResolvedAsset(
                canonical_url=source.canonical_url + "#" + _CONVERTER,
                path=path,
                sha256=_sha256(checkpoint),
                override="model.train.backbone_weights",
                revision=DEIM_REVISION,
                derivation=derivation,
            )
            metadata = Path(staging) / receipt.name
            metadata.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
            checkpoint.replace(path)
            metadata.replace(receipt)
        return record


def resolve_backbone(preset: str, source_dir: Path) -> ResolvedAsset:
    """Reuse an original Meta checkpoint, otherwise obtain the authorized HF representation."""
    try:
        return resolve_asset(backbone_asset(preset), local_only=True)
    except AssetResolutionError:
        spec = huggingface_backbone_asset(preset)
        source = resolve_asset(spec)
        return _publish(source, preset, source_dir)
