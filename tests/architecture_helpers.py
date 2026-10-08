"""Static architecture checks shared by positive and injected negative tests."""

import ast
import re
import sys
import tomllib
from collections.abc import Mapping
from importlib.util import resolve_name
from pathlib import Path

import grimp

PROJECT_ROOTS = ("clearml_yolo", "hydra_plugins.cy_queue")
ADAPTER_RESPONSIBILITIES = {
    "storage",
    "yolo",
    "clearml",
    "evaluation",
    "reporting",
    "fiftyone",
    "runtime",
    "integrations",
    "observability",
}
COMMANDS = {
    "pipeline",
    "train",
    "predict",
    "val",
    "metrics",
    "report",
    "compare",
    "ground_truth",
    "config_tree",
    "dedup",
}
SCIENTIFIC = {"pydantic", "pandera", "pandas", "numpy", "scipy"}
APPLICATION_EFFECT_DEPENDENCIES = {
    "loguru",
    "matplotlib",
    "PIL",
    "openpyxl",
    "requests",
    "filelock",
}
SDK_OWNERS = {
    "ultralytics": (
        "clearml_yolo.adapters.yolo",
        "clearml_yolo.adapters.integrations.native_runtime",
        "clearml_yolo.adapters.integrations.native_ddp",
        "clearml_yolo.adapters.integrations.training",
    ),
    "torch": (
        "clearml_yolo.adapters.yolo",
        "clearml_yolo.adapters.integrations.native_runtime",
        "clearml_yolo.adapters.integrations.native_ddp",
        "clearml_yolo.adapters.integrations.training",
    ),
    "clearml": (
        "clearml_yolo.adapters.clearml",
        "clearml_yolo.adapters.integrations.native_runtime",
        "clearml_yolo.adapters.integrations.training",
    ),
    "digital_metrics": ("clearml_yolo.adapters.evaluation", "clearml_yolo.adapters.reporting"),
    "report_generator": ("clearml_yolo.adapters.reporting",),
    "openpyxl": ("clearml_yolo.adapters.reporting",),
    "fiftyone": ("clearml_yolo.adapters.fiftyone",),
    "hydra": ("clearml_yolo.entrypoints.hydra", "hydra_plugins.cy_queue"),
    "hydra_zen": ("clearml_yolo.entrypoints.hydra",),
    "omegaconf": ("clearml_yolo.entrypoints.hydra", "hydra_plugins.cy_queue"),
}
# The probe reads CUDA visibility in a fresh disposable process before scheduling.
SDK_EXCEPTIONS = {("clearml_yolo.adapters.runtime.gpu_probe", "torch")}
ADAPTER_PEERS = {
    "storage": {"observability"},
    "observability": set(),
    "yolo": {"storage", "observability"},
    "evaluation": set(),
    "reporting": {"storage", "observability"},
    "clearml": {"storage", "observability"},
    "fiftyone": set(),
    "runtime": {"observability"},
    "integrations": {"storage", "observability"},
}
# These edges implement explicit cross-adapter coordination or data conversion.
PEER_EXCEPTIONS = {
    ("clearml_yolo.adapters.clearml.models", "clearml_yolo.adapters.reporting.workbook_identity"),
    ("clearml_yolo.adapters.fiftyone.publisher", "clearml_yolo.adapters.storage.publication_data"),
    ("clearml_yolo.adapters.runtime.gpu_runtime", "clearml_yolo.adapters.clearml.session"),
    (
        "clearml_yolo.adapters.runtime.gpu_runtime",
        "clearml_yolo.adapters.integrations.native_runtime",
    ),
    ("clearml_yolo.adapters.integrations.native_runtime", "clearml_yolo.adapters.clearml.session"),
    ("clearml_yolo.adapters.integrations.native_ddp", "clearml_yolo.adapters.clearml.session"),
    ("clearml_yolo.adapters.integrations.training", "clearml_yolo.adapters.clearml.session"),
    ("clearml_yolo.adapters.integrations.training", "clearml_yolo.adapters.clearml.native"),
    ("clearml_yolo.adapters.integrations.training", "clearml_yolo.adapters.yolo.config"),
}
EFFECTFUL_CALLS = {
    "open",
    "read_text",
    "read_bytes",
    "write_text",
    "write_bytes",
    "read_csv",
    "read_excel",
    "to_csv",
    "to_excel",
    "savefig",
    "mkdir",
    "unlink",
    "rmdir",
    "rename",
    "glob",
    "rglob",
    "stat",
    "lstat",
    "exists",
    "is_file",
    "is_dir",
    "resolve",
    "iterdir",
    "import_module",
    "__import__",
    "system",
    "popen",
    "Popen",
    "run",
    "check_call",
    "check_output",
    "urlopen",
    "urlretrieve",
    "connect",
    "send",
    "recv",
    "getenv",
    "ExcelWriter",
    "Workbook",
    "load_workbook",
}


def within(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(prefix + ".")


def layer(module: str) -> str | None:
    if within(module, "hydra_plugins.cy_queue"):
        return "entrypoints"
    pieces = module.split(".")
    if module == "clearml_yolo":
        return "root"
    if len(pieces) < 2 or pieces[0] != "clearml_yolo":
        return None
    responsibilities: dict[str, set[str] | None] = {
        "core": None,
        "adapters": ADAPTER_RESPONSIBILITIES,
        "application": {"contracts", "ports", "evaluation", "use_cases"},
        "entrypoints": COMMANDS | {"composition", "hydra"},
    }
    selected = pieces[1]
    if selected not in responsibilities:
        return None
    permitted = responsibilities[selected]
    if len(pieces) == 2 or permitted is None or pieces[2] in permitted:
        return selected
    return None


def _edge_findings(importer: str, imported: str) -> list[str]:
    findings = []
    source_layer = next(
        (
            name
            for name in ("core", "application", "adapters", "entrypoints")
            if within(importer, f"clearml_yolo.{name}")
        ),
        layer(importer),
    )
    target_layer = layer(imported)
    if source_layer == target_layer == "adapters":
        source_parts, target_parts = importer.split("."), imported.split(".")
        if len(source_parts) > 2 and len(target_parts) > 2:
            source_peer, target_peer = source_parts[2], target_parts[2]
            if (
                source_peer != target_peer
                and target_peer not in ADAPTER_PEERS.get(source_peer, set())
                and (importer, imported) not in PEER_EXCEPTIONS
            ):
                findings.append(f"adapter peer ownership: {importer} -> {imported}")
    if target_layer is not None:
        forbidden = (
            (source_layer == "core" and target_layer not in {"core", "root"})
            or (source_layer == "application" and target_layer in {"adapters", "entrypoints"})
            or (source_layer == "adapters" and target_layer == "entrypoints")
            or (
                source_layer == "adapters"
                and target_layer == "application"
                and imported
                not in {
                    "clearml_yolo.application",
                    "clearml_yolo.application.ports",
                    "clearml_yolo.application.contracts",
                }
            )
        )
        if forbidden:
            findings.append(f"dependency direction: {importer} -> {imported}")
    external_root = imported.split(".", maxsplit=1)[0]
    if source_layer == "application" and external_root in APPLICATION_EFFECT_DEPENDENCIES:
        findings.append(f"application effects require ports: {importer} -> {imported}")
    if external_root in SDK_OWNERS and (
        not any(within(importer, owner) for owner in SDK_OWNERS[external_root])
        and (importer, external_root) not in SDK_EXCEPTIONS
    ):
        findings.append(f"SDK ownership: {importer} -> {imported}")
    if (
        source_layer == "core"
        and target_layer is None
        and (external_root not in sys.stdlib_module_names | SCIENTIFIC)
    ):
        findings.append(f"core dependency allowlist: {importer} -> {imported}")
    return findings


def _cycle_findings(graph: grimp.ImportGraph, modules: set[str]) -> list[str]:
    visited: set[str] = set()
    active: list[str] = []
    findings: list[str] = []

    def visit(module: str) -> None:
        if module in active:
            cycle = [*active[active.index(module) :], module]
            findings.append("dependency cycle: " + " -> ".join(cycle))
            return
        if module in visited:
            return
        active.append(module)
        for imported in sorted(graph.find_modules_directly_imported_by(module) & modules):
            visit(imported)
        active.pop()
        visited.add(module)

    for module in sorted(modules):
        visit(module)
    return findings


def graph_findings(graph: grimp.ImportGraph) -> list[str]:
    """Inspect every project module and edge, including transitive escape causes."""
    modules = {
        module for module in graph.modules if any(within(module, root) for root in PROJECT_ROOTS)
    }
    findings = []
    for module in sorted(modules):
        if layer(module) is None:
            findings.append(f"unclassified module: {module}")
        for imported in sorted(graph.find_modules_directly_imported_by(module)):
            findings.extend(_edge_findings(module, imported))
    findings.extend(_cycle_findings(graph, modules))
    return findings


def _call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def core_effect_findings(tree: ast.Module) -> list[str]:
    """Find explicit filesystem/network/process/config effects, including aliases."""
    aliases = {
        alias.asname or alias.name: alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if aliases.get(name, name) in EFFECTFUL_CALLS:
                findings.append(f"effectful core call at line {node.lineno}: {name}")
    return findings


def application_effect_findings(tree: ast.Module) -> list[str]:
    """Applications route effects through explicit injected storage ports."""
    findings: list[str] = []
    aliases = {
        alias.asname or alias.name: alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and aliases.get(_call_name(node.func), _call_name(node.func)) in EFFECTFUL_CALLS
        ):
            function = node.func
            if (
                isinstance(function, ast.Attribute)
                and isinstance(function.value, ast.Attribute)
                and function.value.attr == "storage"
                and isinstance(function.value.value, ast.Name)
                and function.value.value.id == "deps"
            ):
                continue
            findings.append(
                f"direct application effect at line {node.lineno}: {_call_name(function)}"
            )
    return findings


def _module_name(path: Path, source_root: Path) -> str:
    parts = path.relative_to(source_root).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def add_dynamic_imports(graph: grimp.ImportGraph, source_root: Path) -> None:
    """Literal import_module calls obey the same ownership as ordinary imports."""
    for path in source_root.rglob("*.py"):
        importer = _module_name(path, source_root)
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.Call)
                and _call_name(node.func) == "import_module"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                target = node.args[0].value
                imported = target if target.startswith(PROJECT_ROOTS) else target.split(".")[0]
                if imported not in graph.modules:
                    graph.add_module(imported)
                graph.add_import(importer=importer, imported=imported)


def _eager_import_nodes(statements: list[ast.stmt]) -> list[ast.Import | ast.ImportFrom]:
    imports: list[ast.Import | ast.ImportFrom] = []
    for node in statements:
        if isinstance(node, ast.Import | ast.ImportFrom):
            imports.append(node)
        elif isinstance(node, ast.ClassDef):
            imports.extend(_eager_import_nodes(node.body))
        elif isinstance(node, ast.If) and not (
            isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING"
        ):
            imports.extend(_eager_import_nodes(node.body + node.orelse))
    return imports


def _eager_targets(path: Path, source_root: Path, modules: set[str]) -> set[str]:
    targets: set[str] = set()
    module = _module_name(path, source_root)
    package = module if path.name == "__init__.py" else module.rsplit(".", 1)[0]
    for node in _eager_import_nodes(ast.parse(path.read_text()).body):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        else:
            base = (
                resolve_name("." * node.level + (node.module or ""), package)
                if node.level
                else node.module or ""
            )
            targets.add(base)
            targets.update(
                f"{base}.{alias.name}" for alias in node.names if f"{base}.{alias.name}" in modules
            )
    return targets


def initializer_dependency_findings(source_root: Path) -> list[str]:
    """Check eager imports through project re-exports without treating lazy calls as eager."""
    paths = {_module_name(path, source_root): path for path in source_root.rglob("*.py")}
    edges = {
        module: _eager_targets(path, source_root, set(paths)) for module, path in paths.items()
    }
    findings: list[str] = []

    def visit(module: str, chain: tuple[str, ...]) -> None:
        if module in chain:
            return
        next_chain = (*chain, module)
        if module.split(".", maxsplit=1)[0] in SDK_OWNERS:
            findings.append("eager SDK import chain: " + " -> ".join(next_chain))
        for imported in edges.get(module, set()):
            visit(imported, next_chain)

    for module, path in paths.items():
        if path.name == "__init__.py":
            visit(module, ())
    return findings


def config_targets(value: object) -> set[str]:
    """Collect dynamically generated Hydra targets without instantiating them."""
    targets: set[str] = set()
    if isinstance(value, Mapping):
        target = value.get("_target_")
        if isinstance(target, str) and target.startswith(PROJECT_ROOTS):
            targets.add(target)
        for child in value.values():
            targets.update(config_targets(child))
    elif isinstance(value, list | tuple):
        for child in value:
            targets.update(config_targets(child))
    return targets


def initializer_findings(tree: ast.Module) -> list[str]:
    """Definitions and pure re-exports are inert; eager SDK imports/calls are not."""
    findings: list[str] = []

    def inspect(statements: list[ast.stmt]) -> None:
        for node in statements:
            if (
                isinstance(node, ast.If)
                and isinstance(node.test, ast.Name)
                and node.test.id == "TYPE_CHECKING"
            ):
                continue
            if isinstance(node, ast.Import | ast.ImportFrom):
                names = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                if any(name.split(".")[0] in SDK_OWNERS for name in names):
                    findings.append(f"eager SDK import at line {node.lineno}")
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            elif isinstance(node, ast.ClassDef):
                inspect(node.body)
            elif any(isinstance(child, ast.Call) for child in ast.walk(node)):
                findings.append(f"initializer operation at line {node.lineno}")

    inspect(tree.body)
    return findings


def runtime_targets(source_root: Path, pyproject: Path) -> set[str]:
    """Inventory literal worker/probe/plugin/Hydra and console-script targets."""
    pattern = re.compile(r"(?:clearml_yolo|hydra_plugins)(?:\.[A-Za-z_]\w*)+(?::\w+)?")
    targets: set[str] = set()
    for path in source_root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and pattern.fullmatch(node.value)
            ):
                targets.add(node.value)
    config = tomllib.loads(pyproject.read_text())
    targets.update(config["project"]["scripts"].values())
    return targets


def _module_symbols(path: Path) -> set[str]:
    symbols: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            symbols.add(node.name)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            symbols.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            symbols.add(node.id)
    return symbols


def target_findings(targets: set[str], graph: grimp.ImportGraph, source_root: Path) -> list[str]:
    findings = []
    for target in sorted(targets):
        dotted = target.replace(":", ".")
        module = dotted
        while module not in graph.modules and "." in module:
            module = module.rsplit(".", 1)[0]
        if module not in graph.modules or module in PROJECT_ROOTS:
            findings.append(f"missing runtime module: {target}")
            continue
        if module == dotted:
            continue
        attribute = dotted[len(module) + 1 :].split(".")[0]
        path = source_root.joinpath(*module.split("."))
        path = (
            path.with_suffix(".py") if path.with_suffix(".py").is_file() else path / "__init__.py"
        )
        if attribute not in _module_symbols(path):
            findings.append(f"missing runtime attribute: {target}")
    return findings
