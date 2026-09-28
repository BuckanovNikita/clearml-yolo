"""Generated examples must compose and preserve existing user files."""

from importlib.metadata import distribution
from pathlib import Path

import pytest
from hydra import compose, initialize_config_dir, initialize_config_module
from omegaconf import OmegaConf

COMMANDS = {
    "cy": "pipeline",
    "cy-train": "train",
    "cy-predict": "predict",
    "cy-val": "val",
    "cy-metrics": "metrics",
    "cy-report": "report",
    "cy-compare": "compare",
    "cy-ground-truth": "ground_truth",
}


def test_installed_command_creates_examples(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entrypoints = [
        entry
        for entry in distribution("clearml-yolo").entry_points
        if entry.group == "console_scripts" and entry.name == "cy-init-config"
    ]
    assert len(entrypoints) == 1, "cy-init-config must be installed as a console command"
    target = tmp_path / "nested" / "example configs"
    monkeypatch.setattr("sys.argv", ["cy-init-config", str(target)])
    entrypoints[0].load()()
    assert {path.name for path in target.iterdir()} == {
        f"{command}.yaml" for command in COMMANDS
    }


@pytest.mark.parametrize(("command", "config_name"), COMMANDS.items())
def test_examples_round_trip_through_hydra(
    tmp_path: Path, command: str, config_name: str
) -> None:
    from clearml_yolo.config_tree import dump_config_tree

    dump_config_tree(tmp_path)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        builtin = compose(config_name=config_name)
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        example = compose(config_name=command)
    assert OmegaConf.to_container(example) == OmegaConf.to_container(builtin)


def test_generated_pipeline_accepts_inputs_and_native_overrides(tmp_path: Path) -> None:
    from clearml_yolo.config_tree import dump_config_tree

    dump_config_tree(tmp_path)
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        config = compose(
            config_name="cy",
            overrides=[
                "ground_truth=truth.csv",
                "run_dir=runs/example",
                "+train.ultralytics.data=data.yaml",
                "+train.ultralytics.epochs=2",
                "+predict.ultralytics.device=cpu",
            ],
        )
    assert config.ground_truth == "truth.csv"
    assert config.run_dir == "runs/example"
    assert dict(config.train.ultralytics) == {"data": "data.yaml", "epochs": 2}
    assert dict(config.predict.ultralytics) == {"device": "cpu"}
    assert not OmegaConf.missing_keys(config)


def test_existing_config_prevents_all_writes(tmp_path: Path) -> None:
    from clearml_yolo.config_tree import dump_config_tree

    existing = tmp_path / "cy-ground-truth.yaml"
    existing.write_text("# My edited config\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="--force"):
        dump_config_tree(tmp_path)
    assert existing.read_text(encoding="utf-8") == "# My edited config\n"
    assert list(tmp_path.iterdir()) == [existing]


def test_force_replaces_examples_and_preserves_unrelated_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.apps.config_tree import main

    example = tmp_path / "cy.yaml"
    example.write_text("# Old example\n", encoding="utf-8")
    unrelated = tmp_path / "experiment.yaml"
    unrelated.write_text("# Keep me\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["cy-init-config", str(tmp_path), "--force"])
    main()
    assert OmegaConf.is_missing(OmegaConf.load(example), "ground_truth")
    assert unrelated.read_text(encoding="utf-8") == "# Keep me\n"


def test_cli_reports_write_errors_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from clearml_yolo.apps.config_tree import main

    target = tmp_path / "file"
    target.write_text("existing data", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["cy-init-config", str(target)])
    with pytest.raises(SystemExit) as caught:
        main()
    assert caught.value.code == 2
    assert "error:" in capsys.readouterr().err
    assert target.read_text(encoding="utf-8") == "existing data"


def test_dangling_symlink_is_not_followed(tmp_path: Path) -> None:
    from clearml_yolo.config_tree import dump_config_tree

    external = tmp_path / "external.yaml"
    target = tmp_path / "configs"
    target.mkdir()
    (target / "cy.yaml").symlink_to(external)
    with pytest.raises(FileExistsError, match="--force"):
        dump_config_tree(target)
    assert not external.exists()


@pytest.mark.parametrize("destination_kind", ["directory", "symlink", "dangling_symlink"])
def test_force_rejects_nonregular_destinations_before_writing(
    tmp_path: Path, destination_kind: str
) -> None:
    from clearml_yolo.config_tree import dump_config_tree

    target = tmp_path / "configs"
    target.mkdir()
    example = target / "cy-ground-truth.yaml"
    external = tmp_path / "external.yaml"
    if destination_kind == "directory":
        example.mkdir()
    else:
        if destination_kind == "symlink":
            external.write_text("# Keep me\n", encoding="utf-8")
        example.symlink_to(external)
    with pytest.raises(FileExistsError, match="not a regular file"):
        dump_config_tree(target, overwrite=True)
    assert list(target.iterdir()) == [example]
    if destination_kind == "symlink":
        assert external.read_text(encoding="utf-8") == "# Keep me\n"
    else:
        assert not external.exists()
