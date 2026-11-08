"""Keep product imports independent of test helpers and unapproved asset interfaces."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
        if name.split(".")[0] in helpers | {"tests", "hypothesis", "pytest_cov", "coverage", "pytest"}
    }


def test_production_has_no_test_tool_or_helper_imports() -> None:
    for path in (ROOT / "src").rglob("*.py"):
        assert not _test_dependency_imports(path.read_text(encoding="utf-8")), str(path)


WEIGHT_PACKAGER_IMPORTS = {
    "clearml_yolo.adapters.assets.hub": {
        "_etag_matches",
        "_native_identity",
        "_validate_config_data",
    },
    "clearml_yolo.adapters.assets.preparation": {"_discover"},
    "clearml_yolo.adapters.assets.resolver": {"resolve_asset"},
    "clearml_yolo.adapters.assets.validation": {"validate_asset"},
    "clearml_yolo.core.assets": {"AssetSpec", "ResolvedAsset"},
    "clearml_yolo.core.weight_bundles": {
        "BundleArchive",
        "BundleAsset",
        "BundleConfig",
        "BundleHub",
        "BundleManifest",
    },
}


def weight_packager_import_findings(source: str) -> set[str]:
    """Keep the explicit maintainer tool within its approved static asset interfaces."""
    findings: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            findings.update(
                alias.name
                for alias in node.names
                if alias.name.split(".")[0] not in sys.stdlib_module_names and alias.name not in WEIGHT_PACKAGER_IMPORTS
            )
            if any(alias.name.split(".")[0] == "importlib" for alias in node.names):
                findings.add("dynamic import facility")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or "relative import"
            if node.level or node.module is None:
                findings.add("relative import")
            elif module.split(".")[0] not in sys.stdlib_module_names:
                allowed_names = WEIGHT_PACKAGER_IMPORTS.get(module, set())
                findings.update(f"{module}.{alias.name}" for alias in node.names if alias.name not in allowed_names)
            if module.split(".")[0] == "importlib" or any(
                alias.name in {"__import__", "eval", "exec"} for alias in node.names
            ):
                findings.add("dynamic import facility")
        elif (isinstance(node, ast.Name) and node.id in {"__import__", "eval", "exec"}) or (
            isinstance(node, ast.Attribute) and node.attr in {"__import__", "import_module", "eval", "exec"}
        ):
            findings.add("dynamic import facility")
    return findings


def test_weight_packager_uses_only_standard_library_and_approved_asset_interfaces() -> None:
    assert not weight_packager_import_findings((ROOT / "scripts/package_weights.py").read_text(encoding="utf-8"))
