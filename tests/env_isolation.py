"""Redirect HOME away from the developer's real one before clearml_yolo is imported.

Loaded through ``-p tests.env_isolation`` in ``[tool.pytest.ini_options].addopts`` so it
runs during pytest startup, ahead of every conftest and test module. SDKs used by the
project (ClearML, Ultralytics, FiftyOne, Hydra) read configuration and caches from HOME;
tests must never read or write the developer's real files.

Live tests need some real locations (the k8s-infra skill directory, weights caches). The
original values are kept as JSON in ``CY_REAL_ENV``; read them with ``real_env``.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

REAL_ENV_VARIABLE = "CY_REAL_ENV"
_REPLACED = ("HOME", "USERPROFILE", "XDG_CONFIG_HOME", "XDG_CACHE_HOME")
_FAKE_HOME = Path(tempfile.mkdtemp(prefix="clearml-yolo-test-home-"))

# An xdist worker inherits the controller's record, so only the first writer sets it.
os.environ.setdefault(REAL_ENV_VARIABLE, json.dumps({name: os.environ.get(name) for name in _REPLACED}))

os.environ["HOME"] = str(_FAKE_HOME)
os.environ["USERPROFILE"] = str(_FAKE_HOME)
os.environ["XDG_CONFIG_HOME"] = str(_FAKE_HOME / ".config")
os.environ["XDG_CACHE_HOME"] = str(_FAKE_HOME / ".cache")

# Under the pre-commit hook git exports GIT_INDEX_FILE (and may export GIT_DIR or
# GIT_WORK_TREE). Tests that build throwaway repositories must not touch the commit
# in progress.
for _name in [name for name in os.environ if name.startswith("GIT_")]:
    del os.environ[_name]


def real_env() -> dict[str, str]:
    """Return the HOME-related variables as they were before isolation."""
    recorded: dict[str, str | None] = json.loads(os.environ[REAL_ENV_VARIABLE])
    return {name: value for name, value in recorded.items() if value is not None}


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Give each mutation child a temporary root whose cleanup cannot affect siblings."""
    mutation_root = os.environ.get("PYTEST_DEBUG_TEMPROOT")
    if mutation_root and os.environ.get("MUTANT_UNDER_TEST"):
        config.option.basetemp = str(Path(mutation_root) / f"worker-{os.getpid()}")


def pytest_unconfigure(config: pytest.Config) -> None:
    """Remove the throwaway home once the session or xdist worker finishes."""
    shutil.rmtree(_FAKE_HOME, ignore_errors=True)
