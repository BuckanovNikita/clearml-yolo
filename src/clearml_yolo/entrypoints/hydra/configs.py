"""Shared native Hydra groups for training and prediction overrides."""

import os
import socket
from importlib.resources import files
from typing import Any, override

from hydra.conf import HydraConf, JobConf, RunDir, SweepDir
from hydra.core.config_search_path import ConfigSearchPath
from hydra.core.plugins import Plugins
from hydra.plugins.search_path_plugin import SearchPathPlugin
from hydra_zen import builds, make_config, store
from omegaconf import MISSING, DictConfig, OmegaConf

from clearml_yolo.adapters.storage.filesystem import cy_home
from clearml_yolo.adapters.yolo.config import native_defaults, prediction_defaults, stage_settings
from clearml_yolo.application.contracts import ClearMLConfig, ModelRef
from clearml_yolo.core.evaluation.models import EvaluationConfig
from clearml_yolo.core.export_requests import ExportSettings
from clearml_yolo.core.models import PRESETS, model_preset
from clearml_yolo.core.publication import FiftyOneConfig
from clearml_yolo.entrypoints.hydra.transforms import (
    model_selections,
    native_overlay,
    profile_values,
)

RUN_STAMP_RESOLVER = "cy_run_token"
HYDRA_RUN_DIR = "${cy_home:}/outputs/${now:%Y-%m-%d}/${now:%H-%M-%S}-${cy_run_token:}"
PREDICTION_COMMANDS = frozenset({"train", "predict", "val", "pipeline", "compare"})
NATIVE_COMMANDS = PREDICTION_COMMANDS | {"export"}
SCHEMA_GROUP = "_cy_schemas"
CONFIG_MODULE = "clearml_yolo.entrypoints.hydra.defaults"


class ApplicationSearchPath(SearchPathPlugin):
    """Keep packaged public YAML available after the user's configuration directory."""

    @override
    def manipulate_search_path(self, search_path: ConfigSearchPath) -> None:
        search_path.append(provider="clearml-yolo", path=f"pkg://{CONFIG_MODULE}")


def command_schema(name: str) -> DictConfig:
    """Return authoritative fields without inheriting a user's local YAML search path."""
    config = OmegaConf.structured(store[SCHEMA_GROUP, name])
    if not isinstance(config, DictConfig):
        raise TypeError("Built-in command defaults must be a mapping")
    return config


def command_document(name: str) -> DictConfig:
    """Materialize an editable command base with its explicit composition defaults."""
    template = files(CONFIG_MODULE).joinpath(f"{name}.yaml").read_text(encoding="utf-8")
    config = OmegaConf.merge(OmegaConf.create(template), command_schema(name))
    if not isinstance(config, DictConfig):
        raise TypeError("Built-in command document must be a mapping")
    return config


def _schema(node: Any, *, name: str, group: str = "", package: str = "_global_") -> None:
    store(
        node, name=name, group=f"{SCHEMA_GROUP}/{group}" if group else SCHEMA_GROUP, package=package
    )


def _native(*, training: bool = False) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "model": {},
        "ultralytics": stage_settings(native_defaults(), "train"),
    }
    fields["ultralytics_predict"] = prediction_defaults()
    if training:
        fields["transforms"] = profile_values("default")
    return fields


def _token() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def register_configs() -> None:
    """Register application commands without importing model runtime dependencies."""
    Plugins.instance().register(ApplicationSearchPath)
    OmegaConf.register_new_resolver(RUN_STAMP_RESOLVER, _token, replace=True)
    OmegaConf.register_new_resolver("cy_home", lambda: str(cy_home()), replace=True)
    store(
        HydraConf(
            job=JobConf(chdir=False),
            run=RunDir(dir=HYDRA_RUN_DIR),
            sweep=SweepDir(
                dir="${cy_home:}/multirun/${now:%Y-%m-%d}/${now:%H-%M-%S}-${cy_run_token:}"
            ),
        )
    )
    tracking = builds(ClearMLConfig, populate_full_signature=True)
    publishing = builds(FiftyOneConfig, populate_full_signature=True)
    evaluation = builds(EvaluationConfig, populate_full_signature=True)
    model = builds(ModelRef, populate_full_signature=True)
    # Hydra composes the default group before expanding multirun model choices.
    # Keep native override paths available in that root; YOLO still uses its own groups.
    _schema(
        model_preset("ultralytics").model_dump(mode="json"),
        group="model",
        name="ultralytics",
        package="model",
    )
    for backend, presets in PRESETS.items():
        if backend != "ultralytics":
            for preset in presets:
                selection = f"{backend}/{preset}"
                _schema(
                    model_preset(selection).model_dump(mode="json"),
                    group=f"model/{backend}",
                    name=preset,
                    package="model",
                )
    _schema({}, group="ultralytics", name="_defaults", package="ultralytics")
    _schema({}, group="ultralytics_predict", name="_defaults", package="ultralytics_predict")
    for profile in ("default", "albumentations"):
        _schema(profile_values(profile), group="transforms", name=profile, package="transforms")
        for selection in model_selections():
            group, name = f"transform_overrides/{selection}_{profile}".rsplit("/", maxsplit=1)
            _schema(native_overlay(selection, profile), group=group, name=name, package="_global_")
    _schema(
        make_config(
            model={},
            export=ExportSettings().model_dump(mode="json"),
            weights=None,
            ground_truth=None,
            output_dir=None,
            clearml=tracking,
        ),
        name="export",
    )
    _schema(
        make_config(
            **_native(training=True),
            clearml=tracking,
            ground_truth=MISSING,
            dataset_format="ndjson",
            dataset_cache_dir=None,
            required_splits=None,
        ),
        name="train",
    )
    _schema(
        make_config(
            **_native(),
            weights=None,
            model_label=None,
            ground_truth=MISSING,
            output=None,
            splits=None,
            image_name="name",
            clearml=tracking,
            fiftyone=publishing,
        ),
        name="predict",
    )
    _schema(
        make_config(
            **_native(),
            weights=None,
            model_label=None,
            ground_truth=MISSING,
            output_dir=None,
            splits=["train", "val", "test"],
            evaluation=evaluation,
            clearml=tracking,
        ),
        name="val",
    )
    _schema(
        make_config(
            predictions=MISSING,
            model_label=None,
            ground_truth=MISSING,
            output_dir=None,
            splits=["train", "val", "test"],
            calibration_split="val",
            evaluation=evaluation,
            clearml=tracking,
            fiftyone=publishing,
        ),
        name="metrics",
    )
    _schema(
        make_config(
            comparison_dir=MISSING,
            baseline_label=None,
            candidate_label=None,
            output_dir=None,
            report_config_path=None,
            clearml=tracking,
        ),
        name="report",
    )
    _schema(
        make_config(
            baseline_model=model,
            candidate_model=model,
            ground_truth=MISSING,
            output_dir=None,
            split="test",
            **_native(),
            inference={"reuse_existing": True, "image_name": "name"},
            q=0.05,
            bootstrap_iterations=10000,
            seed=0,
            evaluation=evaluation,
            clearml=tracking,
        ),
        name="compare",
    )
    _schema(
        make_config(
            data_yaml=MISSING,
            output=None,
            test_fraction=0.5,
            seed=0,
            clearml=tracking,
        ),
        name="ground_truth",
    )
    _schema(
        make_config(
            **_native(training=True),
            metrics=make_config(evaluation=evaluation, calibration_split="val"),
            compare=make_config(baseline_model=model, q=0.05, bootstrap_iterations=10000, seed=0),
            report=make_config(report_config_path=None),
            clearml=tracking,
            ground_truth=MISSING,
            splits=["train", "val", "test"],
            dataset_format="ndjson",
            dataset_cache_dir=None,
            weights=None,
            model_label=None,
            run_id=None,
            run_dir=None,
            skip_train=False,
            skip_predict=False,
            skip_metrics=False,
            skip_report=False,
            skip_compare=False,
            fiftyone=publishing,
        ),
        name="pipeline",
    )


register_configs()
