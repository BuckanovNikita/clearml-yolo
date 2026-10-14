"""Keep release tooling independent and analysis dependencies out of runtime installs."""

import ast
import sys
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_PACKAGES = {
    "mypy",
    "ruff",
    "vulture",
    "scipy-stubs",
    "types-tqdm",
    "optype",
    "numpy-typing-compat",
    "hypothesis",
    "pytest-cov",
    "coverage",
}


def release_import_findings(source: str) -> set[str]:
    allowed = sys.stdlib_module_names | {"loguru", "pydantic"}
    findings: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            findings.update(
                alias.name for alias in node.names if alias.name.split(".")[0] not in allowed
            )
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module is None or node.module.split(".")[0] not in allowed:
                findings.add(node.module or "relative import")
            # This helper has no plugin boundary: dynamic loading would evade its allowlist.
            if node.module == "importlib":
                findings.add("dynamic import facility")
        elif (isinstance(node, ast.Name) and node.id == "__import__") or (
            isinstance(node, ast.Attribute) and node.attr == "import_module"
        ):
            findings.add("dynamic import facility")
    return findings


def runtime_analysis_dependencies(requirements: list[str]) -> set[str]:
    return {
        name
        for requirement in requirements
        if (name := canonicalize_name(Requirement(requirement).name)) in ANALYSIS_PACKAGES
        or name.endswith("-stubs")
        or name.startswith("types-")
    }


def test_release_helper_uses_only_its_owned_dependencies() -> None:
    assert not release_import_findings(
        (ROOT / "scripts/local_release.py").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    "source",
    [
        "import clearml_yolo.application.use_cases.train",
        "from torch import Tensor",
        "if TYPE_CHECKING:\n    from clearml import Task",
        "def lazy():\n    import ultralytics",
        "from importlib import import_module as load\nload('torch')",
        "import importlib as loader\nloader.import_module('clearml')",
        "__import__('torch')",
    ],
)
def test_release_import_guard_rejects_injected_violations(source: str) -> None:
    assert release_import_findings(source)


def test_release_import_guard_allows_owned_dependencies() -> None:
    assert not release_import_findings(
        "import subprocess\nfrom pathlib import Path\nfrom loguru import logger\n"
        "from pydantic import BaseModel"
    )


def test_analysis_packages_are_development_only() -> None:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        config = tomllib.load(stream)
    project = config["project"]
    requirements = list(project["dependencies"])
    for extra in project["optional-dependencies"].values():
        requirements.extend(extra)
    assert not runtime_analysis_dependencies(requirements)
    dev = {canonicalize_name(Requirement(item).name) for item in config["dependency-groups"]["dev"]}
    assert {
        "ruff",
        "mypy",
        "vulture",
        "scipy-stubs",
        "types-tqdm",
        "hypothesis",
        "pytest-cov",
    } <= dev


@pytest.mark.parametrize(
    "requirement",
    [
        "ruff>=0.16",
        "Vulture==2.16",
        "scipy_stubs==1.18.0.1",
        "types-tqdm; python_version>='3.12'",
        "hypothesis>=6",
        "pytest-cov>=7",
        "coverage>=7",
    ],
)
def test_runtime_dependency_guard_rejects_injected_analysis_packages(requirement: str) -> None:
    assert runtime_analysis_dependencies(["numpy>=1.24", requirement])


def _test_dependency_imports(source: str) -> set[str]:
    """Recognize project test helpers, including literal dynamic imports."""
    helpers = {path.stem for path in (ROOT / "tests").glob("*.py")}
    imports: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call) and node.args:
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else ""
            )
            if name in {"import_module", "__import__"}:
                argument = node.args[0]
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    imports.add(argument.value)
    return {
        name
        for name in imports
        if name.split(".")[0]
        in helpers | {"tests", "hypothesis", "pytest_cov", "coverage", "pytest"}
    }


def test_production_has_no_test_tool_or_helper_imports() -> None:
    for path in (ROOT / "src").rglob("*.py"):
        assert not _test_dependency_imports(path.read_text(encoding="utf-8")), str(path)


@pytest.mark.parametrize(
    "source",
    [
        "import tests.ddp_cpu_launcher",
        "from workflow_dependencies import patch_workflow",
        "import hypothesis",
        "import importlib; importlib.import_module('ddp_cpu_launcher')",
        "__import__('pytest')",
    ],
)
def test_helper_import_guard_rejects_injected_dependencies(source: str) -> None:
    assert _test_dependency_imports(source)
