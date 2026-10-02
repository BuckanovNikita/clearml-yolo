"""Shared native Hydra groups for training and prediction overrides."""

import os
import socket
from typing import Any

from hydra.conf import HydraConf, JobConf, RunDir, SweepDir
from hydra_zen import builds, make_config, store
from omegaconf import MISSING, OmegaConf

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.filesystem import cy_home
from clearml_yolo.native_config import native_defaults, prediction_defaults, stage_settings
from clearml_yolo.publishing.models import FiftyOneConfig
from clearml_yolo.tasks.compare import ModelRef
from clearml_yolo.tasks.metrics import EvaluationConfig

RUN_STAMP_RESOLVER = "cy_run_token"
HYDRA_RUN_DIR = "${cy_home:}/outputs/${now:%Y-%m-%d}/${now:%H-%M-%S}-${cy_run_token:}"
NATIVE_COMMANDS = frozenset({"train", "predict", "val", "pipeline", "compare"})
PREDICTION_COMMANDS = NATIVE_COMMANDS


def _native() -> dict[str, Any]:
    groups: list[Any] = ["_self_", {"ultralytics": "_defaults"}]
    fields: dict[str, Any] = {"ultralytics": stage_settings(native_defaults(), "train")}
    groups.append({"ultralytics_predict": "_defaults"})
    fields["ultralytics_predict"] = prediction_defaults()
    return {"hydra_defaults": groups, **fields}


def _token() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def register_configs() -> None:
    """Register all eight commands without importing model runtime dependencies."""
    OmegaConf.register_new_resolver(RUN_STAMP_RESOLVER, _token, replace=True)
    OmegaConf.register_new_resolver("cy_home", lambda: str(cy_home()), replace=True)
    store(
        HydraConf(
            job=JobConf(chdir=False), run=RunDir(dir=HYDRA_RUN_DIR),
            sweep=SweepDir(dir="${cy_home:}/multirun/${now:%Y-%m-%d}/${now:%H-%M-%S}"),
        )
    )
    tracking = builds(ClearMLConfig, populate_full_signature=True)
    publishing = builds(FiftyOneConfig, populate_full_signature=True)
    evaluation = builds(EvaluationConfig, populate_full_signature=True)
    model = builds(ModelRef, populate_full_signature=True)
    store({}, group="ultralytics", name="_defaults")
    store({}, group="ultralytics_predict", name="_defaults")
    store(
        make_config(
            **_native(),
            clearml=tracking,
            ground_truth=MISSING,
            dataset_format="ndjson",
            dataset_cache_dir=None,
            required_splits=None,
        ),
        name="train",
    )
    store(
        make_config(
            **_native(),
            weights=None,
            ground_truth=MISSING,
            output=None,
            splits=None,
            image_name="name",
            clearml=tracking,
            fiftyone=publishing,
        ),
        name="predict",
    )
    store(
        make_config(
            **_native(),
            weights=None,
            ground_truth=MISSING,
            output_dir=None,
            splits=["train", "val", "test"],
            evaluation=evaluation,
            clearml=tracking,
        ),
        name="val",
    )
    store(
        make_config(
            predictions=MISSING,
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
    store(
        make_config(
            comparison_dir=MISSING,
            output_dir=None,
            report_config_path=None,
            clearml=tracking,
        ),
        name="report",
    )
    store(
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
    store(
        make_config(
            data_yaml=MISSING,
            output=None,
            test_fraction=0.5,
            seed=0,
            clearml=tracking,
        ),
        name="ground_truth",
    )
    store(
        make_config(
            **_native(),
            metrics=make_config(evaluation=evaluation, calibration_split="val"),
            compare=make_config(baseline_model=model, q=0.05, bootstrap_iterations=10000, seed=0),
            report=make_config(report_config_path=None),
            clearml=tracking,
            ground_truth=MISSING,
            splits=["train", "val", "test"],
            dataset_format="ndjson",
            dataset_cache_dir=None,
            weights=None,
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
