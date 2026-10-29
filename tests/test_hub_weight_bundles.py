"""Restore pinned native Hub weights/config while every network boundary is unavailable."""

import hashlib
from pathlib import Path

import pytest
from huggingface_hub import try_to_load_from_cache

from clearml_yolo.adapters.assets import hub
from clearml_yolo.core.assets import AssetSpec, HubAsset
from clearml_yolo.core.weight_bundles import BundleAsset, BundleConfig, BundleHub

WEIGHT = b"\x80\x02\x8a\x0a\x6c\xfc\x9c\x46\xf9\x20\x6a\xa8\x50\x19payload"
COMMIT = "a" * 40


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture(tmp_path: Path) -> tuple[AssetSpec, BundleAsset, Path, Path]:
    spec = AssetSpec(
        backend="example",
        preset="small",
        filename="original.pth",
        canonical_url="https://upstream.example/model.pth",
        revision="timm:example",
        override="model.weights",
        hub=HubAsset(repository="timm/example", cache_dir=tmp_path / "hub"),
    )
    weight = tmp_path / "weight"
    weight.write_bytes(WEIGHT)
    config = tmp_path / "config.json"
    config.write_bytes(b'{"architecture":"example"}')
    asset = BundleAsset(
        identity=spec.identity,
        backend=spec.backend,
        preset=spec.preset,
        filename=spec.filename,
        source_url=spec.canonical_url,
        source_revision=spec.revision,
        kind="weights",
        archive="weights.tar",
        member=f"assets/{spec.identity}/pytorch_model.bin",
        size=weight.stat().st_size,
        sha256=_digest(WEIGHT),
        hub=BundleHub(
            repository="timm/example",
            revision="main",
            commit=COMMIT,
            filename="pytorch_model.bin",
            etag=_digest(WEIGHT),
            config=BundleConfig(
                member=f"assets/{spec.identity}/config.json",
                size=config.stat().st_size,
                sha256=_digest(config.read_bytes()),
                etag=_digest(config.read_bytes()),
            ),
        ),
    )
    return spec, asset, weight, config


def test_restore_real_snapshot_and_config_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, asset, weight, config = _fixture(tmp_path)
    monkeypatch.setattr(hub, "hf_hub_download", lambda **kw: pytest.fail("network requested"))
    monkeypatch.setattr(hub, "get_hf_file_metadata", lambda **kw: pytest.fail("metadata requested"))
    result = hub.restore_bundle_asset(spec, asset, weight, config)
    assert result.revision == COMMIT
    assert result.canonical_url == (
        f"https://huggingface.co/timm/example/resolve/{COMMIT}/pytorch_model.bin"
    )
    assert hub.bundle_asset_ready(spec)
    assert hub.resolve_hub_asset(spec) == result
    assert spec.hub is not None
    cached_config = try_to_load_from_cache(
        "timm/example", "config.json", cache_dir=spec.hub.cache_dir, revision="main"
    )
    assert isinstance(cached_config, str)
    assert Path(cached_config).read_bytes() == config.read_bytes()
    assert result.path.read_bytes() == WEIGHT


@pytest.mark.parametrize("corrupt", ["weight", "config", "etag"])
def test_invalid_hub_bytes_never_publish(tmp_path: Path, corrupt: str) -> None:
    spec, asset, weight, config = _fixture(tmp_path)
    if corrupt == "weight":
        weight.write_bytes(b"invalid")
    elif corrupt == "config":
        config.write_bytes(b"[]")
    else:
        assert asset.hub is not None
        asset = asset.model_copy(update={"hub": asset.hub.model_copy(update={"etag": "0" * 64})})
    with pytest.raises(ValueError, match=r"(checkpoint|config|ETag)"):
        hub.restore_bundle_asset(spec, asset, weight, config)
    assert spec.hub is not None
    assert not spec.hub.cache_dir.exists()
