"""Console imports leave configuration and filesystem initialization deferred."""

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONSOLE_SCRIPTS: dict[str, str] = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["scripts"]


@pytest.mark.parametrize("command", sorted(CONSOLE_SCRIPTS))
def test_console_import_is_inert(command: str, tmp_path: Path) -> None:
    # These two commands already compose lightweight adapters (including Loguru)
    # at import time; all console targets must still defer heavyweight SDKs.
    lightweight_adapters = command in {"cy-download-weights", "cy-batch-estimate"}
    result = subprocess.run(  # noqa: S603 - fixed assertion in an isolated interpreter
        [
            sys.executable,
            "-c",
            (
                "import os, sys, tempfile; from pathlib import Path; "
                "from importlib.metadata import distribution; "
                "before = dict(os.environ); temporary = tempfile.tempdir; "
                "bytecode = sys.pycache_prefix; cwd = Path.cwd(); "
                "entries = {e.name: e for e in distribution('clearml-yolo').entry_points "
                "if e.group == 'console_scripts'}; "
                f"entry = entries[{command!r}]; "
                f"assert entry.value == {CONSOLE_SCRIPTS[command]!r}; "
                "assert callable(entry.load()); "
                "assert not ({'torch', 'torchvision', 'rfdetr', 'timm', 'tensorrt', "
                "'ultralytics', 'clearml', 'matplotlib'} "
                "& sys.modules.keys()); "
                f"assert {lightweight_adapters!r} or 'loguru' not in sys.modules; "
                "assert dict(os.environ) == before; assert Path.cwd() == cwd; "
                f"assert {lightweight_adapters!r} or tempfile.tempdir == temporary; "
                "assert sys.pycache_prefix == bytecode; "
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
