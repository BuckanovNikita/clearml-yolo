"""Concrete workflow operations behind application ports."""

from pathlib import Path
from typing import Literal

import pandas as pd


def mkdir(path: Path, *, parents: bool = False, exist_ok: bool = False) -> None:
    path.mkdir(parents=parents, exist_ok=exist_ok)

def read_text(path: Path, *, encoding: str = "utf-8") -> str:
    return path.read_text(encoding=encoding)

def write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    path.write_text(content, encoding=encoding)

def read_csv(
    path: str | Path,
    *,
    dtype: dict[str, type[str]] | None = None,
    float_precision: Literal["round_trip"] | None = None,
) -> pd.DataFrame:
    return pd.read_csv(path, dtype=dtype, float_precision=float_precision)

def write_csv(
    frame: pd.DataFrame, path: str | Path, *, index: bool = False, float_format: str | None = None
) -> None:
    frame.to_csv(path, index=index, float_format=float_format)
