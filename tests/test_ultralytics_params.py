"""The packaged parameter files must stay the whole of ultralytics' configuration.

They are vendored rather than read out of ultralytics at run time, because reading them
there would import torch on every CLI start and put a model-loading dependency inside the
config layer. The cost of vendoring is that an ultralytics upgrade can add a parameter the
files never hear about — which is what these tests are for.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from ultralytics.cfg import get_cfg
from ultralytics.utils import DEFAULT_CFG_DICT, YAML

from clearml_yolo.configs import TRAIN_PROJECT
from clearml_yolo.ultralytics_params import fill_unset

PARAMS_DIR = Path(__file__).resolve().parents[1] / "src" / "clearml_yolo" / "conf" / "ultralytics"
IGNORED_MARKER = "# ---- ignored by detection"

LIVE_KEY = re.compile(r"^([a-z_0-9]+):")
COMMENTED_KEY = re.compile(r"^# ([a-z_0-9]+):")

# What each stage works out for itself, and a value it plausibly works out. The files
# leave these null, which is this project's own sentinel — ultralytics rejects a null
# `batch` or `compile` outright — so they are filled before the acceptance check, exactly
# as the tasks fill them.
RUN_DECIDES: dict[str, dict[str, Any]] = {
    "train": {"batch": 16, "device": [0], "name": "yolo-run", "amp": True, "compile": True},
    "predict": {"batch": 16, "device": "0", "imgsz": 640, "quantize": 16, "compile": True},
}


def _written(stem: str) -> dict[str, Any]:
    """One parameter file as YAML sees it, comments gone."""
    loaded: dict[str, Any] = YAML.load(PARAMS_DIR / f"{stem}.yaml")  # type: ignore[no-untyped-call]
    return loaded


def _keys(stem: str) -> tuple[set[str], set[str]]:
    """The live keys and the commented-out ones, read off the file as written."""
    text = (PARAMS_DIR / f"{stem}.yaml").read_text(encoding="utf-8")
    head, marker, tail = text.partition(IGNORED_MARKER)
    assert marker, f"{stem}.yaml has no ignored section"
    live = {match.group(1) for line in head.splitlines() if (match := LIVE_KEY.match(line))}
    ignored = {match.group(1) for line in tail.splitlines() if (match := COMMENTED_KEY.match(line))}
    return live, ignored


@pytest.mark.parametrize("stem", ["train", "predict"])
def test_every_ultralytics_param_is_live_or_commented(stem: str) -> None:
    """An upgrade that adds a parameter must fail here rather than hide it.

    A key nobody lists is a knob that has silently stopped being visible in the config,
    which is the whole defect this file set exists to remove.
    """
    live, ignored = _keys(stem)

    assert live | ignored == set(DEFAULT_CFG_DICT)
    assert not live & ignored


@pytest.mark.parametrize("stem", ["train", "predict"])
def test_every_live_param_is_one_ultralytics_accepts(stem: str) -> None:
    """Values, not just keys: a live key ultralytics refuses is a config that cannot run."""
    live, _ = _keys(stem)
    written = _written(stem)
    settled = fill_unset(written, **RUN_DECIDES[stem])

    assert set(written) == live
    get_cfg({**DEFAULT_CFG_DICT, **settled})


def test_prediction_keeps_every_detection_calibration_needs() -> None:
    """Ultralytics reads an unset `conf` as 0.25 at predict time, which would drop the
    low-confidence detections the per-class thresholds are chosen from. The key-union test
    cannot see a wrong value, so the one value that matters is pinned here."""
    written = _written("predict")

    assert written["conf"] is not None
    assert written["conf"] < 0.01


@pytest.mark.parametrize("stem", ["train", "predict"])
def test_the_keys_the_run_decides_are_left_for_it_to_decide(stem: str) -> None:
    """Written with a value, each of these would pin a choice the hardware has to make."""
    written = _written(stem)

    assert {key: written[key] for key in RUN_DECIDES[stem]} == dict.fromkeys(RUN_DECIDES[stem])


def test_the_run_directory_is_the_one_a_skipped_training_stage_is_pointed_at() -> None:
    """`project` is written in the parameter file and read again by `DEFAULT_CHECKPOINT`,
    which is where a standalone `cy-predict` looks with no weights named. Two copies of one
    path: edit the file alone and inference quietly reads a directory training never wrote
    to. `name` has no such pair — it is single-sourced from the ClearML task name.
    """
    assert _written("train")["project"] == TRAIN_PROJECT


def test_the_prediction_file_never_names_what_the_inference_call_sets_itself() -> None:
    """`predict_on_images` passes these three itself — the manifest it wrote, and the
    streaming and logging it needs — so a live key here would arrive twice and raise a
    TypeError inside the run rather than at composition time."""
    written = _written("predict")

    assert not {"source", "stream", "verbose"} & set(written)


def test_a_value_written_in_the_file_is_never_overridden() -> None:
    """The whole rule: null means the run decides, a value means it does not get to."""
    written = {"amp": False, "batch": 8, "compile": False, "quantize": 32, "name": None}

    assert fill_unset(written, amp=True, batch=64, compile=True, quantize=16, name="yolo-run") == {
        "amp": False,
        "batch": 8,
        "compile": False,
        "quantize": 32,
        "name": "yolo-run",
    }


def test_a_key_the_file_never_mentions_is_still_filled() -> None:
    """A commented-out key and a null one are the same thing once Hydra has composed the
    file, so both have to reach the run the same way."""
    assert fill_unset({"epochs": 100}, batch=64) == {"epochs": 100, "batch": 64}
