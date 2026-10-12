"""Selected detector configuration composes without native SDK initialization."""

from pathlib import Path

import pytest
from hydra import compose, initialize_config_dir, initialize_config_module
from hydra.core.global_hydra import GlobalHydra
from hydra.types import RunMode
from hydra_zen import store
from omegaconf import OmegaConf

from clearml_yolo.application.use_cases.predict import predict
from clearml_yolo.application.use_cases.train import train
from clearml_yolo.core.models import PRESETS
from clearml_yolo.entrypoints.hydra.config_tree import dump_config_tree
from clearml_yolo.entrypoints.hydra.validation import validate_wrapper_keys


@pytest.mark.parametrize(
    "selection",
    [
        f"{backend}/{preset}"
        for backend, presets in PRESETS.items()
        if backend != "ultralytics"
        for preset in presets
    ],
)
def test_model_group_selects_typed_settings_before_training(selection: str) -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="train",
            overrides=[f"model={selection}", "model.train.device=cpu", "ground_truth=truth.csv"],
        )
    validate_wrapper_keys(config, train)
    assert config.model.backend == selection.split("/", maxsplit=1)[0]
    assert config.model.train.device == "cpu"


def test_selected_model_export_contains_only_required_groups(tmp_path: Path) -> None:
    paths = dump_config_tree(tmp_path, command="cy-train", model="rfdetr/small")
    assert {path.relative_to(tmp_path).as_posix() for path in paths} == {
        "cy-train.yaml",
        "model/rfdetr/small.yaml",
    }
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        config = compose(config_name="cy-train", overrides=["model.train.epochs=2"])
    assert config.model.backend == "rfdetr"
    assert config.model.train.epochs == 2


def test_unknown_native_setting_rejected_before_training() -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="train", overrides=["model=rfdetr/small", "+model.train.epohs=2"]
        )
    with pytest.raises(ValueError, match="epohs"):
        validate_wrapper_keys(config, train)


@pytest.mark.parametrize(
    "override",
    [
        "ultralytics.epochs=2",
        "ultralytics.device=cpu",
        "ultralytics_predict.conf=0.9",
        "ultralytics_predict.classes=[0]",
    ],
)
def test_native_selection_rejects_changed_inactive_yolo_groups(override: str) -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="train", overrides=["model=rfdetr/small", override])
    with pytest.raises(ValueError, match=r"inactive.*model\.(train|predict)"):
        validate_wrapper_keys(config, train)


@pytest.mark.parametrize("queued", [True, False])
def test_initial_mixed_model_multirun_accepts_native_overrides(
    monkeypatch: pytest.MonkeyPatch, queued: bool
) -> None:
    selections = ("deimv2/s", "rfdetr/nano", "fasterrcnn/resnet50_fpn")
    resolutions = {"deimv2": 128, "rfdetr": 64, "fasterrcnn": 128}
    for backend, resolution in resolutions.items():
        monkeypatch.setenv(f"CY_TEST_IMGSZ_{backend}", str(resolution))
    monkeypatch.setenv("CY_TEST_SOURCE_deimv2", "/native/deimv2")
    overrides = [
        "ground_truth=truth.csv",
        f"queue.enabled={str(queued).lower()}",
        'model.source_dir="${oc.env:CY_TEST_SOURCE_${model.backend},null}"',
        'model.train.imgsz="${oc.decode:${oc.env:CY_TEST_IMGSZ_${model.backend}}}"',
        'model.predict.imgsz="${oc.decode:${oc.env:CY_TEST_IMGSZ_${model.backend}}}"',
        "model.predict.device=cpu",
        "model.predict.batch=2",
        "model.predict.conf=0.001",
        "model.predict.half=false",
    ]
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        loader = GlobalHydra.instance().config_loader()
        initial = loader.load_configuration(
            config_name="predict",
            overrides=[f"model={','.join(selections)}", *overrides],
            run_mode=RunMode.MULTIRUN,
        )
        # Hydra composes this default-model root before expanding group choices.
        assert initial.model.backend == "ultralytics"
        assert {"source_dir", "train", "predict"} <= set(initial.model)
        assert initial.model.predict.device == "cpu"
        for selection in selections:
            expanded = loader.load_sweep_config(initial, [f"model={selection}", *overrides])
            job = OmegaConf.masked_copy(expanded, [str(key) for key in expanded if key != "hydra"])
            validate_wrapper_keys(job, predict)
            backend, preset = selection.split("/")
            assert job.model.backend == backend
            assert job.model.preset == preset
            assert job.model.predict.imgsz == resolutions[backend]
            assert job.model.train.imgsz == resolutions[backend]
            assert job.model.predict.device == "cpu"
            assert job.model.predict.batch == 2
            assert job.model.source_dir == ("/native/deimv2" if backend == "deimv2" else None)


def test_default_model_schema_preserves_authoritative_yolo_settings() -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="train",
            overrides=["ultralytics.epochs=2", "ultralytics_predict.batch=8"],
        )
    validate_wrapper_keys(config, train)
    assert config.model.backend == "ultralytics"
    assert config.ultralytics.epochs == 2
    assert config.ultralytics_predict.batch == 8
    assert config.ultralytics_predict.imgsz == 960


@pytest.mark.parametrize("selection", ["ultralytics", "rfdetr/nano"])
@pytest.mark.parametrize("override", ["+model.predict.conff=0.5", "model.predict.batch=0"])
def test_full_model_schema_retains_native_setting_validation(selection: str, override: str) -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="predict", overrides=[f"model={selection}", override])
    with pytest.raises(ValueError, match=r"conff|batch"):
        validate_wrapper_keys(config, predict)


@pytest.mark.parametrize(
    ("override", "owner"),
    [
        ("model.train.epochs=2", "ultralytics"),
        ("model.train.device=cpu", "ultralytics"),
        ("model.predict.conf=0.9", "ultralytics_predict"),
        ("model.predict.device=cpu", "ultralytics_predict"),
    ],
)
def test_yolo_rejects_changed_inactive_model_settings(override: str, owner: str) -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="train", overrides=[override])
    # These accepted model values would otherwise leave native YOLO settings unchanged.
    assert config.ultralytics.epochs == 100
    assert config.ultralytics_predict.conf == 0.001
    assert config.ultralytics_predict.device == [-1]
    with pytest.raises(ValueError, match=rf"inactive.*use {owner} instead"):
        validate_wrapper_keys(config, train)


def test_yolo_accepts_unchanged_model_defaults_with_ordinary_native_overrides() -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="train",
            overrides=[
                "model.train.epochs=100",
                "model.train.imgsz=640",
                "model.predict.device=null",
                "model.predict.conf=0.001",
                "ultralytics.epochs=2",
                "ultralytics_predict.device=cpu",
                "ultralytics_predict.conf=0.9",
            ],
        )
    validate_wrapper_keys(config, train)
    assert config.ultralytics.epochs == 2
    assert config.ultralytics_predict.device == "cpu"
    assert config.ultralytics_predict.conf == 0.9
