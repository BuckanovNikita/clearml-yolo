"""Distributed runtime configuration composes without devices or live services."""

from pathlib import Path

import pytest
from hydra import compose, initialize_config_dir, initialize_config_module
from hydra_zen import store

import clearml_yolo.entrypoints.hydra.configs  # noqa: F401 - register product configurations


@pytest.mark.parametrize("selection", ["deimv2/s", "rfdetr/nano", "fasterrcnn/resnet50_fpn", "fcos/resnet50_fpn"])
def test_native_public_command_composes_without_execution(selection: str) -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=[
                f"model={selection}",
                "model.train.batch=4",
                "model.train.device=[0,1]",
                "model.train.pretrained=false",
            ],
        )
    assert f"{config.model.backend}/{config.model.preset}" == selection
    assert config.model.train.batch == 4
    assert config.model.train.device == [0, 1]
    assert config.model.train.pretrained is False


def test_file_backed_yolo_config_preserves_native_training_settings(tmp_path: Path) -> None:
    (tmp_path / "distributed.yaml").write_text(
        "defaults: [pipeline, _self_]\nultralytics:\n  pretrained: false\n  device: [0, 1]\n  batch: 8\n",
        encoding="utf-8",
    )
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        config = compose(config_name="distributed")
    assert config.ultralytics.pretrained is False
    assert config.ultralytics.device == [0, 1]
    assert config.ultralytics.batch == 8
