"""Project-local display name collision resolution without changing run routing."""

import re
import sys
import types
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo import clearml_naming


@pytest.fixture
def naming_sdk(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    records: dict[str, list[Any]] = {"tasks": [], "models": []}
    calls: list[dict[str, Any]] = []
    resources: dict[tuple[str, str], Any] = {}
    configuration: dict[str, Any] = {}

    def resource(task: Any, key: str, factory: Callable[[], Any]) -> Any:
        identity = (task.id, key)
        if identity not in resources:
            resources[identity] = factory()
        return resources[identity]

    def query_tasks(**kwargs: Any) -> list[dict[str, str]]:
        calls.append(kwargs)
        assert kwargs["project_name"] == "project.+"
        assert kwargs["task_filter"] == {"system_tags": []}
        return [
            {"id": row.id, "name": row.name, "project": row.project}
            for row in records["tasks"]
            if re.search(kwargs["task_name"], row.name)
        ]

    def query_models(**kwargs: Any) -> list[Any]:
        calls.append(kwargs)
        assert kwargs["project_name"] == "project.+"
        assert kwargs["include_archived"] is True
        assert kwargs["only_published"] is False
        return list(records["models"])

    module = types.ModuleType("clearml")
    module.Task = SimpleNamespace(query_tasks=query_tasks)  # type: ignore[attr-defined]
    module.Model = SimpleNamespace(query_models=query_models)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "clearml", module)
    monkeypatch.setattr(clearml_naming, "invocation_resource", resource)
    monkeypatch.setattr(
        clearml_naming,
        "record_run_configuration",
        lambda _task, values: configuration.update(values),
    )
    monkeypatch.setattr(
        clearml_naming, "task_identity", lambda task: ("project.+", task.name, task.id)
    )
    monkeypatch.setattr(clearml_naming, "_readable_suffix", lambda: "gentle-otter")
    task = SimpleNamespace(id="own-task", project="project-id", name="run.+")

    def rename(name: str) -> None:
        task.name = name

    task.set_name = rename
    return SimpleNamespace(
        task=task,
        records=records,
        calls=calls,
        resources=resources,
        configuration=configuration,
    )


def test_unused_names_and_current_records_are_preserved(naming_sdk: SimpleNamespace) -> None:
    task = naming_sdk.task
    naming_sdk.records["tasks"] = [
        task,
        SimpleNamespace(id="other", name="run.+\n", project=task.project),
    ]
    naming_sdk.records["models"] = [
        SimpleNamespace(id="own-model", name="detector", project=task.project),
        SimpleNamespace(id="elsewhere", name="detector", project="other-project"),
    ]
    state = clearml_naming.initialize_naming(task)
    assert state.requested_task_name == state.effective_task_name == "run.+"
    assert clearml_naming.resolve_model_name(task, "detector", model_id="own-model") == "detector"
    assert state.suffix is None


def test_archived_task_collision_and_model_share_readable_suffix(
    naming_sdk: SimpleNamespace,
) -> None:
    task = naming_sdk.task
    naming_sdk.records["tasks"] = [
        SimpleNamespace(
            id="archived", name=task.name, project=task.project, system_tags=["archived"]
        )
    ]
    state = clearml_naming.initialize_naming(task)
    assert task.name == "run.+-gentle-otter"
    assert (
        clearml_naming.resolve_model_name(task, "detector", model_id="own-model")
        == "detector-gentle-otter"
    )
    assert state.requested_task_name == "run.+"


def test_archived_model_collision_renames_both_displays(naming_sdk: SimpleNamespace) -> None:
    task = naming_sdk.task
    state = clearml_naming.initialize_naming(task)
    naming_sdk.records["models"] = [
        SimpleNamespace(
            id="archived", name="detector", project=task.project, system_tags=["archived"]
        )
    ]
    assert (
        clearml_naming.resolve_model_name(task, "detector", model_id="own-model")
        == "detector-gentle-otter"
    )
    assert task.name == "run.+-gentle-otter"
    assert state.effective_model_name == "detector-gentle-otter"


def test_collision_is_rechecked_after_rename_and_retried(
    naming_sdk: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = naming_sdk.task
    original = task.set_name
    suffixes = iter(["gentle-otter", "brave-badger"])
    monkeypatch.setattr(clearml_naming, "_readable_suffix", lambda: next(suffixes))
    naming_sdk.records["tasks"] = [
        SimpleNamespace(id="occupied", name=task.name, project=task.project)
    ]

    def race(name: str) -> None:
        original(name)
        if name.endswith("gentle-otter"):
            naming_sdk.records["tasks"].append(
                SimpleNamespace(id="racer", name=name, project=task.project)
            )

    task.set_name = race
    state = clearml_naming.initialize_naming(task)
    assert state.effective_task_name == "run.+-brave-badger"


def test_twenty_suffix_attempts_exhaust_cleanly(
    naming_sdk: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = naming_sdk.task
    attempts: list[str] = []

    def suffix() -> str:
        attempts.append("gentle-otter")
        return "gentle-otter"

    monkeypatch.setattr(clearml_naming, "_readable_suffix", suffix)
    naming_sdk.records["tasks"] = [
        SimpleNamespace(id=str(index), name=name, project=task.project)
        for index, name in enumerate([task.name, task.name + "-gentle-otter"])
    ]
    with pytest.raises(clearml_naming.NameResolutionError, match="20"):
        clearml_naming.initialize_naming(task)
    assert len(attempts) == 20


def test_clones_resolve_a_fresh_state(naming_sdk: SimpleNamespace) -> None:
    task = naming_sdk.task
    clearml_naming.initialize_naming(task)
    naming_sdk.records["tasks"] = [
        SimpleNamespace(id="source", name=task.name, project=task.project)
    ]
    task.id = "clone"
    state = clearml_naming.initialize_naming(task)
    assert state.effective_task_name == "run.+-gentle-otter"


def test_task_collision_in_another_project_is_ignored(naming_sdk: SimpleNamespace) -> None:
    task = naming_sdk.task
    naming_sdk.records["tasks"] = [
        SimpleNamespace(id="foreign", name=task.name, project="foreign-project")
    ]
    assert clearml_naming.initialize_naming(task).effective_task_name == "run.+"


def test_model_suffix_collision_retries_and_preserves_both_requested_names(
    naming_sdk: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = naming_sdk.task
    state = clearml_naming.initialize_naming(task)
    suffixes = iter(["gentle-otter", "brave-badger"])
    monkeypatch.setattr(clearml_naming, "_readable_suffix", lambda: next(suffixes))
    naming_sdk.records["models"] = [
        SimpleNamespace(id=str(index), name=name, project=task.project)
        for index, name in enumerate(["detector", "detector-gentle-otter"])
    ]
    assert (
        clearml_naming.resolve_model_name(task, "detector", model_id="own-model")
        == "detector-brave-badger"
    )
    assert state.requested_task_name == "run.+"
    assert state.requested_model_name == "detector"
    assert task.name == "run.+-brave-badger"


def test_rejected_rename_is_actionable(naming_sdk: SimpleNamespace) -> None:
    task = naming_sdk.task
    naming_sdk.records["tasks"] = [
        SimpleNamespace(id="occupied", name=task.name, project=task.project)
    ]
    task.set_name = lambda _name: None
    with pytest.raises(clearml_naming.NameResolutionError, match="rejected"):
        clearml_naming.initialize_naming(task)


def test_initialized_name_is_reused_without_additional_search(naming_sdk: SimpleNamespace) -> None:
    task = naming_sdk.task
    first = clearml_naming.initialize_naming(task)
    calls = len(naming_sdk.calls)
    assert clearml_naming.initialize_naming(task) is first
    assert len(naming_sdk.calls) == calls


def test_requested_and_effective_names_persist_in_result_only_section(
    naming_sdk: SimpleNamespace,
) -> None:
    task = naming_sdk.task
    clearml_naming.initialize_naming(task)
    assert naming_sdk.configuration == {
        "display_names": {
            "requested_task_name": "run.+",
            "effective_task_name": "run.+",
            "requested_model_name": None,
            "effective_model_name": None,
            "suffix": None,
        }
    }
    naming_sdk.records["models"] = [
        SimpleNamespace(id="previous", name="detector", project=task.project)
    ]
    clearml_naming.resolve_model_name(task, "detector", model_id="own-model")
    assert naming_sdk.configuration == {
        "display_names": {
            "requested_task_name": "run.+",
            "effective_task_name": "run.+-gentle-otter",
            "requested_model_name": "detector",
            "effective_model_name": "detector-gentle-otter",
            "suffix": "gentle-otter",
        }
    }


def test_repeated_post_model_write_races_exhaust_twenty_suffix_attempts(
    naming_sdk: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = naming_sdk.task
    writes: list[str] = []
    attempts: list[str] = []

    def suffix() -> str:
        value = f"gentle-otter-{len(attempts)}"
        attempts.append(value)
        return value

    def write(name: str) -> None:
        writes.append(name)
        naming_sdk.records["models"].append(
            SimpleNamespace(id=f"racer-{len(writes)}", name=name, project=task.project)
        )

    monkeypatch.setattr(clearml_naming, "_readable_suffix", suffix)
    with pytest.raises(clearml_naming.NameResolutionError, match="20"):
        clearml_naming.resolve_model_name(
            task, "detector", model_id="own-model", write_model_name=write
        )
    assert len(attempts) == 20
    assert len(writes) == 21
