"""Isolate process-wide runtime configuration between tests."""

import os
import sys
import tempfile
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path

import pytest

from clearml_yolo.adapters.runtime import bootstrap
from ddp_gpu_harness import GPUOptions


@pytest.fixture(autouse=True)
def restore_clearml_owner_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset adapter ownership at test boundaries, never between sweep invocations."""
    from clearml_yolo.adapters.clearml import session

    monkeypatch.setattr(session, "_INCOMPLETE_OWNER", session._IncompleteOwner())


@pytest.fixture(autouse=True)
def restore_runtime_configuration(tmp_path: Path) -> Iterator[None]:
    """Programmatic initialization persists intentionally, but not across test cases."""
    environment = dict(os.environ)
    bytecode = sys.pycache_prefix
    temporary = tempfile.tempdir
    state = deepcopy(bootstrap._STATE)
    os.environ["CY_HOME"] = str(tmp_path)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(environment)
        sys.pycache_prefix = bytecode
        tempfile.tempdir = temporary
        bootstrap._STATE = state


def pytest_addoption(parser: pytest.Parser) -> None:
    """The physical acceptance suite never starts implicitly."""
    group = parser.getgroup("physical DDP acceptance")
    group.addoption(
        "--run-ddp-gpu",
        action="store_true",
        help="Authorize the marked physical multi-GPU/ClearML suite",
    )
    group.addoption("--ddp-devices", default="", help="Physical nvidia-smi/NVML indexes, e.g. 0,1")
    group.addoption("--ddp-clearml-project", default="", help="Explicit test-owned ClearML project")
    group.addoption("--ddp-artifacts", default="", help="Retained evidence directory")
    group.addoption(
        "--ddp-timeout",
        type=float,
        default=1200,
        help="Per-scenario native execution deadline in seconds",
    )
    group.addoption(
        "--ddp-cleanup-timeout",
        type=float,
        default=150,
        help="Production cleanup deadline; minimum 120 seconds, plus 15-second fallback",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Keep ordinary pytest offline, while an explicit GPU selection fails missing opt-in."""
    explicit_file = any("test_native_ddp_gpu.py" in value for value in config.args)
    if config.getoption("--run-ddp-gpu") or "ddp_gpu" in config.option.markexpr or explicit_file:
        return
    selected = [item for item in items if item.get_closest_marker("ddp_gpu") is None]
    removed = [item for item in items if item.get_closest_marker("ddp_gpu") is not None]
    items[:] = selected
    if removed:
        config.hook.pytest_deselected(items=removed)


@pytest.fixture
def ddp_gpu_options(request: pytest.FixtureRequest) -> GPUOptions:
    """Retain evidence for explicit selections that omit authorization or required options."""
    from ddp_gpu_harness import Evidence, GPUOptions

    config = request.config
    options = GPUOptions(
        devices=config.getoption("--ddp-devices"),
        project=config.getoption("--ddp-clearml-project"),
        artifacts=Path(config.getoption("--ddp-artifacts") or ".tmp/ddp-results"),
        timeout=config.getoption("--ddp-timeout"),
        cleanup_timeout=config.getoption("--ddp-cleanup-timeout"),
    )
    missing = [
        name
        for name in ("--ddp-devices", "--ddp-clearml-project", "--ddp-artifacts")
        if not config.getoption(name)
    ]
    if not config.getoption("--run-ddp-gpu"):
        missing.insert(0, "--run-ddp-gpu")
    if missing:
        evidence = Evidence(options, "selection-error")
        with evidence.retained():
            raise ValueError(
                f"Physical DDP selection requires {' '.join(missing)}; evidence: {evidence.root}"
            )
    return options
