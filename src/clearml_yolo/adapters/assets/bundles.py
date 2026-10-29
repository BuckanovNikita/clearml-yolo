"""Seed ordinary native caches from pinned, verified release archives."""

import hashlib
import os
import shutil
import tarfile
import tempfile
import zipfile
from importlib.resources import files
from pathlib import Path

import requests
from filelock import FileLock, Timeout
from loguru import logger
from pydantic import ValidationError

from clearml_yolo.adapters.assets.http import download
from clearml_yolo.adapters.assets.hub import bundle_asset_ready, restore_bundle_asset
from clearml_yolo.adapters.assets.resolver import asset_destination, release_proxy_url
from clearml_yolo.adapters.assets.storage import promote_asset
from clearml_yolo.adapters.assets.validation import validate_asset
from clearml_yolo.adapters.storage.filesystem import cy_home, write_path
from clearml_yolo.core.assets import AssetSpec
from clearml_yolo.core.weight_bundles import (
    BundleArchive,
    BundleAsset,
    BundleManifest,
    safe_member,
)


def load_manifest() -> BundleManifest | None:
    """Read the installed pin only; source checkouts may precede initial packaging."""
    resource = files("clearml_yolo.adapters.assets").joinpath("weights-manifest.json")
    try:
        return BundleManifest.model_validate_json(resource.read_bytes())
    except FileNotFoundError:
        return None


def _verify(path: Path, size: int, digest: str) -> str:
    if path.stat().st_size != size:
        raise ValueError("Bundle size mismatch")
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != digest:
        raise ValueError("Bundle checksum mismatch")
    return actual


def _archive_path(manifest: BundleManifest, archive: BundleArchive) -> Path:
    root = write_path(cy_home() / ".cache" / "clearml-yolo" / "weight-bundles")
    root.mkdir(parents=True, exist_ok=True)
    destination = write_path(root / f"{archive.sha256}.tar")
    with FileLock(str(destination) + ".lock", timeout=1260):
        try:
            _verify(destination, archive.size, archive.sha256)
        except (OSError, ValueError):
            pass
        else:
            return destination
        original = (
            f"https://github.com/{manifest.repository}/releases/download/"
            f"{manifest.release_tag}/{archive.name}"
        )
        proxy = release_proxy_url(original, os.environ.get("GHR"))
        urls = (proxy, original) if proxy and proxy != original else (original,)
        with tempfile.NamedTemporaryFile(dir=root, delete=False) as stream:
            staging = Path(stream.name)
        try:
            for url in urls:
                for _ in range(2):
                    try:
                        download(url, staging)
                        _verify(staging, archive.size, archive.sha256)
                        staging.replace(destination)
                    except (OSError, ValueError, requests.RequestException):
                        continue
                    else:
                        return destination
        finally:
            staging.unlink(missing_ok=True)
    raise ValueError("Pinned release archive unavailable")


def _members(archive: tarfile.TarFile) -> dict[str, tarfile.TarInfo]:
    entries: dict[str, tarfile.TarInfo] = {}
    for entry in archive:
        safe_member(entry.name)
        if not entry.isfile() or entry.name in entries:
            raise ValueError("Unsafe or duplicate bundle member")
        if not entry.name.startswith(("assets/", "LICENSES/")):
            raise ValueError("Unexpected bundle member")
        entries[entry.name] = entry
    return entries


def _copy_member(
    archive: tarfile.TarFile,
    members: dict[str, tarfile.TarInfo],
    member: str,
    target: Path,
    size: int,
    digest: str,
) -> None:
    entry = members.get(member)
    if entry is None or entry.size != size:
        raise ValueError("Missing or invalid bundle member size")
    incoming = archive.extractfile(entry)
    if incoming is None:
        raise ValueError("Missing regular bundle member")
    with incoming, target.open("wb") as outgoing:
        shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
    _verify(target, size, digest)


def _matches(spec: AssetSpec, asset: BundleAsset) -> bool:
    return (
        asset.identity == spec.identity
        and asset.backend == spec.backend
        and asset.preset == spec.preset
        and asset.filename == spec.filename
        and asset.source_url == spec.canonical_url
        and asset.source_revision == spec.revision
        and asset.kind == spec.kind
        and (
            (asset.hub is None and spec.hub is None)
            or (
                asset.hub is not None
                and spec.hub is not None
                and asset.hub.repository == spec.hub.repository
                and asset.hub.revision == spec.hub.revision
            )
        )
    )


def _flat_ready(spec: AssetSpec, path: Path) -> bool:
    try:
        validate_asset(path, spec)
    except (OSError, ValueError, TypeError, tarfile.TarError, zipfile.BadZipFile):
        return False
    return True


def _seed(spec: AssetSpec, manifest: BundleManifest) -> None:
    asset = next((item for item in manifest.assets if _matches(spec, item)), None)
    if asset is None:
        return
    if spec.hub is not None:
        if bundle_asset_ready(spec):
            return
    elif _flat_ready(spec, asset_destination(spec)):
        return
    record = next(item for item in manifest.archives if item.name == asset.archive)
    path = _archive_path(manifest, record)
    scratch = write_path(cy_home() / ".cache" / "clearml-yolo" / "weight-bundles")
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cy-weight-bundle-", dir=scratch) as temporary:
        weight = Path(temporary) / "weight"
        config = Path(temporary) / "config.json"
        with tarfile.open(path, mode="r:") as archive:
            members = _members(archive)
            _copy_member(archive, members, asset.member, weight, asset.size, asset.sha256)
            if asset.hub is not None:
                metadata = asset.hub.config
                _copy_member(
                    archive, members, metadata.member, config, metadata.size, metadata.sha256
                )
        if spec.hub is not None:
            restore_bundle_asset(spec, asset, weight, config)
        else:
            destination = asset_destination(spec)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with FileLock(str(destination) + ".lock", timeout=1260):
                if _flat_ready(spec, destination):
                    return

                def validate_staging(item: Path) -> str:
                    _verify(item, asset.size, asset.sha256)
                    return validate_asset(item, spec)

                promote_asset(weight, destination, validator=validate_staging)


def seed_bundle_asset(spec: AssetSpec, manifest: BundleManifest | None = None) -> None:
    """Best effort mirror seeding; normal upstream resolution remains authoritative."""
    try:
        selected = manifest if manifest is not None else load_manifest()
        if selected is not None:
            _seed(spec, selected)
    except (
        OSError,
        ValueError,
        TypeError,
        tarfile.TarError,
        Timeout,
        requests.RequestException,
        ValidationError,
        zipfile.BadZipFile,
    ) as error:
        # Never expose transport URLs, credentials, or untrusted archive messages.
        logger.warning(
            "Weight release mirror unavailable for {}: {}", spec.identity, type(error).__name__
        )
