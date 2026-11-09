"""Isolate process-wide runtime configuration between tests."""

import os
import sys
import tempfile
from collections.abc import Callable, Iterator
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from hypothesis import HealthCheck, settings

from clearml_yolo.adapters.runtime import bootstrap
from ddp_gpu_harness import GPUOptions

if TYPE_CHECKING:
    import grimp
    from importlinter.application.user_options import UserOptions
    from importlinter.domain.contract import Contract

    from severstal_harness import SeverstalOptions

# Default runs are deterministic; `HYPOTHESIS_PROFILE=explore` (the `properties` Task stage)
# searches randomly and wider. Tests that pin their own `@settings` keep those values.
# A failure found while exploring is stored in .hypothesis/ and replayed by later runs.
settings.register_profile(
    "clearml-yolo",
    deadline=None,
    derandomize=True,
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "explore",
    deadline=None,
    derandomize=False,
    max_examples=1000,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "clearml-yolo"))

INTEGRATION_DIR = Path(__file__).resolve().parent / "integration"
# Linux process-supervision modules: they own process groups, subreapers, signals and
# timing-sensitive children, so one xdist worker runs them one after another.
SERIAL_MODULES = frozenset(
    {
        "test_bounded_fiftyone.py",
        "test_direct_descendants.py",
        "test_execution_lifecycle.py",
        "test_gpu_cancellation.py",
        "test_subreaper_process_tree.py",
        "test_training_workers.py",
        "test_worker_pool.py",
    }
)
SERIAL_MARKERS = ("ddp_cpu", "process_capabilities")


@pytest.fixture(scope="session")
def import_options() -> "UserOptions":
    from importlinter.adapters.user_options import IniFileUserOptionReader
    from importlinter.configuration import configure

    configure()  # type: ignore[no-untyped-call]
    options = IniFileUserOptionReader().read_options(str(Path(__file__).resolve().parents[1] / ".importlinter"))
    assert options is not None
    assert options.contracts_options
    return options


@pytest.fixture(scope="session")
def configured_contract(import_options: "UserOptions") -> "Callable[[str], Contract]":
    from importlinter.contracts.forbidden import ForbiddenContract
    from importlinter.contracts.independence import IndependenceContract
    from importlinter.contracts.layers import LayersContract
    from importlinter.domain.contract import Contract

    classes: dict[str, type[Contract]] = {
        "layers": LayersContract,
        "forbidden": ForbiddenContract,
        "independence": IndependenceContract,
    }

    def create(name: str) -> Contract:
        selected = next(contract for contract in import_options.contracts_options if contract["name"] == name)
        return classes[selected["type"]](
            name=name,
            session_options=import_options.session_options,
            contract_options=selected,
        )

    return create


@pytest.fixture(scope="session")
def graph() -> "grimp.ImportGraph":
    import grimp

    import architecture_helpers as architecture

    imported = grimp.build_graph("clearml_yolo", include_external_packages=True, cache_dir=None)
    architecture.add_dynamic_imports(imported, Path(__file__).resolve().parents[1] / "src")
    return imported


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
        help=("Local pretrained backbone for a DEIMv2/Faster R-CNN/FCOS selection; repeat for each model"),
    )


def pytest_itemcollected(item: pytest.Item) -> None:
    """Assign xdist groups during collection, before xdist distributes the items.

    Everything under ``tests/integration`` is marked ``integration`` and joins the ``live``
    group, so one worker runs the live tests serially and the session run is prepared once.
    CPU DDP and process-supervision tests share the ``serial`` group; with
    ``--dist loadgroup`` every other test stays parallel.
    """
    if item.path.resolve().is_relative_to(INTEGRATION_DIR):
        item.add_marker(pytest.mark.integration)
        item.add_marker(pytest.mark.xdist_group("live"))
    elif item.path.name in SERIAL_MODULES or any(item.get_closest_marker(name) for name in SERIAL_MARKERS):
        item.add_marker(pytest.mark.xdist_group("serial"))


def _selects_integration(config: pytest.Config) -> bool:
    """Whether the invocation names tests/integration (or a path inside it) or the marker."""
    if "integration" in config.option.markexpr:
        return True
    base = config.invocation_params.dir
    for argument in config.args:
        path = (base / argument.split("::", 1)[0]).resolve()
        if path.is_relative_to(INTEGRATION_DIR):
            return True
    return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Keep ordinary pytest offline, while an explicit live or GPU selection runs.

    A GPU suite runs when its opt-in flag, its marker expression or its file is named; an
    explicit GPU selection without the opt-in fails in the option fixtures below. Other live
    tests run only when the invocation names ``tests/integration`` (or a path inside it) or
    selects the ``integration`` marker, so a plain ``pytest`` never contacts the stand.
    """
    selected_gpu = {
        marker
        for marker, flag, filename in (
            ("ddp_gpu", "--run-ddp-gpu", "test_native_ddp_gpu.py"),
            ("severstal_gpu", "--run-severstal-gpu", "test_severstal_gpu.py"),
        )
        if config.getoption(flag) or marker in config.option.markexpr or any(filename in value for value in config.args)
    }
    live = _selects_integration(config)

    def keep(item: pytest.Item) -> bool:
        gpu = [marker for marker in ("ddp_gpu", "severstal_gpu") if item.get_closest_marker(marker) is not None]
        if gpu:
            return any(marker in selected_gpu for marker in gpu)
        return live or item.get_closest_marker("integration") is None

    removed = [item for item in items if not keep(item)]
    if removed:
        items[:] = [item for item in items if keep(item)]
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
        name for name in ("--ddp-devices", "--ddp-clearml-project", "--ddp-artifacts") if not config.getoption(name)
    ]
    if not config.getoption("--run-ddp-gpu"):
        missing.insert(0, "--run-ddp-gpu")
    if missing:
        evidence = Evidence(options, "selection-error")
        with evidence.retained():
            raise ValueError(f"Physical DDP selection requires {' '.join(missing)}; evidence: {evidence.root}")
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
