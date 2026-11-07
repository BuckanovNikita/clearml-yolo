"""Concrete workflow operations behind application ports."""

import csv
import io
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal

import pandas as pd

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.storage.filesystem import write_path
from clearml_yolo.application.contracts import GroundTruthRead


def mkdir(path: Path, *, parents: bool = False, exist_ok: bool = False) -> None:
    with trace_operation("storage.directory.create", context={"path": str(path)}):
        write_path(path).mkdir(parents=parents, exist_ok=exist_ok)


def read_text(path: Path, *, encoding: str = "utf-8") -> str:
    with trace_operation("storage.text.read", context={"path": str(path)}):
        return path.read_text(encoding=encoding)


def write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    with trace_operation("storage.text.write", context={"path": str(path)}):
        write_path(path).write_text(content, encoding=encoding)


def atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Replace a complete text snapshot without exposing a partially written file."""
    destination = write_path(path)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            dir=destination.parent,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_csv(
    path: str | Path,
    *,
    dtype: dict[str, type[str]] | None = None,
    float_precision: Literal["round_trip"] | None = None,
) -> pd.DataFrame:
    with trace_operation("storage.csv.read", context={"path": str(path)}):
        return pd.read_csv(path, dtype=dtype, float_precision=float_precision)


def write_csv(frame: pd.DataFrame, path: str | Path, *, index: bool = False, float_format: str | None = None) -> None:
    with trace_operation(
        "storage.csv.write",
        context={"path": str(path), "rows": len(frame), "columns": len(frame.columns)},
    ):
        frame.to_csv(write_path(path), index=index, float_format=float_format)


# Keep identifier fields textual even when every value happens to look numeric.
_DETECTION_TEXT_COLUMNS = dict.fromkeys(
    (
        "image_name",
        "image_path",
        "instance_label",
        "split",
        "source_row_id",
        "object_id",
        "context_id",
        "model_id",
        "model_name",
        "training_task_id",
        "checkpoint_sha256",
        "row_type",
        "evaluation_status",
        "exclusion_reason",
        "prediction_image_name",
        "matches_pre_threshold",
        "matches_post_threshold",
    ),
    str,
)


def read_detection_csv(path: str | Path) -> pd.DataFrame:
    """Read identities literally, with only empty cells missing and exact float replay."""
    with trace_operation("storage.csv.read", context={"path": str(path)}):
        return pd.read_csv(
            path,
            dtype=_DETECTION_TEXT_COLUMNS,
            keep_default_na=False,
            na_values=[""],
            encoding="utf-8-sig",
            float_precision="round_trip",
        )


def resolved_image_path(value: str, csv_parent: Path) -> Path:
    """Resolve media against its source CSV, independently of the execution directory."""
    path = Path(value).expanduser()
    return (path if path.is_absolute() else csv_parent / path).resolve()


def resolved_image_references(source: Path, content: bytes) -> list[str]:
    """Read only captured CSV references; never inspect image contents or mtimes."""
    rows = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""))
    return [
        str(resolved_image_path(value, source.parent))
        for row in rows
        if isinstance(value := row.get("image_path"), str) and value
    ]


def read_ground_truth(path: str | Path) -> GroundTruthRead:
    """Retain source-row identity while resolving only the execution media paths."""
    source_path = Path(path).expanduser().resolve()
    source = read_detection_csv(source_path)
    if "image_path" not in source:
        raise ValueError("Ground truth has no 'image_path' column")
    if source["image_path"].isna().any():
        raise ValueError("Ground truth contains an empty image_path")
    execution = source.copy()
    execution["image_path"] = [
        str(resolved_image_path(str(value), source_path.parent)) for value in source["image_path"]
    ]
    return GroundTruthRead(source=source, execution=execution)
