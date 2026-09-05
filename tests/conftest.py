"""Fixtures every test file shares."""

from __future__ import annotations

import pytest

from clearml_yolo.clearml_session import RUN_TAG_ENV_VARS


@pytest.fixture(autouse=True)
def no_run_tag_from_the_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip the run tag an agent's shell exports, so a default name means the default.

    ``ClearMLConfig`` derives its project from the tag, and the suite is run from shells
    that carry one; a test about the tag sets it itself.
    """
    for name in RUN_TAG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
