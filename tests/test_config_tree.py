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
        *[f"{command}.yaml" for command in COMMANDS],
        "ultralytics",
        "ultralytics_predict",
    }


@pytest.mark.parametrize(("command", "config_name"), COMMANDS.items())
def test_examples_round_trip_through_hydra(tmp_path: Path, command: str, config_name: str) -> None:
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
                "ultralytics.data=data.yaml",
                "ultralytics.epochs=2",
                "ultralytics_predict.device=cpu",
            ],
        )
    assert config.ground_truth == "truth.csv"
    assert config.run_dir == "runs/example"
    assert config.ultralytics.data == "data.yaml"
    assert config.ultralytics.epochs == 2
    assert config.ultralytics_predict.device == "cpu"
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


def test_upstream_can_be_pasted_unchanged_into_group(tmp_path: Path) -> None:
    from clearml_yolo.config_tree import dump_config_tree
    from clearml_yolo.native_config import native_template

    dump_config_tree(tmp_path)
    (tmp_path / "ultralytics/default.yaml").write_text(native_template())
    with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
        config = compose(config_name="cy", overrides=["ultralytics.imgsz=1280"])
    assert config.ultralytics_predict.imgsz == 1280
    assert config.ultralytics_predict.conf == 0.001


def test_group_directory_symlink_is_rejected(tmp_path: Path) -> None:
    from clearml_yolo.config_tree import dump_config_tree

    target = tmp_path / "configs"
    target.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    (target / "ultralytics").symlink_to(external, target_is_directory=True)
    with pytest.raises(FileExistsError):
        dump_config_tree(target, overwrite=True)
    assert list(external.iterdir()) == []
    assert not (target / "cy.yaml").exists()


@pytest.mark.parametrize(("command", "config_name"), COMMANDS.items())
def test_generated_examples_load_in_fresh_cli_process(
    tmp_path: Path, command: str, config_name: str
) -> None:
    import subprocess
    import sys

    from clearml_yolo.config_tree import dump_config_tree

    dump_config_tree(tmp_path)
    result = subprocess.run(  # noqa: S603 - fixed project modules and generated test paths
        [
            sys.executable,
            "-m",
            f"clearml_yolo.apps.{config_name}",
            "--config-dir",
            str(tmp_path),
            "--config-name",
            command,
            "--cfg",
            "job",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "clearml:" in result.stdout
