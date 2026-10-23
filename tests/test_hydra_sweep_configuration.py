"""Saved Hydra mode and sweep parameters have identical direct/queued semantics."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from omegaconf import OmegaConf


def _configuration(root: Path, *, mode: str | None, epochs: str = "1,2") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    config = {
        "defaults": ["pipeline", "_self_"],
        "ground_truth": "input.csv",
        "hydra": {"mode": mode, "sweeper": {"params": {"ultralytics.epochs": epochs}}},
    }
    OmegaConf.save(OmegaConf.create(config), root / "sweep.yaml")
    return root


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
