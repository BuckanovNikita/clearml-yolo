"""Configuration file references follow the command's effective replay state."""

from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

import hydra
import pytest
from omegaconf import OmegaConf

from clearml_yolo.apps import common
from clearml_yolo.clearml_session import ResolvedConfigFile
from clearml_yolo.run_identity import RUNS_ROOT, task_run_dir
from test_clearml_session import FakeTask


def test_file_resolver_sees_remote_inputs_and_derived_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = OmegaConf.create(
        {"clearml": {"task_name": "source"}, "weights": "local.pt", "output_dir": None}
    )
    attached: list[Any] = []
    resolver: Any = None

    class RemoteTask:
        id = "clone-id"
        name = "clone/report"

        @staticmethod
        def get_project_name() -> str:
            return "clone-project"

        @staticmethod
        def running_locally() -> bool:
            return False

    @contextmanager
    def owner(*_args: Any, **kwargs: Any) -> Any:
        nonlocal resolver
        resolver = kwargs.get("config_resolver")
        yield RemoteTask()

    def replay(_task: Any, values: dict[str, Any]) -> dict[str, Any]:
        return values | {"weights": "remote.pt", "clearml": {"task_name": "remote"}}

    def command(clearml: Any, weights: str, output_dir: str | None) -> None:
        assert weights == "remote.pt"
        assert output_dir is not None
        assert callable(resolver), "The shared command must bind its configuration-file resolver"
        resolved_file = resolver(
            {
                "artifact_dir": "${output_dir}",
                "model": "${weights}",
                "owner": "${clearml.task_name}",
            }
        )
        assert isinstance(resolved_file, ResolvedConfigFile)
        attached.append(resolved_file.values)

    monkeypatch.setattr(hydra, "main", lambda **_kwargs: lambda fn: lambda: fn(config))
    monkeypatch.setattr(common, "native_runtime", nullcontext)
    monkeypatch.setattr(common, "invocation", owner)
    monkeypatch.setattr(common, "replay_configuration", replay)

    common.launch("report", command)

    assert attached == [
        {
            "artifact_dir": str(
                task_run_dir(RUNS_ROOT, "clone-project", "clone/report", "clone-id") / "report"
            ),
            "model": "remote.pt",
            "owner": "remote",
        }
    ]


def test_numbered_configuration_copies_and_overrides_replay_without_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import clearml

    from clearml_yolo.clearml_session import (
        ClearMLConfig,
        connect_config_file,
        invocation,
        record_run_configuration,
        replay_configuration,
    )

    source = tmp_path / "dataset.yaml"
    source.write_text("# Dataset replay source\nnames: [widget]\ntrain: images/train\n")
    local = FakeTask()
    remote = FakeTask()
    remote.local = False
    selected = local
    monkeypatch.setattr(clearml.Task, "init", lambda **_kwargs: selected)
    monkeypatch.setattr(clearml.Task, "get_task", lambda **_kwargs: selected)
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    copies: list[tuple[str, Path, str]] = []

    def attach(**kwargs: Any) -> Any:
        configuration = kwargs["configuration"]
        if isinstance(configuration, Path):
            copies.append((kwargs["name"], configuration, configuration.read_text()))
        return configuration

    monkeypatch.setattr(local, "connect_configuration", attach)
    overrides = {"fraction": {"requested": 0.5, "effective": 1.0}}
    normalization = {"batch": {"requested": -1, "effective": 8}}
    with invocation(ClearMLConfig(), "train") as task:
        for _ in range(40):
            assert connect_config_file(task, "dataset", source) == source
        run = record_run_configuration(
            task,
            {
                "ground_truth": "truth.csv",
                "training_data_overrides": overrides,
                "training_normalization": normalization,
            },
        )

    assert any(path.name == "0038.yaml" for _, path, _ in copies)
    assert {name for name, _, _ in copies} == {"dataset"}
    assert all(not path.exists() for _, path, _ in copies)
    assert local.uploads == []
    assert run["training_data_overrides"] == overrides
    assert run["training_normalization"] == normalization
    remote_source = tmp_path / "server-dataset.yaml"
    remote_source.write_text(copies[-1][2])
    source.unlink()
    selected = remote
    remote.configuration_result = remote_source
    remote.run_configuration_result = run

    with invocation(ClearMLConfig(), "train") as task:
        recovered = connect_config_file(task, "dataset", source)
        assert recovered == remote_source
        assert recovered.read_text() == remote_source.read_text()
        effective = replay_configuration(task, {"ground_truth": "placeholder.csv"})

    assert effective == run
    assert remote.uploads == []
    assert {entry["name"] for entry in remote.configurations} == {"dataset", "run"}


def test_missing_remote_named_configuration_fails_without_artifact_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import clearml

    from clearml_yolo.clearml_session import ClearMLConfig, connect_config_file, invocation

    remote = FakeTask()
    remote.local = False
    monkeypatch.setattr(clearml.Task, "init", lambda **_kwargs: remote)
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    with (
        pytest.raises(FileNotFoundError, match="Remote task has no attached configuration"),
        invocation(ClearMLConfig(), "train") as task,
    ):
        connect_config_file(task, "dataset", tmp_path / "missing.yaml")

    assert remote.failed
    assert not remote.completed
    assert remote.uploads == []
