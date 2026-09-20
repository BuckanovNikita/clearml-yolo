"""Configuration provenance must preserve explicit native defaults."""

from __future__ import annotations

from pathlib import Path

import pytest
from omegaconf import OmegaConf

from clearml_yolo.configs import overlay_ultralytics_files


def test_explicit_default_beats_raw_yaml(tmp_path: Path) -> None:
    raw = tmp_path / "native.yaml"
    raw.write_text("epochs: 3\nbatch: 2\n")
    config = OmegaConf.create({"cfg": str(raw), "ultralytics": {"epochs": 100}})
    overlay_ultralytics_files("train")(config)
    assert dict(config.ultralytics) == {"epochs": 100, "batch": 2}


def test_raw_yaml_is_not_limited_by_packaged_parameter_list(tmp_path: Path) -> None:
    raw = tmp_path / "native.yaml"
    raw.write_text("task: detect\nmode: train\nepochs: 1\n")
    config = OmegaConf.create({"cfg": str(raw), "ultralytics": {}})
    overlay_ultralytics_files("train")(config)
    assert dict(config.ultralytics) == {"task": "detect", "mode": "train", "epochs": 1}


def test_raw_sequence_is_rejected(tmp_path: Path) -> None:
    raw = tmp_path / "native.yaml"
    raw.write_text("- epochs\n")
    config = OmegaConf.create({"cfg": str(raw), "ultralytics": {}})
    with pytest.raises(ValueError, match="mapping"):
        overlay_ultralytics_files("train")(config)


@pytest.mark.parametrize("key", ["auto_gpu", "augmentations", "force_gpu", "enabled"])
def test_added_removed_wrapper_keys_are_not_silently_ignored(key: str) -> None:
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


def test_file_backed_hydra_mapping_and_cli_preserve_precedence(tmp_path: Path) -> None:
    from hydra import compose, initialize_config_dir
    from hydra_zen import store

    raw = tmp_path / "native.yaml"
    raw.write_text("epochs: 3\nbatch: 2\n")
    (tmp_path / "experiment.yaml").write_text(
        "defaults:\n  - pipeline\n  - _self_\n"
        f"train:\n  cfg: {raw}\n  ultralytics:\n    epochs: 100\n"
    )
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        embedded = compose(config_name="experiment")
        overridden = compose(config_name="experiment", overrides=["train.ultralytics.epochs=1"])
    overlay_ultralytics_files("pipeline")(embedded)
    overlay_ultralytics_files("pipeline")(overridden)
    assert dict(embedded.train.ultralytics) == {"epochs": 100, "batch": 2}
    assert dict(overridden.train.ultralytics) == {"epochs": 1, "batch": 2}


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("pipeline", "ground_truth"),
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


def test_standalone_compare_exposes_a_sparse_evaluation_mapping() -> None:
    from hydra import compose, initialize_config_module
    from hydra_zen import store

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        defaults = compose(config_name="compare")
        overridden = compose(
            config_name="compare", overrides=["+evaluation.ap_method=continuous"]
        )

    assert OmegaConf.to_container(defaults.evaluation) == {}
    assert overridden.evaluation.ap_method == "continuous"


def test_native_source_connection_controls_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from hydra.core.hydra_config import HydraConfig

    from clearml_yolo.apps import common

    original = tmp_path / "original.yaml"
    override = tmp_path / "override.yaml"
    override.write_text("epochs: 2\nbatch: 4\n")
    config = OmegaConf.create({"cfg": str(original), "ultralytics": {"epochs": 100}})
    monkeypatch.setattr(common, "connect_config_file", lambda *args: override)
    monkeypatch.setattr(
        HydraConfig,
        "get",
        lambda: SimpleNamespace(
            job=SimpleNamespace(config_name="train"),
            runtime=SimpleNamespace(choices={}, config_sources=[]),
        ),
    )
    common._sources(config, "train", object())
    overlay_ultralytics_files("train")(config)
    assert dict(config.ultralytics) == {"epochs": 100, "batch": 4}
