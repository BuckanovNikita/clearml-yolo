"""Explicitly assemble complete, independently downloadable native weight bundles."""

import argparse
import hashlib
import json
import stat
import sys
import tarfile
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from clearml_yolo.adapters.assets.hub import (
    _etag_matches,  # noqa: PLC2701 -- native cache validation
    _native_identity,  # noqa: PLC2701 -- native cache provenance
    _validate_config_data,  # noqa: PLC2701 -- native config validation
)
from clearml_yolo.adapters.assets.preparation import _discover  # noqa: PLC2701 -- full catalogue
from clearml_yolo.adapters.assets.resolver import resolve_asset
from clearml_yolo.adapters.assets.validation import validate_asset
from clearml_yolo.core.assets import AssetSpec, ResolvedAsset
from clearml_yolo.core.weight_bundles import (
    BundleArchive,
    BundleAsset,
    BundleConfig,
    BundleHub,
    BundleManifest,
)

_DEFAULT_LIMIT = 1_900_000_000
_GITHUB_LIMIT = 2**31
_BLOCK = 512
_RECORD = 10240
_MAX_MEMBER_BYTES = 100


@dataclass(frozen=True)
class _File:
    path: Path
    member: str
    size: int
    sha256: str


@dataclass(frozen=True)
class _Prepared:
    asset: BundleAsset
    files: tuple[_File, ...]
    noncommercial: bool


def _hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _file(path: Path, member: str) -> _File:
    parts = member.split("/")
    if (
        PurePosixPath(member).is_absolute()
        or any(part in {"", ".", ".."} for part in parts)
        or "\\" in member
        or ":" in member
        or len(member.encode("utf-8")) > _MAX_MEMBER_BYTES
    ):
        raise ValueError("Unsafe or unsupported archive member name")
    if not path.is_file() or path.stat().st_size <= 0:
        raise ValueError("Archive input must be a nonempty regular file")
    return _File(path, member, path.stat().st_size, _hash(path))


def _blob_etag(path: Path, spec: AssetSpec, digest: str) -> tuple[str, str]:
    hub = spec.hub
    if hub is None:
        raise ValueError("Hub metadata requires a Hub request")
    commit, etag = _native_identity(path, hub)
    if etag is None:
        # Native Windows caches can contain plain snapshot copies. Only retain
        # an ETag if its real native blob exists and verifies, never invent one.
        git_hash = hashlib.sha1(usedforsecurity=False)
        git_hash.update(f"blob {path.stat().st_size}\0".encode())
        with path.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                git_hash.update(block)
        root = hub.cache_dir / ("models--" + hub.repository.replace("/", "--"))
        for candidate in (digest, git_hash.hexdigest()):
            blob = root / "blobs" / candidate
            if blob.is_file() and _hash(blob) == digest:
                etag = candidate
                break
    if etag is None or not _etag_matches(path, etag, digest):
        raise ValueError("Native Hub snapshot has no verified real blob ETag")
    return commit, etag


def _prepare(spec: AssetSpec, resolve: Callable[[AssetSpec], ResolvedAsset]) -> _Prepared:
    # Resolve the original tar request directly, even when an extracted DEIM
    # tree exists. Packaging arbitrary trees loses the pinned upstream bytes.
    resolved = resolve(spec)
    if resolved.content_kind != "file":
        raise ValueError("Packaging requires the original native file")
    filename = resolved.path.name if spec.hub is not None else spec.filename
    file_spec = spec.model_copy(
        update={"filename": filename, "checksum": None} if spec.hub is not None else {}
    )
    digest = validate_asset(resolved.path, file_spec)
    if digest != resolved.sha256:
        raise ValueError("Resolved asset changed before packaging")
    member = f"assets/{spec.identity}/{filename}"
    weight = _file(resolved.path, member)
    files: tuple[_File, ...] = (weight,)
    metadata: BundleHub | None = None
    if spec.hub is not None:
        commit, etag = _blob_etag(resolved.path, spec, digest)
        if resolved.revision != commit:
            raise ValueError("Resolved Hub revision differs from native snapshot")
        config_path = resolved.path.parent / "config.json"
        config = _file(config_path, f"assets/{spec.identity}/config.json")
        config_commit, config_etag = _blob_etag(config_path, spec, config.sha256)
        if config_commit != commit:
            raise ValueError("Hub config belongs to another snapshot")
        _validate_config_data(config_path, config_etag)
        metadata = BundleHub(
            repository=spec.hub.repository,
            revision=spec.hub.revision,
            commit=commit,
            filename=filename,
            etag=etag,
            config=BundleConfig(
                member=config.member, size=config.size, sha256=config.sha256, etag=config_etag
            ),
        )
        files += (config,)
    return _Prepared(
        BundleAsset(
            identity=spec.identity,
            backend=spec.backend,
            preset=spec.preset,
            filename=spec.filename,
            source_url=spec.canonical_url,
            source_revision=spec.revision,
            kind=spec.kind,
            archive="pending.tar",
            member=member,
            size=weight.size,
            sha256=weight.sha256,
            hub=metadata,
        ),
        files,
        spec.backend == "deimv2" or spec.kind == "deim-source",
    )


def _notices(directory: Path | None) -> tuple[_File, ...]:
    if directory is None:
        return ()
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Notices must be a regular directory")
    files: list[_File] = []
    for path in sorted(directory.rglob("*")):
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise ValueError("Notices cannot contain symlinks or special files")
        files.append(_file(path, "LICENSES/" + path.relative_to(directory).as_posix()))
    return tuple(files)


def _tar_size(files: Sequence[_File]) -> int:
    size = sum(_BLOCK + ((file.size + _BLOCK - 1) // _BLOCK) * _BLOCK for file in files)
    return ((size + 2 * _BLOCK + _RECORD - 1) // _RECORD) * _RECORD


def _write_tar(path: Path, files: Sequence[_File]) -> None:
    names: set[str] = set()
    with tarfile.open(path, "w", format=tarfile.USTAR_FORMAT) as archive:
        for file in sorted(files, key=lambda item: item.member):
            if file.member in names:
                raise ValueError("Duplicate archive member")
            names.add(file.member)
            info = tarfile.TarInfo(file.member)
            info.size = file.size
            info.mode = 0o644
            with file.path.open("rb") as stream:
                archive.addfile(info, stream)
    # Re-read the bytes actually written: concurrent input replacement must not
    # produce a success manifest that describes different content.
    with tarfile.open(path, "r:") as archive:
        expected = {file.member: file for file in files}
        members = archive.getmembers()
        if len(members) != len(expected):
            raise ValueError("Archive member inventory changed")
        for member in members:
            file = expected[member.name]
            member_stream = archive.extractfile(member)
            if not member.isfile() or member_stream is None or member.size != file.size:
                raise ValueError("Archive member structure changed")
            actual = hashlib.sha256()
            with member_stream:
                while block := member_stream.read(1024 * 1024):
                    actual.update(block)
            if actual.hexdigest() != file.sha256:
                raise ValueError("Archive input changed during packaging")


def _partition(
    prepared: Sequence[_Prepared],
    notices: tuple[_File, ...],
    noncommercial: bool,
    cap: int,
) -> list[list[_Prepared]]:
    groups: list[list[_Prepared]] = []
    for item in (entry for entry in prepared if entry.noncommercial == noncommercial):
        if _tar_size((*notices, *item.files)) > cap:
            raise ValueError(f"Asset {item.asset.identity} cannot fit archive cap")
        previous = tuple(file for entry in groups[-1] for file in entry.files) if groups else ()
        if not groups or _tar_size((*notices, *previous, *item.files)) > cap:
            groups.append([])
        groups[-1].append(item)
    return groups


def package_catalogue(
    requests: Sequence[AssetSpec],
    *,
    output: Path,
    tag: str,
    max_archive_bytes: int = _DEFAULT_LIMIT,
    notices: Path | None = None,
    resolve: Callable[[AssetSpec], ResolvedAsset] = resolve_asset,
) -> BundleManifest:
    """Validate every request and atomically publish a complete local snapshot.

    The caller supplies the complete discovered inventory; discovery failures
    must be rejected before invoking this function. No SDK model is loaded and
    no GitHub upload is performed.
    """
    if not 0 < max_archive_bytes < _GITHUB_LIMIT:
        raise ValueError("Archive cap must be positive and below 2 GiB")
    if not requests:
        raise ValueError("Cannot package an empty catalogue")
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Output directory must be empty")
    unique: dict[str, AssetSpec] = {}
    for spec in sorted(requests, key=lambda item: (item.identity, item.backend, item.preset)):
        previous = unique.get(spec.identity)
        if previous is not None and (previous.kind != spec.kind or previous.hub != spec.hub):
            raise ValueError("Conflicting requests share an asset identity")
        unique.setdefault(spec.identity, spec)
    notice_files = _notices(notices)
    prepared = [_prepare(spec, resolve) for spec in unique.values()]
    assets: list[BundleAsset] = []
    archives: list[BundleArchive] = []
    with tempfile.TemporaryDirectory(prefix=".weight-bundles-", dir=output.parent) as temporary:
        staging = Path(temporary)
        for noncommercial in (False, True):
            groups = _partition(prepared, notice_files, noncommercial, max_archive_bytes)
            for index, group in enumerate(groups, start=1):
                label = "deim-noncommercial" if noncommercial else "weights"
                name = f"{label}-{index:03d}.tar"
                files = (*notice_files, *(file for item in group for file in item.files))
                path = staging / name
                _write_tar(path, files)
                if (
                    path.stat().st_size != _tar_size(files)
                    or path.stat().st_size > max_archive_bytes
                ):
                    raise ValueError("Actual archive exceeds planned size")
                archives.append(
                    BundleArchive(name=name, size=path.stat().st_size, sha256=_hash(path))
                )
                assets.extend(item.asset.model_copy(update={"archive": name}) for item in group)
        manifest = BundleManifest(
            schema_version=1,
            repository="BuckanovNikita/clearml-yolo",
            release_tag=tag,
            archives=tuple(archives),
            assets=tuple(sorted(assets, key=lambda item: item.identity)),
        )
        manifest_path = staging / "manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
        sums = [f"{archive.sha256}  {archive.name}\n" for archive in archives]
        sums.append(f"{_hash(manifest_path)}  manifest.json\n")
        (staging / "SHA256SUMS").write_text("".join(sums), encoding="utf-8")
        for path in sorted(staging.iterdir(), key=lambda path: path.name == "manifest.json"):
            path.replace(output / path.name)
    return manifest


def main() -> None:
    """Discover and package the full eligible catalogue, failing closed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--max-archive-bytes", type=int, default=_DEFAULT_LIMIT)
    parser.add_argument("--notices", type=Path)
    args = parser.parse_args()
    _, _, requests, failures = _discover()
    if failures:
        raise RuntimeError(
            "Incomplete catalogue discovery: " + ", ".join(f.selection for f in failures)
        )
    manifest = package_catalogue(
        [spec for _, spec in requests],
        output=args.output,
        tag=args.tag,
        max_archive_bytes=args.max_archive_bytes,
        notices=args.notices,
    )
    sys.stdout.write(
        json.dumps({"archives": len(manifest.archives), "assets": len(manifest.assets)}) + "\n"
    )


if __name__ == "__main__":
    main()
