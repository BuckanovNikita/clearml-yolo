"""One launch groups its ClearML tasks without replacing explicit tags."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from omegaconf import OmegaConf


def _group(tags: list[str], user_tags: list[str]) -> str:
    assert tags[:-1] == user_tags
    tag = tags[-1]
    assert re.fullmatch(r"multirun-\d{8}-\d{6}(?:-[a-z]+){6}", tag)
    return tag


def _launches(
    tmp_path: Path, arguments: list[str], *, command: str = "pipeline"
) -> list[list[str]]:
    script = """
import json
import sys
from clearml_yolo.entrypoints.hydra import common
def record(name, config, function):
    print('TASK_TAGS:' + json.dumps(list(config.clearml.tags)), flush=True)
common.execute_owned = record
arguments = sys.argv[1:]
for _ in range(2):
    sys.argv = ['test-launch', *arguments]
    common.launch(COMMAND, lambda: None)
sys.argv = ['test-launch', 'ground_truth=input.csv', 'clearml.tags=[single]']
common.launch(COMMAND, lambda: None)
""".replace("COMMAND", repr(command))
    result = subprocess.run(  # noqa: S603 - real Hydra with a recording execution boundary
        [sys.executable, "-c", script, *arguments],
        cwd=tmp_path,
        env=dict(os.environ, CY_HOME=str(tmp_path)),
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return [
        json.loads(line.removeprefix("TASK_TAGS:"))
        for line in result.stdout.splitlines()
        if line.startswith("TASK_TAGS:")
    ]


@pytest.mark.parametrize("mode", [["-m"], ["--multirun"], ["hydra.mode=MULTIRUN"]])
@pytest.mark.parametrize("command", ["pipeline", "train"])
def test_direct_multiruns_share_tags_only_within_each_launch(
    tmp_path: Path, mode: list[str], command: str
) -> None:
    tags = _launches(
        tmp_path,
        [*mode, "ground_truth=input.csv", "ultralytics.epochs=1,2", "clearml.tags=[prod,prod]"],
        command=command,
    )
    assert len(tags) == 5
    first = _group(tags[0], ["prod", "prod"])
    second = _group(tags[2], ["prod", "prod"])
    assert first != second
    assert tags[0] == tags[1]
    assert tags[2] == tags[3]
    assert tags[4] == ["single"]


@pytest.mark.parametrize("saved_mode", ["MULTIRUN", "RUN"])
def test_saved_mode_and_one_job_multiruns_receive_fresh_tags(
    tmp_path: Path, saved_mode: str
) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    OmegaConf.save(
        OmegaConf.create(
            {
                "defaults": ["pipeline", "_self_"],
                "ground_truth": "input.csv",
                "hydra": {"mode": saved_mode},
            }
        ),
        config_dir / "saved.yaml",
    )
    arguments = ["--config-dir", str(config_dir), "--config-name", "saved"]
    if saved_mode == "RUN":
        arguments.append("-m")
    tags = _launches(tmp_path, arguments)
    assert len(tags) == 3
    assert _group(tags[0], []) != _group(tags[1], [])
    assert tags[2] == ["single"]


def test_direct_per_job_tags_survive_grouping(tmp_path: Path) -> None:
    tags = _launches(tmp_path, ["-m", "ground_truth=input.csv", "clearml.tags=[first],[second]"])
    assert len(tags) == 5
    assert _group(tags[0], ["first"]) == _group(tags[1], ["second"])
    assert _group(tags[2], ["first"]) == _group(tags[3], ["second"])
    assert tags[0][-1] != tags[2][-1]
