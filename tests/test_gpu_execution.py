"""Process supervision preserves child lifetime and failure status."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import store
from omegaconf import OmegaConf

from clearml_yolo.application.ports import WorkflowDependencies
from workflow_dependencies import patch_workflow
from workflow_dependencies import workflow_dependencies as workflow_dependencies  # noqa: PLC0414


def test_model_commands_choose_concurrent_queue_launcher() -> None:
    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        for command in ("pipeline", "train", "predict", "val", "compare"):
            config = compose(config_name=command, return_hydra_config=True)
            assert config.hydra.launcher._target_ == "hydra_plugins.cy_queue.launcher.QueueLauncher"


def test_supervisor_waits_for_child_and_preserves_environment(tmp_path: Path) -> None:
    from clearml_yolo.entrypoints.hydra.execution import wait_process

    destination = tmp_path / "child.txt"
    script = "import os,pathlib,sys; pathlib.Path(sys.argv[1]).write_text(os.environ['JOB_DEVICE'])"
    process = subprocess.Popen(  # noqa: S603 - current interpreter and task-owned test script
        [sys.executable, "-c", script, str(destination)],
        env=os.environ | {"JOB_DEVICE": "GPU-a"},
    )
    assert wait_process(process) == 0
    assert process.returncode == 0
    assert destination.read_text() == "GPU-a"


def test_supervisor_reports_failed_child() -> None:
    from clearml_yolo.entrypoints.hydra.execution import wait_process

    process = subprocess.Popen([sys.executable, "-c", "raise SystemExit(7)"])
    assert wait_process(process) == 7


def test_cancellation_reaps_owned_child(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.entrypoints.hydra.execution import cancel_process

    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    cancel_process(process)
    assert process.poll() is not None


def test_effective_configuration_uses_reserved_ordinals_without_changing_request() -> None:
    from clearml_yolo.entrypoints.hydra.execution import effective_configuration

    requested = OmegaConf.create(
        {"ultralytics": {"device": [5, 7]}, "ultralytics_predict": {"device": [-1, -1]}}
    )
    effective = effective_configuration(requested, ("GPU-a", "GPU-b"))
    assert list(effective.ultralytics.device) == [0, 1]
    assert list(effective.ultralytics_predict.device) == [0]
    assert list(requested.ultralytics.device) == [5, 7]


def test_effective_configuration_preserves_explicit_cpu_inference() -> None:
    from clearml_yolo.entrypoints.hydra.execution import effective_configuration

    requested = OmegaConf.create(
        {"ultralytics": {"device": [4, 9]}, "ultralytics_predict": {"device": "cpu"}}
    )
    effective = effective_configuration(requested, ("GPU-a", "GPU-b"))
    assert effective.ultralytics_predict.device == "cpu"


def test_training_transition_runs_before_pipeline_prediction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    from test_pipeline import test_hydra_pipeline_passes_real_stage_objects

    def transition() -> None:
        raise RuntimeError("training transition reached")

    monkeypatch.setattr(workflow_dependencies.resources, "training_finished", transition)
    with pytest.raises(RuntimeError, match="training transition reached"):
        test_hydra_pipeline_passes_real_stage_objects(tmp_path, monkeypatch, workflow_dependencies)


def test_replay_cannot_turn_cpu_worker_into_unreserved_gpu_job() -> None:
    from clearml_yolo.adapters.runtime.gpu_runtime import reservation
    from clearml_yolo.application.use_cases.predict import predict
    from clearml_yolo.entrypoints.hydra.common import _execute_assigned

    with reservation(None), pytest.raises(ValueError, match="admitted reservation"):
        _execute_assigned(
            "predict", OmegaConf.create({"ultralytics_predict": {"device": [0]}}), predict, None
        )


def test_requested_device_context_preserves_values_and_restores_after_failure() -> None:
    from clearml_yolo.adapters.yolo.config import requested_devices, requested_settings

    def fail_with_context() -> None:
        with requested_devices({"ultralytics": [7, 9], "ultralytics_predict": -1}):
            assert requested_settings({"device": [0, 1]}, "train")["device"] == [7, 9]
            assert requested_settings({"device": [0]}, "predict")["device"] == -1
            raise RuntimeError("failed")

    with pytest.raises(RuntimeError, match="failed"):
        fail_with_context()
    assert requested_settings({"device": [0]}, "predict")["device"] == [0]


def test_prediction_retains_requested_device_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> None:
    import pandas as pd
    import yaml

    from clearml_yolo.adapters.yolo.config import requested_devices
    from clearml_yolo.application.use_cases.predict import _predict_group

    def native_predict(*args: object, **kwargs: object) -> pd.DataFrame:
        return pd.DataFrame()

    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.predict.predict_on_images",
        native_predict,
    )
    with requested_devices({"ultralytics_predict": 7}):
        _predict_group(
            "best.pt",
            [str(tmp_path / "image.png")],
            "name",
            {"device": [0]},
            tmp_path / "predictions.csv",
            0,
            deps=workflow_dependencies,
        )
    requested = yaml.safe_load((tmp_path / "ultralytics_predict_requested.yaml").read_text())
    effective = yaml.safe_load((tmp_path / "ultralytics_predict.yaml").read_text())
    assert requested["device"] == 7
    assert effective["device"] == [0]
