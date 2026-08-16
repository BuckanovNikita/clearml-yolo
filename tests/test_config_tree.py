"""The dumped config folder must compose back into exactly the built-in defaults."""

from __future__ import annotations

from pathlib import Path

import pytest
from hydra import compose, initialize_config_dir, initialize_config_module
from hydra_zen import store
from omegaconf import OmegaConf

import clearml_yolo.configs  # noqa: F401  registers every config
from clearml_yolo.config_tree import COMMAND_OF_CONFIG, ULTRALYTICS_BLOCKS, dump_config_tree
from clearml_yolo.tasks.pipeline import PIPELINE_FILLED_KEYS


@pytest.fixture(scope="module", autouse=True)
def hydra_store() -> None:
    store.add_to_hydra_store(overwrite_ok=True)


def _header_of(path: Path) -> str:
    """The comment block a dumped file opens with, which is all a reader has to go on."""
    return "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("#")
    )


def test_one_file_per_command(tmp_path: Path) -> None:
    written = dump_config_tree(tmp_path)

    assert {path.name for path in written if path.parent == tmp_path} == {
        f"{command}.yaml" for command in COMMAND_OF_CONFIG.values()
    }


def test_the_ultralytics_parameters_are_a_folder_of_their_own(tmp_path: Path) -> None:
    """One file per stage, selectable by name, rather than a block inlined into every
    command that has one — which would be the same hundred and fifteen keys in three
    places, any two of which could disagree."""
    dump_config_tree(tmp_path)

    assert {path.name for path in (tmp_path / "ultralytics").glob("*.yaml")} == {
        "train.yaml",
        "predict.yaml",
    }
    assert "- /ultralytics@ultralytics: train" in (tmp_path / "cy-train.yaml").read_text(
        encoding="utf-8"
    )


def test_the_copied_parameters_keep_the_documentation_that_makes_them_legible(
    tmp_path: Path,
) -> None:
    """They are copied byte for byte rather than rendered: every key carries ultralytics'
    own one-line explanation, and OmegaConf would drop all of them."""
    dump_config_tree(tmp_path)
    text = (tmp_path / "ultralytics" / "train.yaml").read_text(encoding="utf-8")

    assert "# (float) initial learning rate" in text
    assert "# ---- ignored by detection training ----" in text


def test_the_pipeline_file_has_nothing_left_to_resolve(tmp_path: Path) -> None:
    """Shared values are named once at the top level and handed to stages by run_pipeline,
    so a stage block pointing at another key would be a reference nothing keeps true."""
    dump_config_tree(tmp_path)

    assert "${" not in (tmp_path / "cy.yaml").read_text(encoding="utf-8")


def test_the_dumped_pipeline_leaves_the_run_to_decide_what_the_run_decides(
    tmp_path: Path,
) -> None:
    """A dumped folder outlives the code, and a stage block in it that still carries a key
    the run now fills is not merely stale — the run overwrites it, so the value a user
    edited is silently discarded, and composition fails outright once the key is gone from
    the stage's config. The output paths are the newest of these: every one of them is
    part of the run directory now.
    """
    dump_config_tree(tmp_path)
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        dumped = compose(config_name="cy")

    for stage, filled in PIPELINE_FILLED_KEYS.items():
        assert not set(dumped[stage]) & filled, stage
    assert dumped.run_dir is None
    assert dumped.run_id is None


def test_dumped_files_explain_how_to_use_them(tmp_path: Path) -> None:
    dump_config_tree(tmp_path)

    assert "--config-dir" in (tmp_path / "cy-train.yaml").read_text(encoding="utf-8")


def test_the_pipeline_header_names_every_value_the_run_hands_to_its_stages(
    tmp_path: Path,
) -> None:
    """A short list read as the whole list is worse than no list at all: a reader who does
    not find a value among the run's own reaches for a stage's key instead, and every path
    a stage used to own is now the run's to decide and no longer composes at all. The list
    is checked against the file rather than against a copy of itself, so a value that joins
    the top level without joining the header fails here."""
    dump_config_tree(tmp_path)
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        dumped = compose(config_name="cy")
    header = _header_of(tmp_path / "cy.yaml")

    handed_to_stages = [
        str(key)
        for key in dumped
        if str(key) not in PIPELINE_FILLED_KEYS and not str(key).startswith("skip_")
    ]
    for key in handed_to_stages:
        assert key in header, key


@pytest.mark.parametrize("command", sorted(ULTRALYTICS_BLOCKS))
def test_the_group_override_a_header_prints_is_one_that_command_takes(
    tmp_path: Path, command: str
) -> None:
    """The group is mounted at the top level for a standalone app and once per stage inside
    `cy`, and Hydra refuses an override naming a key a config never mounted rather than
    ignoring it. One spelling printed in every file therefore sent most of its readers to a
    composition error, so the line is built from the same mapping that mounts the blocks and
    is composed here exactly as printed."""
    dump_config_tree(tmp_path)
    blocks = ULTRALYTICS_BLOCKS[command]
    prefix = f"#     {command} "
    printed = [
        line[len(prefix) :]
        for line in _header_of(tmp_path / f"{command}.yaml").splitlines()
        if line.startswith(prefix)
    ]

    assert len(printed) == len(blocks)
    overrides = [
        line.replace("<file-stem>", name)
        for line, name in zip(printed, blocks.values(), strict=True)
    ]
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        as_printed = compose(config_name=command, overrides=overrides)
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        untouched = compose(config_name=command)

    assert OmegaConf.to_container(as_printed, resolve=False) == OmegaConf.to_container(
        untouched, resolve=False
    )


def test_a_command_with_no_parameters_of_its_own_is_told_nothing_about_the_group(
    tmp_path: Path,
) -> None:
    """`cy-metrics` and its like compose no ultralytics block at all, so a paragraph about
    editing one and an override selecting it are both instructions the command rejects."""
    dump_config_tree(tmp_path)

    for command in set(COMMAND_OF_CONFIG.values()) - set(ULTRALYTICS_BLOCKS):
        assert "ultralytics" not in (tmp_path / f"{command}.yaml").read_text(encoding="utf-8")


@pytest.mark.parametrize(("config_name", "command"), sorted(COMMAND_OF_CONFIG.items()))
def test_folder_composes_back_to_the_built_in_defaults(
    tmp_path: Path, config_name: str, command: str
) -> None:
    """A dumped-then-loaded config is the config, or the folder is a lie.

    Compared as containers rather than as rendered YAML: the ultralytics block is lifted
    out into a defaults list, and a key that arrives through one lands at the end of the
    file rather than where it was declared. That is a difference in key order and in
    nothing else, which is not a difference in the configuration.
    """
    dump_config_tree(tmp_path)

    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        from_store = compose(config_name=config_name)
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        from_folder = compose(config_name=command)

    assert OmegaConf.to_container(from_store, resolve=False) == OmegaConf.to_container(
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
