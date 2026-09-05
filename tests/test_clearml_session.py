"""The ClearML identity of a run: where a tagged run's experiments go."""

from __future__ import annotations

import pytest

from clearml_yolo.clearml_session import (
    DEFAULT_PROJECT_NAME,
    RUN_TAG_ENV_VARS,
    ClearMLConfig,
    run_tag,
    tagged_project_name,
)

TAG = "clearml-yolo-claude-20260905-deadline-a1b2"


def test_a_run_without_a_tag_keeps_the_default_project() -> None:
    config = ClearMLConfig()

    assert run_tag() is None
    assert config.project_name == DEFAULT_PROJECT_NAME
    assert config.tags == []


@pytest.mark.parametrize("variable", RUN_TAG_ENV_VARS)
def test_a_tagged_run_lands_in_the_tags_project_and_carries_the_tag(
    monkeypatch: pytest.MonkeyPatch, variable: str
) -> None:
    """An agent's experiments belong in a project named after its tag, where the janitor
    finds them, and never among the user's own runs under the default name."""
    monkeypatch.setenv(variable, TAG)

    config = ClearMLConfig()

    assert config.project_name == tagged_project_name(TAG) == f"{TAG} {DEFAULT_PROJECT_NAME}"
    assert config.tags == [TAG]


def test_a_project_named_outright_is_kept_and_still_tagged(monkeypatch: pytest.MonkeyPatch) -> None:
    """Naming the project is the override; the tag goes on regardless so the run is
    findable by tag wherever it landed."""
    monkeypatch.setenv("CY_RUN_TAG", TAG)

    config = ClearMLConfig(project_name="detection", tags=["prod"])

    assert config.project_name == "detection"
    assert config.tags == ["prod", TAG]


def test_the_projects_own_spelling_of_the_tag_wins_over_the_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INFRA_RUN_TAG", "clearml-yolo-ci-20260905-other-ffff")
    monkeypatch.setenv("CY_RUN_TAG", TAG)

    assert run_tag() == TAG
    assert ClearMLConfig().project_name == tagged_project_name(TAG)


def test_a_blank_tag_is_no_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CY_RUN_TAG", "  ")
    monkeypatch.setenv("INFRA_RUN_TAG", "")

    assert run_tag() is None
    assert ClearMLConfig().project_name == DEFAULT_PROJECT_NAME


def test_a_tag_already_on_the_run_is_not_added_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CY_RUN_TAG", TAG)

    assert ClearMLConfig(tags=[TAG]).tags == [TAG]
