"""Run product architecture checks as part of the native development Task flow."""

import ast
import json
from copy import deepcopy
from pathlib import Path

import grimp
from importlinter.adapters.user_options import IniFileUserOptionReader
from importlinter.configuration import configure
from importlinter.contracts.forbidden import ForbiddenContract
from importlinter.contracts.independence import IndependenceContract
from importlinter.contracts.layers import LayersContract
from importlinter.domain.contract import Contract

from scripts import architecture_helpers as architecture
from scripts.architecture_tooling import test_dependency_imports, weight_packager_import_findings

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def dependency_findings(graph: grimp.ImportGraph) -> list[str]:
    configure()  # type: ignore[no-untyped-call]
    options = IniFileUserOptionReader().read_options(str(ROOT / ".importlinter"))
    if options is None or not options.contracts_options:
        raise ValueError("Architecture checks require configured .importlinter contracts")
    classes: dict[str, type[Contract]] = {
        "layers": LayersContract,
        "forbidden": ForbiddenContract,
        "independence": IndependenceContract,
    }
    findings: list[str] = []
    for contract_options in options.contracts_options:
        contract = classes[contract_options["type"]](
            name=contract_options["name"],
            session_options=options.session_options,
            contract_options=contract_options,
        )
        # Contract evaluation removes ignored edges; each receives its own graph.
        result = contract.check(deepcopy(graph), verbose=False)
        if not result.kept:
            findings.append(f"{contract.name}: {result.metadata}")
    return findings + architecture.graph_findings(graph)


def source_findings() -> list[str]:
    findings: list[str] = []
    for layer, check in (
        ("core", architecture.core_effect_findings),
        ("application", architecture.application_effect_findings),
    ):
        for path in (SRC / "clearml_yolo" / layer).rglob("*.py"):
            findings.extend(f"{path.relative_to(ROOT)}: {item}" for item in check(ast.parse(path.read_text())))
    for module in architecture.PURE_ADAPTERS:
        path = SRC.joinpath(*module.split(".")).with_suffix(".py")
        findings.extend(
            f"{module}: {item}"
            for item in architecture.pure_adapter_effect_findings(module, ast.parse(path.read_text()))
        )
    for path in SRC.rglob("__init__.py"):
        findings.extend(
            f"{path.relative_to(ROOT)}: {item}"
            for item in architecture.initializer_findings(ast.parse(path.read_text()))
        )
    return findings + architecture.initializer_dependency_findings(SRC)


def target_findings(graph: grimp.ImportGraph) -> list[str]:
    targets = architecture.runtime_targets(SRC, ROOT / "pyproject.toml")
    findings = [f"extracted queue target: {target}" for target in targets if target.startswith("cy_queue")]
    findings.extend(architecture.target_findings(targets, graph, SRC))
    findings.extend(architecture.runtime_boundary_findings(SRC))
    migration = json.loads((ROOT / "tests/fixtures/legacy-module-map.json").read_text())
    findings.extend(f"legacy module in import graph: {module}" for module in set(migration).intersection(graph.modules))
    for legacy in migration:
        path = SRC.joinpath(*legacy.split("."))
        if path.with_suffix(".py").exists() or (path / "__init__.py").exists():
            findings.append(f"legacy module on disk: {legacy}")
    return findings


def tooling_findings() -> list[str]:
    findings: list[str] = []
    for path in SRC.rglob("*.py"):
        findings.extend(
            f"{path.relative_to(ROOT)} imports test dependency {name}"
            for name in sorted(test_dependency_imports(path.read_text(encoding="utf-8")))
        )
    findings.extend(
        f"weight packager boundary: {item}"
        for item in sorted(weight_packager_import_findings((ROOT / "scripts/package_weights.py").read_text()))
    )
    return findings


def main() -> int:
    graph = grimp.build_graph("clearml_yolo", include_external_packages=True, cache_dir=None)
    architecture.add_dynamic_imports(graph, SRC)
    findings = dependency_findings(graph) + source_findings() + target_findings(graph) + tooling_findings()
    for finding in findings:
        print(finding)
    if findings:
        print(f"Architecture checks failed: {len(findings)} finding(s)")
        return 1
    print("Architecture checks passed: imports, effects, initializers, runtime targets and tooling boundaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
