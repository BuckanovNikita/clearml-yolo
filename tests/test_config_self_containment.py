"""Exported trees carry application defaults without implicit schema matching."""

import subprocess
import sys
import warnings
from pathlib import Path

import pytest
from hydra import compose, initialize_config_dir, initialize_config_module
from omegaconf import OmegaConf

from clearml_yolo.core.models import PRESETS
from clearml_yolo.entrypoints.hydra.config_tree import COMMAND_OF_CONFIG, dump_config_tree
from clearml_yolo.entrypoints.hydra.configs import NATIVE_COMMANDS, ApplicationSearchPath
from clearml_yolo.entrypoints.hydra.validation import validate_pipeline_configuration

SELECTIONS = [
    "ultralytics" if backend == "ultralytics" else f"{backend}/{preset}"
    for backend, presets in PRESETS.items()
    for preset in presets
]
COMMAND_MODELS = [
    (config, command, selection)
    for config, command in COMMAND_OF_CONFIG.items()
    for selection in (SELECTIONS if config in NATIVE_COMMANDS else ["ultralytics"])
    if config != "export" or selection.startswith("fasterrcnn/")
]


def test_export_contains_editable_command_base(tmp_path: Path) -> None:
    dump_config_tree(tmp_path, model="fasterrcnn/resnet50_fpn")
    base = tmp_path / "pipeline.yaml"
    assert base.is_file(), "The wrapper's pipeline default must be exported locally"
    values = OmegaConf.load(base)
    assert values.skip_train is False
    assert list(values.splits) == ["train", "val", "test"]


@pytest.mark.parametrize("profile", ["default", "albumentations"])
@pytest.mark.parametrize("selection", ["ultralytics", "fasterrcnn/resnet50_fpn"])
def test_export_composes_without_schema_matching_warnings(
    tmp_path: Path, profile: str, selection: str
) -> None:
    dump_config_tree(tmp_path, model=selection)
    with (
        warnings.catch_warnings(),
        initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"),
    ):
        warnings.filterwarnings("error", message="(?s).*validated against ConfigStore schema.*")
        config = compose(config_name="cy", overrides=[f"transforms={profile}"])
    assert config.model.backend == selection.split("/", maxsplit=1)[0]
    assert config.transforms.mode == ("native" if profile == "default" else "albumentations")


@pytest.mark.parametrize(("name", "command", "selection"), COMMAND_MODELS)
def test_every_export_composes_with_packaged_application_defaults_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    command: str,
    selection: str,
) -> None:
    """Missing any selected YAML dependency fails when the fallback cannot hide it."""
    with warnings.catch_warnings():
        warnings.filterwarnings("error", message="(?s).*validated against ConfigStore schema.*")
        dump_config_tree(tmp_path, command=command, model=selection)
        profiles = ("default", "albumentations") if name in {"train", "pipeline"} else (None,)
        for profile in profiles:
            overrides = [f"transforms={profile}"] if profile else []
            model = [f"model={selection}"] if name in NATIVE_COMMANDS else []
            with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
                baseline = compose(config_name=name, overrides=[*model, *overrides])
            with monkeypatch.context() as isolated:
                isolated.setattr(ApplicationSearchPath, "manipulate_search_path", lambda *_: None)
                with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
                    exported = compose(config_name=command, overrides=overrides)
            assert OmegaConf.to_container(exported, resolve=False) == OmegaConf.to_container(
                baseline, resolve=False
            )


@pytest.mark.parametrize("selection", ["ultralytics", "rfdetr/small"])
def test_legacy_generated_tree_uses_packaged_base_without_rewriting(
    tmp_path: Path, selection: str
) -> None:
    dump_config_tree(tmp_path, command="cy-train", model=selection)
    # These files were absent from the preceding exporter. Its wrapper and full
    # group documents are unchanged, so removing only the additions gives its tree.
    (tmp_path / "train.yaml").unlink()
    (tmp_path / "ultralytics/_defaults.yaml").unlink()
    (tmp_path / "ultralytics_predict/_defaults.yaml").unlink()
    if selection == "ultralytics":
        (tmp_path / "model/ultralytics.yaml").unlink()
        group = tmp_path / "ultralytics/default.yaml"
    else:
        group = tmp_path / "model/rfdetr/small.yaml"
    document = OmegaConf.load(group)
    if selection == "ultralytics":
        document.epochs = 17
    else:
        document.train.epochs = 17
    OmegaConf.save(document, group)
    original = {path: path.read_bytes() for path in tmp_path.rglob("*.yaml")}
    with (
        warnings.catch_warnings(),
        initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"),
    ):
        warnings.filterwarnings("error", message="(?s).*validated against ConfigStore schema.*")
        config = compose(config_name="cy-train", overrides=["ground_truth=truth.csv"])
    assert config.ground_truth == "truth.csv"
    assert (config.ultralytics if selection == "ultralytics" else config.model.train).epochs == 17
    assert {path: path.read_bytes() for path in tmp_path.rglob("*.yaml")} == original


@pytest.mark.parametrize("bad_value", ["clearml.tags=3", "skip_train=perhaps"])
def test_export_preserves_explicit_command_schema_validation(
    tmp_path: Path, bad_value: str
) -> None:
    dump_config_tree(tmp_path)
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        config = compose(config_name="cy", overrides=["ground_truth=truth.csv", bad_value])
    field = bad_value.split("=", maxsplit=1)[0].rsplit(".", maxsplit=1)[-1]
    with pytest.raises(ValueError, match=field):
        validate_pipeline_configuration(config)


def test_command_base_collision_prevents_any_export_write(tmp_path: Path) -> None:
    base = tmp_path / "pipeline.yaml"
    base.write_text("# User's existing base\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="--force"):
        dump_config_tree(tmp_path)
    assert list(tmp_path.iterdir()) == [base]
    assert base.read_text(encoding="utf-8") == "# User's existing base\n"


def test_cli_local_group_precedes_packaged_defaults(tmp_path: Path) -> None:
    """Hydra adds --config-dir after plugins, so CLI precedence needs explicit ownership."""
    dump_config_tree(tmp_path, command="cy-train", model="rfdetr/small")
    model_path = tmp_path / "model/rfdetr/small.yaml"
    model = OmegaConf.load(model_path)
    model.train.epochs = 23
    OmegaConf.save(model, model_path)
    script = """
from clearml_yolo.entrypoints.hydra import common
def show_local(name, config, function):
    print('LOCAL_EPOCHS=' + str(config.model.train.epochs))
common.execute_owned = show_local
common.launch('train', lambda: None)
"""
    result = subprocess.run(  # noqa: S603 - fixed inert launcher and isolated configuration
        [
            sys.executable,
            "-c",
            script,
            "--config-dir",
            str(tmp_path),
            "--config-name",
            "cy-train",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "LOCAL_EPOCHS=23" in result.stdout
