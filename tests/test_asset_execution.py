"""Asset preparation changes execution copies and separate provenance, never replay inputs."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from omegaconf import OmegaConf

from clearml_yolo.adapters.clearml import session
from clearml_yolo.core.assets import ResolvedAsset
from clearml_yolo.core.models import ModelConfig, model_preset
from clearml_yolo.entrypoints.hydra import common


def test_execution_copy_preserves_null_selectors_and_publishes_separate_provenance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    original = model_preset("fasterrcnn/resnet50_fpn").model_dump(mode="json")
    config = OmegaConf.create({"model": original, "clearml": {}})
    writes: dict[str, Any] = {}
    task = SimpleNamespace(
        set_configuration_object=lambda **values: writes.update(
            {values["name"]: values["config_text"]}
        )
    )
    state = session._InvocationState(task=task, stages=["train"], current_stage="train")
    token = session._ACTIVE_INVOCATION.set(state)
    weights = tmp_path / "resolved.pth"
    record = ResolvedAsset(
        canonical_url="https://weights.example/backbone.pth",
        path=weights,
        sha256="a" * 64,
        override="model.train.backbone_weights",
    )

    def prepare(
        selected: ModelConfig, *, training: bool
    ) -> tuple[ModelConfig, tuple[ResolvedAsset, ...]]:
        assert training
        assert state.run_configuration["model"]["train"]["backbone_weights"] is None
        prepared = selected.model_copy(deep=True)
        prepared.train.backbone_weights = weights
        return prepared, (record,)

    monkeypatch.setattr(common, "prepare_model_assets", prepare)
    try:
        session.publish_run_configuration(task, {"model": original}, {"model": original})
        saved = deepcopy(state.run_configuration)
        prepared = common._execution_model("train", config)
        session.publish_model_assets(task, (record,))
    finally:
        session._ACTIVE_INVOCATION.reset(token)
    assert prepared.train.backbone_weights == weights
    assert OmegaConf.to_container(config.model) == original
    assert state.run_configuration == saved
    assert "model_assets" not in state.run_configuration
    assert len(state.model_assets) == 1
    assert set(writes) == {"run", "run_overrides", "model_assets"}


@pytest.mark.parametrize("command", ["predict", "val", "compare", "export", "pipeline"])
def test_nontraining_execution_does_not_request_pretrained_assets(
    monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    observed: list[bool] = []

    def prepare(
        selected: ModelConfig, *, training: bool
    ) -> tuple[ModelConfig, tuple[ResolvedAsset, ...]]:
        observed.append(training)
        return selected, ()

    monkeypatch.setattr(common, "prepare_model_assets", prepare)
    config = OmegaConf.create(
        {"model": model_preset("deimv2/s").model_dump(mode="json"), "skip_train": True}
    )
    common._execution_model(command, config)
    assert observed == [False]


def test_late_asset_provenance_retains_earlier_model_assets(tmp_path: Path) -> None:
    writes: list[str] = []
    task = SimpleNamespace(set_configuration_object=lambda **values: writes.append(values["name"]))
    state = session._InvocationState(task=task, stages=["pipeline"], current_stage="compare")
    token = session._ACTIVE_INVOCATION.set(state)
    records = tuple(
        ResolvedAsset(
            canonical_url=f"https://weights.example/{name}",
            path=tmp_path / name,
            sha256="a" * 64,
            override="model.source_dir",
        )
        for name in ("candidate.pth", "baseline.tar.gz")
    )
    try:
        for record in records:
            session.publish_model_assets(task, (record,))
    finally:
        session._ACTIVE_INVOCATION.reset(token)
    assert tuple(state.model_assets.values()) == records
    assert writes == ["model_assets", "model_assets"]
    assert not state.run_configuration
