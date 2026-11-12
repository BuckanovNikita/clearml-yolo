"""Historical model populations follow their verified original training task."""

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Never

import pytest

from clearml_yolo.adapters.clearml import models, session
from clearml_yolo.core.identity import ModelIdentity


@pytest.fixture
def invocation() -> Iterator[session._InvocationState]:
    task = SimpleNamespace(id="comparison")
    state = session._InvocationState(task=task, stages=["compare"], current_stage="compare")
    token = session._ACTIVE_INVOCATION.set(state)
    try:
        yield state
    finally:
        session._ACTIVE_INVOCATION.reset(token)


def test_original_population_recovered_and_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invocation: session._InvocationState
) -> None:
    truth = tmp_path / "gt.csv"
    truth.write_text("instance_label,split\n0001,train\n0001,train\nNA,val\ncat,test\n,custom\n")
    artifact = SimpleNamespace(get_local_copy=lambda: str(truth))
    source = SimpleNamespace(artifacts={"gt_csv": artifact})
    calls = []

    def resolve(task_id: str) -> tuple[Path, dict[str, str]]:
        calls.append(task_id)
        return tmp_path / "best.pt", {
            "training_task_id": "original",
            "checkpoint_sha256": "digest",
            "model_id": "model",
        }

    monkeypatch.setattr(models, "resolve_task_model", resolve)
    monkeypatch.setattr(models, "_task", lambda task_id: source)
    identity = ModelIdentity(
        model_name="old", training_task_id="original", checkpoint_sha256="digest", model_id="model"
    )
    expected = {"train": {"0001": 2}, "val": {"NA": 1}, "test": {"cat": 1}, "custom": {}}
    counts = session.population_counts(identity)
    assert counts == expected
    assert counts is not None
    counts["train"]["0001"] = 99
    assert session.population_counts(identity) == expected
    assert session.training_counts(identity) == {"0001": 2}
    assert calls == ["original"]


@pytest.mark.parametrize("field", ["training_task_id", "checkpoint_sha256", "model_id"])
def test_mismatched_population_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invocation: session._InvocationState, field: str
) -> None:
    links = {"training_task_id": "original", "checkpoint_sha256": "digest", "model_id": "model"}
    links[field] = "different"
    monkeypatch.setattr(models, "resolve_task_model", lambda task_id: (tmp_path / "best.pt", links))
    identity = ModelIdentity(
        model_name="old", training_task_id="original", checkpoint_sha256="digest", model_id="model"
    )
    assert session.population_counts(identity) is None


def test_absent_evidence_stays_unknown(monkeypatch: pytest.MonkeyPatch, invocation: session._InvocationState) -> None:
    def unavailable(task_id: str) -> Never:
        raise ConnectionError("unavailable")

    monkeypatch.setattr(models, "resolve_task_model", unavailable)
    identity = ModelIdentity(model_name="old", training_task_id="original", checkpoint_sha256="digest")
    assert session.population_counts(identity) is None
    assert session.training_counts(identity) is None


def test_registration_copies_every_split(tmp_path: Path, invocation: session._InvocationState) -> None:
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"weights")
    counts = {"train": {"a": 2}, "test": {"a": 3}}
    session.register_population_counts(invocation.task, weights, counts)
    digest = next(iter(invocation.checkpoint_population_counts))
    identity = ModelIdentity(model_name="new", checkpoint_sha256=digest)
    counts["test"]["a"] = 99
    assert session.population_counts(identity) == {"train": {"a": 2}, "test": {"a": 3}}
    assert session.training_counts(identity) == {"a": 2}


@pytest.mark.parametrize("failure", ["absent", "no_download", "malformed", "missing_file"])
def test_unrecoverable_artifact_remains_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invocation: session._InvocationState, failure: str
) -> None:
    truth = tmp_path / "gt.csv"
    if failure != "missing_file":
        truth.write_text("class,split\na,train\n", encoding="utf-8")
    source = SimpleNamespace(
        artifacts=(
            {}
            if failure == "absent"
            else {"gt_csv": SimpleNamespace(get_local_copy=lambda: None if failure == "no_download" else str(truth))}
        )
    )
    links = {"training_task_id": "original", "checkpoint_sha256": "digest"}
    monkeypatch.setattr(models, "resolve_task_model", lambda task_id: (tmp_path / "best.pt", links))
    monkeypatch.setattr(models, "_task", lambda task_id: source)
    identity = ModelIdentity(model_name="old", training_task_id="original", checkpoint_sha256="digest")
    assert session.population_counts(identity) is None
    assert session.training_counts(identity) is None


def test_recovery_without_active_invocation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    truth = tmp_path / "gt.csv"
    truth.write_text("instance_label,split\na,train\nb,val\n", encoding="utf-8")
    source = SimpleNamespace(artifacts={"gt_csv": SimpleNamespace(get_local_copy=lambda: str(truth))})
    links = {"training_task_id": "original", "checkpoint_sha256": "digest"}
    monkeypatch.setattr(models, "resolve_task_model", lambda task_id: (tmp_path / "best.pt", links))
    monkeypatch.setattr(models, "_task", lambda task_id: source)
    token = session._ACTIVE_INVOCATION.set(None)
    try:
        identity = ModelIdentity(model_name="old", training_task_id="original", checkpoint_sha256="digest")
        assert session.population_counts(identity) == {"train": {"a": 1}, "val": {"b": 1}}
    finally:
        session._ACTIVE_INVOCATION.reset(token)
