"""Pinned archive trust, native cache reuse and sanitized transport recovery."""

import hashlib
import io
import tarfile
import tempfile
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from clearml_yolo.adapters.assets import bundles
from clearml_yolo.adapters.assets.resolver import asset_destination
from clearml_yolo.adapters.assets.validation import validate_asset
from clearml_yolo.core.assets import AssetSpec
from clearml_yolo.core.weight_bundles import BundleArchive, BundleAsset, BundleManifest

# A recognized legacy Torch header avoids running executable model deserialization.
WEIGHT = b"\x80\x02\x8a\x0a\x6c\xfc\x9c\x46\xf9\x20\x6a\xa8\x50\x19payload"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixture_bundle(
    tmp_path: Path, *, unsafe: str | None = None, kind: bytes = tarfile.REGTYPE
) -> tuple[AssetSpec, BundleManifest, Path]:
    spec = AssetSpec(
        backend="example",
        preset="small",
        filename="model.pt",
        canonical_url="https://upstream.example/model.pt",
        override="model.path",
        native_cache=tmp_path / "native",
    )
    member = f"assets/{spec.identity}/model.pt"
    path = tmp_path / "weights.tar"
    with tarfile.open(path, "w") as archive:
        entry = tarfile.TarInfo(member)
        entry.size = len(WEIGHT)
        archive.addfile(entry, io.BytesIO(WEIGHT))
        if unsafe:
            entry = tarfile.TarInfo(unsafe)
            entry.type = kind
            entry.linkname = "../../escaped"
            archive.addfile(entry)
    manifest = BundleManifest(
        schema_version=1,
        repository="BuckanovNikita/clearml-yolo",
        release_tag="weights-2026-10-29",
        archives=(
            BundleArchive(
                name=path.name, size=path.stat().st_size, sha256=digest(path.read_bytes())
            ),
        ),
        assets=(
            BundleAsset(
                identity=spec.identity,
                backend=spec.backend,
                preset=spec.preset,
                filename=spec.filename,
                source_url=spec.canonical_url,
                source_revision=None,
                kind="weights",
                archive=path.name,
                member=member,
                size=len(WEIGHT),
                sha256=digest(WEIGHT),
                hub=None,
            ),
        ),
    )
    return spec, manifest, path


def test_restore_and_offline_cache_reuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec, manifest, archive = fixture_bundle(tmp_path)
    monkeypatch.setattr(bundles, "cy_home", lambda: tmp_path)
    monkeypatch.setattr(bundles, "write_path", lambda path: path)
    transfers: list[str] = []

    def download(url: str, destination: Path) -> None:
        transfers.append(url)
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(bundles, "download", download)
    bundles.seed_bundle_asset(spec, manifest)
    assert asset_destination(spec).read_bytes() == WEIGHT
    bundles.seed_bundle_asset(spec, manifest)
    assert len(transfers) == 1
    asset_destination(spec).unlink()
    bundles.seed_bundle_asset(spec, manifest)
    assert asset_destination(spec).read_bytes() == WEIGHT
    assert len(transfers) == 1


@pytest.mark.parametrize(
    ("unsafe", "kind"),
    [
        ("../escaped", tarfile.REGTYPE),
        ("/escaped", tarfile.REGTYPE),
        ("assets/link", tarfile.SYMTYPE),
        ("assets/link", tarfile.LNKTYPE),
        ("assets/device", tarfile.CHRTYPE),
        ("assets//bad", tarfile.REGTYPE),
    ],
)
def test_reject_unsafe_archive_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unsafe: str, kind: bytes
) -> None:
    spec, manifest, archive = fixture_bundle(tmp_path, unsafe=unsafe, kind=kind)
    monkeypatch.setattr(bundles, "cy_home", lambda: tmp_path)
    monkeypatch.setattr(bundles, "write_path", lambda path: path)
    monkeypatch.setattr(
        bundles, "download", lambda url, destination: destination.write_bytes(archive.read_bytes())
    )
    bundles.seed_bundle_asset(spec, manifest)
    assert not asset_destination(spec).exists()
    assert not (tmp_path / "escaped").exists()


@pytest.mark.parametrize("corrupt_archive", [True, False])
def test_checksum_failures_never_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corrupt_archive: bool
) -> None:
    spec, manifest, archive = fixture_bundle(tmp_path)
    if corrupt_archive:
        archive.write_bytes(archive.read_bytes() + b"corrupt")
    else:
        asset = manifest.assets[0].model_copy(update={"sha256": "0" * 64})
        manifest = manifest.model_copy(update={"assets": (asset,)})
    monkeypatch.setattr(bundles, "cy_home", lambda: tmp_path)
    monkeypatch.setattr(bundles, "write_path", lambda path: path)
    monkeypatch.setattr(
        bundles, "download", lambda url, destination: destination.write_bytes(archive.read_bytes())
    )
    bundles.seed_bundle_asset(spec, manifest)
    assert not asset_destination(spec).exists()


def test_proxy_failure_recovers_at_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, manifest, archive = fixture_bundle(tmp_path)
    monkeypatch.setattr(bundles, "cy_home", lambda: tmp_path)
    monkeypatch.setattr(bundles, "write_path", lambda path: path)
    monkeypatch.setenv("GHR", "https://proxy.example/releases")
    attempts: list[str] = []

    def download(url: str, destination: Path) -> None:
        attempts.append(url)
        if "proxy.example" in url:
            raise OSError("secret transport credential")
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(bundles, "download", download)
    bundles.seed_bundle_asset(spec, manifest)
    assert len(attempts) == 3
    assert "github.com/BuckanovNikita/clearml-yolo/releases/download/weights-" in attempts[-1]
    assert asset_destination(spec).read_bytes() == WEIGHT


def test_manifest_rejects_duplicates_and_unknown_fields(tmp_path: Path) -> None:
    _, manifest, _ = fixture_bundle(tmp_path)
    data = manifest.model_dump()
    data["assets"] = (manifest.assets[0], manifest.assets[0])
    with pytest.raises(ValidationError, match="Duplicate bundle asset"):
        BundleManifest.model_validate(data)
    data = manifest.model_dump()
    data["unexpected"] = True
    with pytest.raises(ValidationError, match="Extra inputs"):
        BundleManifest.model_validate(data)


def test_duplicate_archive_members_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, _, _ = fixture_bundle(tmp_path)
    spec, manifest, archive = fixture_bundle(tmp_path, unsafe=f"assets/{spec.identity}/model.pt")
    monkeypatch.setattr(bundles, "cy_home", lambda: tmp_path)
    monkeypatch.setattr(bundles, "write_path", lambda path: path)
    monkeypatch.setattr(
        bundles, "download", lambda url, destination: destination.write_bytes(archive.read_bytes())
    )
    bundles.seed_bundle_asset(spec, manifest)
    assert not asset_destination(spec).exists()


def test_unavailable_mirror_retains_upstream_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.assets import preparation
    from clearml_yolo.core.assets import ResolvedAsset

    spec, manifest, _ = fixture_bundle(tmp_path)
    monkeypatch.setattr(bundles, "cy_home", lambda: tmp_path)
    monkeypatch.setattr(bundles, "write_path", lambda path: path)
    monkeypatch.setattr(bundles, "load_manifest", lambda: manifest)
    monkeypatch.setattr(preparation, "cy_home", lambda: tmp_path)
    monkeypatch.setattr(preparation, "write_path", lambda path: path)
    monkeypatch.setattr(
        preparation, "_discover", lambda: ("fixture", (), (("example/small", spec),), ())
    )

    def unavailable(url: str, destination: Path) -> None:
        raise OSError("private credential")

    monkeypatch.setattr(bundles, "download", unavailable)
    record = ResolvedAsset(
        canonical_url=spec.canonical_url,
        path=tmp_path / "upstream.pt",
        sha256=digest(WEIGHT),
        override=spec.override,
    )
    monkeypatch.setattr(preparation, "_resolve", lambda requested: record)
    result = preparation.prepare_catalogue(automatic=False)
    assert result.assets == (record,)
    assert not result.failures


def test_pinned_manifest_identity_changes_preparation_fingerprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.assets import preparation

    _, manifest, _ = fixture_bundle(tmp_path)
    monkeypatch.setattr(preparation, "model_catalogue", lambda: ())
    monkeypatch.setattr(preparation, "load_manifest", lambda: manifest)
    first = preparation._discover()[0]
    manifest = manifest.model_copy(update={"release_tag": "weights-2026-10-30"})
    second = preparation._discover()[0]
    assert first != second


def test_extraction_scratch_stays_under_cy_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, manifest, archive = fixture_bundle(tmp_path)
    monkeypatch.setattr(bundles, "cy_home", lambda: tmp_path)
    monkeypatch.setattr(bundles, "write_path", lambda path: path)
    monkeypatch.setattr(
        bundles, "download", lambda url, destination: destination.write_bytes(archive.read_bytes())
    )
    default_temp = tempfile.gettempdir()
    original_verify = bundles._verify
    extracted: list[Path] = []

    def verify(path: Path, size: int, checksum: str) -> str:
        if path.name in {"weight", "config.json"}:
            extracted.append(path)
            assert path.is_relative_to(tmp_path / ".cache" / "clearml-yolo" / "weight-bundles")
        return original_verify(path, size, checksum)

    monkeypatch.setattr(bundles, "_verify", verify)
    bundles.seed_bundle_asset(spec, manifest)
    assert extracted
    assert all(not path.parent.exists() for path in extracted)
    assert tempfile.gettempdir() == default_temp
    assert asset_destination(spec).read_bytes() == WEIGHT


def test_mirror_repairs_native_zip_with_invalid_central_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, manifest, archive = fixture_bundle(tmp_path)
    native = asset_destination(spec)
    native.parent.mkdir(parents=True)
    with zipfile.ZipFile(native, "w") as checkpoint:
        checkpoint.writestr("archive/data.pkl", b"checkpoint")
    native.write_bytes(native.read_bytes().replace(b"PK\x01\x02", b"BAD!", 1))
    assert zipfile.is_zipfile(native)
    with pytest.raises(zipfile.BadZipFile, match="Bad magic number"):
        validate_asset(native, spec)
    monkeypatch.setattr(bundles, "cy_home", lambda: tmp_path)
    monkeypatch.setattr(bundles, "write_path", lambda path: path)
    transfers: list[str] = []

    def download(url: str, destination: Path) -> None:
        transfers.append(url)
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(bundles, "download", download)
    bundles.seed_bundle_asset(spec, manifest)
    assert native.read_bytes() == WEIGHT
    assert len(transfers) == 1
    assert "github.com/BuckanovNikita/clearml-yolo/releases/download/" in transfers[0]


def test_concurrent_native_publication_is_preserved_under_destination_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, manifest, archive = fixture_bundle(tmp_path)
    monkeypatch.setattr(bundles, "cy_home", lambda: tmp_path)
    monkeypatch.setattr(bundles, "write_path", lambda path: path)
    concurrent_weight = WEIGHT + b"valid concurrent native representation"

    def download(url: str, destination: Path) -> None:
        native = asset_destination(spec)
        native.parent.mkdir(parents=True, exist_ok=True)
        native.write_bytes(concurrent_weight)
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(bundles, "download", download)
    bundles.seed_bundle_asset(spec, manifest)
    assert asset_destination(spec).read_bytes() == concurrent_weight
