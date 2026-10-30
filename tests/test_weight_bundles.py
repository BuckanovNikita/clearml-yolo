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

    def download(url: str, destination: Path, **kwargs: object) -> None:
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
        bundles,
        "download",
        lambda url, destination, **kwargs: destination.write_bytes(archive.read_bytes()),
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
        bundles,
        "download",
        lambda url, destination, **kwargs: destination.write_bytes(archive.read_bytes()),
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

    def download(url: str, destination: Path, **kwargs: object) -> None:
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
        bundles,
        "download",
        lambda url, destination, **kwargs: destination.write_bytes(archive.read_bytes()),
    )
    bundles.seed_bundle_asset(spec, manifest)
    assert not asset_destination(spec).exists()


def test_valid_native_cache_does_not_require_a_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.assets import preparation

    spec, _, _ = fixture_bundle(tmp_path)
    destination = asset_destination(spec)
    destination.parent.mkdir(parents=True)
    destination.write_bytes(WEIGHT)
    monkeypatch.setattr(bundles, "load_manifest", lambda: None)
    monkeypatch.setattr(
        preparation, "_discover", lambda: ("fixture", (), (("example/small", spec),), ())
    )
    monkeypatch.setattr(
        bundles, "download", lambda *args, **kwargs: pytest.fail("release network requested")
    )
    result = preparation.prepare_catalogue(automatic=False)
    assert len(result.assets) == 1
    assert result.assets[0].path == destination
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
        bundles,
        "download",
        lambda url, destination, **kwargs: destination.write_bytes(archive.read_bytes()),
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

    def download(url: str, destination: Path, **kwargs: object) -> None:
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

    def download(url: str, destination: Path, **kwargs: object) -> None:
        native = asset_destination(spec)
        native.parent.mkdir(parents=True, exist_ok=True)
        native.write_bytes(concurrent_weight)
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(bundles, "download", download)
    bundles.seed_bundle_asset(spec, manifest)
    assert asset_destination(spec).read_bytes() == concurrent_weight


def test_resnet_bundle_matches_same_content_across_torchvision_versions() -> None:
    manifest = bundles.load_manifest()
    assert manifest is not None
    asset = next(item for item in manifest.assets if item.preset == "resnet50_fpn")
    spec = AssetSpec(
        backend=asset.backend,
        preset=asset.preset,
        filename=asset.filename,
        canonical_url=asset.source_url,
        revision="0.28.0",
        checksum="11ad3fa6",
        override="model.train.backbone_weights",
    )
    assert bundles._matches(spec, asset)
    for updates in (
        {"canonical_url": "https://unrelated.example/model.pth"},
        {"checksum": "00000000"},
        {"checksum": None},
        {"preset": "resnet101_fpn"},
        {"filename": "another.pth"},
        {"kind": "deim-source"},
    ):
        assert not bundles._matches(spec.model_copy(update=updates), asset)
    deim = next(item for item in manifest.assets if item.backend == "deimv2")
    changed_source = AssetSpec(
        backend=deim.backend,
        preset=deim.preset,
        filename=deim.filename,
        canonical_url=deim.source_url,
        revision="b" * 40,
        override="model.train.backbone_weights",
    )
    assert not bundles._matches(changed_source, deim)


def test_bulk_release_failure_never_contacts_upstream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import requests

    from clearml_yolo.adapters.assets import preparation, resolver

    spec, manifest, _ = fixture_bundle(tmp_path)
    monkeypatch.setattr(bundles, "load_manifest", lambda: manifest)
    monkeypatch.setattr(
        preparation, "_discover", lambda: ("release-only", (), (("example/small", spec),), ())
    )
    monkeypatch.setenv("GHR", "https://user:secret@private.example/artifactory/files?token=hidden")
    attempts: list[str] = []

    def unavailable(url: str, destination: Path, **kwargs: object) -> None:
        attempts.append(url)
        response = requests.Response()
        response.status_code = 401
        raise requests.HTTPError("opaque-private-secret", response=response)

    upstream: list[str] = []

    def forbidden(url: str, destination: Path) -> None:
        upstream.append(url)
        raise requests.ConnectionError("opaque-private-secret")

    monkeypatch.setattr(bundles, "download", unavailable)
    monkeypatch.setattr(resolver, "_download", forbidden)
    result = preparation.prepare_catalogue(automatic=False)
    assert not upstream
    assert len(attempts) == 4
    assert len(result.failures) == 1
    message = result.failures[0].message
    assert "GHR Files remote: HTTP 401" in message
    assert "GitHub release: HTTP 401" in message
    assert "weights.tar" in message
    assert all(
        secret not in message for secret in ("opaque-private-secret", "hidden", "private.example")
    )
    assert not asset_destination(spec).exists()


@pytest.mark.parametrize("manifest_state", ["missing", "no-match", "false-success"])
def test_bulk_unavailable_pin_or_incomplete_restore_never_uses_upstream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest_state: str
) -> None:
    from clearml_yolo.adapters.assets import preparation, resolver

    spec, manifest, _ = fixture_bundle(tmp_path)
    selected = None if manifest_state == "missing" else manifest
    if manifest_state == "no-match":
        spec = spec.model_copy(update={"revision": "changed"})
    monkeypatch.setattr(bundles, "load_manifest", lambda: selected)
    monkeypatch.setattr(
        preparation, "_discover", lambda: (manifest_state, (), (("example/small", spec),), ())
    )
    if manifest_state == "false-success":
        monkeypatch.setattr(preparation, "seed_bundle_asset", lambda requested: None)
    upstream: list[str] = []

    def forbidden(url: str, destination: Path) -> None:
        upstream.append(url)
        raise OSError("blocked original host")

    monkeypatch.setattr(resolver, "_download", forbidden)
    result = preparation.prepare_catalogue(automatic=False)
    assert not upstream
    assert len(result.failures) == 1
    expected = {
        "missing": "manifest is missing",
        "no-match": "no matching asset",
        "false-success": "local cache",
    }
    assert expected[manifest_state] in result.failures[0].message


@pytest.mark.parametrize("configured", [None, "3600", "0", "nan", "inf", "private-secret"])
def test_archive_timeout_is_configurable_and_invalid_values_are_private(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configured: str | None
) -> None:
    spec, manifest, archive = fixture_bundle(tmp_path)
    if configured is None:
        monkeypatch.delenv("CY_WEIGHTS_DOWNLOAD_TIMEOUT", raising=False)
    else:
        monkeypatch.setenv("CY_WEIGHTS_DOWNLOAD_TIMEOUT", configured)
    observed: list[float] = []

    def download(url: str, destination: Path, *, max_seconds: float) -> None:
        observed.append(max_seconds)
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(bundles, "download", download)
    failure = bundles.seed_bundle_asset(spec, manifest)
    if configured in {None, "3600"}:
        assert failure is None
        assert observed == [1800 if configured is None else 3600]
        assert asset_destination(spec).read_bytes() == WEIGHT
    else:
        assert not observed
        assert failure is not None
        assert "CY_WEIGHTS_DOWNLOAD_TIMEOUT" in failure
        assert "positive finite" in failure
        assert "private-secret" not in failure


def test_http_extended_budget_does_not_change_ordinary_download_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time
    from contextlib import nullcontext
    from unittest.mock import Mock

    import requests

    from clearml_yolo.adapters.assets import http

    response = Mock()
    response.headers = {"Content-Length": "8"}
    response.iter_content.side_effect = lambda **kwargs: iter([b"12345678"])
    session = Mock()
    session.get.side_effect = lambda *args, **kwargs: nullcontext(response)
    monkeypatch.setattr(requests, "Session", lambda: nullcontext(session))
    monkeypatch.setattr(time, "monotonic", iter([0.0, 301.0, 0.0, 301.0]).__next__)
    with pytest.raises(TimeoutError):
        http.download("https://example.invalid/file", tmp_path / "ordinary")
    http.download("https://example.invalid/archive", tmp_path / "archive", max_seconds=1800)
    assert (tmp_path / "archive").read_bytes() == b"12345678"


@pytest.mark.parametrize("weight_cached", [False, True])
def test_local_only_hub_resolution_never_repairs_metadata_over_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, weight_cached: bool
) -> None:
    from clearml_yolo.adapters.assets import hub, resolver
    from clearml_yolo.core.assets import HubAsset

    spec = AssetSpec(
        backend="fasterrcnn",
        preset="dinov2_small",
        filename="original.pth",
        canonical_url="https://original.example/checkpoint.pth",
        override="model.train.backbone_weights",
        hub=HubAsset(repository="timm/example", cache_dir=tmp_path / "hub"),
    )
    if weight_cached:
        repo = tmp_path / "hub" / "models--timm--example"
        commit = "a" * 40
        snapshot = repo / "snapshots" / commit
        snapshot.mkdir(parents=True)
        (snapshot / "pytorch_model.bin").write_bytes(WEIGHT)
        (repo / "refs").mkdir()
        (repo / "refs" / "main").write_text(commit)
    monkeypatch.setattr(hub, "hf_hub_download", lambda **kw: pytest.fail("Hub download requested"))
    monkeypatch.setattr(
        hub, "get_hf_file_metadata", lambda **kw: pytest.fail("Hub metadata requested")
    )
    with pytest.raises(resolver.AssetResolutionError, match="local cache"):
        resolver.resolve_asset(spec, local_only=True)


def test_bulk_success_from_release_does_not_contact_original_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.assets import preparation, resolver

    spec, manifest, archive = fixture_bundle(tmp_path)
    monkeypatch.setattr(bundles, "load_manifest", lambda: manifest)
    monkeypatch.setattr(
        preparation, "_discover", lambda: ("release-success", (), (("example/small", spec),), ())
    )
    monkeypatch.setattr(
        bundles,
        "download",
        lambda url, destination, **kwargs: destination.write_bytes(archive.read_bytes()),
    )
    monkeypatch.setattr(resolver, "_download", lambda *args: pytest.fail("original host requested"))
    result = preparation.prepare_catalogue(automatic=False)
    assert not result.failures
    assert len(result.assets) == 1
    assert result.assets[0].path.read_bytes() == WEIGHT
