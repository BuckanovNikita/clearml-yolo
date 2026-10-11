"""Console entry modules defer dependency imports until runtime policy exists."""

import subprocess
import sys

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
        "config_tree",
        "dedup",
    ],
)
def test_console_import_is_inert(command: str) -> None:
    result = subprocess.run(  # noqa: S603 - fixed assertion in an isolated interpreter
        [
            sys.executable,
            "-c",
            (
                f"import clearml_yolo.entrypoints.{command}; import sys; "
                "assert not ({'torch', 'ultralytics', 'clearml', 'matplotlib', 'loguru'} "
                "& sys.modules.keys())"
            ),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
