"""Direct commands preserve native requests and validate writes before Hydra effects."""

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import store
from omegaconf import OmegaConf


@pytest.mark.parametrize(
    "cleanup_error", [RuntimeError("cleanup failed"), KeyboardInterrupt(), SystemExit(143)]
)
@pytest.mark.parametrize("broken_sink", [False, True])
def test_gpu_cleanup_retains_original_error(
    monkeypatch: pytest.MonkeyPatch, cleanup_error: BaseException, broken_sink: bool
) -> None:
    from loguru import logger

    from clearml_yolo.entrypoints.hydra import common

    original = ValueError("original computation failed")
    diagnostics: list[str] = []

    def cleanup() -> None:
        raise cleanup_error

    def sink(message: Any) -> None:
        if "Native GPU memory cleanup failed" in message.record["message"]:
            diagnostics.append(message.record["message"])
            if broken_sink:
                raise RuntimeError("broken cleanup diagnostic sink")

    monkeypatch.setattr(common, "release_training_memory", cleanup)
    handle = logger.add(sink, catch=False, format="{message}")
    try:
        with (
            pytest.raises(BaseException, match="original computation failed") as raised,
            common._gpu_cleanup(True),
        ):
            raise original
    finally:
        logger.remove(handle)
    assert raised.value is original
    assert diagnostics


@pytest.mark.parametrize(
    "cleanup_error", [RuntimeError("cleanup failed"), KeyboardInterrupt(), SystemExit(143)]
)
def test_gpu_cleanup_without_primary_propagates_failure(
    monkeypatch: pytest.MonkeyPatch, cleanup_error: BaseException
) -> None:
    from clearml_yolo.entrypoints.hydra import common

    def cleanup() -> None:
        raise cleanup_error

    monkeypatch.setattr(common, "release_training_memory", cleanup)
    with pytest.raises(type(cleanup_error)) as raised, common._gpu_cleanup(True):
        pass
    assert raised.value is cleanup_error


def _cli(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["CY_HOME"] = str(root)
    environment.pop("CY_RUNTIME_TEMP_ROOT", None)
    return subprocess.run(  # noqa: S603 - fixed console entrypoint and fixture-owned arguments
        [
            sys.executable,
            "-c",
            "from clearml_yolo.entrypoints.pipeline import main; main()",
            *arguments,
        ],
        env=environment,
        cwd=root.parent,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_direct_schemas_have_no_scheduler_and_use_basic_launcher() -> None:
    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        for name in ("pipeline", "train", "predict", "val", "compare", "export"):
            config = compose(config_name=name, return_hydra_config=True)
            assert "queue" not in config
            assert "autogpu" not in config
            assert (
                config.hydra.launcher._target_
                == "hydra._internal.core_plugins.basic_launcher.BasicLauncher"
            )


@pytest.mark.parametrize("device", [-1, "cuda", "2,0", [2, 0], "cpu", None])
def test_direct_execution_preserves_native_device_and_has_no_scheduler_imports(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, device: Any
) -> None:
    from clearml_yolo.entrypoints.hydra import common

    received = []

    @contextmanager
    def runtime() -> Iterator[None]:
        yield

    @contextmanager
    def invocation(*args: Any, **kwargs: Any) -> Iterator[Any]:
        yield SimpleNamespace(running_locally=lambda: True)

    def workflow(ultralytics_predict: dict[str, Any], clearml: dict[str, Any]) -> None:
        received.append((os.getpid(), ultralytics_predict["device"]))

    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.setattr(common, "native_runtime", runtime)
    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(common, "replay_configuration", lambda task, values: values)
    monkeypatch.setattr(common, "initialize_naming", lambda task: None)
    monkeypatch.setattr(common, "release_training_memory", lambda: None)
    config = OmegaConf.create({"ultralytics_predict": {"device": device}, "clearml": {}})
    common.execute_owned("predict", config, workflow)
    assert received == [(os.getpid(), device)]
    source = Path(common.__file__).read_text(encoding="utf-8")
    assert "gpu_runtime" not in source
    assert "gpu_scheduling" not in source
    assert "hydra.execution" not in source


@pytest.mark.parametrize(
    "override",
    [
        "queue.enabled=false",
        "autogpu.force=true",
        "+queue.enabled=true",
        "auto_gpu.force=true",
        "hydra/launcher=cy_queue",
    ],
)
def test_legacy_cli_controls_report_migration_before_hydra(tmp_path: Path, override: str) -> None:
    result = _cli(tmp_path / "workspace", "--cfg", "job", override)
    assert result.returncode != 0
    assert "cy-queue" in result.stderr
    assert "Could not override" not in result.stderr


def test_saved_legacy_configuration_reports_migration(tmp_path: Path) -> None:
    config = tmp_path / "legacy"
    config.mkdir()
    (config / "legacy.yaml").write_text("defaults: [pipeline, _self_]\nqueue: {enabled: false}\n")
    result = _cli(
        tmp_path / "workspace",
        "--config-dir",
        str(config),
        "--config-name",
        "legacy",
        "--cfg",
        "job",
    )
    assert result.returncode != 0
    assert "cy-queue" in result.stderr


@pytest.mark.parametrize(
    "setting",
    [
        "hydra.run.dir",
        "hydra.sweep.dir",
        "hydra.output_subdir",
        "hydra.job_logging.handlers.file.filename",
        "run_dir",
        "dataset_cache_dir",
        "ultralytics.project",
    ],
)
def test_external_project_routes_are_rejected_before_any_external_creation(
    tmp_path: Path, setting: str
) -> None:
    outside = tmp_path / "outside" / "never-created"
    arguments = [f"{setting}={outside}"]
    if setting == "hydra.sweep.dir":
        arguments.insert(0, "-m")
    result = _cli(tmp_path / "workspace", *arguments)
    assert result.returncode != 0
    assert "CY_HOME" in result.stderr
    assert not outside.parent.exists()


def test_external_input_remains_allowed_for_config_inspection(tmp_path: Path) -> None:
    result = _cli(
        tmp_path / "workspace", "--cfg", "job", f"ground_truth={tmp_path / 'external.csv'}"
    )
    assert result.returncode == 0, result.stderr
    assert "external.csv" in result.stdout


def test_symlink_hydra_route_rejected_before_log_directory(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)
    result = _cli(root, f"hydra.run.dir={root / 'escape' / 'job'}")
    assert result.returncode != 0
    assert "CY_HOME" in result.stderr
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize(
    ("leaf", "multirun", "chdir"),
    [
        (".hydra/config.yaml", False, False),
        (".hydra/hydra.yaml", False, False),
        (".hydra/overrides.yaml", False, False),
        ("escaped.log", False, False),
        ("escaped.log", False, True),
        ("1/.hydra/config.yaml", True, False),
        ("multirun.yaml", True, False),
    ],
)
def test_hydra_generated_files_reject_symlinks_before_any_job(
    tmp_path: Path, leaf: str, multirun: bool, chdir: bool
) -> None:
    root = tmp_path / "workspace"
    selected = root / "selected"
    destination = selected / leaf
    destination.parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.write_text("preserved")
    destination.symlink_to(outside)
    script = """
import logging
from clearml_yolo.entrypoints.hydra import common
def execute(*args):
    print('WORKFLOW_STARTED', flush=True)
    logging.getLogger('probe').warning('unexpected external write')
common.execute_owned = execute
common.launch('pipeline', lambda: None)
"""
    arguments = (
        ["-m", "ultralytics.epochs=1,2", f"hydra.sweep.dir={selected}"]
        if multirun
        else [f"hydra.run.dir={selected}"]
    )
    if leaf == "escaped.log":
        arguments.append(
            "hydra.job_logging.handlers.file.filename="
            + ("escaped.log" if chdir else "${hydra.runtime.output_dir}/escaped.log")
        )
    if chdir:
        arguments.append("hydra.job.chdir=true")
    result = subprocess.run(  # noqa: S603 - isolated real Hydra with inert task callback
        [sys.executable, "-c", script, *arguments],
        cwd=root,
        env=dict(os.environ, CY_HOME=str(root)),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert "CY_HOME" in result.stderr
    assert "WORKFLOW_STARTED" not in result.stdout
    assert outside.read_text() == "preserved"


def test_direct_multirun_is_sequential_in_one_process(tmp_path: Path) -> None:
    environment = dict(os.environ)
    environment["CY_HOME"] = str(tmp_path)
    script = """
import json, os
from pathlib import Path
from clearml_yolo.entrypoints.hydra import common
observed=[]
def execute(name, config, function):
    observed.append((os.getpid(), config.ultralytics.device))
common.execute_owned=execute
common.launch('pipeline', lambda: None)
Path(os.environ['CY_HOME'], 'observed.json').write_text(json.dumps(observed))
"""
    result = subprocess.run(  # noqa: S603 - fixed isolated direct-launch test
        [sys.executable, "-c", script, "-m", "ultralytics.device=2,0"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads((tmp_path / "observed.json").read_text(encoding="utf-8"))
    assert [value[1] for value in observed] == [2, 0]
    assert len({value[0] for value in observed}) == 1
