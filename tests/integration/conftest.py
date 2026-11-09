"""Stand-test session: one tagged live run on the shared ClearML stand.

``tests/conftest.py`` marks every test under ``tests/integration`` ``integration`` and puts it
in the ``live`` xdist group, so one worker runs them serially. Tests that use the ClearML stand
request the session fixture ``live_run``; it is not autouse, so the GPU and FiftyOne suites
in this directory reach it only through ``stand_project``. ``live_run`` performs the bounded preflight, claims
one run tag through ``lifecycle.py`` before the first stand test, and after the last one removes
exactly that tag's objects, failing the session when cleanup is incomplete.

The module is imported as ``integration.lifecycle``: ``tests`` is a mypy and pytest import
root, and one module identity keeps its exception classes shared with the unit tests.
"""

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from integration import lifecycle

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def live_run() -> Iterator[lifecycle.Run]:
    """Prepare this session's run, export its stand variables, then stop it.

    Stand unavailability blocks setup rather than failing a test: under Task verification
    (``CY_TASK_VERIFICATION=1``, run without xdist workers by ``task integration``) the session
    exits with status 3 (deferred); an interactive run skips the stand tests. Every other
    refusal fails setup. The environment is restored when the session ends.
    """
    saved = dict(os.environ)
    try:
        run = lifecycle.prepare(REPO_ROOT)
    except lifecycle.StandUnavailableError as error:
        os.environ.clear()
        os.environ.update(saved)
        message = f"UNAVAILABLE: live setup blocked: {error}; live verification is deferred"
        if os.environ.get(lifecycle.TASK_VERIFICATION_VARIABLE) == "1":
            pytest.exit(message, returncode=lifecycle.EXIT_UNAVAILABLE)
        pytest.skip(message)
    except lifecycle.LifecycleError as error:
        os.environ.clear()
        os.environ.update(saved)
        pytest.fail("\n".join(error.lines), pytrace=False)
    try:
        yield run
    finally:
        try:
            if lifecycle.finish(run):
                pytest.fail(
                    f"run '{run.tag}' is not fully torn down; retry exact-tag cleanup with "
                    f"INFRA_RUN_TAG={run.tag} {lifecycle.MODULE} stop; see the output above.",
                    pytrace=False,
                )
        finally:
            os.environ.clear()
            os.environ.update(saved)


@pytest.fixture
def stand_project(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Callable[[str], str]:
    """Join the live run on demand and return the tagged form of an explicit project name.

    The GPU suites validate their explicit options first and only then call the returned
    function, so a rejected selection never claims a run tag. Environment isolation hides
    ``~/clearml.conf``; the call exports the run's stand credentials and CA trust for this
    test, and prefixes the project with the run tag so exact-tag cleanup removes what the
    suite publishes.
    """

    def join(project: str) -> str:
        run: lifecycle.Run = request.getfixturevalue("live_run")
        for key, value in run.exported.items():
            monkeypatch.setenv(key, value)
        if project.split()[:1] == [run.tag]:
            return project
        return lifecycle.tagged_project_name(run.tag, project)

    return join
