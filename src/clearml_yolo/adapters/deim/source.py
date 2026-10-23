"""Load the approved source tree in its own package namespace, without sys.path edits."""

import hashlib
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import shutil
import subprocess
import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import CodeType, ModuleType
from typing import Any, override

from clearml_yolo.core.assets import DEIM_REVISION

REVISION = DEIM_REVISION


def _coco_modules() -> dict[str, ModuleType]:
    return {
        name: module
        for name, module in list(sys.modules.items())
        if name == "pycocotools" or name.startswith("pycocotools.")
    }


@contextmanager
def _preserve_coco_modules() -> Iterator[None]:
    original = _coco_modules()
    try:
        yield
    finally:
        for name in _coco_modules():
            del sys.modules[name]
        sys.modules.update(original)


@contextmanager
def native_coco_modules() -> Iterator[None]:
    """Keep native fast COCO dataset construction local to sequential DEIM execution.

    Torchvision delays its COCO import until dataset construction. The constructed
    reader retains native classes after restoration. Parallel family execution must
    use separate processes because Python's module registry is process-global.
    """
    with _preserve_coco_modules():
        modules = {
            "pycocotools": "faster_coco_eval",
            "pycocotools.coco": "faster_coco_eval.core.coco",
            "pycocotools.cocoeval": "faster_coco_eval.core.faster_eval_api",
            "pycocotools.mask": "faster_coco_eval.core.mask",
        }
        sys.modules.update(
            {name: importlib.import_module(source) for name, source in modules.items()}
        )
        yield


def validate_checkout(source: Path) -> None:
    from clearml_yolo.adapters.assets.archive import validate_source
    from clearml_yolo.adapters.storage.filesystem import cy_home

    source = source.expanduser().resolve()
    managed = cy_home() / ".cache" / "clearml-yolo" / "sources" / "DEIMv2" / REVISION
    if source == managed:
        validate_source(source)
        return
    if not (source / "engine" / "__init__.py").is_file():
        raise FileNotFoundError(f"DEIMv2 source_dir has no engine package: {source}")
    git = shutil.which("git")
    if git is None:
        raise FileNotFoundError("Git is required to verify the pinned DEIMv2 source checkout")
    revision = subprocess.run(  # noqa: S603 -- fixed Git operation; no shell interpolation
        [git, "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    ).stdout.strip()
    if revision != REVISION:
        raise ValueError(f"DEIMv2 requires source revision {REVISION}; found {revision}")
    dirty = subprocess.run(  # noqa: S603 -- fixed Git operation; no shell interpolation
        [git, "-C", str(source), "diff", "--exit-code", "HEAD", "--", "engine", "configs"],
        check=False,
        capture_output=True,
        timeout=15,
    )
    if dirty.returncode:
        raise ValueError("DEIMv2 source engine/configs differ from the approved revision")
    untracked = subprocess.run(  # noqa: S603 -- fixed Git operation; no shell interpolation
        [
            git,
            "-C",
            str(source),
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "engine",
            "configs",
        ],
        check=True,
        capture_output=True,
        timeout=15,
    )
    if untracked.stdout:
        raise ValueError("DEIMv2 source engine/configs contain untracked files")


def load_source(source: Path | None) -> tuple[Any, Any]:
    if source is None:
        from clearml_yolo.adapters.assets.sources import prepare_deim_source

        source, _ = prepare_deim_source()
    source = source.expanduser().resolve()
    from clearml_yolo.adapters.assets.archive import validate_source
    from clearml_yolo.adapters.storage.filesystem import cy_home

    managed = cy_home() / ".cache" / "clearml-yolo" / "sources" / "DEIMv2" / REVISION
    if source == managed:
        validate_source(source)
    else:
        validate_checkout(source)
    namespace = "_clearml_yolo_deimv2_" + hashlib.sha256(str(source).encode()).hexdigest()[:16]
    if namespace not in sys.modules:
        _load_package(namespace, source / "engine", verified=source == managed)
    return importlib.import_module(f"{namespace}.core"), importlib.import_module(
        f"{namespace}.solver"
    )


class _VerifiedSourceLoader(importlib.machinery.SourceFileLoader):
    def __init__(self, name: str, path: str, root: Path, manifest: dict[str, str]) -> None:
        super().__init__(name, path)
        self.root = root
        self.manifest = manifest

    @override
    def get_code(self, fullname: str) -> CodeType:
        source = self.get_data(self.path)
        relative = Path(self.path).relative_to(self.root).as_posix()
        if hashlib.sha256(source).hexdigest() != self.manifest.get(relative):
            raise ImportError(f"DEIM source changed before importing {fullname}: {relative}")
        # Never consume or publish .pyc files for downloaded code; a stale or
        # modified bytecode cache cannot bypass the packaged source manifest.
        return self.source_to_code(source, self.path)


class _VerifiedSourceFinder(importlib.abc.MetaPathFinder):
    def __init__(self, namespace: str, root: Path) -> None:
        from clearml_yolo.adapters.assets.archive import source_manifest

        self.namespace = namespace
        self.root = root
        self.manifest = source_manifest()

    @override
    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if not fullname.startswith(self.namespace + "."):
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None:
            return None
        if not spec.origin or not isinstance(spec.loader, importlib.machinery.SourceFileLoader):
            raise ImportError(
                f"DEIM managed modules require manifest-verified Python source: {fullname}"
            )
        spec.loader = _VerifiedSourceLoader(fullname, spec.origin, self.root, self.manifest)
        return spec


def _load_package(namespace: str, engine: Path, *, verified: bool = False) -> ModuleType:
    finder = _VerifiedSourceFinder(namespace, engine.parent) if verified else None
    loader = (
        _VerifiedSourceLoader(
            namespace, str(engine / "__init__.py"), engine.parent, finder.manifest
        )
        if finder
        else None
    )
    spec = importlib.util.spec_from_file_location(
        namespace, engine / "__init__.py", loader=loader, submodule_search_locations=[str(engine)]
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load DEIMv2 package from {engine}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[namespace] = module
    complete = False
    if finder is not None:
        sys.meta_path.insert(0, finder)
    try:
        # The pinned dataset module invokes init_as_pycocotools during import.
        # Preserve external evaluator identities while native modules retain their refs.
        with _preserve_coco_modules():
            spec.loader.exec_module(module)
        complete = True
    finally:
        if not complete:
            if finder is not None:
                sys.meta_path.remove(finder)
            for key in list(sys.modules):
                if key == namespace or key.startswith(f"{namespace}."):
                    del sys.modules[key]
    return module
