"""Child-only guard for SDK constants that ignore documented environment selectors."""

import ast
import importlib.abc
import importlib.machinery
import importlib.metadata
import json
import os
import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import override

from packaging.version import Version

_PATHS = {
    "FIFTYONE_CONFIG_PATH": "config.json",
    "FIFTYONE_ANNOTATION_CONFIG_PATH": "annotation_config.json",
    "FIFTYONE_EVALUATION_CONFIG_PATH": "evaluation_config.json",
    "FIFTYONE_APP_CONFIG_PATH": "app_config.json",
    "TEAMS_PATH": "var/teams.json",
    "WELCOME_PATH": "var/welcome.json",
    "MIGRATIONS_PATH": "migrations",
    "MIGRATIONS_HEAD_PATH": "migrations/head.json",
}


def _guard_layout() -> None:
    version = Version(importlib.metadata.version("fiftyone"))
    if version < Version("1.22") or version >= Version("2"):
        raise RuntimeError(f"Unsupported FiftyOne constants compatibility version: {version}")
    spec = importlib.machinery.PathFinder.find_spec("fiftyone")
    if spec is None or spec.origin is None:
        raise RuntimeError("FiftyOne package initializer is unavailable")
    source = ast.parse(Path(spec.origin).read_text(encoding="utf-8"))
    constants_index: int | None = None
    public_index: int | None = None
    for index, node in enumerate(source.body):
        if isinstance(node, ast.Import) and any(
            alias.name == "fiftyone.constants" for alias in node.names
        ):
            constants_index = index
        if isinstance(node, ast.ImportFrom) and node.module == "fiftyone.__public__":
            public_index = index
    if constants_index is None or public_index is None or constants_index >= public_index:
        raise RuntimeError(
            "Unsupported FiftyOne initializer: constants must precede public imports"
        )


class _ConstantsLoader(importlib.abc.Loader):
    def __init__(self, original: importlib.abc.Loader) -> None:
        self.original = original

    @override
    def create_module(self, spec: importlib.machinery.ModuleSpec) -> ModuleType | None:
        return self.original.create_module(spec)

    @override
    def exec_module(self, module: ModuleType) -> None:
        self.original.exec_module(module)
        # This SDK module is untyped; validate its complete known layout before redirecting.
        names = ["FIFTYONE_CONFIG_DIR", "DEFAULT_DB_DIR", "FIFTYONE_DB_BIN_DIR", *_PATHS]
        if any(not isinstance(getattr(module, name, None), str) for name in names):
            raise RuntimeError("Unsupported FiftyOne constants layout")
        old_root = Path(module.__dict__["FIFTYONE_CONFIG_DIR"])
        for name in ["DEFAULT_DB_DIR", *_PATHS]:
            if not Path(getattr(module, name)).is_relative_to(old_root):
                raise RuntimeError(f"Unsupported FiftyOne constant path layout: {name}")
        root = Path(os.environ["FIFTYONE_CONFIG_PATH"]).parent
        if not root.is_absolute():
            raise RuntimeError("FiftyOne configuration directory must be absolute")
        project = Path(os.environ.get("CY_HOME", root)).resolve()
        old_bin = Path(module.__dict__["FIFTYONE_DB_BIN_DIR"])
        module.__dict__["FIFTYONE_CONFIG_DIR"] = str(root)
        for name, relative in _PATHS.items():
            # Only documented configuration selectors were validated by bootstrap.
            # Internal SDK state constants are not independent environment selectors.
            selected = (
                os.environ.get(name, str(root / relative))
                if name.startswith("FIFTYONE_")
                else str(root / relative)
            )
            setattr(module, name, str(_project_state_path(project, Path(selected))))
        module.__dict__["DEFAULT_DB_DIR"] = os.environ["FIFTYONE_DATABASE_DIR"]
        if old_bin.is_relative_to(old_root):
            module.__dict__["FIFTYONE_DB_BIN_DIR"] = str(_project_state_path(project, root / "bin"))


def _project_state_path(project: Path, selected: Path) -> Path:
    selected = selected.resolve()
    if not selected.is_relative_to(project):
        raise RuntimeError(
            f"FiftyOne state must resolve inside the physical project root: {selected}"
        )
    return selected


class _ConstantsFinder(importlib.abc.MetaPathFinder):
    @override
    def find_spec(
        self, fullname: str, path: Sequence[str] | None, target: ModuleType | None = None
    ) -> importlib.machinery.ModuleSpec | None:
        del target
        if fullname != "fiftyone.constants":
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or spec.loader is None:
            raise RuntimeError("FiftyOne constants loader is unavailable")
        spec.loader = _ConstantsLoader(spec.loader)
        return spec


@contextmanager
def isolated_constants() -> Iterator[None]:
    """Install for the worker's first backend import only; never edit SDK source."""
    if "fiftyone" in sys.modules or "fiftyone.constants" in sys.modules:
        raise RuntimeError("FiftyOne compatibility must be installed before backend import")
    _guard_layout()
    _configure_eta_models()
    finder = _ConstantsFinder()
    sys.meta_path.insert(0, finder)
    try:
        yield
    finally:
        sys.meta_path.remove(finder)


def _configure_eta_models() -> None:
    selected = os.environ.get("CY_ETA_MODELS_DIRS")
    if selected is None:
        return
    paths: object = json.loads(selected)
    if not isinstance(paths, list) or not all(isinstance(value, str) for value in paths):
        raise RuntimeError("Owned ETA model directories must be a JSON array of strings")
    if "ETA_MODELS_DIRS" in os.environ:
        raise RuntimeError("ETA model environment must be normalized before backend import")
    import eta

    # The dependency has no type information; its documented API validates
    # configuration without mutating its implementation or parsing a path list.
    eta.set_config_settings(models_dirs=paths)
