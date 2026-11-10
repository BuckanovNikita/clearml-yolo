"""Comment-preserving atomic storage of editable batches and internal provenance."""

import hashlib
import json
import os
import tempfile
from copy import deepcopy
from io import StringIO
from pathlib import Path
from typing import Literal

from filelock import FileLock, SoftFileLock
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError

from clearml_yolo.adapters.storage.filesystem import cy_home, write_path
from clearml_yolo.core.batch_estimation import EstimateCase, PositiveInt, SearchStatus, estimate_key, model_catalogue
from clearml_yolo.core.batch_sizes import (
    BatchSizeEntry,
    BatchSizeFailure,
    BatchSizeTable,
    gpu_label,
    parse_gpu_label,
)

_METADATA_PREFIX = "# clearml-yolo-batch-metadata: "


class _Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SearchStatus
    diagnostic: str
    estimate_key: str


class _Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    capacities: dict[str, PositiveInt] = Field(default_factory=dict)
    measured: dict[str, PositiveInt] = Field(default_factory=dict)
    failures: tuple[BatchSizeFailure, ...] = ()
    forced: dict[str, StrictBool] = Field(default_factory=dict)
    sources: dict[str, _Source] = Field(default_factory=dict)


def _entry_key(label: str, size: int, model: str) -> str:
    return json.dumps([label, size, model], separators=(",", ":"))


def _yaml() -> YAML:
    parser = YAML(typ="rt")
    parser.allow_duplicate_keys = False
    parser.preserve_quotes = True
    return parser


class BatchSizeStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = write_path(path or cy_home() / ".config/clearml-yolo/batch-sizes.yaml")

    def load(self) -> BatchSizeTable:
        """The table and internal metadata share one atomic file snapshot."""
        return self._read()[2]

    def _read(self) -> tuple[CommentedMap, _Metadata, BatchSizeTable]:
        try:
            payload = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            payload = ""
        try:
            document, metadata = _parse(payload)
            entries = _entries(document, metadata)
            table = BatchSizeTable(
                digest=hashlib.sha256(payload.encode()).hexdigest(), entries=entries, failures=metadata.failures
            )
        except (ValueError, TypeError, YAMLError) as error:
            raise ValueError(
                f"Invalid batch size table {self.path}; repair it before retrying; file preserved"
            ) from error
        return document, metadata, table

    def publish(self, cases: tuple[EstimateCase, ...], *, replace: bool = True) -> None:
        """Publish accepted cases only; callers own worker exit and cleanup evidence.

        The smallest confirmed batch wins within this publication. Earlier
        measurements never compete with a new refresh. Failed refreshes do nothing.
        """
        validated = tuple(EstimateCase.model_validate_json(case.model_dump_json()) for case in cases)
        selected = _publication_entries(validated)
        if not selected:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if FileLock is SoftFileLock:
            raise RuntimeError("Batch tables require native file locks")
        with FileLock(
            write_path(self.path.with_suffix(".yaml.lock")), timeout=30, fallback_to_soft=False, preserve_lock_file=True
        ):
            document, metadata, table = self._read()
            for failure, case in selected.items():
                self._update(document, metadata, table, failure, case, replace=replace)
            stream = StringIO()
            _yaml().dump(document, stream)
            payload = (
                stream.getvalue()
                + _METADATA_PREFIX
                + json.dumps(metadata.model_dump(mode="json"), ensure_ascii=True)
                + "\n"
            )
            self._replace(payload)

    @staticmethod
    def _update(
        document: CommentedMap,
        metadata: _Metadata,
        table: BatchSizeTable,
        failure: BatchSizeFailure,
        case: EstimateCase,
        *,
        replace: bool,
    ) -> None:
        gpu = next(
            gpu
            for gpu in case.profile.gpus
            if gpu.name == failure.gpu_name and gpu.total_memory_bytes == failure.total_memory_bytes
        )
        exact = table.exact(gpu, failure.image_size, failure.model)
        if not replace and (exact is not None or failure in metadata.failures):
            return
        label = exact.gpu_label if exact else gpu_label(gpu)
        # Rounded display labels can collide. Preserve each precise capacity under
        # an exact decimal GiB label rather than overwrite another device's row.
        existing_capacity = metadata.capacities.get(label)
        if existing_capacity is None and label in document:
            _, existing_capacity = parse_gpu_label(label)
        if existing_capacity is not None and existing_capacity != gpu.total_memory_bytes:
            from decimal import Decimal

            label = f"{gpu.name} [{Decimal(gpu.total_memory_bytes) / 1024**3} GiB]"
        aliases = {
            entry.gpu_label
            for entry in table.entries
            if (entry.gpu_name, entry.total_memory_bytes, entry.image_size, entry.model)
            == (failure.gpu_name, failure.total_memory_bytes, failure.image_size, failure.model)
        }
        _detach_paths(document, aliases | {label}, failure.image_size)
        key = _entry_key(label, failure.image_size, failure.model)
        metadata.capacities[label] = gpu.total_memory_bytes
        metadata.failures = tuple(item for item in metadata.failures if item != failure)
        if case.status == "no_capacity":
            for entry in table.entries:
                if (entry.gpu_name, entry.total_memory_bytes, entry.image_size, entry.model) == (
                    failure.gpu_name,
                    failure.total_memory_bytes,
                    failure.image_size,
                    failure.model,
                ):
                    del document[entry.gpu_label][entry.image_size][entry.model]
                    metadata.measured.pop(_entry_key(entry.gpu_label, entry.image_size, entry.model), None)
                    metadata.forced.pop(_entry_key(entry.gpu_label, entry.image_size, entry.model), None)
                    metadata.sources.pop(_entry_key(entry.gpu_label, entry.image_size, entry.model), None)
            metadata.failures += (failure,)
            return
        if case.per_gpu_batch is None:
            raise ValueError("Usable publication lacks a confirmed per-GPU batch")
        document.setdefault(label, CommentedMap()).setdefault(failure.image_size, CommentedMap())[failure.model] = (
            case.per_gpu_batch
        )
        metadata.measured[key] = case.per_gpu_batch
        metadata.forced[key] = case.settings.force
        source = _Source(
            status=case.status,
            diagnostic=case.diagnostic,
            estimate_key=estimate_key(case.profile, case.workload, case.settings),
        )
        metadata.sources[key] = source
        # Alternate literal labels may denote the same hardware. Refresh every
        # exact alias so a stale smaller value cannot override fresh evidence.
        for entry in table.entries:
            if (entry.gpu_name, entry.total_memory_bytes, entry.image_size, entry.model) == (
                failure.gpu_name,
                failure.total_memory_bytes,
                failure.image_size,
                failure.model,
            ):
                document[entry.gpu_label][entry.image_size][entry.model] = case.per_gpu_batch
                alias_key = _entry_key(entry.gpu_label, entry.image_size, entry.model)
                metadata.measured[alias_key] = case.per_gpu_batch
                metadata.forced[alias_key] = case.settings.force
                metadata.sources[alias_key] = source

    def _replace(self, payload: str) -> None:
        descriptor, name = tempfile.mkstemp(prefix=".batch-sizes-", suffix=".tmp", dir=self.path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(write_path(self.path))
            directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)


def _detach_paths(document: CommentedMap, labels: set[str], size: int) -> None:
    for label in labels:
        if label in document:
            # YAML anchors can share a whole GPU map or just an image-size map.
            # Detach both changed levels while preserving unrelated comments.
            document[label] = deepcopy(document[label])
            if size in document[label]:
                document[label][size] = deepcopy(document[label][size])


def _parse(payload: str) -> tuple[CommentedMap, _Metadata]:
    lines = payload.splitlines(keepends=True)
    records = [line[len(_METADATA_PREFIX) :] for line in lines if line.startswith(_METADATA_PREFIX)]
    if len(records) > 1:
        raise ValueError("Duplicate internal metadata")
    metadata = _Metadata.model_validate_json(records[0]) if records else _Metadata()
    public_text = "".join(line for line in lines if not line.startswith(_METADATA_PREFIX))
    document = _yaml().load(public_text)
    if document is None and all(not line.strip() or line.lstrip().startswith("#") for line in lines):
        document = CommentedMap()
        if public_text.strip():
            document.yaml_set_start_comment(public_text.rstrip())
    if not isinstance(document, CommentedMap):
        raise TypeError("Batch table must be a mapping")
    return document, metadata


def _entries(document: CommentedMap, metadata: _Metadata) -> tuple[BatchSizeEntry, ...]:
    result = []
    models = {model.selection for model in model_catalogue()}
    for label, sizes in document.items():
        if not isinstance(label, str) or not isinstance(sizes, dict):
            raise TypeError("GPU labels must map to image-size mappings")
        name, literal_capacity = parse_gpu_label(label)
        capacity = metadata.capacities.get(label, literal_capacity)
        for size, batches in sizes.items():
            if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or not isinstance(batches, dict):
                raise ValueError("Image sizes must be positive integers mapping to model batches")
            for model, batch in batches.items():
                if (
                    not isinstance(model, str)
                    or model not in models
                    or not isinstance(batch, int)
                    or isinstance(batch, bool)
                    or batch <= 0
                ):
                    raise ValueError("Models must be canonical and batches positive integers")
                measured = metadata.measured.get(_entry_key(label, size, model)) == batch
                source = metadata.sources.get(_entry_key(label, size, model)) if measured else None
                result.append(
                    BatchSizeEntry(
                        gpu_label=label,
                        gpu_name=name,
                        total_memory_bytes=capacity,
                        image_size=size,
                        model=model,
                        per_gpu_batch=batch,
                        origin="measurement" if measured else "manual",
                        forced=measured and metadata.forced.get(_entry_key(label, size, model), False),
                        source_status=source.status if source else None,
                        source_diagnostic=source.diagnostic if source else "",
                        source_estimate_key=source.estimate_key if source else None,
                    )
                )
    return tuple(result)


def _publication_entries(cases: tuple[EstimateCase, ...]) -> dict[BatchSizeFailure, EstimateCase]:
    selected: dict[BatchSizeFailure, EstimateCase] = {}
    for case in cases:
        if not case.usable and case.status != "no_capacity":
            continue
        if case.status == "no_capacity" and (
            not case.trials or case.trials[-1].global_batch != case.profile.world_size
        ):
            # Historical aligned searches stopped at eight; they cannot establish
            # that one image does not fit and must not block today's fallback.
            continue
        if case.profile.nominal_size[0] != case.profile.nominal_size[1]:
            raise ValueError("Batch table publication requires square images")
        for gpu in case.profile.gpus:
            key = BatchSizeFailure(
                gpu_name=gpu.name,
                total_memory_bytes=gpu.total_memory_bytes,
                image_size=case.profile.nominal_size[0],
                model=case.profile.model.selection,
            )
            prior = selected.get(key)
            if (
                prior is None
                or case.status == "no_capacity"
                or (
                    prior.status != "no_capacity"
                    and case.per_gpu_batch is not None
                    and prior.per_gpu_batch is not None
                    and case.per_gpu_batch < prior.per_gpu_batch
                )
            ):
                selected[key] = case
    return selected
