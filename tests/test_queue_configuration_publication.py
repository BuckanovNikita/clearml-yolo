"""Trace queue YAML/CLI selections through frozen worker inputs and publication."""

import json
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from hydra import compose, initialize_config_dir
from hydra_zen import instantiate
from omegaconf import DictConfig

from clearml_yolo.adapters.clearml import session
from clearml_yolo.application.use_cases.pipeline import run_pipeline
from clearml_yolo.application.use_cases.train import train
from clearml_yolo.core.queue import JobSnapshot, ResourceRequest
from clearml_yolo.entrypoints.hydra import common
from clearml_yolo.entrypoints.hydra.queue_config import compose_snapshots, write_execution_config


@pytest.mark.parametrize("weight_decay", [None, "0.03", "0.03,0.04"])
def test_queue_weight_decay_survives_yaml_cli_snapshot_worker_and_training(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, weight_decay: str | None
) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    (config_dir / "chosen.yaml").write_text(
        "defaults:\n  - pipeline\n  - _self_\nground_truth: input.csv\n"
        "ultralytics:\n  weight_decay: 0.02\n  compile: false\n"
        "skip_predict: true\nskip_metrics: true\nskip_compare: true\nskip_report: true\n"
        "fiftyone:\n  enabled: false\n"
    )
    arguments = ["--config-dir", str(config_dir), "--config-name", "chosen"]
    if weight_decay is not None:
        arguments.append(f"ultralytics.weight_decay={weight_decay}")
    if weight_decay is not None and "," in weight_decay:
        arguments.append("-m")
    snapshots = compose_snapshots(arguments, ResourceRequest(gpus=2), project_root=tmp_path)
    expected = (
        [0.02] if weight_decay is None else [float(value) for value in weight_decay.split(",")]
    )
    assert len(snapshots) == len(expected)
    for index, (snapshot, decay) in enumerate(zip(snapshots, expected, strict=True)):
        _assert_execution(snapshot, decay, tmp_path / f"worker-{index}", monkeypatch)


def _assert_execution(
    snapshot: JobSnapshot, decay: float, execution_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.entrypoints.composition import build_dependencies

    # Private storage serializes this same immutable envelope before worker loading.
    loaded = JobSnapshot.model_validate_json(snapshot.model_dump_json())
    assert json.loads(loaded.config_json)["ultralytics"]["weight_decay"] == decay
    execution_dir.mkdir()
    executable = write_execution_config(loaded, 2, execution_dir)
    with initialize_config_dir(config_dir=str(execution_dir), version_base="1.3"):
        config = compose(config_name=executable.stem)
    documents: dict[str, Any] = {}
    parameters: list[dict[str, Any]] = []
    events: list[str] = []
    task = SimpleNamespace(
        id="owner",
        name="owner",
        running_locally=lambda: True,
        get_project_name=lambda: "test",
        set_configuration_object=lambda **values: documents.update(
            {values["name"]: json.loads(values["config_text"])}
        ),
        connect=lambda values, **kwargs: parameters.append(deepcopy(values)),
    )

    @contextmanager
    def invocation(*args: Any, **kwargs: Any) -> Iterator[Any]:
        state = session._InvocationState(task=task, stages=["pipeline"], current_stage="pipeline")
        token = session._ACTIVE_INVOCATION.set(state)
        try:
            yield task
        finally:
            session._ACTIVE_INVOCATION.reset(token)

    deps = build_dependencies()
    monkeypatch.setattr(deps.tracking, "init_task", lambda *a, **k: task)
    native: list[dict[str, Any]] = []

    def prepare(*args: Any, **kwargs: Any) -> Any:
        assert parameters
        assert parameters[-1]["weight_decay"] == decay
        events.append("prepare")
        prepared = SimpleNamespace(ground_truth=Path("truth.csv"), data=Path("data.yaml"))
        return nullcontext((prepared, args[1]))

    def native_train(
        owner: object, architecture: str, settings: dict[str, Any], prepared: Any
    ) -> Any:
        native.append(deepcopy(settings))
        events.append("train")

    def execute(name: str, effective: DictConfig, function: Any) -> None:
        train(
            dict(effective.ultralytics),
            instantiate(effective.clearml),
            effective.ground_truth,
            deps=deps,
        )

    monkeypatch.setattr("clearml_yolo.application.use_cases.train._prepare_csv_dataset", prepare)
    monkeypatch.setattr(deps.model, "train", native_train)
    monkeypatch.setattr(common, "initialize_filesystem", lambda: None)
    monkeypatch.setattr(common, "native_runtime", nullcontext)
    monkeypatch.setattr(common, "execution_lifecycle", lambda: nullcontext(True))
    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(common, "release_training_memory", lambda: None)
    monkeypatch.setattr(common, "initialize_naming", lambda task: None)
    monkeypatch.setattr(common, "_execute_direct", execute)
    common.execute_owned("pipeline", config, run_pipeline)
    assert documents["run_overrides"]["ultralytics"]["weight_decay"] == decay
    assert documents["run"]["ultralytics"]["device"] == [0, 1]
    assert "train" not in documents["run"]["model"]
    assert native[0]["weight_decay"] == decay
    assert native[0]["device"] == [0, 1]
    assert parameters[0]["weight_decay"] == decay
    assert "device" not in parameters[0]
    assert events == ["prepare", "train"]
