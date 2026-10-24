"""Isolate process-wide runtime configuration between tests."""

import os
import sys
import tempfile
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from clearml_yolo.adapters.runtime import bootstrap
from ddp_gpu_harness import GPUOptions

if TYPE_CHECKING:
    from severstal_harness import SeverstalOptions


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
    severstal = parser.getgroup("native Severstal acceptance")
    severstal.addoption("--run-severstal-gpu", action="store_true")
    severstal.addoption("--severstal-dataset", default="")
    severstal.addoption("--severstal-artifacts", default="")
    severstal.addoption("--severstal-clearml-project", default="")
    severstal.addoption("--severstal-tags", default="", help="Comma-separated ownership tags")
    severstal.addoption("--severstal-device", default="0")
    severstal.addoption("--severstal-timeout", type=float, default=1800)
    severstal.addoption(
        "--severstal-backbone",
        action="append",
        default=[],
        metavar="MODEL=PATH",
        help="Local pretrained backbone for a DEIMv2/Faster R-CNN selection; repeat for each model",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Keep ordinary pytest offline, while an explicit GPU selection fails missing opt-in."""
    for marker, flag, filename in (
        ("ddp_gpu", "--run-ddp-gpu", "test_native_ddp_gpu.py"),
        ("severstal_gpu", "--run-severstal-gpu", "test_severstal_gpu.py"),
    ):
        explicit_file = any(filename in value for value in config.args)
        if config.getoption(flag) or marker in config.option.markexpr or explicit_file:
            continue
        removed = [item for item in items if item.get_closest_marker(marker) is not None]
        items[:] = [item for item in items if item.get_closest_marker(marker) is None]
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


@pytest.fixture
def severstal_options(request: pytest.FixtureRequest) -> "SeverstalOptions":
    """Require explicit data, evidence and stand ownership before any native run."""
    from severstal_harness import SeverstalOptions, parse_backbone_options

    config = request.config
    required = (
        "--run-severstal-gpu",
        "--severstal-dataset",
        "--severstal-artifacts",
        "--severstal-clearml-project",
        "--severstal-tags",
    )
    missing = [name for name in required if not config.getoption(name)]
    if missing:
        raise ValueError(f"Native Severstal selection requires {' '.join(missing)}")
    return SeverstalOptions(
        dataset=Path(config.getoption("--severstal-dataset")),
        artifacts=Path(config.getoption("--severstal-artifacts")),
        project=config.getoption("--severstal-clearml-project"),
        tags=tuple(value.strip() for value in config.getoption("--severstal-tags").split(",")),
        device=config.getoption("--severstal-device"),
        timeout=config.getoption("--severstal-timeout"),
        backbone_weights=parse_backbone_options(config.getoption("--severstal-backbone")),
    )
