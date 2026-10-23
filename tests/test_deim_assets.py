"""Managed native source verifies every file, archive path and loaded source byte."""

import hashlib
import io
import tarfile
from pathlib import Path

import pytest

from clearml_yolo.adapters.assets import archive, execution, resolver, sources
from clearml_yolo.adapters.deim.assets import backbone_asset, source_asset
from clearml_yolo.adapters.deim.source import REVISION, _VerifiedSourceLoader, validate_checkout
from clearml_yolo.core.models import model_preset


def _archive(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w:gz") as stream:
        for name, content in members.items():
            info = tarfile.TarInfo("repository/" + name)
            info.size = len(content)
            stream.addfile(info, io.BytesIO(content))


@pytest.fixture
def source_files(monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    values = {
        "engine/__init__.py": b"VALUE = 1\n",
        "configs/train.yml": b"model: test\n",
        "LICENSE.md": b"license\n",
    }
    manifest = {key: hashlib.sha256(value).hexdigest() for key, value in values.items()}
    monkeypatch.setattr(archive, "source_manifest", lambda: manifest)
    monkeypatch.setattr(sources, "source_manifest", lambda: manifest)
    return values


def test_manual_archive_extracts_offline_and_preserves_null_selector(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_files: dict[str, bytes],
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    asset = source_asset()
    destination = resolver.asset_destination(asset)
    destination.parent.mkdir(parents=True)
    _archive(destination, source_files)
    monkeypatch.setattr(
        resolver, "_download", lambda *args: pytest.fail("manual archive is sufficient")
    )
    original = model_preset("deimv2/s")
    model, records = execution.prepare_model_assets(original, training=False)
    assert original.source_dir is None
    assert model.source_dir == destination.parent / REVISION
    assert model.source_dir is not None
    assert (model.source_dir / "engine/__init__.py").read_bytes() == source_files[
        "engine/__init__.py"
    ]
    assert len(records) == 1
    validate_checkout(model.source_dir)
    destination.unlink()
    model_again, records_again = execution.prepare_model_assets(original, training=False)
    assert model_again.source_dir == model.source_dir
    assert records_again[0].content_kind == "source-tree"


@pytest.mark.parametrize("extra", ["../escape.py", "/absolute.py", "unexpected.py"])
def test_unsafe_or_unmanifested_members_fail(
    tmp_path: Path,
    source_files: dict[str, bytes],
    extra: str,
) -> None:
    path = tmp_path / "source.tar.gz"
    _archive(path, source_files | {extra: b"malicious = True\n"})
    with pytest.raises(ValueError, match=r"Unsafe|approved manifest"):
        archive.extract_source(path, tmp_path / "source")
    assert not (tmp_path / "source").exists()


def test_links_and_modified_extracted_content_fail(
    tmp_path: Path,
    source_files: dict[str, bytes],
) -> None:
    path = tmp_path / "source.tar.gz"
    with tarfile.open(path, "w:gz") as stream:
        info = tarfile.TarInfo("repository/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/tmp/outside"
        stream.addfile(info)
    with pytest.raises(ValueError, match="Unsupported"):
        archive.validate_archive(path)
    _archive(path, source_files)
    destination = archive.extract_source(path, tmp_path / "source")
    (destination / "engine/__init__.py").write_text("VALUE = 2\n")
    with pytest.raises(ValueError, match="approved manifest"):
        archive.validate_source(destination)


def test_source_loader_compiles_verified_bytes_and_rejects_tampering(
    tmp_path: Path,
    source_files: dict[str, bytes],
) -> None:
    source = tmp_path / "engine/__init__.py"
    source.parent.mkdir()
    source.write_bytes(source_files["engine/__init__.py"])
    loader = _VerifiedSourceLoader(
        "test_namespace", str(source), tmp_path, archive.source_manifest()
    )
    assert loader.get_code("test_namespace").co_filename == str(source)
    source.write_text("VALUE = 2\n")
    with pytest.raises(ImportError, match="changed before importing"):
        loader.get_code("test_namespace")


@pytest.mark.parametrize(
    ("preset", "filename"),
    [
        ("s", "vitt_distill.pt"),
        ("m", "vittplus_distill.pt"),
        ("l", "dinov3_vits16_pretrain_lvd1689m-08c60483.pth"),
        ("x", "dinov3_vits16plus_pretrain_lvd1689m-4057cbaa.pth"),
    ],
)
def test_deim_native_backbone_selection(preset: str, filename: str) -> None:
    asset = backbone_asset(preset)
    assert asset.filename == filename
    assert asset.override == "model.train.backbone_weights"
    assert asset.access_requirement


def test_source_failure_reports_archive_destination_and_directory_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    spec = source_asset()
    destination = resolver.asset_destination(spec)
    message = resolver._failure(spec, destination, "offline")
    assert f"Local destination: {destination}" in message
    assert f"Override: model.source_dir={destination.parent / REVISION}\n" in message


def test_missing_source_and_backbone_are_reported_together(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))

    def unavailable(*args: object) -> None:
        raise TimeoutError("offline")

    monkeypatch.setattr(resolver, "_download", unavailable)
    with pytest.raises(resolver.AssetResolutionError) as caught:
        execution.prepare_model_assets(model_preset("deimv2/s"), training=True)
    message = str(caught.value)
    for asset in (source_asset(), backbone_asset("s")):
        assert asset.canonical_url in message
        assert str(resolver.asset_destination(asset)) in message
        assert asset.override in message
