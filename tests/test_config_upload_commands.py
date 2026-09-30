"""Configuration file references follow the command's effective replay state."""

from contextlib import contextmanager, nullcontext
from typing import Any

import hydra
import pytest
from omegaconf import OmegaConf

from clearml_yolo.apps import common
from clearml_yolo.clearml_session import ResolvedConfigFile
from clearml_yolo.run_identity import RUNS_ROOT, task_run_dir


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
