"""Populate native Hub caches without changing SDK endpoint or cache selectors."""

import hashlib
import json
import logging  # noqa: TID251 -- sanitize the third-party SDK's stdlib logging boundary
import os
import re
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import partial
from pathlib import Path, PurePosixPath
from threading import RLock
from typing import Any, override

from filelock import FileLock, Timeout
from huggingface_hub import (
    HfFileMetadata,
    constants,
    get_hf_file_metadata,
    hf_hub_download,
    hf_hub_url,
    try_to_load_from_cache,
)
from huggingface_hub.utils import validate_repo_id  # type: ignore[attr-defined]
from huggingface_hub.utils.tqdm import tqdm as hub_progress

from clearml_yolo.adapters.assets.storage import promote_asset
from clearml_yolo.adapters.assets.validation import validate_asset
from clearml_yolo.adapters.storage.filesystem import cy_home
from clearml_yolo.core.assets import AssetSpec, HubAsset, ResolvedAsset
from clearml_yolo.core.weight_bundles import BundleAsset

_PUBLIC_ENDPOINT = "https://huggingface.co"
_COMMIT = re.compile(r"[0-9a-fA-F]{40}")
_ETAG = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")
_SHA256_LENGTH = 64
_SNAPSHOT_COMPONENTS = 3
_SDK_DIAGNOSTIC_NAMESPACES = ("huggingface_hub", "httpx2", "httpcore2", "hpack")
# HTTPX lazily imports HTTPcore, whose optional HTTP/2 stack lazily imports
# HPACK. Register their concrete source loggers before the guarded request so
# first-use transport/header diagnostics cannot precede filter installation.
_LAZY_TRANSPORT_LOGGERS = (
    "httpx2",
    "httpcore2.connection",
    "httpcore2.http11",
    "httpcore2.http2",
    "httpcore2.proxy",
    "httpcore2.socks",
    "hpack.hpack",
    "hpack.table",
)


class HubResolutionError(RuntimeError):
    """A sanitized native Hub preparation failure."""


class _AssetDownloadProgress(hub_progress):
    """Per-call quiet progress for both HTTP and native Xet transfer reporters."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # The SDK passes transport-specific tqdm options through this public
        # hook. Keep the full tqdm protocol for Xet callbacks without rendering
        # SDK-generated descriptions, which can contain signed download URLs.
        kwargs["disable"] = True
        kwargs["desc"] = "Preparing model asset"
        super().__init__(*args, **kwargs)  # type: ignore[no-untyped-call]


class _SdkDiagnosticFilter(logging.Filter):
    def __init__(self, active: ContextVar[bool]) -> None:
        super().__init__()
        self.active = active

    @override
    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        if not self.active.get():
            return record
        # Replace the source record before any handler sees it. A fresh record
        # also discards raw args, cached exception text, stack and custom fields;
        # changing only msg leaves credential-bearing material for formatters.
        return logging.LogRecord(
            name=record.name,
            level=record.levelno,
            pathname=record.pathname,
            lineno=record.lineno,
            msg="Hugging Face SDK diagnostic redacted during model asset preparation",
            args=(),
            exc_info=None,
            func=record.funcName,
            sinfo=None,
        )


class _SdkDiagnostics:
    def __init__(self) -> None:
        self.lock = RLock()
        self.active = ContextVar("cy_hub_sdk_diagnostics", default=False)
        self.filter = _SdkDiagnosticFilter(self.active)
        self.users = 0
        self.loggers: set[logging.Logger] = set()


_SDK_DIAGNOSTICS: dict[str, _SdkDiagnostics] = {}


def _sdk_diagnostics_state() -> _SdkDiagnostics:
    existing = _SDK_DIAGNOSTICS.get("sdk")
    if existing is not None:
        return existing
    # The atomic dictionary operation selects one shared instance even when the
    # first calls overlap. Unselected instances never touch logging settings.
    return _SDK_DIAGNOSTICS.setdefault("sdk", _SdkDiagnostics())


@contextmanager
def _safe_sdk_diagnostics() -> Iterator[None]:
    state = _sdk_diagnostics_state()
    with state.lock:
        for name in _LAZY_TRANSPORT_LOGGERS:
            logging.getLogger(name)
        # getChildren() omits descendant loggers when intermediate dotted names
        # are placeholders (as with huggingface_hub.utils._http). Snapshot the
        # registry instead of creating those parents and changing logger ancestry.
        registered = logging.Logger.manager.loggerDict.copy()
        for name, logger in registered.items():
            if not isinstance(logger, logging.Logger) or not any(
                name == namespace or name.startswith(namespace + ".")
                for namespace in _SDK_DIAGNOSTIC_NAMESPACES
            ):
                continue
            if logger not in state.loggers:
                logger.addFilter(state.filter)
                state.loggers.add(logger)
        state.users += 1
    token = state.active.set(True)
    try:
        yield
    finally:
        state.active.reset(token)
        with state.lock:
            state.users -= 1
            if state.users == 0:
                # Reference counting keeps overlapping calls protected while
                # their peers finish. Preserve every caller-owned filter and all
                # levels, handlers, propagation and disabled settings.
                for logger in state.loggers:
                    logger.removeFilter(state.filter)
                state.loggers.clear()


def _sdk_call[T](operation: Callable[[], T]) -> T:
    try:
        with _safe_sdk_diagnostics():
            return operation()
    except Exception as error:
        # This SDK boundary handles transport, auth, OIDC and cache errors whose
        # messages may contain tokens or signed URLs. Preserve the cause privately.
        raise HubResolutionError(type(error).__name__) from error


def _request(spec: AssetSpec) -> HubAsset:
    if spec.hub is None:
        raise ValueError("A Hub asset request is required")
    return spec.hub


def _relative(value: str) -> Path:
    parts = PurePosixPath(value)
    if parts.is_absolute() or "\\" in value or any(p in {".", ".."} for p in value.split("/")):
        raise ValueError("Invalid Hub cache relative path")
    return Path(*parts.parts)


def _contained(root: Path, path: Path) -> Path:
    try:
        contained = path.resolve().is_relative_to(root.resolve())
    except RuntimeError as error:
        raise ValueError("Invalid Hub cache symlink") from error
    if not contained:
        raise ValueError("Hub cache entry escapes its configured root")
    return path


def _repo_root(hub: HubAsset) -> Path:
    validate_repo_id(hub.repository)
    return _contained(
        hub.cache_dir, hub.cache_dir / ("models--" + hub.repository.replace("/", "--"))
    )


def _filenames(hub: HubAsset) -> tuple[str, ...]:
    _relative(hub.filename)
    if hub.filename.endswith(".safetensors"):
        return (hub.filename,)
    if hub.filename == "pytorch_model.bin":
        return ("model.safetensors", hub.filename)
    if hub.filename == "open_clip_pytorch_model.bin":
        return ("open_clip_model.safetensors", hub.filename)
    if hub.filename.endswith(".bin"):
        return (hub.filename[:-4] + ".safetensors", hub.filename)
    return (hub.filename,)


def _etag_matches(path: Path, etag: str, digest: str) -> bool:
    if not _ETAG.fullmatch(etag):
        return False
    if len(etag) == _SHA256_LENGTH:
        return digest == etag.lower()
    git_digest = hashlib.sha1(usedforsecurity=False)
    git_digest.update(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as incoming:
        while block := incoming.read(1024 * 1024):
            git_digest.update(block)
    return git_digest.hexdigest() == etag.lower()


def _native_identity(path: Path, hub: HubAsset) -> tuple[str, str | None]:
    root = _repo_root(hub)
    _contained(hub.cache_dir, path)
    relative = path.absolute().relative_to(root.absolute())
    if len(relative.parts) < _SNAPSHOT_COMPONENTS or relative.parts[0] != "snapshots":
        raise ValueError("Hub SDK returned a path outside its native snapshot")
    commit = relative.parts[1]
    if not _COMMIT.fullmatch(commit):
        raise ValueError("Invalid native Hub snapshot commit")
    blob = path.resolve()
    etag = blob.name if blob.parent == root.resolve() / "blobs" else None
    return commit, etag


def _file_spec(spec: AssetSpec, filename: str) -> AssetSpec:
    # Original URL checksums describe another serialization. Native Hub ETags
    # validate the selected representation independently.
    return spec.model_copy(
        update={"filename": filename, "checksum": None, "checksum_algorithm": "sha256"}
    )


def _record(path: Path, spec: AssetSpec, filename: str) -> ResolvedAsset:
    hub = _request(spec)
    commit, etag = _native_identity(path, hub)
    digest = validate_asset(path, _file_spec(spec, filename))
    if etag is not None and not _etag_matches(path, etag, digest):
        raise ValueError("Native Hub blob checksum mismatch")
    return ResolvedAsset(
        canonical_url=hf_hub_url(
            hub.repository, filename, revision=commit, endpoint=_PUBLIC_ENDPOINT
        ),
        path=path.absolute(),
        sha256=digest,
        override=spec.override,
        revision=commit,
    )


def _cached(spec: AssetSpec) -> tuple[ResolvedAsset | None, set[str]]:
    hub = _request(spec)
    corrupt: set[str] = set()
    for filename in _filenames(hub):
        cached = try_to_load_from_cache(
            hub.repository, filename, cache_dir=hub.cache_dir, revision=hub.revision
        )
        if not isinstance(cached, str):
            continue
        try:
            result = _record(Path(cached), spec, filename)
        except (OSError, ValueError):
            corrupt.add(filename)
        else:
            # A present corrupt preferred representation blocks native loading;
            # hiding it behind a valid binary would falsely report readiness.
            if not corrupt:
                return result, corrupt
    return None, corrupt


def _endpoints() -> tuple[tuple[str, bool | None], ...]:
    configured = constants.ENDPOINT.rstrip("/")
    if configured == _PUBLIC_ENDPOINT:
        return ((configured, None),)
    # HF_TOKEN can be an Artifactory credential. Never reuse it at the fallback
    # origin; SDK token=False also suppresses implicit stored credentials.
    return ((configured, None), (_PUBLIC_ENDPOINT, False))


def _legacy_candidates(spec: AssetSpec) -> tuple[Path, ...]:
    legacy = (
        cy_home()
        / ".cache"
        / "clearml-yolo"
        / "models"
        / spec.backend
        / spec.preset
        / spec.identity
        / spec.filename
    )
    return (*spec.cache_candidates, *(cached.path for cached in spec.equivalent_caches), legacy)


def _publish_legacy(
    source: Path, spec: AssetSpec, filename: str, metadata: HfFileMetadata, digest: str
) -> ResolvedAsset:
    hub = _request(spec)
    commit, etag = metadata.commit_hash, metadata.etag
    if commit is None or not _COMMIT.fullmatch(commit) or etag is None:
        raise ValueError("Legacy promotion requires real Hub metadata")
    if not _etag_matches(source, etag, digest):
        raise ValueError("Legacy checkpoint is not the native Hub representation")
    repo = _repo_root(hub)
    blob = _contained(hub.cache_dir, repo / "blobs" / etag)
    snapshot = _contained(hub.cache_dir, repo / "snapshots" / commit / _relative(filename))

    # Copy instead of consuming the old cache. Validate staging against metadata
    # too, so a concurrently replaced source cannot publish mismatched bytes.
    def validate_staging(path: Path) -> str:
        actual = validate_asset(path, _file_spec(spec, filename))
        if not _etag_matches(path, etag, actual):
            raise ValueError("Legacy checkpoint changed during promotion")
        return actual

    promote_asset(source, blob, validator=validate_staging)
    # Preserve the native blob link where the filesystem supports symlinks. A
    # plain snapshot copy is the SDK's supported fallback on other filesystems.
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=snapshot.parent, delete=False) as temporary:
        link = Path(temporary.name)
    link.unlink()
    try:
        try:
            link.symlink_to(os.path.relpath(blob, snapshot.parent))
            link.replace(snapshot)
        except OSError:
            promote_asset(blob, snapshot, validator=validate_staging)
    finally:
        link.unlink(missing_ok=True)
    if hub.revision != commit:
        reference = _contained(hub.cache_dir, repo / "refs" / _relative(hub.revision))
        reference.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=reference.parent, delete=False) as temporary:
            temporary.write(commit.encode())
            temporary.flush()
            os.fsync(temporary.fileno())
            staging = Path(temporary.name)
        try:
            staging.replace(reference)
        finally:
            staging.unlink(missing_ok=True)
    return _record(snapshot, spec, filename)


def _legacy_metadata(candidate: Path, hub: HubAsset, filename: str) -> HfFileMetadata | None:
    """Reuse known native metadata without inventing commits for URL checkpoints."""
    parts = candidate.absolute().parts
    for index, part in enumerate(parts):
        if part != "snapshots" or index < 1 or index + 2 >= len(parts):
            continue
        if parts[index - 1] != "models--" + hub.repository.replace("/", "--"):
            continue
        commit = parts[index + 1]
        if not _COMMIT.fullmatch(commit) or Path(*parts[index + 2 :]) != _relative(filename):
            continue
        repo = Path(*parts[:index])
        reference = repo / "refs" / _relative(hub.revision)
        if hub.revision != commit and (
            not reference.is_file() or reference.read_text().strip() != commit
        ):
            continue
        blob = candidate.resolve()
        if blob.parent != repo / "blobs" or not _ETAG.fullmatch(blob.name):
            continue
        return HfFileMetadata(
            commit_hash=commit,
            etag=blob.name,
            size=candidate.stat().st_size,
            location=hf_hub_url(
                hub.repository, filename, revision=commit, endpoint=_PUBLIC_ENDPOINT
            ),
            xet_file_data=None,
        )
    return None


def _copy_legacy_config(candidate: Path, spec: AssetSpec, commit: str) -> None:
    hub = _request(spec)
    for snapshot in candidate.absolute().parents:
        if snapshot.name != commit or snapshot.parent.name != "snapshots":
            continue
        source = snapshot / "config.json"
        if not source.is_file():
            return
        source_hub = hub.model_copy(update={"cache_dir": snapshot.parent.parent.parent})
        _, etag = _native_identity(source, source_hub)
        _validate_config(source, source_hub)
        repo = _repo_root(hub)
        destination = _contained(hub.cache_dir, repo / "snapshots" / commit / "config.json")

        validate_copy = partial(_validate_config_data, etag=etag)

        if etag is not None:
            blob = _contained(hub.cache_dir, repo / "blobs" / etag)
            promote_asset(source, blob, validator=validate_copy)
        promote_asset(source, destination, validator=validate_copy)
        return


def _promote(spec: AssetSpec) -> ResolvedAsset | None:
    hub = _request(spec)
    for filename in _filenames(hub):
        for candidate in _legacy_candidates(spec):
            try:
                digest = validate_asset(candidate, _file_spec(spec, filename))
            except (OSError, ValueError):
                continue
            metadata = _legacy_metadata(candidate, hub, filename)
            if metadata is not None:
                try:
                    result = _publish_legacy(candidate, spec, filename, metadata, digest)
                    commit, _ = _native_identity(result.path, hub)
                    _copy_legacy_config(candidate, spec, commit)
                except (OSError, ValueError):
                    continue
                else:
                    return result
            for endpoint, token in _endpoints():
                try:
                    metadata = _sdk_call(
                        partial(
                            get_hf_file_metadata,
                            hf_hub_url(
                                hub.repository, filename, revision=hub.revision, endpoint=endpoint
                            ),
                            token=token,
                            endpoint=endpoint,
                        )
                    )
                    return _publish_legacy(candidate, spec, filename, metadata, digest)
                except (HubResolutionError, OSError, ValueError):
                    continue
    return None


def _config(spec: AssetSpec, commit: str, endpoint: str, token: bool | None) -> None:
    hub = _request(spec)
    existing = try_to_load_from_cache(
        hub.repository, "config.json", cache_dir=hub.cache_dir, revision=commit
    )
    force = False
    if isinstance(existing, str):
        try:
            _validate_config(Path(existing), hub)
        except (OSError, ValueError):
            force = True
        else:
            return
    path = _sdk_call(
        partial(
            hf_hub_download,
            repo_id=hub.repository,
            filename="config.json",
            revision=commit,
            cache_dir=hub.cache_dir,
            endpoint=endpoint,
            token=token,
            force_download=force,
            tqdm_class=_AssetDownloadProgress,
        )
    )
    _validate_config(Path(path), hub)


def _validate_config(path: Path, hub: HubAsset) -> None:
    _, etag = _native_identity(path, hub)
    _validate_config_data(path, etag)


def _validate_config_data(path: Path, etag: str | None) -> str:
    data = path.read_bytes()
    if not isinstance(json.loads(data), dict):
        raise ValueError("Invalid native model config")  # noqa: TRY004 -- invalid file content
    digest = hashlib.sha256(data).hexdigest()
    if etag is not None and not _etag_matches(path, etag, digest):
        raise ValueError("Native model config checksum mismatch")
    return digest


def _needs_config_repair(spec: AssetSpec, result: ResolvedAsset) -> bool:
    hub = _request(spec)
    commit, _ = _native_identity(result.path, hub)
    config = try_to_load_from_cache(
        hub.repository, "config.json", cache_dir=hub.cache_dir, revision=commit
    )
    if not isinstance(config, str):
        # We cannot distinguish a historical weight-only cache from a previous
        # preparation attempt whose config download failed. Both need repair
        # before the complete Hub request can be reported as prepared.
        return True
    try:
        _validate_config(Path(config), hub)
    except (OSError, ValueError):
        return True
    return False


def _failure(hub: HubAsset, failures: list[str]) -> HubResolutionError:
    return HubResolutionError(
        f"Native Hub asset unavailable: {hub.repository}@{hub.revision}; "
        f"cache {hub.cache_dir}; attempts: {', '.join(failures)}"
    )


def _repair_config(spec: AssetSpec, existing: ResolvedAsset) -> ResolvedAsset:
    hub = _request(spec)
    commit, _ = _native_identity(existing.path, hub)
    failures: list[str] = []
    for endpoint, token in _endpoints():
        try:
            _config(spec, commit, endpoint, token)
        except (HubResolutionError, OSError, ValueError) as error:
            failures.append(type(error).__name__)
        else:
            return existing
    raise _failure(hub, failures)


def _ready(spec: AssetSpec) -> ResolvedAsset:
    ready, _ = _cached(spec)
    if ready is None:
        raise ValueError("Preferred native Hub representation remains corrupt")
    return ready


def _retrieve_one(
    spec: AssetSpec, filename: str, endpoint: str, token: bool | None, force: bool
) -> ResolvedAsset:
    hub = _request(spec)
    path = _sdk_call(
        partial(
            hf_hub_download,
            repo_id=hub.repository,
            filename=filename,
            revision=hub.revision,
            cache_dir=hub.cache_dir,
            endpoint=endpoint,
            token=token,
            force_download=force,
            tqdm_class=_AssetDownloadProgress,
        )
    )
    _record(Path(path), spec, filename)
    commit, _ = _native_identity(Path(path), hub)
    _config(spec, commit, endpoint, token)
    return _ready(spec)


def _retrieve(spec: AssetSpec, corrupt: set[str]) -> ResolvedAsset:
    hub = _request(spec)
    failures: list[str] = []
    for endpoint, token in _endpoints():
        for filename in _filenames(hub):
            try:
                result = _retrieve_one(spec, filename, endpoint, token, filename in corrupt)
            except (HubResolutionError, OSError, ValueError) as error:
                failures.append(type(error).__name__)
            else:
                return result
    raise _failure(hub, failures)


def _resolve_hub_asset(spec: AssetSpec, *, local_only: bool = False) -> ResolvedAsset:
    """Resolve timm's selected representation into the ordinary native Hub cache."""
    hub = _request(spec)
    _repo_root(hub)
    _relative(hub.revision)
    existing, _ = _cached(spec)
    if existing is not None and not _needs_config_repair(spec, existing):
        return existing
    if local_only:
        raise _failure(hub, ["local cache lacks validated weights or config.json"])
    key = hashlib.sha256(f"{hub.repository}@{hub.revision}".encode()).hexdigest()
    lock = _contained(hub.cache_dir, hub.cache_dir / ".locks" / "clearml-yolo" / f"{key}.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(lock, timeout=1260):
        existing, corrupt = _cached(spec)
        if existing is not None:
            if _needs_config_repair(spec, existing):
                return _repair_config(spec, existing)
            return existing
        promoted = _promote(spec)
        if promoted is not None:
            ready, _ = _cached(spec)
            if ready is not None:
                if _needs_config_repair(spec, ready):
                    return _repair_config(spec, ready)
                return ready
        return _retrieve(spec, corrupt)


def resolve_hub_asset(spec: AssetSpec, *, local_only: bool = False) -> ResolvedAsset:
    """Keep local cache, permission and locking failures within the public boundary."""
    hub = _request(spec)
    try:
        return _resolve_hub_asset(spec, local_only=local_only)
    except (OSError, ValueError, Timeout) as error:
        raise _failure(hub, [type(error).__name__]) from error


def bundle_asset_ready(spec: AssetSpec) -> bool:
    """Check complete native cache readiness without requesting Hub metadata."""
    existing, _ = _cached(spec)
    return existing is not None and not _needs_config_repair(spec, existing)


def restore_bundle_asset(
    spec: AssetSpec, asset: BundleAsset, weight_path: Path, config_path: Path
) -> ResolvedAsset:
    """Restore a real pinned snapshot without a metadata or config network request."""
    hub = _request(spec)
    metadata = asset.hub
    if (
        metadata is None
        or metadata.repository != hub.repository
        or metadata.revision != hub.revision
        or metadata.filename not in _filenames(hub)
    ):
        raise ValueError("Bundle does not match native Hub request")
    digest = validate_asset(weight_path, _file_spec(spec, metadata.filename))
    if digest != asset.sha256 or weight_path.stat().st_size != asset.size:
        raise ValueError("Bundle weight checksum mismatch")
    if not _etag_matches(weight_path, metadata.etag, digest):
        raise ValueError("Bundle weight ETag mismatch")
    config_digest = _validate_config_data(config_path, metadata.config.etag)
    if (
        config_digest != metadata.config.sha256
        or config_path.stat().st_size != metadata.config.size
    ):
        raise ValueError("Bundle config checksum mismatch")
    key = hashlib.sha256(f"{hub.repository}@{hub.revision}".encode()).hexdigest()
    lock = _contained(hub.cache_dir, hub.cache_dir / ".locks" / "clearml-yolo" / f"{key}.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(lock, timeout=1260):
        existing, _ = _cached(spec)
        if existing is not None and not _needs_config_repair(spec, existing):
            return existing
        repo = _repo_root(hub)
        blob = _contained(hub.cache_dir, repo / "blobs" / metadata.config.etag)
        snapshot = _contained(hub.cache_dir, repo / "snapshots" / metadata.commit / "config.json")
        validate_config = partial(_validate_config_data, etag=metadata.config.etag)
        promote_asset(config_path, blob, validator=validate_config)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=snapshot.parent, delete=False) as temporary:
            link = Path(temporary.name)
        link.unlink()
        try:
            try:
                link.symlink_to(os.path.relpath(blob, snapshot.parent))
                link.replace(snapshot)
            except OSError:
                promote_asset(blob, snapshot, validator=validate_config)
        finally:
            link.unlink(missing_ok=True)
        native = HfFileMetadata(
            commit_hash=metadata.commit,
            etag=metadata.etag,
            size=asset.size,
            location=hf_hub_url(
                hub.repository,
                metadata.filename,
                revision=metadata.commit,
                endpoint=_PUBLIC_ENDPOINT,
            ),
            xet_file_data=None,
        )
        return _publish_legacy(weight_path, spec, metadata.filename, native, digest)
