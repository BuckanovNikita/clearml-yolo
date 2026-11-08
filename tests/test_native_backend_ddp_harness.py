"""Compose product configuration for native distributed training."""

from pathlib import Path

import pytest

from ddp_gpu_harness import GPUOptions
from native_backend_ddp_harness import (
    SELECTIONS,
    pipeline_arguments,
    request_document,
)


@pytest.mark.parametrize("selection", SELECTIONS)
def test_native_public_command_composes_without_execution(tmp_path: Path, selection: str) -> None:
    from hydra import compose, initialize_config_module
    from hydra_zen import store

    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401

    request = request_document(GPUOptions("0,1", "owned", tmp_path), selection, "none")
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline", overrides=pipeline_arguments(tmp_path, request)[3:])
    assert f"{config.model.backend}/{config.model.preset}" == selection
    assert config.model.train.batch == 4
    assert config.model.train.device == [0, 1]
    assert config.model.train.pretrained is False
