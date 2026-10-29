"""Native cache writes must preserve discovery and project output containment."""

from pathlib import Path

import pytest
import torch

from clearml_yolo.adapters.assets import resolver
from clearml_yolo.adapters.storage.filesystem import write_path
from clearml_yolo.core.assets import AssetSpec


def test_legacy_asset_is_promoted_to_native_cache_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path / "project"))
    spec = AssetSpec(
        backend="test",
        preset="one",
        filename="weights.pt",
        canonical_url="https://example.invalid/weights.pt",
        override="model.train.weights",
    )
    legacy = resolver.asset_destination(spec)
    legacy.parent.mkdir(parents=True)
    torch.save({"weight": torch.ones(2)}, legacy)
    native = tmp_path / "native-cache"
    selected = AssetSpec.model_validate(spec.model_dump() | {"native_cache": native})

    def no_download(url: str, destination: Path) -> None:
        pytest.fail("Compatible legacy bytes must be promoted without downloading")

    monkeypatch.setattr(resolver, "_download", no_download)
    result = resolver.resolve_asset(selected)
    assert result.path == native / "weights.pt"
    assert result.path.read_bytes() == legacy.read_bytes()
    assert legacy.is_file()
    with pytest.raises(ValueError, match="CY_HOME"):
        write_path(native / "project-output.csv")


def test_native_destination_rejects_escaping_leaf_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path / "project"))
    native = tmp_path / "cache"
    native.mkdir()
    (native / "weights.pt").symlink_to(tmp_path / "unrelated.pt")
    spec = AssetSpec(
        backend="test",
        preset="one",
        filename="weights.pt",
        native_cache=native,
        canonical_url="https://example.invalid/weights.pt",
        override="model.train.weights",
    )
    with pytest.raises(ValueError, match="native cache"):
        resolver.asset_destination(spec)


def test_yolo_discovery_preserves_literal_settings_path_and_settings_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ultralytics.utils import SETTINGS

    from clearml_yolo.adapters.yolo.assets import pretrained_asset

    monkeypatch.chdir(tmp_path)
    before = SETTINGS.file.read_bytes()
    previous = SETTINGS["weights_dir"]
    # Bypass the persistent setter for this isolated native-settings fixture.
    dict.__setitem__(SETTINGS, "weights_dir", "~/native-weights")
    try:
        spec = pretrained_asset("yolo11n.pt")
        assert spec.native_cache == tmp_path / "~" / "native-weights"
        assert SETTINGS["weights_dir"] == "~/native-weights"
    finally:
        dict.__setitem__(SETTINGS, "weights_dir", previous)
    assert SETTINGS.file.read_bytes() == before


def test_asset_source_diagnostics_retain_public_ids_but_redact_credentials() -> None:
    from clearml_yolo.adapters.assets.http import asset_source_url

    public = "https://drive.usercontent.google.com/download?id=public-id&export=download&confirm=t"
    assert asset_source_url(public) == public
    for source in (
        public + "&token=private-value",
        "https://user:private-value@example.test/model.pt?token=private-value",
    ):
        assert "private-value" not in asset_source_url(source)
