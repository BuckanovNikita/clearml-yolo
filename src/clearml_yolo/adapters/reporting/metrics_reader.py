"""Preserve the public dashboard reader through structured reporting inputs."""

from pathlib import Path
from typing import cast

import pandas as pd
from report_generator.v2 import read_metrics_table


class DashboardReader:
    """Read exact lexical class labels with historical constructor semantics."""

    def __init__(self, file_path: str | Path, sheet_name: str | int = 0) -> None:
        self.file_path = Path(file_path)
        self.sheet_name = sheet_name

    def read(self) -> pd.DataFrame:
        return cast(pd.DataFrame, read_metrics_table(self.file_path, self.sheet_name).frame)
