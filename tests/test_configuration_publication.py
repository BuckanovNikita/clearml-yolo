"""Executable snapshots and concise differences reflect only the selected inputs."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
from hydra_zen import store
from omegaconf import OmegaConf

from clearml_yolo.adapters.clearml import session
from clearml_yolo.core.models import model_preset
from clearml_yolo.entrypoints.hydra import common


@contextmanager
def _owner() -> Iterator[tuple[Any, dict[str, Any]]]:
    documents: dict[str, Any] = {}
    task = SimpleNamespace(
        name="configuration-test",
        set_configuration_object=lambda **values: documents.update(
            {values["name"]: json.loads(values["config_text"])}
        ),
    )
    state = session._InvocationState(task=task, stages=["train"], current_stage="train")
    token = session._ACTIVE_INVOCATION.set(state)
    try:
        yield task, documents
    finally:
        session._ACTIVE_INVOCATION.reset(token)


def test_difference_preserves_explicit_empty_and_typed_values_without_mutating_inputs() -> None:
    defaults = {
        "nested": {
            "same": 1,
            "enabled": True,
            "count": 2,
            "value": 1,
            "list": [1],
            "mapping": {"x": 1},
            "order": [1, 2],
            "false": 0,
        }
    }
    values: dict[str, Any] = {
        "nested": {
            "same": 1,
            "enabled": False,
            "count": 0,
            "value": None,
            "list": [],
            "mapping": {},
            "order": [2, 1],
            "false": False,
        }
    }
    original = deepcopy(values)
    with _owner() as (task, documents):
        session.publish_run_configuration(task, values, defaults)
        assert documents["run"] == original
        assert documents["run_overrides"] == {
            "nested": {key: value for key, value in original["nested"].items() if key != "same"}
        }
        session.record_run_configuration(
            task,
            {
                "nested": {"count": 9},
                "training_normalization": {"count": {"requested": 0, "effective": 9}},
            },
        )
        assert documents["run"]["nested"]["count"] == 0
        assert "training_normalization" in documents["run"]
        assert "training_normalization" not in documents["run_overrides"]
    assert values == original


def test_difference_prunes_unchanged_parents_and_generated_routing_and_redacts_secrets() -> None:
    defaults = {"nested": {"same": []}, "ultralytics": {"weight_decay": 0.0005}}
    values: dict[str, Any] = {
        "nested": {"same": []},
        "output_dir": "/generated/run",
        "run_id": "id",
        "clearml": {
            "task_name": "name",
            "tags": ["tag"],
            "output_uri": "https://user:password@host",
        },
        "ultralytics": {"weight_decay": 0.02, "project": "/generated", "name": "generated"},
        "api_token": "private",
    }
    with _owner() as (task, documents):
        session.publish_run_configuration(task, values, defaults)
        assert documents["run_overrides"] == {
            "ultralytics": {"weight_decay": 0.02},
            "api_token": "<redacted>",
        }
        assert "private" not in json.dumps(documents)


def test_difference_json_is_deterministic_and_empty_override_is_published() -> None:
    with _owner() as (task, _):
        serialized: list[str] = []
        task.set_configuration_object = lambda **kwargs: serialized.append(kwargs["config_text"])
        session.publish_run_configuration(task, {"b": 2, "a": 1}, {})
        first = list(serialized)
        serialized.clear()
        session.publish_run_configuration(task, {"a": 1, "b": 2}, {})
        assert serialized == first
        session.publish_run_configuration(task, {"a": 1}, {"a": 1})
        assert json.loads(serialized[-1]) == {}


@pytest.mark.parametrize(
    "selection", ["ultralytics", "rfdetr/small", "deimv2/s", "fasterrcnn/resnet50_fpn"]
)
def test_defaults_use_same_selected_preset_and_only_active_backend(selection: str) -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    model = model_preset(selection).model_dump(mode="json")
    selected = OmegaConf.create({"model": model})
    defaults = common._builtin_defaults("pipeline", selected)
    assert defaults["model"]["backend"] == model["backend"]
    assert defaults["model"]["preset"] == model["preset"]
    if selection == "ultralytics":
        assert "train" not in defaults["model"]
        assert "predict" not in defaults["model"]
        assert defaults["ultralytics"]["weight_decay"] == 0.0005
    else:
        assert "ultralytics" not in defaults
        assert "ultralytics_predict" not in defaults
        assert defaults["model"]["train"]["imgsz"] == model["train"]["imgsz"]
        assert defaults["dataset_format"] == "coco"
    with _owner() as (task, documents):
        session.publish_run_configuration(task, defaults, defaults)
        assert documents["run_overrides"] == {}


def test_training_parameters_are_detached_sanitized_and_owner_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = {
        "epochs": 2,
        "device": [0, 1],
        "data": "data.yaml",
        "project": "outputs",
        "name": "run",
        "exist_ok": False,
        "classes": [],
        "api_token": "private",
    }
    with _owner() as (task, _):
        connected: list[dict[str, Any]] = []
        task.connect = lambda values, **kwargs: connected.append(
            {"values": deepcopy(values), **kwargs}
        )
        session.publish_training_parameters(task, values)
        session.publish_training_parameters(task, values | {"project": "later-route"})
        assert connected == [
            {
                "values": {"epochs": 2, "classes": [], "api_token": "<redacted>"},
                "name": "General",
                "ignore_remote_overrides": True,
            }
        ]
        monkeypatch.setenv(session.OWNER_PID_ENV, "-42")
        monkeypatch.setenv(session.OWNER_TASK_ENV, "owner")
        session.publish_training_parameters(None, values)
        assert len(connected) == 1
    assert values["api_token"] != session.REDACTED


def test_ordered_lists_keep_nested_boolean_and_zero_differences() -> None:
    with _owner() as (task, documents):
        session.publish_run_configuration(
            task, {"values": [False, {"flag": False}]}, {"values": [0, {"flag": 0}]}
        )
        assert documents["run_overrides"] == {"values": [False, {"flag": False}]}


def test_remote_general_read_does_not_publish_or_redact_executable_credentials() -> None:
    native = {"model": "https://models.example/best.pt?token=private", "epochs": 1, "device": [0]}
    with _owner() as (task, documents):
        task.get_parameters = lambda **kwargs: {
            "General/model": session.prepare_native_parameters(native)["model"],
            "General/epochs": 3,
            "General/device": [9],
        }
        resolved = session.replay_training_parameters(task, native)
        assert resolved == native | {"epochs": 3}
        assert documents == {}
        session.publish_run_configuration(task, {"ultralytics": resolved}, {})
        assert "private" not in json.dumps(documents)
        assert "private" in resolved["model"]


@pytest.mark.parametrize(
    "selection", ["ultralytics", "rfdetr/small", "deimv2/s", "fasterrcnn/resnet50_fpn"]
)
@pytest.mark.parametrize("skip_train", [False, True])
def test_general_precedes_workflow_and_optional_publisher_and_skipped_training_has_none(
    monkeypatch: pytest.MonkeyPatch, selection: str, skip_train: bool
) -> None:
    from contextlib import nullcontext

    from hydra import compose, initialize

    from clearml_yolo.application.use_cases.pipeline import run_pipeline

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize(version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=[
                f"model={selection}",
                "ground_truth=input.csv",
                f"skip_train={str(skip_train).lower()}",
            ],
        )
    events: list[str] = []
    with _owner() as (task, documents):
        task.running_locally = lambda: False
        task.get_configuration_object_as_dict = lambda name: None
        task.get_configuration_object = lambda name: None
        task.get_parameters = lambda **kwargs: {"General/weight_decay": 0.03}
        task.connect = lambda values, **kwargs: events.append("General")
        monkeypatch.setattr(common, "invocation", lambda *args, **kwargs: nullcontext(task))
        monkeypatch.setattr(common, "native_runtime", nullcontext)
        monkeypatch.setattr(common, "detector_runtime", nullcontext)
        monkeypatch.setattr(common, "execution_lifecycle", lambda: nullcontext(True))
        monkeypatch.setattr(common, "initialize_filesystem", lambda: None)
        monkeypatch.setattr(common, "initialize_naming", lambda task: None)
        monkeypatch.setattr(common, "release_training_memory", lambda: None)

        def enter_workflow(*args: Any, **kwargs: Any) -> None:
            assert events == ([] if skip_train else ["General"])
            events.append("workflow and publisher")

        monkeypatch.setattr(common, "zen", lambda *args, **kwargs: enter_workflow)
        common.execute_owned("pipeline", config, run_pipeline)
        assert events == (
            ["workflow and publisher"] if skip_train else ["General", "workflow and publisher"]
        )
        if selection == "ultralytics":
            expected = 0.0005 if skip_train else 0.03
            assert documents["run"]["ultralytics"]["weight_decay"] == expected
            assert "train" not in documents["run"]["model"]
        else:
            assert "ultralytics" not in documents["run"]
            assert documents["run"]["model"]["preset"] == selection.split("/")[1]
