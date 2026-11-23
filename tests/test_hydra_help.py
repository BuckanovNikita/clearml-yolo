"""The Hydra commands print help that names the command and lists only selectable groups."""

import os
import subprocess
import sys
import tempfile
from functools import cache
from pathlib import Path

import pytest

_NATIVE = ("cy", "cy-train", "cy-predict", "cy-val", "cy-compare")
_PLAIN = ("cy-metrics", "cy-report", "cy-ground-truth")


@cache
def _help(command: str) -> str:
    with tempfile.TemporaryDirectory() as directory:
        return _run_help(command, Path(directory))


def _run_help(command: str, root: Path) -> str:
    environment = {key: value for key, value in os.environ.items() if not key.startswith(("GIT_", "CY_"))}
    environment["CY_HOME"] = str(root)
    result = subprocess.run(  # noqa: S603 - installed console script and test-owned paths, no shell
        [str(Path(sys.executable).with_name(command)), "--help"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.parametrize("command", [*_NATIVE, *_PLAIN, "cy-export"])
def test_help_names_the_command_and_hides_internal_groups(command: str) -> None:
    text = _help(command)
    assert text.startswith(f"{command}\n")
    assert "common is powered by Hydra" not in text
    assert "_cy_schemas" not in text
    assert "defaults/" not in text
    assert "transform_overrides" not in text
    assert "== Configuration groups ==" in text
    assert "== Config ==" in text


@pytest.mark.parametrize("command", _NATIVE)
def test_help_lists_the_selectable_groups(command: str) -> None:
    text = _help(command)
    assert "\nmodel: ultralytics\n" in text
    assert "\nmodel/rfdetr: large, medium, nano, small\n" in text
    assert ("\ntransforms: albumentations, default\n" in text) == (command in {"cy", "cy-train"})


def test_export_help_lists_only_the_supported_model_group() -> None:
    text = _help("cy-export")
    assert "\nmodel/fasterrcnn: " in text
    assert "model/rfdetr" not in text


@pytest.mark.parametrize("command", _PLAIN)
def test_help_of_commands_without_groups_lists_none(command: str) -> None:
    text = _help(command)
    groups = text.split("== Configuration groups ==")[1].split("== Config ==")[0]
    assert "model" not in groups
    assert "transforms" not in groups
    assert "no selectable groups" in groups
