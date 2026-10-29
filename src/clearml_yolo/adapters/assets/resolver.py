"""Resolve native assets with proxy fallback, atomic publication and offline recovery."""

import os
import tarfile
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests
from filelock import FileLock, Timeout

from clearml_yolo.adapters.assets.http import asset_source_url, redacted_url
from clearml_yolo.adapters.assets.http import download as _download
from clearml_yolo.adapters.assets.storage import native_asset_path, promote_asset
from clearml_yolo.adapters.assets.validation import validate_asset
from clearml_yolo.adapters.storage.filesystem import cy_home, write_path
from clearml_yolo.core.assets import AssetSpec, ResolvedAsset

__all__ = [
    "AssetResolutionError",
    "asset_destination",
    "managed_asset_destination",
    "release_proxy_url",
    "resolve_asset",
    "resolve_assets",
    "source_proxy_url",
    "source_urls",
    "validate_asset",
]

_ATTEMPTS = 2
_LOCK_TIMEOUT = 1260


class AssetResolutionError(RuntimeError):
    """Every known unavailable asset with original sources and offline destinations."""


def managed_asset_destination(spec: AssetSpec) -> Path:
    root = cy_home() / ".cache" / "clearml-yolo"
    if spec.kind == "deim-source":
        return write_path(root / "sources" / "DEIMv2" / spec.filename)
    return write_path(root / "models" / spec.backend / spec.preset / spec.identity / spec.filename)


def asset_destination(spec: AssetSpec) -> Path:
    if spec.hub is not None:
        # Hub publication owns repository snapshots and refs. This is a reportable
        # repository root, not a synthetic flat checkpoint destination.
        return spec.hub.cache_dir.expanduser().resolve() / (
            "models--" + spec.hub.repository.replace("/", "--")
        )
    if spec.native_cache is not None:
        return native_asset_path(spec.native_cache, spec.filename)
    return managed_asset_destination(spec)


def release_proxy_url(url: str, root: str | None) -> str | None:
    source = urlsplit(url)
    if not root or not root.strip() or source.hostname != "github.com":
        return None
    if "/releases/download/" not in source.path:
        return None
    proxy = urlsplit(root.strip())
    return urlunsplit(
        (proxy.scheme, proxy.netloc, proxy.path.rstrip("/") + source.path, proxy.query, "")
    )


def source_proxy_url(url: str, revision: str, root: str | None) -> str | None:
    source = urlsplit(url)
    if not root or not root.strip() or source.hostname != "github.com":
        return None
    owner, repository, *_ = source.path.strip("/").split("/")
    proxy = urlsplit(root.strip())
    prefix, _, repository_key = proxy.path.rstrip("/").rpartition("/")
    if not repository_key:
        raise ValueError("GH must identify an Artifactory VCS repository root")
    path = f"{prefix}/api/vcs/downloadCommit/{repository_key}/{owner}/{repository}/{revision}"
    query = "ext=tar.gz" + (f"&{proxy.query}" if proxy.query else "")
    return urlunsplit((proxy.scheme, proxy.netloc, path, query, ""))


def source_urls(spec: AssetSpec) -> tuple[str, ...]:
    proxy = (
        source_proxy_url(spec.canonical_url, spec.revision or "", os.environ.get("GH"))
        if spec.kind == "deim-source"
        else release_proxy_url(spec.canonical_url, os.environ.get("GHR"))
    )
    return (
        (proxy, spec.canonical_url)
        if proxy and proxy != spec.canonical_url
        else (spec.canonical_url,)
    )


def _record(spec: AssetSpec, path: Path, digest: str) -> ResolvedAsset:
    return ResolvedAsset(
        canonical_url=spec.canonical_url,
        path=path.expanduser().absolute(),
        sha256=digest,
        override=spec.override,
        revision=spec.revision,
    )


def _existing(spec: AssetSpec, destination: Path) -> ResolvedAsset | None:
    for candidate in (destination, managed_asset_destination(spec), *spec.cache_candidates):
        try:
            return _record(spec, candidate, validate_asset(candidate, spec))
        except (OSError, ValueError, TypeError, tarfile.TarError, zipfile.BadZipFile):
            continue
    # Native URL discovery requires the named representation, not merely a file
    # that CY could load through an explicit override.
    for cached in () if spec.native_cache is not None else spec.equivalent_caches:
        candidate_spec = spec.model_copy(
            update={
                "canonical_url": cached.canonical_url,
                "filename": cached.path.name,
                "checksum": cached.checksum,
                "checksum_algorithm": "sha256",
            }
        )
        try:
            return _record(candidate_spec, cached.path, validate_asset(cached.path, candidate_spec))
        except (OSError, ValueError, TypeError, tarfile.TarError, zipfile.BadZipFile):
            continue
    return None


def _retrieve(spec: AssetSpec, destination: Path) -> ResolvedAsset:
    errors: list[str] = []
    with tempfile.NamedTemporaryFile(
        prefix=".asset-", dir=destination.parent, delete=False
    ) as temporary:
        staging = Path(temporary.name)
    try:
        try:
            urls = source_urls(spec)
        except ValueError:
            errors.append("Invalid configured proxy repository root")
            urls = (spec.canonical_url,)
        for url in urls:
            for _ in range(_ATTEMPTS):
                try:
                    _download(url, staging)
                    digest = validate_asset(staging, spec)
                    staging.replace(destination)
                    return _record(spec, destination, digest)
                except (
                    OSError,
                    ValueError,
                    TypeError,
                    tarfile.TarError,
                    zipfile.BadZipFile,
                    requests.RequestException,
                ) as error:
                    # Exception text can contain credentials, signed redirect URLs or tokens.
                    errors.append(f"{redacted_url(url)} ({type(error).__name__})")
    finally:
        staging.unlink(missing_ok=True)
    raise AssetResolutionError(_failure(spec, destination, "; ".join(errors)))


def _failure(spec: AssetSpec, destination: Path, reason: str) -> str:
    access = f"\n  Access: {spec.access_requirement}" if spec.access_requirement else ""
    if spec.kind == "deim-source":
        access += (
            "\n  Offline archive: leave model.source_dir=null to verify and extract it on rerun."
        )
    override_path = (
        destination.with_suffix("").with_suffix("") if spec.kind == "deim-source" else destination
    )
    return (
        f"Missing {spec.backend}/{spec.preset} asset {spec.filename}:\n"
        f"  Original URL: {asset_source_url(spec.canonical_url)}\n"
        f"  Local destination: {destination.resolve()}\n"
        f"  Override: {spec.override}={override_path.resolve()}{access}\n  Attempts: {reason}"
    )


def _publish_existing(spec: AssetSpec, record: ResolvedAsset, destination: Path) -> ResolvedAsset:
    if spec.native_cache is None or record.path == destination:
        return record
    # Alternate representations belong to their own native filenames; never put
    # safetensors bytes under a Torch URL filename or mislabel their provenance.
    if record.canonical_url != spec.canonical_url:
        return record
    promote_asset(record.path, destination, validator=lambda path: validate_asset(path, spec))
    return _record(spec, destination, validate_asset(destination, spec))


def resolve_asset(spec: AssetSpec) -> ResolvedAsset:
    if spec.hub is not None:
        from clearml_yolo.adapters.assets.hub import HubResolutionError, resolve_hub_asset

        try:
            return resolve_hub_asset(spec)
        except HubResolutionError as error:
            raise AssetResolutionError(str(error)) from error
    destination = asset_destination(spec)
    existing = _existing(spec, destination)
    if existing is not None and (spec.native_cache is None or existing.path == destination):
        return existing
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock = (
            native_asset_path(spec.native_cache, spec.filename + ".lock")
            if spec.native_cache is not None
            else write_path(str(destination) + ".lock")
        )
        with FileLock(lock, timeout=_LOCK_TIMEOUT):
            existing = _existing(spec, destination)
            return (
                _publish_existing(spec, existing, destination)
                if existing is not None
                else _retrieve(spec, destination)
            )
    except Timeout as error:
        raise AssetResolutionError(_failure(spec, destination, "asset lock timeout")) from error


def resolve_assets(specs: tuple[AssetSpec, ...]) -> tuple[ResolvedAsset, ...]:
    resolved: list[ResolvedAsset] = []
    failures: list[str] = []
    for spec in specs:
        try:
            resolved.append(resolve_asset(spec))
        except AssetResolutionError as error:
            failures.append(str(error))
    if failures:
        raise AssetResolutionError(
            "Model asset preparation failed. Copy the original files to the listed destinations "
            "and rerun offline; no download receipt is required.\n" + "\n".join(failures)
        )
    return tuple(resolved)
