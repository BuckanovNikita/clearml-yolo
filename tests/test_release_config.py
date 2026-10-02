"""Configuration provenance must preserve explicit native defaults."""

from pathlib import Path

import pytest
from omegaconf import OmegaConf


@pytest.mark.parametrize(
    "key", ["unknown_option", "iou_threshold", "matching_strategy"]
)
def test_added_unknown_wrapper_keys_are_not_silently_ignored(key: str) -> None:
    from clearml_yolo.apps.common import validate_wrapper_keys
    from clearml_yolo.tasks.train import train

    config = OmegaConf.create({"ultralytics": {}, "clearml": {}, key: True})
    with pytest.raises(ValueError, match="Unsupported wrapper"):
        validate_wrapper_keys(config, train)


def test_tracking_disabled_option_is_rejected() -> None:
    from pydantic import ValidationError

    from clearml_yolo.clearml_session import ClearMLConfig

    with pytest.raises(ValidationError, match="Extra inputs"):
        ClearMLConfig.model_validate({"enabled": False})


def test_file_backed_group_and_cli_preserve_precedence(tmp_path: Path) -> None:
    from hydra import compose, initialize_config_dir

    from clearml_yolo.config_tree import dump_config_tree

    dump_config_tree(tmp_path)
    (tmp_path / "ultralytics/default.yaml").write_text("epochs: 3\nbatch: 2\n")
    (tmp_path / "ultralytics_predict/default.yaml").write_text("batch: 16\nconf: null\n")
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        config = compose(config_name="cy", overrides=["ultralytics.epochs=100"])
    assert config.ultralytics.epochs == 100
    assert config.ultralytics.batch == 2
    assert config.ultralytics_predict.batch == 16
    assert config.ultralytics_predict.conf is None


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("pipeline", "ground_truth"),
        ("train", "ground_truth"),
        ("predict", "ground_truth"),
        ("val", "ground_truth"),
        ("metrics", "predictions"),
        ("metrics", "ground_truth"),
        ("report", "comparison_dir"),
        ("compare", "ground_truth"),
        ("ground_truth", "data_yaml"),
    ],
)
def test_command_inputs_are_required(name: str, key: str) -> None:
    from hydra import compose, initialize_config_module
    from hydra_zen import store

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name=name)
    assert OmegaConf.is_missing(config, key)


def test_standalone_compare_exposes_shared_evaluation_defaults() -> None:
    from hydra import compose, initialize_config_module
    from hydra_zen import store

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        defaults = compose(config_name="compare")
        overridden = compose(config_name="compare", overrides=["evaluation.ap_method=continuous"])

    from clearml_yolo.comparison.scoring import EvaluationConfig

    values = OmegaConf.to_container(defaults.evaluation)
    assert isinstance(values, dict)
    values.pop("_target_")
    assert values == EvaluationConfig().model_dump()
    assert overridden.evaluation.ap_method == "continuous"


def test_unknown_inference_settings_are_rejected() -> None:
    from clearml_yolo.apps.common import validate_wrapper_keys
    from clearml_yolo.tasks.compare import compare

    config = OmegaConf.create({"inference": {"batch": 4}})
    with pytest.raises(ValueError, match="Unsupported inference settings"):
        validate_wrapper_keys(config, compare)


@pytest.mark.parametrize("key", ["model", "project", "name"])
def test_comparison_rejects_owned_prediction_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    from clearml_yolo.clearml_session import ClearMLConfig
    from clearml_yolo.tasks import compare as module

    monkeypatch.setattr(module, "init_task", lambda *a, **k: pytest.fail("created task"))
    with pytest.raises(ValueError, match="owned by comparison"):
        module.compare(
            module.ModelRef(),
            module.ModelRef(),
            "truth.csv",
            tmp_path,
            ClearMLConfig(),
            {},
            ultralytics_predict={key: "conflicting"},
        )
