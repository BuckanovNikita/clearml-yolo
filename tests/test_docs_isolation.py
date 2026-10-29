"""Reject hypothetical documentation imports and isolate faults from normal commands."""

import subprocess
import sys
from copy import deepcopy

import grimp
import pytest
from importlinter.adapters.user_options import IniFileUserOptionReader
from importlinter.application.user_options import UserOptions
from importlinter.configuration import configure
from importlinter.contracts.forbidden import ForbiddenContract


@pytest.fixture(scope="module")
def docs_import_contract() -> ForbiddenContract:
    configure()  # type: ignore[no-untyped-call]
    options: UserOptions | None = IniFileUserOptionReader().read_options(".importlinter")
    assert options is not None
    contract = next(
        item
        for item in options.contracts_options
        if item["name"] == "Documentation serving is isolated from ordinary execution"
    )
    return ForbiddenContract(
        name=contract["name"], session_options=options.session_options, contract_options=contract
    )


@pytest.mark.parametrize(
    "source",
    [
        "clearml_yolo.core.models",
        "clearml_yolo.application.contracts",
        "clearml_yolo.entrypoints.hydra.configs",
        "clearml_yolo.entrypoints.train",
    ],
)
def test_documentation_import_boundary_rejects_injected_edges(
    docs_import_contract: ForbiddenContract, source: str
) -> None:
    graph = grimp.build_graph("clearml_yolo", include_external_packages=True)
    assert docs_import_contract.check(deepcopy(graph), verbose=False).kept
    graph.add_import(
        importer=source,
        imported="clearml_yolo.adapters.documentation.server",
        line_number=1,
        line_contents="injected forbidden import",
    )
    assert not docs_import_contract.check(graph, verbose=False).kept


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
