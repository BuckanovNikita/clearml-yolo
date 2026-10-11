"""Isolate process-wide runtime configuration between tests."""

import os
import sys
import tempfile
from collections.abc import Iterator
from copy import deepcopy

import pytest

from clearml_yolo.adapters.runtime import bootstrap


@pytest.fixture(autouse=True)
def restore_runtime_configuration() -> Iterator[None]:
    """Programmatic initialization persists intentionally, but not across test cases."""
    environment = dict(os.environ)
    bytecode = sys.pycache_prefix
    temporary = tempfile.tempdir
    state = deepcopy(bootstrap._STATE)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(environment)
        sys.pycache_prefix = bytecode
        tempfile.tempdir = temporary
        bootstrap._STATE = state
