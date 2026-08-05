"""The dumped config folder must compose back into exactly the built-in defaults."""

from __future__ import annotations

from pathlib import Path

import pytest
from hydra import compose, initialize_config_dir, initialize_config_module
from hydra_zen import store
from omegaconf import OmegaConf

import clearml_yolo.configs  # noqa: F401  registers every config
from clearml_yolo.config_tree import COMMAND_OF_CONFIG, dump_config_tree

INTERPOLATED = "${clearml.project_name}"


@pytest.fixture(scope="module", autouse=True)
def hydra_store() -> None:
    store.add_to_hydra_store(overwrite_ok=True)


def test_one_file_per_command(tmp_path: Path) -> None:
    written = dump_config_tree(tmp_path)

    assert {path.name for path in written} == {
        f"{command}.yaml" for command in COMMAND_OF_CONFIG.values()
    }


def test_interpolations_are_dumped_unresolved(tmp_path: Path) -> None:
    """Resolving them would freeze today's project name and break one-name-per-run."""
    dump_config_tree(tmp_path)

    assert INTERPOLATED in (tmp_path / "cy.yaml").read_text(encoding="utf-8")


def test_dumped_files_explain_how_to_use_them(tmp_path: Path) -> None:
    dump_config_tree(tmp_path)

    assert "--config-dir" in (tmp_path / "cy-train.yaml").read_text(encoding="utf-8")


@pytest.mark.parametrize("config_name,command", sorted(COMMAND_OF_CONFIG.items()))
def test_folder_composes_back_to_the_built_in_defaults(
    tmp_path: Path, config_name: str, command: str
) -> None:
    """A dumped-then-loaded config is the config, or the folder is a lie."""
    dump_config_tree(tmp_path)

    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        from_store = compose(config_name=config_name)
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        from_folder = compose(config_name=command)

    assert OmegaConf.to_yaml(from_store, resolve=False) == OmegaConf.to_yaml(
        from_folder, resolve=False
    )


def test_dumped_names_never_collide_with_the_store(tmp_path: Path) -> None:
    """Hydra dropped automatic schema matching: a same-named file is an error, not a merge."""
    dump_config_tree(tmp_path)
    registered = {entry["name"] for entry in store if entry["group"] is None}

    assert not registered & {path.stem for path in tmp_path.glob("*.yaml")}


def test_existing_files_are_not_silently_replaced(tmp_path: Path) -> None:
    dump_config_tree(tmp_path)
    (tmp_path / "cy.yaml").write_text("epochs: mine", encoding="utf-8")

    with pytest.raises(FileExistsError, match="--force"):
        dump_config_tree(tmp_path)

    assert (tmp_path / "cy.yaml").read_text(encoding="utf-8") == "epochs: mine"
    dump_config_tree(tmp_path, overwrite=True)
    assert (tmp_path / "cy.yaml").read_text(encoding="utf-8") != "epochs: mine"
