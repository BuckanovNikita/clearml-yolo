"""Explicit scheduling preserves identities and rejects unsafe replay."""

import pytest
from omegaconf import OmegaConf

from clearml_yolo.adapters.runtime.gpu_scheduling import (
    exact_request,
    execution_controls,
)
from clearml_yolo.entrypoints.hydra.execution import exact_effective_configuration


def test_exact_union_retains_inference_identity_and_training_order() -> None:
    config = {"ultralytics": {"device": [2, 0]}, "ultralytics_predict": {"device": 1}}
    selection = exact_request("pipeline", config, ("GPU-a", "GPU-b", "GPU-c"))
    assert selection.devices == ("GPU-b", "GPU-c", "GPU-a")
    effective = exact_effective_configuration(
        "pipeline", OmegaConf.create(config), selection, selection.devices
    )
    assert list(effective.ultralytics.device) == [1, 2]
    assert list(effective.ultralytics_predict.device) == [0]
    # Shrinking the lease does not change CUDA's already-initialized ordinal mapping.
    replay = OmegaConf.create({"skip_train": True, **config})
    effective = exact_effective_configuration("pipeline", replay, selection, ("GPU-b",))
    assert list(effective.ultralytics_predict.device) == [0]


@pytest.mark.parametrize("selector", [None, "", "cuda", -1, [-1], [0, 0], "0,-1"])
def test_queued_exact_rejects_ambiguous_selectors(selector: object) -> None:
    with pytest.raises(ValueError, match="exact"):
        exact_request("train", {"ultralytics": {"device": selector}}, ("GPU-a", "GPU-b"))


def test_exact_replay_cannot_add_unadmitted_identity() -> None:
    selection = exact_request("train", {"ultralytics": {"device": 0}}, ("GPU-a", "GPU-b"))
    with pytest.raises(ValueError, match="admitted"):
        exact_effective_configuration(
            "train", OmegaConf.create({"ultralytics": {"device": 1}}), selection, selection.devices
        )


def test_exact_cpu_bypasses_queue_demand() -> None:
    assert exact_request("train", {"ultralytics": {"device": "cpu"}}, ()).devices == ()


def test_controls_are_strict_booleans() -> None:
    assert execution_controls({}) == (True, True)
    assert execution_controls({"queue": {"enabled": False}, "autogpu": {"enabled": False}}) == (
        False,
        False,
    )
    with pytest.raises(TypeError, match="boolean"):
        execution_controls({"queue": {"enabled": "false"}})
