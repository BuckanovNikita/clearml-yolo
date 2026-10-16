"""Saved Hydra mode and sweep parameters have identical direct/queued semantics."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from omegaconf import OmegaConf

from clearml_yolo.core.queue import ResourceRequest
from clearml_yolo.entrypoints.hydra.queue_config import compose_snapshots
from queue_cli_helpers import queue_command, queue_environment


def _configuration(root: Path, *, mode: str | None, epochs: str = "1,2") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    config = {
        "defaults": ["pipeline", "_self_"],
        "ground_truth": "input.csv",
        "hydra": {"mode": mode, "sweeper": {"params": {"ultralytics.epochs": epochs}}},
    }
    OmegaConf.save(OmegaConf.create(config), root / "sweep.yaml")
    return root


@pytest.mark.parametrize(
    ("mode", "arguments", "expected"),
    [
        (None, ["-m"], [1, 2]),
        ("MULTIRUN", [], [1, 2]),
        (None, ["hydra.mode=MULTIRUN"], [1, 2]),
        ("RUN", ["-m"], [1, 2]),
        ("MULTIRUN", ["ultralytics.epochs=3,4"], [3, 4]),
        ("MULTIRUN", ["ultralytics.epochs=5"], [5]),
        ("RUN", [], [100]),
    ],
)
def test_queue_expands_saved_parameters_with_cli_precedence(
    tmp_path: Path, mode: str | None, arguments: list[str], expected: list[int]
) -> None:
    config = _configuration(tmp_path / "config", mode=mode)
    snapshots = compose_snapshots(
        ["--config-dir", str(config), "--config-name", "sweep", *arguments],
        ResourceRequest(gpus=1),
        project_root=tmp_path,
    )
    assert [json.loads(item.config_json)["ultralytics"]["epochs"] for item in snapshots] == expected


def test_invalid_saved_sweep_is_rejected_before_manifest_commit(tmp_path: Path) -> None:
    config = _configuration(tmp_path / "config", mode="MULTIRUN", epochs="1,0")
    result = subprocess.run(  # noqa: S603 - fixed queue CLI and invalid saved fixture
        [
            *queue_command(tmp_path),
            "submit",
            "--gpus",
            "1",
            "--",
            "--config-dir",
            str(config),
            "--config-name",
            "sweep",
        ],
        env=queue_environment(tmp_path),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0
    assert "epochs" in result.stderr
    assert not list((tmp_path / "queue").rglob("snapshot.json"))


@pytest.mark.parametrize("source", ["cli", "saved"])
def test_queue_labels_use_frozen_job_local_task_names(tmp_path: Path, source: str) -> None:
    arguments = ["-m", "ground_truth=input.csv", "ultralytics.epochs=1,2"]
    if source == "cli":
        arguments.append("clearml.task_name=Experiment-${hydra:job.num}")
    else:
        config = _configuration(tmp_path / "config", mode="MULTIRUN")
        saved = OmegaConf.load(config / "sweep.yaml")
        saved.clearml = {"task_name": "Experiment-${hydra:job.num}"}
        OmegaConf.save(saved, config / "sweep.yaml")
        arguments = ["--config-dir", str(config), "--config-name", "sweep"]
    snapshots = compose_snapshots(
        arguments,
        ResourceRequest(gpus=1),
        project_root=tmp_path,
    )
    assert [item.label for item in snapshots] == ["Experiment-0", "Experiment-1"]
    assert [json.loads(item.config_json)["clearml"]["task_name"] for item in snapshots] == [
        item.label for item in snapshots
    ]


@pytest.mark.parametrize("plugin", ["sweeper", "launcher"])
def test_nonsequential_sweep_plugins_are_rejected_before_instantiation(
    tmp_path: Path, plugin: str
) -> None:
    with pytest.raises(ValueError, match="BasicSweeper/BasicLauncher"):
        compose_snapshots(
            ["-m", "ground_truth=input.csv", f"hydra.{plugin}._target_=unsupported.Launch"],
            ResourceRequest(gpus=1),
            project_root=tmp_path,
        )


@pytest.mark.parametrize("mode_source", ["cli", "saved", "flag_precedence"])
@pytest.mark.parametrize("leaf", ["multirun.yaml", "1/.hydra/config.yaml"])
def test_effective_direct_multirun_checks_every_destination_before_start(
    tmp_path: Path, mode_source: str, leaf: str
) -> None:
    root = tmp_path / "workspace"
    selected = root / "selected"
    target = selected / leaf
    target.parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.write_text("preserved")
    target.symlink_to(outside)
    config = _configuration(root / "config", mode="MULTIRUN" if mode_source == "saved" else "RUN")
    arguments = [
        "--config-dir",
        str(config),
        "--config-name",
        "sweep",
        f"hydra.sweep.dir={selected}",
    ]
    if mode_source == "cli":
        arguments.append("hydra.mode=MULTIRUN")
    elif mode_source == "flag_precedence":
        arguments.append("-m")
    script = """
from clearml_yolo.entrypoints.hydra import common
common.execute_owned = lambda *args: print('WORKFLOW_STARTED', flush=True)
common.launch('pipeline', lambda: None)
"""
    result = subprocess.run(  # noqa: S603 - inert real Hydra pipeline
        [sys.executable, "-c", script, *arguments],
        cwd=root,
        env=dict(os.environ, CY_HOME=str(root)),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert "CY_HOME" in result.stderr
    assert "WORKFLOW_STARTED" not in result.stdout
    assert outside.read_text() == "preserved"
