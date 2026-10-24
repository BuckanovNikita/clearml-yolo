"""Training profiles expose native replacements and freeze portable pipelines."""

import json
from pathlib import Path

import pytest
from hydra import compose, initialize_config_dir, initialize_config_module
from hydra_zen import store

from clearml_yolo.application.use_cases.train import train
from clearml_yolo.core.models import PRESETS
from clearml_yolo.entrypoints.hydra.config_tree import dump_config_tree
from clearml_yolo.entrypoints.hydra.validation import validate_wrapper_keys

SELECTIONS = [
    "ultralytics" if backend == "ultralytics" else f"{backend}/{preset}"
    for backend, presets in PRESETS.items()
    for preset in presets
]


def _pipeline(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "__version__": "2.0.8",
                "transform": {
                    "__class_fullname__": "Compose",
                    "p": 1.0,
                    "transforms": [{"__class_fullname__": "HorizontalFlip", "p": 1.0}],
                },
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize("selection", SELECTIONS)
def test_custom_profile_is_visible_and_freezes_file(selection: str, tmp_path: Path) -> None:
    pipeline = tmp_path / "pipeline.json"
    _pipeline(pipeline)
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="train",
            overrides=[
                f"model={selection}",
                "transforms=albumentations",
                f"transforms.pipeline_file={pipeline}",
                "ground_truth=truth.csv",
            ],
        )
    if selection == "ultralytics":
        assert config.ultralytics.hsv_v == 0
        assert config.ultralytics.mosaic == 0
        assert config.ultralytics.multi_scale == 0
    elif selection.startswith("rfdetr"):
        assert config.model.train.augmentation.multi_scale == "off"
    elif selection.startswith("deim"):
        assert config.model.train.augmentation.mixup_prob == 0
    else:
        assert config.model.train.augmentation == {}
    validate_wrapper_keys(config, train)
    assert len(config.transforms.snapshot.sha256) == 64
    pipeline.unlink()
    validate_wrapper_keys(config, train)
    assert config.transforms.snapshot.pipeline.transform.transforms[0].p == 1.0


def test_default_profile_retains_native_augmentation() -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="train")
    assert config.transforms.mode == "native"
    assert config.ultralytics.hsv_v > 0
    assert config.ultralytics.mosaic > 0


def test_custom_profile_overrides_competing_native_settings(tmp_path: Path) -> None:
    pipeline = tmp_path / "pipeline.json"
    _pipeline(pipeline)
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="train",
            overrides=[
                "transforms=albumentations",
                f"transforms.pipeline_file={pipeline}",
                "ultralytics.fliplr=1",
                "ultralytics.mosaic=1",
                "ground_truth=truth.csv",
            ],
        )
    validate_wrapper_keys(config, train)
    assert config.ultralytics.fliplr == 0
    assert config.ultralytics.mosaic == 0


@pytest.mark.parametrize("selection", ["ultralytics", "rfdetr/nano"])
def test_exported_profiles_can_switch_without_wrapper_shadowing(
    selection: str, tmp_path: Path
) -> None:
    pipeline = tmp_path / "pipeline.json"
    _pipeline(pipeline)
    folder = tmp_path / "config"
    dump_config_tree(folder, command="cy-train", model=selection)
    with initialize_config_dir(config_dir=str(folder), version_base="1.3"):
        config = compose(
            config_name="cy-train",
            overrides=["transforms=albumentations", f"transforms.pipeline_file={pipeline}"],
        )
    assert config.transforms.mode == "albumentations"
    if selection == "ultralytics":
        assert config.ultralytics.hsv_v == 0
    else:
        assert config.model.train.augmentation.scale_jitter is False


@pytest.mark.parametrize(
    "selection", ["ultralytics", "deimv2/s", "rfdetr/nano", "fasterrcnn/resnet50_fpn"]
)
def test_canonical_agent_replay_preserves_pipeline_without_local_file(
    selection: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.clearml.session import RemoteReplay
    from clearml_yolo.entrypoints.hydra import common

    pipeline = tmp_path / "pipeline.json"
    _pipeline(pipeline)
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        original = compose(
            config_name="train",
            overrides=[
                f"model={selection}",
                "transforms=albumentations",
                f"transforms.pipeline_file={pipeline}",
                "ground_truth=truth.csv",
            ],
        )
        replay = compose(config_name="train")
    validate_wrapper_keys(original, train)
    canonical = common._publication_inputs(original)
    digest = canonical["transforms"]["snapshot"]["sha256"]
    pipeline.unlink()
    snapshot = RemoteReplay("remote-task", canonical, {})
    monkeypatch.setattr(common, "fetch_remote_replay", lambda: snapshot)
    common._restore_agent_inputs(replay, train)
    validate_wrapper_keys(replay, train)
    assert replay.transforms.snapshot.sha256 == digest
    assert replay.transforms.snapshot.pipeline == original.transforms.snapshot.pipeline
    assert replay.model.backend == original.model.backend


def test_new_file_selection_replaces_replayed_snapshot(tmp_path: Path) -> None:
    from omegaconf import OmegaConf

    from clearml_yolo.core.models import model_preset
    from clearml_yolo.entrypoints.hydra.transforms import prepare_transforms

    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    _pipeline(first)
    second.write_text(
        first.read_text(encoding="utf-8").replace("HorizontalFlip", "VerticalFlip"),
        encoding="utf-8",
    )
    config = OmegaConf.create(
        {
            "model": model_preset("rfdetr/nano").model_dump(mode="json"),
            "transforms": {"mode": "albumentations", "pipeline_file": str(first)},
        }
    )
    original = prepare_transforms(config)
    config.transforms.pipeline_file = str(second)
    replacement = prepare_transforms(config)
    assert replacement.snapshot is not None
    assert original.snapshot is not None
    assert replacement.snapshot.sha256 != original.snapshot.sha256
    assert replacement.snapshot.source == str(second)


def test_custom_profile_rejects_unknown_native_augmentation_field(tmp_path: Path) -> None:
    pipeline = tmp_path / "pipeline.json"
    _pipeline(pipeline)
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="train",
            overrides=[
                "model=rfdetr/nano",
                "transforms=albumentations",
                f"transforms.pipeline_file={pipeline}",
                "+model.train.augmentation.mutli_scale=off",
            ],
        )
    with pytest.raises(ValueError, match="mutli_scale"):
        validate_wrapper_keys(config, train)
