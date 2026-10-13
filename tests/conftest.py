"""Isolate process-wide runtime configuration between tests."""

import os
import sys
import tempfile
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path

import pytest

from clearml_yolo.adapters.runtime import bootstrap


@pytest.fixture(autouse=True)
def restore_clearml_owner_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset adapter ownership at test boundaries, never between sweep invocations."""
    from clearml_yolo.adapters.clearml import session

    monkeypatch.setattr(session, "_INCOMPLETE_OWNER", session._IncompleteOwner())


@pytest.fixture(autouse=True)
def restore_runtime_configuration(tmp_path: Path) -> Iterator[None]:
    """Programmatic initialization persists intentionally, but not across test cases."""
    environment = dict(os.environ)
    bytecode = sys.pycache_prefix
    temporary = tempfile.tempdir
    state = deepcopy(bootstrap._STATE)
    os.environ["CY_HOME"] = str(tmp_path)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(environment)
        sys.pycache_prefix = bytecode
        tempfile.tempdir = temporary
        bootstrap._STATE = state
