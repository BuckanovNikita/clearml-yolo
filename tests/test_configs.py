"""Every retained CLI composes while removed fields fail explicitly."""

import pytest
from hydra import compose, initialize_config_module
from hydra.errors import ConfigCompositionException
from hydra_zen import store

import clearml_yolo.configs  # noqa: F401

COMMANDS = ["train", "predict", "val", "metrics", "report", "compare", "ground_truth", "pipeline"]


@pytest.fixture(autouse=True)
def registered() -> None:
    store.add_to_hydra_store(overwrite_ok=True)


@pytest.mark.parametrize("command", COMMANDS)
def test_command_composes(command: str) -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name=command)
    assert "clearml" in config
    assert "enabled" not in config.clearml


@pytest.mark.parametrize("override", ["auto_gpu.force=true", "clearml.enabled=false"])
def test_removed_overrides_fail(override: str) -> None:
    with (
        initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"),
        pytest.raises(ConfigCompositionException),
    ):
        compose(config_name="pipeline", overrides=[override])


def test_native_mapping_starts_full_and_accepts_explicit_values() -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="train", overrides=["ultralytics.epochs=100", "ultralytics.amp=false"]
        )
    assert config.ultralytics.epochs == 100
    assert config.ultralytics.amp is False
    assert "optimizer" in config.ultralytics


def test_prediction_inherits_shared_cli_values_and_explicit_overrides() -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=[
                "ultralytics.imgsz=1280",
                "ultralytics.batch=4",
                "ultralytics_predict.batch=8",
            ],
        )
    assert config.ultralytics_predict.imgsz == 1280
    assert config.ultralytics_predict.batch == 8
    assert config.ultralytics_predict.conf == 0.001
    assert "train" not in config
    assert "predict" not in config


def test_training_exposes_the_same_prediction_group_without_changing_train_values() -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="train", overrides=["ultralytics_predict.batch=8"])
    assert config.ultralytics.batch == 16
    assert config.ultralytics_predict.batch == 8


def test_composed_prediction_uses_produced_checkpoint_and_shared_resolution() -> None:
    from clearml_yolo.native_config import prediction_settings

    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=["ultralytics.model=architecture.pt", "ultralytics.imgsz=1280"],
        )
    base = dict(config.ultralytics)
    overrides = dict(config.ultralytics_predict)
    settings = prediction_settings(base, overrides, "produced.pt")
    assert settings["model"] == "produced.pt"
    assert settings["imgsz"] == 1280
    assert settings["conf"] == 0.001
