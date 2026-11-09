"""ClearML identity links are exact when a session exists and optional otherwise."""

from typing import Any

import pytest

from clearml_yolo.adapters.clearml.links import identity_links
from clearml_yolo.core.identity import IdentityLinks, ModelIdentity

TASK_ID = "203ccb8ae84143aca02bdb0ecec59c7d"
MODEL_ID = "f" * 32


@pytest.fixture
def clearml_host(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from clearml.backend_api.session import Session

    calls: list[str] = []

    def host(*args: Any, **kwargs: Any) -> str:
        calls.append("host")
        return "https://app.example/"

    monkeypatch.setattr(Session, "get_app_server_host", classmethod(lambda cls, config=None: host()))
    # Older API versions use the legacy "experiments" segment; pin the current one offline.
    monkeypatch.setattr(Session, "check_min_api_version", classmethod(lambda cls, *args, **kwargs: True))
    return calls


def test_links_use_exact_identifiers_and_the_session_web_host(clearml_host: list[str]) -> None:
    identity = ModelIdentity(model_name="train-brave-willow", training_task_id=TASK_ID, model_id=MODEL_ID)
    links = identity_links(object(), identity)
    assert links == IdentityLinks(
        model_url=f"https://app.example/projects/*/models/{MODEL_ID}",
        task_url=f"https://app.example/projects/*/tasks/{TASK_ID}/output/log",
    )


def test_no_invocation_task_means_no_sdk_call(clearml_host: list[str]) -> None:
    identity = ModelIdentity(model_name="m", training_task_id=TASK_ID, model_id=MODEL_ID)
    assert identity_links(None, identity) == IdentityLinks()
    assert clearml_host == []


def test_identity_without_source_identifiers_needs_no_session(clearml_host: list[str]) -> None:
    assert identity_links(object(), ModelIdentity(model_name="custom")) == IdentityLinks()
    assert clearml_host == []


@pytest.mark.parametrize("failure", [RuntimeError("no configuration"), "ftp://files.example"])
def test_unavailable_or_unsafe_host_renders_plain_text(
    monkeypatch: pytest.MonkeyPatch, failure: Exception | str
) -> None:
    from clearml.backend_api.session import Session
    from loguru import logger

    def host(cls: Any, config: Any = None) -> str:
        if isinstance(failure, Exception):
            raise failure
        return failure

    monkeypatch.setattr(Session, "get_app_server_host", classmethod(host))
    monkeypatch.setattr(Session, "check_min_api_version", classmethod(lambda cls, *args, **kwargs: True))
    messages: list[str] = []
    sink = logger.add(messages.append, level="DEBUG", format="{level}:{message}")
    try:
        links = identity_links(object(), ModelIdentity(model_name="m", training_task_id=TASK_ID))
    finally:
        logger.remove(sink)
    assert links == IdentityLinks()
    assert any(message.startswith("DEBUG:ClearML identity links unavailable") for message in messages)
    assert all(TASK_ID not in message for message in messages)


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///etc/passwd", "app.example/path"])
def test_identity_links_reject_non_web_urls(url: str) -> None:
    with pytest.raises(ValueError, match="http or https"):
        IdentityLinks(task_url=url)


def test_report_never_links_its_own_task(clearml_host: list[str]) -> None:
    class ReportingTask:
        id = TASK_ID

    identity = ModelIdentity(model_name="pipeline-model", training_task_id=TASK_ID, model_id=MODEL_ID)
    assert identity_links(ReportingTask(), identity) == IdentityLinks(
        model_url=f"https://app.example/projects/*/models/{MODEL_ID}"
    )
