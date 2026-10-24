"""Static architecture checks shared by positive and injected negative tests."""

import ast
import configparser
import re
import sys
import tomllib
from collections.abc import Iterator, Mapping
from graphlib import CycleError, TopologicalSorter
from importlib.util import resolve_name
from pathlib import Path
from typing import override

import grimp

PROJECT_ROOTS = ("clearml_yolo",)
SCIENTIFIC = {"pydantic", "pandera", "pandas", "numpy", "scipy"}
PURE_ADAPTERS = {
    "clearml_yolo.adapters.clearml.parameters": set(),
    "clearml_yolo.adapters.clearml.cache": {"yaml", "clearml_yolo.adapters.clearml.parameters"},
}
# Ownership lives in import-linter; initializers and literal launch targets need
# only its external roots, not a second table of permitted owners or peer edges.
IMPORT_CONTRACTS = configparser.ConfigParser()
IMPORT_CONTRACTS.read(Path(__file__).resolve().parents[1] / ".importlinter")
SDK_ROOTS = {
    root
    for section in IMPORT_CONTRACTS.sections()
    if section.endswith("-sdk-has-explicit-owners")
    for root in IMPORT_CONTRACTS[section]["forbidden_modules"].split()
}
QUEUE_ROOTS = set(
    IMPORT_CONTRACTS["importlinter:contract:cy-never-imports-extracted-queue"][
        "forbidden_modules"
    ].split()
)
SDK_ROOTS |= QUEUE_ROOTS
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
    "touch",
}
QUALIFIED_EFFECTS = {
    "requests": {"get", "post", "put", "patch", "delete", "head", "options", "request", "send"},
    "httpx": {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
        "request",
        "send",
        "stream",
    },
    "socket": {
        "socket",
        "socketpair",
        "create_connection",
        "create_server",
        "getaddrinfo",
        "gethostbyname",
        "gethostbyname_ex",
        "gethostbyaddr",
        "bind",
        "listen",
        "accept",
        "connect",
        "connect_ex",
        "send",
        "sendall",
        "sendto",
        "recv",
        "recvfrom",
        "shutdown",
    },
    "subprocess": {
        "run",
        "Popen",
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
    },
    "shutil": {
        "copy",
        "copy2",
        "copyfile",
        "copytree",
        "copystat",
        "copymode",
        "rmtree",
        "move",
        "disk_usage",
        "which",
        "chown",
        "make_archive",
        "unpack_archive",
    },
    "tempfile": {
        "TemporaryFile",
        "NamedTemporaryFile",
        "TemporaryDirectory",
        "mkdtemp",
        "mkstemp",
        "gettempdir",
        "gettempdirb",
    },
    "os": {
        "environ",
        "getenv",
        "putenv",
        "unsetenv",
        "listdir",
        "scandir",
        "walk",
        "chdir",
        "getcwd",
        "mkdir",
        "makedirs",
        "remove",
        "unlink",
        "rename",
        "replace",
        "rmdir",
        "removedirs",
        "stat",
        "lstat",
        "open",
        "read",
        "write",
        "system",
        "popen",
        "fork",
        "kill",
        "execv",
        "execve",
        "spawnv",
        "spawnve",
    },
}


def within(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(prefix + ".")


def launch_target_findings(importer: str, targets: set[str]) -> list[str]:
    return [
        f"CY imports extracted scheduling: {importer} -> {target}"
        for target in targets
        if within(importer, "clearml_yolo") and any(within(target, root) for root in QUEUE_ROOTS)
    ]


def graph_findings(graph: grimp.ImportGraph) -> list[str]:
    """Check allowlists and whole-graph cycles not expressed by import-linter."""
    modules = {module for module in graph.modules if within(module, "clearml_yolo")}
    findings = []
    dependencies = {}
    for module in sorted(modules):
        imports = graph.find_modules_directly_imported_by(module)
        dependencies[module] = imports & modules
        for imported in sorted(imports):
            external_root = imported.split(".", maxsplit=1)[0]
            if (
                module in PURE_ADAPTERS
                and external_root not in sys.stdlib_module_names
                and not any(within(imported, allowed) for allowed in PURE_ADAPTERS[module])
            ):
                findings.append(f"pure adapter dependency: {module} -> {imported}")
            if (
                within(module, "clearml_yolo.core")
                and external_root not in sys.stdlib_module_names | SCIENTIFIC | {"clearml_yolo"}
            ):
                findings.append(f"core dependency allowlist: {module} -> {imported}")
    try:
        tuple(TopologicalSorter(dependencies).static_order())
    except CycleError as error:
        findings.append("dependency cycle: " + " -> ".join(error.args[1]))
    return findings


def _definition_expressions(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda,
) -> Iterator[ast.expr]:
    if not isinstance(node, ast.Lambda):
        yield from node.decorator_list
    if isinstance(node, ast.ClassDef):
        yield from node.bases
        yield from (keyword.value for keyword in node.keywords)
    else:
        yield from node.args.defaults
        yield from (default for default in node.args.kw_defaults if default is not None)
        for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            if argument.annotation is not None:
                yield argument.annotation
        for variadic in (node.args.vararg, node.args.kwarg):
            if variadic is not None and variadic.annotation is not None:
                yield variadic.annotation
        if not isinstance(node, ast.Lambda) and node.returns is not None:
            yield node.returns


def _scope_nodes(
    nodes: list[ast.stmt], type_checking: frozenset[str] = frozenset()
) -> Iterator[ast.AST]:
    """Walk bindings in one Python scope, without entering child namespaces."""
    for node in nodes:
        yield node
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        if isinstance(node, ast.If) and _dotted_name(node.test) in type_checking:
            yield from _scope_nodes(node.orelse, type_checking)
            continue
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                yield from _scope_nodes([child], type_checking)
            elif isinstance(child, ast.ExceptHandler):
                yield from _scope_nodes(child.body, type_checking)


def _bound_names(target: ast.AST) -> Iterator[str]:
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, ast.Tuple | ast.List):
        for child in target.elts:
            yield from _bound_names(child)
    elif isinstance(target, ast.Starred):
        yield from _bound_names(target.value)


def _function_locals(statements: list[ast.stmt], arguments: ast.arguments) -> dict[str, str]:
    local: dict[str, str] = {}
    for statement in _scope_nodes(statements):
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            local[statement.name] = "@local"
        elif isinstance(statement, ast.Import | ast.ImportFrom):
            for alias in statement.names:
                local[alias.asname or alias.name.split(".")[0]] = "@local"
        elif isinstance(statement, ast.Assign | ast.AnnAssign | ast.For | ast.AsyncFor):
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            for target in targets:
                local.update(dict.fromkeys(_bound_names(target), "@local"))
    for argument in (
        *arguments.posonlyargs,
        *arguments.args,
        *arguments.kwonlyargs,
        *([arguments.vararg] if arguments.vararg else []),
        *([arguments.kwarg] if arguments.kwarg else []),
    ):
        local[argument.arg] = "deps" if argument.arg == "deps" else "@local"
    return local


class _EffectVisitor(ast.NodeVisitor):
    """Resolve explicit imports/aliases lexically, without evaluating inspected code."""

    def __init__(self, *, application: bool) -> None:
        self.application = application
        self.scopes: list[dict[str, str]] = [{}]
        self.class_scopes: list[dict[str, str]] = []
        self.findings: list[str] = []
        self.dynamic_imports: set[str] = set()
        self.deferred: list[
            tuple[ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, list[dict[str, str]]]
        ] = []

    @override
    def visit_Module(self, node: ast.Module) -> None:
        self.generic_visit(node)
        module_scopes = self.scopes
        # Deferred callables see final enclosing bindings, while defaults and class
        # bodies above are inspected at their definition point. This does not model
        # calls made during module initialization or arbitrary later rebinding.
        while self.deferred:
            function, self.scopes = self.deferred.pop()
            if isinstance(function, ast.Lambda):
                self.visit(function.body)
            else:
                for statement in function.body:
                    self.visit(statement)
        self.scopes = module_scopes

    def qualified(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            for scope in reversed(self.scopes):
                if node.id in scope:
                    return scope[node.id]
            return node.id if node.id in {"open", "__import__", "deps"} else "@unbound." + node.id
        if isinstance(node, ast.Attribute):
            return self.qualified(node.value) + "." + node.attr
        if isinstance(node, ast.Call):
            return self.qualified(node.func)
        return "@local"

    def report(self, node: ast.expr, name: str) -> None:
        owner = "direct application effect" if self.application else "effectful core call"
        self.findings.append(f"{owner} at line {node.lineno}: {name}")

    @override
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.scopes[-1][alias.asname or alias.name.split(".")[0]] = (
                alias.name if alias.asname else alias.name.split(".")[0]
            )

    @override
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            self.scopes[-1][alias.asname or alias.name] = f"{node.module}.{alias.name}"

    @override
    def visit_Assign(self, node: ast.Assign) -> None:
        self.generic_visit(node)
        for target in node.targets:
            for name in _bound_names(target):
                self.scopes[-1][name] = self.qualified(node.value)

    @override
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.generic_visit(node)
        for name in _bound_names(node.target):
            self.scopes[-1][name] = self.qualified(node.value or node.annotation)

    @override
    def visit_Call(self, node: ast.Call) -> None:
        name = self.qualified(node.func)
        if (
            name in {"importlib.import_module", "__import__", "builtins.__import__"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            self.dynamic_imports.add(node.args[0].value)
        root = name.split(".")[0]
        method = name.rsplit(".", 1)[-1]
        ambiguous = {"run", "connect", "send", "recv", "getenv", "system", "popen", "Popen"}
        explicit = (
            name in {"open", "__import__", "builtins.open", "builtins.__import__"}
            or method in QUALIFIED_EFFECTS.get(root, set())
            or name.startswith(("urllib.request.", "http.client.", "multiprocessing."))
            or method in EFFECTFUL_CALLS - ambiguous
        )
        port_effect = self.application and (
            name.startswith("deps.storage.") or name == "deps.ground_truth_repository.resolve"
        )
        if explicit and not port_effect:
            self.report(node, name)
        self.generic_visit(node)

    @override
    def visit_Attribute(self, node: ast.Attribute) -> None:
        name = self.qualified(node)
        if name == "os.environ":
            self.report(node, name)
        self.generic_visit(node)

    @override
    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and self.qualified(node) == "os.environ":
            self.report(node, "os.environ")

    def function_scope(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda) -> None:
        for expression in _definition_expressions(node):
            self.visit(expression)
        if not isinstance(node, ast.Lambda):
            self.scopes[-1][node.name] = "@local"
        statements = [] if isinstance(node, ast.Lambda) else node.body
        local = _function_locals(statements, node.args)
        # Methods close over surrounding functions/modules, never class namespaces.
        captured = [
            scope
            for scope in self.scopes
            if all(scope is not class_scope for class_scope in self.class_scopes)
        ] + [local]
        self.deferred.append((node, captured))

    @override
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_scope(node)

    @override
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_scope(node)

    @override
    def visit_Lambda(self, node: ast.Lambda) -> None:
        self.function_scope(node)

    @override
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for expression in _definition_expressions(node):
            self.visit(expression)
        outer_scopes = self.scopes
        self.scopes = [
            scope
            for scope in self.scopes
            if all(scope is not class_scope for class_scope in self.class_scopes)
        ] + [{}]
        self.class_scopes.append(self.scopes[-1])
        for statement in node.body:
            self.visit(statement)
        self.class_scopes.pop()
        self.scopes = outer_scopes
        self.scopes[-1][node.name] = "@local"

    def comprehension_scope(
        self, node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp
    ) -> None:
        self.visit(node.generators[0].iter)
        outer_scopes = self.scopes
        self.scopes = [
            scope
            for scope in self.scopes
            if all(scope is not class_scope for class_scope in self.class_scopes)
        ] + [{}]
        for index, generator in enumerate(node.generators):
            if index:
                self.visit(generator.iter)
            self.scopes[-1].update(dict.fromkeys(_bound_names(generator.target), "@local"))
            for condition in generator.ifs:
                self.visit(condition)
        if isinstance(node, ast.DictComp):
            self.visit(node.key)
            self.visit(node.value)
        else:
            self.visit(node.elt)
        self.scopes = outer_scopes

    @override
    def visit_ListComp(self, node: ast.ListComp) -> None:
        self.comprehension_scope(node)

    @override
    def visit_SetComp(self, node: ast.SetComp) -> None:
        self.comprehension_scope(node)

    @override
    def visit_DictComp(self, node: ast.DictComp) -> None:
        self.comprehension_scope(node)

    @override
    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self.comprehension_scope(node)


def core_effect_findings(tree: ast.Module) -> list[str]:
    """Find covered filesystem/network/process/environment effects in lexical scopes."""
    visitor = _EffectVisitor(application=False)
    visitor.visit(tree)
    return visitor.findings


def application_effect_findings(tree: ast.Module) -> list[str]:
    """Applications route effects through explicit injected storage ports."""
    visitor = _EffectVisitor(application=True)
    visitor.visit(tree)
    return visitor.findings


def pure_adapter_effect_findings(module: str, tree: ast.Module) -> list[str]:
    """Apply the established no-effects scanner only to declared pure adapters."""
    return core_effect_findings(tree) if module in PURE_ADAPTERS else []


def _module_name(path: Path, source_root: Path) -> str:
    parts = path.relative_to(source_root).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def add_dynamic_imports(graph: grimp.ImportGraph, source_root: Path) -> None:
    """Literal import_module calls obey the same ownership as ordinary imports."""
    for path in source_root.rglob("*.py"):
        importer = _module_name(path, source_root)
        visitor = _EffectVisitor(application=False)
        visitor.visit(ast.parse(path.read_text()))
        for target in visitor.dynamic_imports:
            imported = target if target.startswith(PROJECT_ROOTS) else target.split(".")[0]
            if imported not in graph.modules:
                graph.add_module(imported)
            graph.add_import(importer=importer, imported=imported)


def _type_checking_names(tree: ast.Module) -> set[str]:
    names = {"TYPE_CHECKING", "typing.TYPE_CHECKING"}
    for node in _scope_nodes(tree.body):
        if isinstance(node, ast.Import):
            names.update(
                f"{alias.asname or alias.name}.TYPE_CHECKING"
                for alias in node.names
                if alias.name == "typing"
            )
        elif isinstance(node, ast.ImportFrom) and node.module == "typing":
            names.update(
                alias.asname or alias.name for alias in node.names if alias.name == "TYPE_CHECKING"
            )
    return names


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _dotted_name(node.value) + "." + node.attr
    return ""


def _eager_nodes(node: ast.AST, type_checking: set[str]) -> Iterator[ast.AST]:
    """Traverse executed definition expressions, but never deferred callable bodies."""
    yield node
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
        for expression in _definition_expressions(node):
            yield from _eager_nodes(expression, type_checking)
        if isinstance(node, ast.ClassDef):
            for statement in node.body:
                yield from _eager_nodes(statement, type_checking)
    elif isinstance(node, ast.If) and _dotted_name(node.test) in type_checking:
        for statement in node.orelse:
            yield from _eager_nodes(statement, type_checking)
    else:
        for child in ast.iter_child_nodes(node):
            yield from _eager_nodes(child, type_checking)


def _eager_targets(path: Path, source_root: Path, modules: set[str]) -> set[str]:
    targets: set[str] = set()
    module = _module_name(path, source_root)
    package = module if path.name == "__init__.py" else module.rsplit(".", 1)[0]
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in _eager_nodes(tree, _type_checking_names(tree)):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
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
        if module.split(".", maxsplit=1)[0] in SDK_ROOTS:
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
    """Plain definitions/re-exports are inert; definition-time calls are not."""
    findings: list[str] = []
    for node in _eager_nodes(tree, _type_checking_names(tree)):
        if isinstance(node, ast.Import | ast.ImportFrom):
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            if any(name.split(".")[0] in SDK_ROOTS for name in names):
                findings.append(f"eager SDK import at line {node.lineno}")
        elif isinstance(node, ast.Call):
            findings.append(f"initializer operation at line {node.lineno}")
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            findings.extend(
                f"initializer decorator at line {decorator.lineno}"
                for decorator in node.decorator_list
            )
    return findings


def runtime_targets(source_root: Path, pyproject: Path) -> set[str]:
    """Inventory literal worker/probe/plugin/Hydra and console-script targets."""
    pattern = re.compile(
        r"(?:clearml_yolo|hydra_plugins)(?:\.[A-Za-z_]\w*)+(?::[A-Za-z_]\w*(?:\.\w+)*)?"
    )
    targets: set[str] = set()
    for path in source_root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and pattern.fullmatch(node.value)
            ):
                targets.add(node.value)
    config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    targets.update(config["project"]["scripts"].values())
    return targets


def runtime_boundary_findings(source_root: Path) -> list[str]:
    """Apply direct/queue boundaries to literal subprocess and dynamic import targets."""
    findings: list[str] = []
    for path in source_root.rglob("*.py"):
        importer = ".".join(path.relative_to(source_root).with_suffix("").parts)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        # A literal used solely as a comparison value is a selector, not a
        # launch target (for example rejection of the retired cy_queue launcher).
        selectors = {
            id(value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Compare)
            for value in (node.left, *node.comparators)
            if isinstance(value, ast.Constant)
        }
        targets = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in selectors
        }
        findings.extend(launch_target_findings(importer, targets))
    return findings


def _symbol_references(symbols: Mapping[str, ast.AST | str], prefix: str) -> dict[str, str]:
    return {
        name: symbol if isinstance(symbol, str) else f"{prefix}.{name}"
        for name, symbol in symbols.items()
    }


def _assignment_symbols(
    node: ast.Assign | ast.AnnAssign, references: Mapping[str, str]
) -> dict[str, ast.AST | str]:
    # An annotation alone does not create a runtime attribute.
    if node.value is None:
        return {}
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    alias_target = _dotted_name(node.value)
    value: ast.AST | str = node.value
    if alias_target:
        root, _, suffix = alias_target.partition(".")
        resolved = references.get(root, f"@unresolved.{root}")
        value = resolved + ("." + suffix if suffix else "")
    return {name: value for target in targets for name in _bound_names(target)}


def _scope_symbols(
    statements: list[ast.stmt],
    prefix: str,
    package: str,
    outer: Mapping[str, str] | None = None,
    *,
    before_line: int | None = None,
) -> dict[str, ast.AST | str]:
    symbols: dict[str, ast.AST | str] = {}
    type_checking = frozenset(_type_checking_names(ast.Module(body=statements, type_ignores=[])))
    for node in _scope_nodes(statements, type_checking):
        if isinstance(node, ast.stmt) and before_line is not None and node.lineno >= before_line:
            continue
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            symbols[node.name] = node
        elif isinstance(node, ast.Import):
            for alias in node.names:
                symbols[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom):
            base = (
                resolve_name("." * node.level + (node.module or ""), package)
                if node.level
                else node.module or ""
            )
            for alias in node.names:
                symbols[alias.asname or alias.name] = f"{base}.{alias.name}"
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            references = dict(outer or {}) | _symbol_references(symbols, prefix)
            symbols.update(_assignment_symbols(node, references))
    return symbols


class _TargetResolver:
    """Resolve explicit source declarations and imports, including cyclic re-exports."""

    def __init__(self, source_root: Path, modules: set[str]) -> None:
        self.paths = {_module_name(path, source_root): path for path in source_root.rglob("*.py")}
        self.modules = modules
        self.parsed: dict[str, ast.Module] = {}

    def module_of(self, target: str) -> str | None:
        module = target
        while module not in self.paths and "." in module:
            module = module.rsplit(".", 1)[0]
        return module if module in self.paths and module in self.modules else None

    def resolves(self, target: str, active: frozenset[str] = frozenset()) -> bool:
        module = self.module_of(target)
        if target in active or module is None:
            return False
        path = self.paths[module]
        package = module if path.name == "__init__.py" else module.rsplit(".", 1)[0]
        if module not in self.parsed:
            self.parsed[module] = ast.parse(path.read_text(encoding="utf-8"))
        scope: ast.Module | ast.ClassDef = self.parsed[module]
        prefix = module
        outer: dict[str, str] = {}
        attributes = target[len(module) + 1 :].split(".") if target != module else []
        for index, attribute in enumerate(attributes):
            symbol = _scope_symbols(scope.body, prefix, package, outer).get(attribute)
            if symbol is None:
                return False
            if isinstance(symbol, str):
                suffix = ".".join(attributes[index + 1 :])
                return self.resolves(symbol + ("." + suffix if suffix else ""), active | {target})
            if index == len(attributes) - 1:
                return True
            if not isinstance(symbol, ast.ClassDef):
                return False
            # A class body sees its own previous assignments and enclosing function/
            # module bindings, never an outer class namespace. Targets inside local
            # function definitions remain unsupported, so this fallback is the module.
            if isinstance(scope, ast.Module):
                outer = _symbol_references(
                    _scope_symbols(scope.body, module, package, before_line=symbol.lineno), module
                )
            scope = symbol
            prefix += "." + attribute
        return True


def target_findings(targets: set[str], graph: grimp.ImportGraph, source_root: Path) -> list[str]:
    """Check every static module/class/re-export segment without importing targets."""
    resolver = _TargetResolver(source_root, set(graph.modules))
    findings = []
    for target in sorted(targets):
        dotted = target.replace(":", ".")
        module = resolver.module_of(dotted)
        if module is None or (module in PROJECT_ROOTS and dotted == module):
            findings.append(f"missing runtime module: {target}")
        elif not resolver.resolves(dotted):
            findings.append(f"missing runtime attribute: {target}")
    return findings
