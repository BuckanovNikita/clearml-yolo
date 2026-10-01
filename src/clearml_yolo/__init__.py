"""Native YOLO workflows with tracked evaluation and comparison."""

# ruff: noqa: PTH100, PTH109, PTH111, PTH118
# os/sys are already loaded by Python; importing pathlib here would precede cache routing.

import os
import sys

# Configure subsequent imports before loading even the filesystem policy's dependencies.
# Python loads this bootstrap module itself before application code can control its cache.
if sys.pycache_prefix is None:
    sys.pycache_prefix = os.environ.setdefault(
        "PYTHONPYCACHEPREFIX",
        os.path.join(os.path.abspath(os.path.expanduser(os.environ.get("CY_HOME") or os.getcwd())),
                     ".cache", "python"),
    )
