"""Compose product configuration for native training scenarios."""

from pathlib import Path

import pytest

from severstal_harness import (
    MODEL_SELECTIONS,
    SeverstalOptions,
    parse_backbone_options,
    scenario_overrides,
)

ROOT = Path(__file__).resolve().parents[1]
with pytest.MonkeyPatch.context() as import_path:
    import_path.syspath_prepend(str(ROOT))


@pytest.mark.parametrize(
    "selection",
    [
        "deimv2/l",
        "fasterrcnn/dinov3_small",
        *(s for s in MODEL_SELECTIONS if s.startswith("fcos/")),
    ],
)
@pytest.mark.parametrize("variant", ["default", "json", "json_mosaic"])
def test_backbone_override_composes_only_for_matching_selection(tmp_path: Path, selection: str, variant: str) -> None:
    from hydra import compose, initialize_config_module
    from hydra_zen import store

    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401 - config registration

    path = tmp_path / "backbone = local.pt"
    path.write_bytes(b"checkpoint")
    options = SeverstalOptions(
        tmp_path,
        tmp_path,
        "acceptance",
        ("owned",),
        backbone_weights=parse_backbone_options([f"{selection}={path}"]),
    )
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=scenario_overrides(options, tmp_path, selection, variant, "native-smoke"),
        )
    assert Path(config.model.train.backbone_weights) == path.resolve()
    assert config.model.train.pretrained is True
    assert config.transforms.mode == ("native" if variant == "default" else "albumentations")


@pytest.mark.parametrize("selection", MODEL_SELECTIONS)
@pytest.mark.parametrize("variant", ["default", "json_mosaic"])
def test_native_scenario_composes(selection: str, variant: str, tmp_path: Path) -> None:
    from hydra import compose, initialize_config_module
    from hydra_zen import store

    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401 - fresh-process config registration

    options = SeverstalOptions(tmp_path, tmp_path, "acceptance", ("owned",))
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=scenario_overrides(options, tmp_path, selection, variant, "native-smoke"),
        )
    assert config.splits == ["val", "test"]
    settings = config.ultralytics if selection == "ultralytics" else config.model.train
    assert settings.epochs == 1
    assert settings.batch == 1
    assert settings.seed == 0
    assert settings.amp is False
