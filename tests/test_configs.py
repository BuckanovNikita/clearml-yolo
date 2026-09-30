"""Every retained CLI composes while removed fields fail explicitly."""

import pytest
from hydra import compose, initialize_config_module
from hydra.errors import ConfigCompositionException
from hydra_zen import store

import clearml_yolo.configs  # noqa: F401


@pytest.fixture(autouse=True)
def registered() -> None:
    store.add_to_hydra_store(overwrite_ok=True)


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


@pytest.mark.parametrize("command", ["train", "pipeline"])
def test_csv_training_commands_expose_dataset_format_defaults(command: str) -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name=command)
    assert config.dataset_format == "ndjson"
    if command == "train":
        assert config.ground_truth is None


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


def test_resolved_prediction_does_not_inherit_batch_or_save_implicitly() -> None:
    from clearml_yolo.native_config import prediction_settings

    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline", overrides=["ultralytics.batch=32"])
    settings = prediction_settings(
        {"imgsz": 1, "model": "hidden.pt"}, dict(config.ultralytics_predict)
    )
    assert settings["model"] is None
    assert settings["imgsz"] == 960
    assert settings["compile"] is True
    assert settings["nms"] is True
    assert settings["batch"] == 1
    assert settings["save"] is False
    assert settings["rect"] is True
    assert "overlap_mask" not in config.ultralytics


@pytest.mark.parametrize("command", ["pipeline", "val", "metrics"])
def test_evaluation_defaults_to_all_three_splits(command: str) -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name=command)
    assert list(config.splits) == ["train", "val", "test"]


@pytest.mark.parametrize("training_device", ["null", "cpu", "[0,1]"])
def test_prediction_device_is_independent(training_device: str) -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline", overrides=[f"ultralytics.device={training_device}"]
        )
        overridden = compose(config_name="pipeline", overrides=["ultralytics_predict.device=null"])
    assert list(config.ultralytics_predict.device) == [-1]
    assert overridden.ultralytics_predict.device is None
    assert overridden.ultralytics.device is None


def test_cache_location_is_exposed_on_training_commands() -> None:
    from hydra import compose, initialize_config_module
    from hydra_zen import store

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        for name in ("train", "pipeline"):
            config = compose(config_name=name, overrides=["dataset_cache_dir=/shared/datasets"])
            assert config.dataset_cache_dir == "/shared/datasets"
