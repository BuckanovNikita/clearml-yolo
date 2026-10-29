"""Documented declarations preserve captured Hydra and argparse public contracts."""

import hashlib
import json
import sys
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import store
from omegaconf import OmegaConf

from clearml_yolo.application.contracts import ClearMLConfig, ClearMLDatasetRef, ModelRef
from clearml_yolo.core.evaluation.models import EvaluationConfig
from clearml_yolo.core.export_requests import ExportSettings
from clearml_yolo.core.models import (
    DeimAugmentationOverrides,
    ModelConfig,
    PredictSettings,
    Preprocessing,
    RFDETRAugmentationOverrides,
    TrainSettings,
)
from clearml_yolo.core.publication import FiftyOneConfig
from clearml_yolo.core.transforms import TransformConfig, TransformSnapshot
from clearml_yolo.entrypoints.hydra.configs import command_schema
from clearml_yolo.entrypoints.hydra.declarations import COMMAND_DECLARATIONS, NESTED_DECLARATIONS
from clearml_yolo.entrypoints.options import OPTION_DECLARATIONS, parser_for

_BASELINE: dict[str, Any] = json.loads(
    Path(__file__).with_name("fixtures").joinpath("docs-compatibility.json").read_text()
)


def _digest(value: object) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode()).hexdigest()


@pytest.mark.parametrize("name", _BASELINE["schemas"])
def test_command_declarations_preserve_original_schema(name: str) -> None:
    assert OmegaConf.to_container(command_schema(name), resolve=False) == _BASELINE["schemas"][name]


@pytest.mark.parametrize("case", _BASELINE["compositions"])
def test_all_compositions_preserve_unresolved_and_resolved_defaults(case: dict[str, Any]) -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name=case["name"], overrides=case["overrides"])
    for label, resolve in (("unresolved", False), ("resolved", True)):
        assert _digest(OmegaConf.to_container(config, resolve=resolve)) == case[label]


@pytest.mark.parametrize("case", _BASELINE["representatives"])
def test_legacy_override_shapes_remain_permissive(case: dict[str, Any]) -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name=case["name"], overrides=case["overrides"])
    assert OmegaConf.to_container(config, resolve=False) == case["values"]


@pytest.mark.parametrize("command", _BASELINE["parser_help"])
def test_inert_parsers_preserve_exact_existing_help(
    command: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", [command])
    assert parser_for(command).format_help() == _BASELINE["parser_help"][command]


def test_option_declarations_preserve_parsing_types_and_defaults() -> None:
    arguments = parser_for("cy-batch-estimate").parse_args(
        ["--imgsz", "640", "--devices", "2,0", "--gpu-counts", "1,2"]
    )
    assert vars(arguments) == {
        "imgsz": 640,
        "classes": 150,
        "objects_per_image": 300,
        "models": None,
        "devices": (2, 0),
        "gpu_counts": (1, 2),
        "refresh": False,
        "memory_budget": 0.9,
        "search_limit": 1024,
        "trial_timeout": 300,
    }
    assert parser_for("cy-dedup").parse_args(["images", "--dry-run"]).directory == Path("images")
    assert parser_for("cy-init-config").parse_args(["configs"]).command == "cy"
    assert vars(parser_for("cy-download-weights").parse_args([])) == {}


@pytest.mark.parametrize("value", ["0,0", "-1", "a"])
def test_batch_integer_list_rejects_original_invalid_values(value: str) -> None:
    with pytest.raises(SystemExit) as failure:
        parser_for("cy-batch-estimate").parse_args(["--imgsz", "640", "--devices", value])
    assert failure.value.code == 2


def test_command_and_option_documentation_is_complete() -> None:
    assert set(COMMAND_DECLARATIONS) == set(_BASELINE["schemas"])
    for declaration in (*COMMAND_DECLARATIONS.values(), *NESTED_DECLARATIONS.values()):
        for item in fields(declaration):
            for key in ("description", "shapes", "constraints", "applicability", "examples"):
                assert item.metadata[key], (declaration.__name__, item.name, key)
    for options in OPTION_DECLARATIONS.values():
        assert options
        for option in options:
            assert option.flags
            assert option.description
            assert option.examples


@pytest.mark.parametrize(
    "model",
    [
        ClearMLDatasetRef,
        ClearMLConfig,
        ModelRef,
        ModelConfig,
        TrainSettings,
        PredictSettings,
        Preprocessing,
        DeimAugmentationOverrides,
        RFDETRAugmentationOverrides,
        EvaluationConfig,
        ExportSettings,
        FiftyOneConfig,
        TransformConfig,
        TransformSnapshot,
    ],
)
def test_public_pydantic_fields_keep_documentation_at_the_definition(model: Any) -> None:
    for name, info in model.model_fields.items():
        assert info.description, (model.__name__, name)
        assert info.examples, (model.__name__, name)
        assert info.json_schema_extra["source"] == f"{model.__module__}.{model.__name__}.{name}"
        assert info.json_schema_extra["classification"] in {"input", "generated"}
