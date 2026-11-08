"""Isolate documentation faults from normal product commands."""

import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module",
    ["train", "pipeline", "predict", "metrics", "export", "config_tree", "download_weights"],
)
def test_documentation_failure_cannot_break_normal_help(module: str) -> None:
    code = """
import importlib.abc
import runpy
import sys
class DenyDocumentation(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if '.documentation' in fullname or fullname.endswith('.docs'):
            raise RuntimeError('injected missing/corrupt documentation')
sys.meta_path.insert(0, DenyDocumentation())
sys.argv = ['cy', '--help']
runpy.run_module(sys.argv_module, run_name='__main__')
""".replace("sys.argv_module", repr(f"clearml_yolo.entrypoints.{module}"))
    result = subprocess.run(  # noqa: S603 - fixed test-only Python code and module allowlist
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=30, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout
