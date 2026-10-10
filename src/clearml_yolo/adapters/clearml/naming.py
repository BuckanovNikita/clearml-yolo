"""Resolve project-local experiment/model display names without changing file routing."""

import re
import secrets
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, cast

from clearml_yolo.adapters.clearml.session import (
    ArtifactUploadError,
    invocation_resource,
    record_run_configuration,
    task_identity,
)
from clearml_yolo.adapters.observability.tracing import trace_operation

MAX_NAME_ATTEMPTS = 20
_ADJECTIVES = (
    "amber",
    "brave",
    "bright",
    "calm",
    "clear",
    "crisp",
    "eager",
    "gentle",
    "golden",
    "happy",
    "kind",
    "lively",
    "merry",
    "nimble",
    "quiet",
    "silver",
    "steady",
    "sunny",
    "swift",
    "vivid",
    "warm",
    "wise",
    "young",
    "zesty",
)
_NOUNS = (
    "badger",
    "birch",
    "brook",
    "cedar",
    "crane",
    "dolphin",
    "eagle",
    "falcon",
    "finch",
    "fox",
    "heron",
    "lake",
    "lark",
    "lynx",
    "maple",
    "meadow",
    "otter",
    "owl",
    "panda",
    "pine",
    "raven",
    "robin",
    "sparrow",
    "willow",
)


class NameResolutionError(ArtifactUploadError):
    """A project-local unique display name could not be verified."""


@dataclass
class NamingState:
    """Requested names remain intact while a shared suffix controls display names."""

    requested_task_name: str
    effective_task_name: str
    requested_model_name: str | None = None
    effective_model_name: str | None = None
    suffix: str | None = None


def _readable_suffix() -> str:
    return f"{secrets.choice(_ADJECTIVES)}-{secrets.choice(_NOUNS)}"


def _display_name(requested: str, suffix: str | None) -> str:
    return requested if suffix is None else f"{requested}-{suffix}"


@trace_operation("clearml.naming.task_query")
def _task_collision(task: Any, name: str) -> bool:
    from clearml import Task

    project_name, _, _ = task_identity(task)
    # query_tasks paginates all results and has no implicit archived-task exclusion.
    # SDK annotations include IDs-only responses; additional fields select mappings.
    rows = cast(
        list[dict[str, str]],
        Task.query_tasks(
            project_name=project_name,
            task_name=rf"\A(?:{re.escape(name)})\Z(?![\s\S])",
            additional_return_fields=["name", "project"],
            task_filter={"system_tags": []},
        ),
    )
    return any(
        row["id"] != str(task.id) and row["name"] == name and row["project"] == str(task.project)
        for row in rows
    )


@trace_operation("clearml.naming.model_query")
def _model_collision(task: Any, name: str, model_id: str | None) -> bool:
    from clearml import Model

    project_name, _, _ = task_identity(task)
    models = Model.query_models(
        project_name=project_name,
        model_name=name,
        include_archived=True,
        only_published=False,
    )
    # Explicit filtering also guards SDK regex end anchors and project selection.
    return any(
        str(model.id) != model_id and model.name == name and str(model.project) == str(task.project)
        for model in models
    )


def _occupied(task: Any, state: NamingState, suffix: str | None, model_id: str | None) -> bool:
    task_name = _display_name(state.requested_task_name, suffix)
    task_occupied = _task_collision(task, task_name)
    model_occupied = (
        _model_collision(task, _display_name(state.requested_model_name, suffix), model_id)
        if state.requested_model_name is not None
        else False
    )
    return task_occupied or model_occupied


@trace_operation("clearml.naming.resolve")
def _resolve(
    task: Any,
    state: NamingState,
    model_id: str | None = None,
    write_model_name: Callable[[str], None] | None = None,
) -> None:
    suffix = state.suffix
    for attempt in range(MAX_NAME_ATTEMPTS + 1):
        if attempt:
            suffix = _readable_suffix()
        if _occupied(task, state, suffix, model_id):
            continue
        task_name = _display_name(state.requested_task_name, suffix)
        if task.name != task_name:
            with trace_operation("clearml.naming.task_write"):
                task.set_name(task_name)
        if task.name != task_name:
            raise NameResolutionError("ClearML rejected the effective experiment name")
        model_name = (
            _display_name(state.requested_model_name, suffix)
            if state.requested_model_name is not None
            else None
        )
        if write_model_name is not None and model_name is not None:
            with trace_operation("clearml.naming.model_write"):
                write_model_name(model_name)
        # Check again after the write: concurrent invocations can choose the same candidate.
        if _occupied(task, state, suffix, model_id):
            continue
        state.suffix = suffix
        state.effective_task_name = task_name
        state.effective_model_name = model_name
        return
    raise NameResolutionError(
        f"Cannot resolve project-local experiment/model names after {MAX_NAME_ATTEMPTS} attempts"
    )


def initialize_naming(task: Any) -> NamingState:
    """Capture this invocation's requested name and resolve a fresh experiment name."""
    if task is None:
        raise NameResolutionError("Display naming requires an invocation-owned task")
    # Read before any rename so session identity can freeze output routing lazily.
    _, requested_name, _ = task_identity(task)

    def create() -> NamingState:
        if not requested_name:
            raise NameResolutionError("Experiment display name must be nonempty")
        state = NamingState(requested_name, requested_name)
        _resolve(task, state)
        record_run_configuration(task, {"display_names": asdict(state)})
        return state

    return invocation_resource(task, "clearml_naming", create)


def resolve_model_name(
    task: Any,
    requested_name: str,
    *,
    model_id: str,
    write_model_name: Callable[[str], None] | None = None,
) -> str:
    """Resolve shared display names, rechecking collisions after the actual model write.

    Native publication supplies its writer so constructor/name-update races can retry
    against the same model ID before final metadata expectations are established.
    """
    if not requested_name or not model_id:
        raise NameResolutionError("Model display name and owned model ID must be nonempty")
    state = initialize_naming(task)
    if state.requested_model_name not in {None, requested_name}:
        raise NameResolutionError("One invocation cannot change its requested best-model name")
    state.requested_model_name = requested_name
    _resolve(task, state, model_id, write_model_name)
    record_run_configuration(task, {"display_names": asdict(state)})
    assert state.effective_model_name is not None  # noqa: S101 - established by _resolve
    return state.effective_model_name
