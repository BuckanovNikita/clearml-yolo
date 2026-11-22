"""Command help is built in process so the mutation run observes the product code."""

import string
from collections.abc import Iterator
from pathlib import Path

import pytest
from hydra.conf import HelpConf
from hydra.core.config_store import ConfigStore
from hydra.core.global_hydra import GlobalHydra
from hydra.core.hydra_config import HydraConfig
from hydra_zen import store
from omegaconf import OmegaConf

from clearml_yolo.entrypoints.hydra import configs
from clearml_yolo.entrypoints.hydra.common import _launch
from clearml_yolo.entrypoints.hydra.config_tree import COMMAND_OF_CONFIG
from clearml_yolo.entrypoints.hydra.configs import (
    _hydra_conf,
    _selectable_group_lines,
    command_help,
    register_command_help,
)

_FASTERRCNN = "model/fasterrcnn: convnext_tiny, dinov2_small, dinov3_small, resnet101_fpn, resnet50_fpn, swin_tiny"
_MODEL_GROUPS = [
    "model: ultralytics",
    "model/deimv2: l, m, s, x",
    _FASTERRCNN,
    "model/fcos: convnext_tiny, dinov2_small, dinov3_small, resnet101_fpn, resnet50_fpn, swin_tiny",
    "model/rfdetr: large, medium, nano, small",
]


@pytest.fixture
def hydra_store() -> Iterator[ConfigStore]:
    store = ConfigStore.instance()
    saved = store.repo["hydra"]["config.yaml"]
    yield store
    store.repo["hydra"]["config.yaml"] = saved
    # A launched application leaves Hydra's process-wide singletons initialized.
    GlobalHydra.instance().clear()
    HydraConfig.instance().cfg = None


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("pipeline", [*_MODEL_GROUPS, "transforms: albumentations, default"]),
        ("train", [*_MODEL_GROUPS, "transforms: albumentations, default"]),
        ("predict", _MODEL_GROUPS),
        ("val", _MODEL_GROUPS),
        ("compare", _MODEL_GROUPS),
        ("export", [_FASTERRCNN]),
        ("metrics", []),
        ("report", []),
        ("ground_truth", []),
    ],
)
def test_selectable_groups_follow_the_command_defaults(name: str, expected: list[str]) -> None:
    assert _selectable_group_lines(name) == expected


def test_group_options_with_a_dollar_sign_survive_hydra_substitution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(configs, "PRESETS", {"ultralytics": {"default": 640}, "rfdetr": {"a$b": 1}})
    help_config = command_help("train", "cy-train")
    assert "model/rfdetr: a$$b\n" in help_config.template
    rendered = string.Template(help_config.template).safe_substitute(CONFIG="", **{"hydra.help.header": ""})
    assert "model/rfdetr: a$b\n" in rendered


@pytest.mark.parametrize("name", ["metrics", "report", "ground_truth"])
def test_help_of_a_command_without_groups_says_so(name: str) -> None:
    template = command_help(name, COMMAND_OF_CONFIG[name]).template
    section = template.split("== Configuration groups ==\n")[1].split("== Config ==")[0]
    assert section == (
        "Compose your configuration from those groups (group=option)\n\nThis command has no selectable groups.\n\n"
    )


def test_command_help_names_the_command_and_keeps_hydra_placeholders() -> None:
    help_config = command_help("export", "cy-export")
    assert isinstance(help_config, HelpConf)
    assert help_config.app_name == "cy-export"
    assert help_config.header == "${hydra.help.app_name}\n"
    assert help_config.footer == "Use --hydra-help to view Hydra specific help\n"
    assert help_config.template == (
        "${hydra.help.header}\n"
        "== Configuration groups ==\n"
        "Compose your configuration from those groups (group=option)\n\n"
        f"{_FASTERRCNN}\n\n"
        "== Config ==\n"
        "Override anything in the config (foo.bar=value)\n\n"
        "$CONFIG\n"
        "${hydra.help.footer}\n"
    )


def test_hydra_conf_keeps_run_layout_and_optional_help() -> None:
    plain = _hydra_conf()
    assert plain.job.chdir is False
    assert plain.run.dir == configs.HYDRA_RUN_DIR
    assert plain.sweep.dir == "${cy_home:}/multirun/${now:%Y-%m-%d}/${now:%H-%M-%S}-${cy_run_token:}"
    assert plain.help.app_name == "???"
    custom = HelpConf(app_name="cy-train", header="h", footer="f", template="t")
    with_help = _hydra_conf(custom)
    assert with_help.help is custom
    assert with_help.job.chdir is False
    assert with_help.run.dir == configs.HYDRA_RUN_DIR


def test_registered_help_replaces_the_hydra_entry_and_keeps_run_layout(hydra_store: ConfigStore) -> None:
    register_command_help("train", "cy-train")
    node = hydra_store.repo["hydra"]["config.yaml"]
    assert node.provider == "clearml-yolo"
    assert node.group == "hydra"
    assert node.name == "config.yaml"
    stored = OmegaConf.to_container(node.node, resolve=False)
    assert isinstance(stored, dict)
    assert stored["help"]["app_name"] == "cy-train"
    assert stored["help"]["template"] == command_help("train", "cy-train").template
    assert stored["job"]["chdir"] is False
    assert stored["run"]["dir"] == configs.HYDRA_RUN_DIR


def test_launch_registers_the_help_of_its_own_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], hydra_store: ConfigStore
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["cy-export", "--help"])
    with pytest.raises(SystemExit) as exit_info:
        _launch("export", lambda: None)
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("cy-export\n")
    assert _FASTERRCNN in out
    assert "model/rfdetr" not in out
    stored = OmegaConf.to_container(hydra_store.repo["hydra"]["config.yaml"].node, resolve=False)
    assert isinstance(stored, dict)
    assert stored["help"]["app_name"] == "cy-export"


def test_import_time_registration_stores_the_run_layout_without_command_help() -> None:
    registered = store["hydra", "config"]
    assert registered.job.chdir is False
    assert registered.run.dir == configs.HYDRA_RUN_DIR
    assert registered.help.app_name == "???"
