"""Versioned shared cache for prepared CSV-owned datasets."""

import hashlib
import json
import shutil
from collections import Counter
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from filelock import FileLock
from pydantic import BaseModel, ValidationError

from clearml_yolo.adapters.observability.diagnostics import log_exception
from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.storage.dataset import PreparedDataset, prepare_dataset
from clearml_yolo.adapters.storage.dataset_export import DatasetFormat
from clearml_yolo.adapters.storage.filesystem import cy_home, write_path

PREPARATION_VERSION = 1
_COMPLETION_FILE = "completion.json"
_SUPPORTED_SPLITS = frozenset({"train", "val", "test"})


class _Completion(BaseModel):
    preparation_version: int
    identity: str
    input_sha256: str
    dataset_format: DatasetFormat
    split_counts: dict[str, int]
    required_files: list[str]
    artifacts: list[str]


def dataset_cache_root(cache_dir: str | Path | None) -> Path:
    """Resolve the shared cache location before validating output ownership."""
    if cache_dir is not None:
        return write_path(cache_dir).resolve()
    return write_path(cy_home() / ".cache" / "clearml-yolo" / "datasets").resolve()


def _identity(csv_sha256: str, dataset_format: DatasetFormat) -> str:
    payload = json.dumps(
        {
            "csv_sha256": csv_sha256,
            "dataset_format": dataset_format,
            "preparation_version": PREPARATION_VERSION,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _safe_relative(value: str) -> Path | None:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        return None
    return path


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        log_exception(
            "Ignoring unreadable dataset cache metadata",
            error,
            level="DEBUG",
            context={"source": path},
            include_message=isinstance(error, OSError),
        )
        return None
    return value if isinstance(value, dict) else None


def _read_completion(
    entry: Path,
    *,
    identity: str,
    input_sha256: str,
    dataset_format: DatasetFormat,
) -> _Completion | None:
    try:
        completion = _Completion.model_validate_json(
            (entry / _COMPLETION_FILE).read_text(encoding="utf-8")
        )
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, ValidationError, ValueError) as error:
        log_exception(
            "Ignoring invalid dataset cache completion",
            error,
            level="DEBUG",
            context={"entry": entry},
            include_message=isinstance(error, OSError),
        )
        return None
    expected = (PREPARATION_VERSION, identity, input_sha256, dataset_format)
    actual = (
        completion.preparation_version,
        completion.identity,
        completion.input_sha256,
        completion.dataset_format,
    )
    return completion if actual == expected else None


def _required_paths(entry: Path, values: list[str]) -> set[Path] | None:
    if len(values) != len(set(values)):
        return None
    paths: set[Path] = set()
    for value in values:
        relative = _safe_relative(value)
        if relative is None:
            return None
        path = entry / relative
        if not path.is_file():
            return None
        paths.add(path.resolve())
    return paths


def _image_split(item: object, required_paths: set[Path]) -> str | None:
    if not isinstance(item, dict):
        return None
    split = item.get("split")
    generated = item.get("generated_path")
    if not isinstance(split, str) or not isinstance(generated, str):
        return None
    generated_path = Path(generated)
    if not generated_path.is_absolute() or generated_path.resolve() not in required_paths:
        return None
    return split


def _validated_splits(
    entry: Path,
    *,
    input_sha256: str,
    dataset_format: DatasetFormat,
    required_paths: set[Path],
) -> dict[str, int] | None:
    preparation = _read_json_object(entry / "preparation.json")
    if (
        preparation is None
        or preparation.get("input_sha256") != input_sha256
        or preparation.get("dataset_format") != dataset_format
    ):
        return None
    raw_splits = preparation.get("splits")
    images = preparation.get("images")
    if not isinstance(raw_splits, dict) or not isinstance(images, list):
        return None
    try:
        split_counts = {str(name): int(count) for name, count in raw_splits.items()}
    except (TypeError, ValueError) as error:
        log_exception(
            "Ignoring invalid dataset cache split counts",
            error,
            level="DEBUG",
            context={"entry": entry},
            include_message=False,
        )
        return None
    observed: Counter[str] = Counter()
    for item in images:
        split = _image_split(item, required_paths)
        if split is None:
            return None
        observed[split] += 1
    return split_counts if dict(observed) == split_counts else None


def _valid_data_yaml(entry: Path, splits: dict[str, int] | None) -> bool:
    try:
        data = yaml.safe_load((entry / "data.yaml").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        log_exception(
            "Ignoring unreadable dataset cache native configuration",
            error,
            level="DEBUG",
            context={"entry": entry},
            include_message=isinstance(error, OSError),
        )
        return False
    manifest = _read_json_object(entry / "preparation.json")
    if not isinstance(data, dict) or manifest is None or not splits:
        return False
    names = data.get("names")
    return (
        data.get("path") == str(entry.resolve())
        and isinstance(names, dict)
        and bool(names)
        and {str(key): value for key, value in names.items()} == manifest.get("class_names")
        and all(data.get(split) == f"images/{split}" for split in splits)
    )


def _artifact_paths(entry: Path, values: list[str], required_paths: set[Path]) -> list[Path] | None:
    artifacts: list[Path] = []
    for value in values:
        relative = _safe_relative(value)
        if relative is None or (entry / relative).resolve() not in required_paths:
            return None
        artifacts.append(entry / relative)
    return artifacts


@trace_operation("storage.cache.validate")
def _load_completed(
    entry: Path,
    *,
    identity: str,
    input_sha256: str,
    dataset_format: DatasetFormat,
    required_splits: tuple[str, ...],
) -> PreparedDataset | None:
    completion = _read_completion(
        entry,
        identity=identity,
        input_sha256=input_sha256,
        dataset_format=dataset_format,
    )
    if completion is None:
        return None
    required_paths = _required_paths(entry, completion.required_files)
    if required_paths is None:
        return None
    minimum = {
        "data.yaml",
        "ground_truth.csv",
        "preparation.json",
        "labels.zip",
        _COMPLETION_FILE,
    }
    if dataset_format == "ndjson":
        minimum.add("dataset.ndjson")
    if not minimum.issubset(completion.required_files):
        return None
    splits = _validated_splits(
        entry,
        input_sha256=input_sha256,
        dataset_format=dataset_format,
        required_paths=required_paths,
    )
    if splits != completion.split_counts or not _valid_data_yaml(entry, splits):
        return None

    missing_splits = sorted(
        split for split in required_splits if completion.split_counts.get(split, 0) < 1
    )
    if missing_splits:
        raise ValueError(
            "Cached dataset required split(s) contain no images: " + ", ".join(missing_splits)
        )

    artifact_paths = _artifact_paths(entry, completion.artifacts, required_paths)
    if artifact_paths is None:
        return None
    return PreparedDataset(
        data=entry / "data.yaml",
        ground_truth=entry / "ground_truth.csv",
        manifest=entry / "preparation.json",
        dataset_format=dataset_format,
        artifacts=artifact_paths,
    )


def _remove_cache_owned_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


@trace_operation("storage.cache.paths.finalize")
def _rewrite_final_paths(staging: Path, entry: Path) -> None:
    data_path = staging / "data.yaml"
    data = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"Prepared dataset configuration is not a mapping: {data_path}")
    data["path"] = str(entry.resolve())
    data_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    manifest_path = staging / "preparation.json"
    manifest = _read_json_object(manifest_path)
    if manifest is None:
        raise ValueError(f"Prepared dataset manifest is not a JSON object: {manifest_path}")
    images = manifest.get("images")
    if not isinstance(images, list):
        raise TypeError(f"Prepared dataset manifest has no image inventory: {manifest_path}")
    for item in images:
        if not isinstance(item, dict):
            raise TypeError(
                f"Prepared dataset manifest has an invalid image entry: {manifest_path}"
            )
        generated = item.get("generated_path")
        if not isinstance(generated, str):
            raise TypeError(
                f"Prepared dataset manifest has an invalid generated path: {manifest_path}"
            )
        try:
            relative = Path(generated).relative_to(staging)
        except ValueError as error:
            raise ValueError(
                f"Prepared generated path is outside the staging directory: {generated}"
            ) from error
        item["generated_path"] = str(entry / relative)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


@trace_operation("storage.cache.publish")
def _publish_entry(
    source: Path,
    source_bytes: bytes,
    staging: Path,
    entry: Path,
    *,
    identity: str,
    input_sha256: str,
    dataset_format: DatasetFormat,
    required_splits: tuple[str, ...],
) -> None:
    prepared = prepare_dataset(
        source,
        staging,
        dataset_format,
        required_splits=required_splits,
        source_bytes=source_bytes,
    )
    _rewrite_final_paths(staging, entry)
    manifest = _read_json_object(staging / "preparation.json")
    if manifest is None or not isinstance(manifest.get("splits"), dict):
        raise ValueError("Prepared dataset manifest has no split counts")
    split_counts = {str(name): int(count) for name, count in manifest["splits"].items()}
    artifact_names = [path.relative_to(staging).as_posix() for path in prepared.artifacts]
    required_files = sorted(
        path.relative_to(staging).as_posix() for path in staging.rglob("*") if path.is_file()
    )
    required_files.append(_COMPLETION_FILE)
    completion = _Completion(
        preparation_version=PREPARATION_VERSION,
        identity=identity,
        input_sha256=input_sha256,
        dataset_format=dataset_format,
        split_counts=split_counts,
        required_files=required_files,
        artifacts=artifact_names,
    )
    (staging / _COMPLETION_FILE).write_text(
        completion.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    staging.rename(entry)


@contextmanager
def cached_dataset(
    source: str | Path,
    cache_dir: str | Path | None = None,
    dataset_format: DatasetFormat = "ndjson",
    required_splits: tuple[str, ...] = ("train", "val"),
) -> Iterator[PreparedDataset]:
    """Yield one reusable prepared dataset while holding its native-consumer lock."""
    if dataset_format not in {"ndjson", "flat"}:
        raise ValueError("dataset_format must be one of: ndjson, flat")
    unsupported_splits = sorted(set(required_splits) - _SUPPORTED_SPLITS)
    if unsupported_splits:
        raise ValueError(
            "Unsupported required split(s): "
            + ", ".join(unsupported_splits)
            + "; expected train, val, or test"
        )
    source_path = Path(source).expanduser().resolve()
    with trace_operation("storage.cache.source.read", context={"path": str(source_path)}):
        source_bytes = source_path.read_bytes()
    with trace_operation("storage.cache.source.hash", context={"bytes": len(source_bytes)}):
        input_sha256 = hashlib.sha256(source_bytes).hexdigest()
    identity = _identity(input_sha256, dataset_format)
    root = dataset_cache_root(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    lock_root = root / ".locks"
    lock_root.mkdir(exist_ok=True)
    entry = root / identity
    lock = FileLock(lock_root / f"{identity}.lock")

    with ExitStack() as stack:
        with trace_operation("storage.cache.lock.acquire", context={"path": str(entry)}):
            stack.enter_context(lock)
        with trace_operation("storage.cache.lock.lifetime", context={"path": str(entry)}):
            prepared = _load_completed(
                entry,
                identity=identity,
                input_sha256=input_sha256,
                dataset_format=dataset_format,
                required_splits=required_splits,
            )
            if prepared is None:
                with trace_operation("storage.cache.miss", context={"format": dataset_format}):
                    _remove_cache_owned_path(entry)
                    for stale in root.glob(f".{identity}.staging-*"):
                        _remove_cache_owned_path(stale)
                    staging = root / f".{identity}.staging-{uuid4().hex}"
                    try:
                        _publish_entry(
                            source_path,
                            source_bytes,
                            staging,
                            entry,
                            identity=identity,
                            input_sha256=input_sha256,
                            dataset_format=dataset_format,
                            required_splits=required_splits,
                        )
                    finally:
                        _remove_cache_owned_path(staging)
                    prepared = _load_completed(
                        entry,
                        identity=identity,
                        input_sha256=input_sha256,
                        dataset_format=dataset_format,
                        required_splits=required_splits,
                    )
                    if prepared is None:
                        _remove_cache_owned_path(entry)
                        raise RuntimeError(
                            f"Prepared dataset cache entry failed validation: {entry}"
                        )
            else:
                with trace_operation("storage.cache.hit", context={"format": dataset_format}):
                    pass
            yield prepared
