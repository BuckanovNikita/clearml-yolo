"""Console imports leave configuration and filesystem initialization deferred."""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "command",
    [
        "pipeline",
        "train",
        "predict",
        "val",
        "metrics",
        "report",
        "compare",
        "ground_truth",
        "export",
        "config_tree",
        "dedup",
    ],
)
def test_console_import_is_inert(command: str, tmp_path: Path) -> None:
    result = subprocess.run(  # noqa: S603 - fixed assertion in an isolated interpreter
        [
            sys.executable,
            "-c",
            (
                "import os, sys, tempfile; from pathlib import Path; "
                "before = dict(os.environ); temporary = tempfile.tempdir; "
                "bytecode = sys.pycache_prefix; cwd = Path.cwd(); "
                f"import clearml_yolo.entrypoints.{command}; "
                "assert not ({'torch', 'torchvision', 'rfdetr', 'timm', 'tensorrt', "
                "'ultralytics', 'clearml', 'matplotlib', 'loguru'} "
                "& sys.modules.keys()); "
                "assert dict(os.environ) == before; assert Path.cwd() == cwd; "
                "assert tempfile.tempdir == temporary; assert sys.pycache_prefix == bytecode; "
                "assert list(cwd.iterdir()) == []"
            ),
        ],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
