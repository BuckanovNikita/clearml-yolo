"""Live-test session: one test environment of this project, selected when first needed.

``tests/conftest.py`` marks every test under ``tests/integration`` ``integration`` and puts it
in the ``live`` xdist group, so one worker runs them serially. Tests that need the ClearML
server request ``live_run``; the FiftyOne suites request ``fiftyone_database``; the GPU suites
reach ClearML only through ``stand_project``. The first of them selects the session's
environment through ``lifecycle.Session``: it adopts the worktree's live recorded environment
when the shell exports ``INTEGRATION_RUN_TAG`` equal to it, and otherwise creates a
``cy-it-<id>`` namespace of its own with only the components the session needs. At the end of
the session an environment it created is deleted and proven absent (unless
``INTEGRATION_KEEP_DATA=1``); an adopted one is left for ``lifecycle stop``.

The module is imported as ``integration.lifecycle``: ``tests`` is a mypy and pytest import
root.
"""

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from integration import lifecycle

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def test_environment() -> Iterator[lifecycle.Session]:
    """The session's environment holder; deletes what it created when the session ends.

    The process environment is restored afterwards. Incomplete deletion fails the session
    and leaves the record for ``lifecycle stop``.
    """
    saved = dict(os.environ)
    session = lifecycle.Session(REPO_ROOT)
    status = lifecycle.EXIT_AVAILABLE
    try:
        yield session
    finally:
        try:
            status = session.finish()
        except lifecycle.LifecycleError as error:
            lifecycle.report(error)
            status = lifecycle.EXIT_ERROR
        finally:
            os.environ.clear()
            os.environ.update(saved)
    if status != lifecycle.EXIT_AVAILABLE and session.environment is not None:
        pytest.fail(
            f"environment '{session.environment.identifier}' is not proven deleted; retry with "
            f"{lifecycle.MODULE} stop --env {session.environment.identifier}; see the output above.",
            pytrace=False,
        )


def _ensure(session: lifecycle.Session, selection: lifecycle.Selection) -> lifecycle.Environment:
    """Select or extend the environment; unavailability defers instead of failing a test.

    Under Task verification (``CY_TASK_VERIFICATION=1``, set without xdist workers by ``task
    integration`` and the release-acceptance commands) the session exits with status 3
    (deferred); an interactive run skips the test. Every other refusal fails setup.
    """
    try:
        return session.ensure(selection)
    except lifecycle.StandUnavailableError as error:
        message = f"UNAVAILABLE: live setup blocked: {error}; live verification is deferred"
        if os.environ.get(lifecycle.TASK_VERIFICATION_VARIABLE) == "1":
            pytest.exit(message, returncode=lifecycle.EXIT_UNAVAILABLE)
        pytest.skip(message)
    except lifecycle.LifecycleError as error:
        pytest.fail("\n".join(error.lines), pytrace=False)


@pytest.fixture(scope="session")
def live_run(test_environment: lifecycle.Session) -> lifecycle.Environment:
    """The environment with its ClearML server; its variables are exported for the session."""
    return _ensure(test_environment, "clearml")


@pytest.fixture(scope="session")
def fiftyone_database(test_environment: lifecycle.Session) -> str:
    """The environment's FiftyOne database URI, in effect for this process and its children.

    Starts only the database component when the session has no environment yet. It fails
    rather than let FiftyOne fall back to a database of its own: the connection must go
    through the environment's port-forward.
    """
    if os.environ.get("CY_TEST_FIFTYONE") != "1":
        pytest.skip("Real FiftyOne databases require CY_TEST_FIFTYONE=1")
    environment = _ensure(test_environment, "fiftyone")
    uri = environment.exported["FIFTYONE_DATABASE_URI"]
    import fiftyone as fo
    from fiftyone.core.odm import database

    if fo.config.database_uri != uri:
        if database._client is not None:
            pytest.fail("FiftyOne connected to another database before the environment's was set", pytrace=False)
        fo.config.database_uri = uri
    address = tuple(database.get_db_client().address)
    if address != ("127.0.0.1", environment.forwards["mongo"].port):
        pytest.fail(f"FiftyOne is connected to {address}, not to the environment's database", pytrace=False)
    return uri


@pytest.fixture
def stand_project(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Callable[[str], str]:
    """Join the environment on demand and return the tagged form of an explicit project name.

    The GPU suites validate their explicit options first and only then call the returned
    function, so a rejected selection never creates an environment. Environment isolation
    hides ``~/clearml.conf``; the call exports the environment's ClearML endpoint and
    credentials for this test and prefixes the project with the environment identifier.
    """

    def join(project: str) -> str:
        environment: lifecycle.Environment = request.getfixturevalue("live_run")
        for key, value in environment.exported.items():
            monkeypatch.setenv(key, value)
        if project.split()[:1] == [environment.tag]:
            return project
        return lifecycle.tagged_project_name(environment.tag, project)

    return join
