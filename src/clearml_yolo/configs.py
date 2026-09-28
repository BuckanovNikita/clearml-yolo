"""Shared native Hydra groups for training and prediction overrides."""

import os
import socket
from typing import Any

from hydra.conf import HydraConf, JobConf, RunDir
from hydra_zen import builds, make_config, store
from omegaconf import MISSING, OmegaConf

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.native_config import native_defaults, prediction_defaults
from clearml_yolo.tasks.compare import ModelRef
from clearml_yolo.tasks.metrics import EvaluationConfig

RUN_STAMP_RESOLVER = "cy_run_token"
HYDRA_RUN_DIR = "outputs/${now:%Y-%m-%d}/${now:%H-%M-%S}-${cy_run_token:}"
NATIVE_COMMANDS = frozenset({"train", "predict", "val", "pipeline", "compare"})
PREDICTION_COMMANDS = NATIVE_COMMANDS


def _native() -> dict[str, Any]:
    groups: list[Any] = ["_self_", {"ultralytics": "_defaults"}]
    fields: dict[str, Any] = {"ultralytics": native_defaults()}
    groups.append({"ultralytics_predict": "_defaults"})
    fields["ultralytics_predict"] = prediction_defaults()
    return {"hydra_defaults": groups, **fields}


def _token() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def register_configs() -> None:
    """Register all eight commands without importing model runtime dependencies."""
    OmegaConf.register_new_resolver(RUN_STAMP_RESOLVER, _token, replace=True)
    store(HydraConf(job=JobConf(chdir=False), run=RunDir(dir=HYDRA_RUN_DIR)))
    tracking = builds(ClearMLConfig, populate_full_signature=True)
    evaluation = builds(EvaluationConfig, populate_full_signature=True)
    model = builds(ModelRef, populate_full_signature=True)
    store({}, group="ultralytics", name="_defaults")
    store({}, group="ultralytics_predict", name="_defaults")
    store(make_config(**_native(), clearml=tracking), name="train")
    store(
        make_config(
            **_native(),
            weights=None,
            ground_truth=MISSING,
            output=None,
            splits=None,
            image_name="name",
            clearml=tracking,
        ),
        name="predict",
    )
    store(
        make_config(
            **_native(),
            weights=None,
            ground_truth=MISSING,
            output_dir=None,
            splits=["val", "test"],
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
            splits=["val", "test"],
            calibration_split="val",
            evaluation=evaluation,
            clearml=tracking,
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
            iou_threshold=0.5,
            matching_strategy="iou_prior",
            q=0.05,
            bootstrap_iterations=10000,
            seed=0,
            evaluation={},
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
            splits=["val", "test"],
            weights=None,
            run_id=None,
            run_dir=None,
            skip_train=False,
            skip_predict=False,
            skip_metrics=False,
            skip_report=False,
            skip_compare=False,
        ),
        name="pipeline",
    )


register_configs()
