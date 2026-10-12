"""Preserve lexical class labels at the external report-builder boundary."""

import math
from pathlib import Path

import pandas as pd


def _valid_id(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class DashboardReader:
    """Supply the reader interface consumed by the pinned report builders.

    Upstream treats numeric-looking strings as threshold footer rows. Our public
    vocabulary permits those strings, so distinguish original text cells from
    numeric footer cells before pandas inference can erase that distinction.
    """

    def __init__(self, file_path: str | Path, sheet_name: str | int = 0) -> None:
        self.file_path = Path(file_path)
        self.sheet_name = sheet_name

    def read(self) -> pd.DataFrame:
        with pd.ExcelFile(self.file_path) as workbook:
            frame = workbook.parse(self.sheet_name)
            if len(frame.columns) == 0:
                raise ValueError(f"Empty worksheet: {self.sheet_name!r} in {self.file_path}")
            # Keep numeric metrics' normal missing-value handling. Only class
            # cells need exact strings, including leading zeros and literal NA.
            labels = workbook.parse(
                self.sheet_name, usecols=[0], dtype=object, keep_default_na=False
            ).iloc[:, 0]
        if len(labels) != len(frame):
            raise ValueError(f"Dashboard class/metric rows disagree: {self.file_path}")
        frame = frame.rename(columns={frame.columns[0]: "Класс"})
        frame["Класс"] = labels
        keep = labels.map(
            lambda label: isinstance(label, str) and bool(label.strip()) and label != "Среднее"
        )
        frame = frame.loc[keep].reset_index(drop=True)
        duplicates = frame.loc[frame["Класс"].duplicated(), "Класс"].tolist()
        if duplicates:
            raise ValueError(f"Duplicate classes in {self.file_path}: {duplicates}")
        if "ID" in frame.columns:
            ids = frame["ID"]
            if ids.isna().any() or not ids.map(_valid_id).all() or ids.duplicated().any():
                raise ValueError(
                    f"ID values must be nonempty unique strings or numbers: {self.file_path}"
                )
        return frame
