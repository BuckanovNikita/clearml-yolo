"""Agent-recorded bare entrypoints restore detached settings before execution setup."""

from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
from omegaconf import OmegaConf

from clearml_yolo.adapters.clearml import session
from clearml_yolo.entrypoints.hydra import common


@pytest.mark.parametrize("command", ["train", "pipeline"])
@pytest.mark.parametrize("has_canonical", [True, False])
@pytest.mark.parametrize(
    ("backend", "preset", "runtime"),
    [("ultralytics", "default", "yolo"), ("rfdetr", "nano", "detector")],
)
def test_bare_agent_restores_before_required_inputs_and_runtime(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    backend: str,
    preset: str,
    runtime: str,
    has_canonical: bool,
) -> None:
    events: list[str] = []
    canonical: dict[str, Any] = {
        "ground_truth": "remote.csv",
        "model": {"backend": backend, "preset": preset},
        "clearml": {},
    }
    snapshot = session.RemoteReplay("agent-task", canonical if has_canonical else None, {})
    monkeypatch.setattr(common, "fetch_remote_replay", lambda: snapshot)
    monkeypatch.setattr(common, "initialize_filesystem", lambda: None)
    monkeypatch.setattr(common, "release_training_memory", lambda: None)
    monkeypatch.setattr(common, "initialize_naming", lambda task: None)
    monkeypatch.setattr(common, "publish_run_configuration", lambda *args: None)
    monkeypatch.setattr(common, "_builtin_defaults", lambda *args: {})

    @contextmanager
    def owner(*args: Any, **kwargs: Any) -> Iterator[Any]:
        assert kwargs["remote_replay"] is snapshot
        events.append("owner")
        task = SimpleNamespace(id="agent-task", running_locally=lambda: False)
        state = session._InvocationState(
            task=task, stages=[command], current_stage=command, remote_replay=snapshot
        )
        token = session._ACTIVE_INVOCATION.set(state)
        try:
            yield task
        finally:
            session._ACTIVE_INVOCATION.reset(token)

    @contextmanager
    def selected_runtime(value: str) -> Iterator[None]:
        events.append(value)
        yield

    def workflow(ground_truth: str, model: dict[str, Any], clearml: Any) -> None:
        assert ground_truth == "remote.csv"
        assert model["backend"] == backend
        events.append("execute")

    monkeypatch.setattr(common, "invocation", owner)
    monkeypatch.setattr(common, "native_runtime", lambda: selected_runtime("yolo"))
    monkeypatch.setattr(common, "detector_runtime", lambda: selected_runtime("detector"))
    config = OmegaConf.create(
        {"ground_truth": "???", "model": {}, "clearml": {}} if has_canonical else canonical
    )
    common.execute_owned(command, config, workflow)
    assert events == [runtime, "owner", "execute"]
    assert snapshot.canonical == (canonical if has_canonical else None)


def test_remote_snapshot_reads_once_and_detaches(monkeypatch: pytest.MonkeyPatch) -> None:
    import clearml
    import clearml.config

    calls: list[str] = []
    canonical: dict[str, Any] = {"ground_truth": "truth.csv", "model": {"weights": None}}
    parameters = {"General/epochs": 2}

    def read(name: str) -> dict[str, Any]:
        calls.append(name)
        return canonical

    task = SimpleNamespace(
        id="agent-task",
        running_locally=lambda: False,
        get_configuration_object_as_dict=read,
        get_parameters=lambda **kwargs: parameters,
    )
    monkeypatch.setattr(clearml.config, "running_remotely", lambda: True)
    monkeypatch.setattr(clearml.config, "get_remote_task_id", lambda: "agent-task")
    monkeypatch.setattr(clearml.Task, "get_task", lambda **kwargs: task)
    snapshot = session.fetch_remote_replay()
    assert snapshot is not None
    canonical["model"]["weights"] = "changed.pt"
    parameters["General/epochs"] = 99
    assert snapshot.canonical == {"ground_truth": "truth.csv", "model": {"weights": None}}
    assert snapshot.parameters == {"General/epochs": 2}
    assert calls == ["run"]


@pytest.mark.parametrize("canonical", [{}, [], "malformed"])
def test_invalid_canonical_snapshot_never_uses_launch_defaults(
    monkeypatch: pytest.MonkeyPatch, canonical: Any
) -> None:
    import clearml
    import clearml.config

    task = SimpleNamespace(
        id="agent-task",
        running_locally=lambda: False,
        get_configuration_object_as_dict=lambda name: deepcopy(canonical),
        get_parameters=lambda **kwargs: {},
    )
    monkeypatch.setattr(clearml.config, "running_remotely", lambda: True)
    monkeypatch.setattr(clearml.config, "get_remote_task_id", lambda: "agent-task")
    monkeypatch.setattr(clearml.Task, "get_task", lambda **kwargs: task)
    with pytest.raises((ValueError, TypeError), match="configuration"):
        session.fetch_remote_replay()


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_absent_and_empty_canonical_remain_distinct(
    monkeypatch: pytest.MonkeyPatch, raw: str | None
) -> None:
    import clearml
    import clearml.config

    task = SimpleNamespace(
        id="agent-task",
        running_locally=lambda: False,
        get_configuration_object_as_dict=lambda name: None,
        get_configuration_object=lambda name: raw,
        get_parameters=lambda **kwargs: {},
    )
    monkeypatch.setattr(clearml.config, "running_remotely", lambda: True)
    monkeypatch.setattr(clearml.config, "get_remote_task_id", lambda: "agent-task")
    monkeypatch.setattr(clearml.Task, "get_task", lambda **kwargs: task)
    if raw is None:
        snapshot = session.fetch_remote_replay()
        assert snapshot is not None
        assert snapshot.canonical is None
    else:
        with pytest.raises(ValueError, match="must not be empty"):
            session.fetch_remote_replay()


def test_replay_and_general_use_same_snapshot_without_refetch() -> None:
    canonical: dict[str, Any] = {
        "ground_truth": "truth.csv",
        "ultralytics": {"device": 0, "epochs": 1},
        "model": {"backend": "ultralytics", "preset": "default", "weights": None},
    }
    snapshot = session.RemoteReplay(
        "agent-task", canonical, {"General/epochs": 3, "General/device": 8}
    )
    # No SDK read methods: any second read would fail this regression.
    task = SimpleNamespace(id="agent-task", running_locally=lambda: False)
    state = session._InvocationState(
        task=task, stages=["train"], current_stage="train", remote_replay=snapshot
    )
    token = session._ACTIVE_INVOCATION.set(state)
    try:
        replayed = session.replay_configuration(task, {"ground_truth": "???"}, publish=False)
        native = session.replay_training_parameters(task, replayed["ultralytics"])
    finally:
        session._ACTIVE_INVOCATION.reset(token)
    assert native == {"device": 0, "epochs": 3}
    assert replayed["model"]["weights"] is None
    replayed["ultralytics"]["device"] = 7
    assert snapshot.canonical == canonical
    assert canonical["ultralytics"]["device"] == 0
