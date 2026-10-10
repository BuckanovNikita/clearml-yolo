"""Concrete workflow operations behind application ports."""

from pathlib import Path
from typing import Literal

import pandas as pd

from clearml_yolo.adapters.observability.tracing import trace_operation


def mkdir(path: Path, *, parents: bool = False, exist_ok: bool = False) -> None:
    with trace_operation("storage.directory.create", context={"path": str(path)}):
        path.mkdir(parents=parents, exist_ok=exist_ok)


def read_text(path: Path, *, encoding: str = "utf-8") -> str:
    with trace_operation("storage.text.read", context={"path": str(path)}):
        return path.read_text(encoding=encoding)


def write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    with trace_operation("storage.text.write", context={"path": str(path)}):
        path.write_text(content, encoding=encoding)


def read_csv(
    path: str | Path,
    *,
    dtype: dict[str, type[str]] | None = None,
    float_precision: Literal["round_trip"] | None = None,
) -> pd.DataFrame:
    with trace_operation("storage.csv.read", context={"path": str(path)}):
        return pd.read_csv(path, dtype=dtype, float_precision=float_precision)


def write_csv(
    frame: pd.DataFrame, path: str | Path, *, index: bool = False, float_format: str | None = None
) -> None:
    with trace_operation(
        "storage.csv.write",
        context={"path": str(path), "rows": len(frame), "columns": len(frame.columns)},
    ):
        frame.to_csv(path, index=index, float_format=float_format)
