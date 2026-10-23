"""Resolve native assets with proxy fallback, atomic publication and offline recovery."""

import hashlib
import json
import os
import tarfile
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests
from filelock import FileLock, Timeout

from clearml_yolo.adapters.assets.archive import validate_archive
from clearml_yolo.adapters.assets.http import download as _download
from clearml_yolo.adapters.assets.http import redacted_url
from clearml_yolo.adapters.storage.filesystem import cy_home, write_path
from clearml_yolo.core.assets import AssetSpec, ResolvedAsset

_ATTEMPTS = 2
_LOCK_TIMEOUT = 1260
_MIN_JSON_BYTES = 2
_OFFSET_PAIR_SIZE = 2


class AssetResolutionError(RuntimeError):
    """Every known unavailable asset with original sources and offline destinations."""


def asset_destination(spec: AssetSpec) -> Path:
    root = cy_home() / ".cache" / "clearml-yolo"
    if spec.kind == "deim-source":
        return write_path(root / "sources" / "DEIMv2" / spec.filename)
    return write_path(root / "models" / spec.backend / spec.preset / spec.identity / spec.filename)


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


def _safetensors(path: Path) -> None:
    size = path.stat().st_size
    with path.open("rb") as stream:
        length = int.from_bytes(stream.read(8), "little")
        if length < _MIN_JSON_BYTES or length > min(size - 8, 100_000_000):
            raise ValueError("Invalid safetensors header length")
        header = json.loads(stream.read(length))
    if not isinstance(header, dict) or not header:
        raise ValueError("Invalid safetensors header")
    ends = []
    for key, value in header.items():
        if key == "__metadata__":
            continue
        if not isinstance(value, dict) or not isinstance(value.get("data_offsets"), list):
            raise TypeError("Invalid safetensors tensor offsets")
        offsets = value["data_offsets"]
        if len(offsets) != _OFFSET_PAIR_SIZE or not all(isinstance(item, int) for item in offsets):
            raise TypeError("Invalid safetensors tensor offsets")
        if not 0 <= offsets[0] <= offsets[1] <= size - 8 - length:
            raise ValueError("Truncated safetensors data")
        ends.append(offsets[1])
    if not ends or max(ends) != size - 8 - length:
        raise ValueError("Incomplete safetensors payload")


def validate_asset(path: Path, spec: AssetSpec) -> str:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Asset is missing or empty")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if spec.checksum:
        actual = digest
        if spec.checksum_algorithm == "md5":
            with path.open("rb") as stream:
                actual = hashlib.file_digest(
                    stream, lambda: hashlib.md5(usedforsecurity=False)
                ).hexdigest()
        if not actual.startswith(spec.checksum.lower()):
            raise ValueError(f"Asset {spec.checksum_algorithm} checksum mismatch")
    if spec.kind == "deim-source":
        validate_archive(path)
    elif spec.filename.endswith(".safetensors"):
        _safetensors(path)
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None or not any(
                name.endswith("/data.pkl") for name in archive.namelist()
            ):
                raise ValueError("Invalid native Torch checkpoint archive")
    else:
        with path.open("rb") as stream:
            prefix = stream.read(16)
        # Legacy Torch serialization begins with its pickled magic integer. Loading
        # and native shape validation remain backend responsibilities, using safe loaders.
        if not prefix.startswith(b"\x80\x02\x8a\x0a\x6c\xfc\x9c\x46\xf9\x20\x6a\xa8\x50\x19"):
            raise ValueError("Asset is not a supported native checkpoint")
    return digest


def _record(spec: AssetSpec, path: Path, digest: str) -> ResolvedAsset:
    return ResolvedAsset(
        canonical_url=spec.canonical_url,
        path=path.expanduser().absolute(),
        sha256=digest,
        override=spec.override,
        revision=spec.revision,
    )


def _existing(spec: AssetSpec, destination: Path) -> ResolvedAsset | None:
    for candidate in (destination, *spec.cache_candidates):
        try:
            return _record(spec, candidate, validate_asset(candidate, spec))
        except (OSError, ValueError, TypeError, tarfile.TarError, zipfile.BadZipFile):
            continue
    for cached in spec.equivalent_caches:
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
        f"  Original URL: {spec.canonical_url}\n  Local destination: {destination.resolve()}\n"
        f"  Override: {spec.override}={override_path.resolve()}{access}\n  Attempts: {reason}"
    )


def resolve_asset(spec: AssetSpec) -> ResolvedAsset:
    destination = asset_destination(spec)
    existing = _existing(spec, destination)
    if existing is not None:
        return existing
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(write_path(str(destination) + ".lock"), timeout=_LOCK_TIMEOUT):
            existing = _existing(spec, destination)
            return existing if existing is not None else _retrieve(spec, destination)
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
