"""Load the approved source tree in its own package namespace, without sys.path edits."""

import hashlib
import importlib
import importlib.util
import shutil
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any

REVISION = "1d2ca42171570c713e78fc6a766ec5104b7f4724"


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


def load_source(source: Path | None) -> tuple[Any, Any]:
    if source is None:
        raise ValueError("DEIMv2 requires source_dir pointing to the approved upstream checkout")
    source = source.resolve()
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
    namespace = "_clearml_yolo_deimv2_" + hashlib.sha256(str(source).encode()).hexdigest()[:16]
    if namespace not in sys.modules:
        _load_package(namespace, source / "engine")
    return importlib.import_module(f"{namespace}.core"), importlib.import_module(
        f"{namespace}.solver"
    )


def _load_package(namespace: str, engine: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        namespace, engine / "__init__.py", submodule_search_locations=[str(engine)]
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load DEIMv2 package from {engine}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[namespace] = module
    complete = False
    try:
        # The pinned dataset module invokes init_as_pycocotools during import.
        # Preserve external evaluator identities while native modules retain their refs.
        with _preserve_coco_modules():
            spec.loader.exec_module(module)
        complete = True
    finally:
        if not complete:
            for key in list(sys.modules):
                if key == namespace or key.startswith(f"{namespace}."):
                    del sys.modules[key]
    return module
