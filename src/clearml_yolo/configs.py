"""Hydra configuration with sparse, explicitly supplied native model arguments."""

from __future__ import annotations

import os
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

from hydra.conf import HydraConf, JobConf, RunDir
from hydra_zen import builds, make_config, store
from omegaconf import MISSING, OmegaConf, open_dict

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.tasks.compare import InferenceConfig, ModelRef
from clearml_yolo.tasks.metrics import EvaluationConfig

RUN_STAMP_RESOLVER = "cy_run_token"
HYDRA_RUN_DIR = "outputs/${now:%Y-%m-%d}/${now:%H-%M-%S}-${cy_run_token:}"
NATIVE_BLOCKS = {
    "train": [""],
    "predict": [""],
    "val": [""],
    "pipeline": ["train", "predict"],
}


def overlay_ultralytics_files(config_name: str) -> Callable[[Any], None]:
    """Overlay raw native YAML below only explicitly supplied embedded/CLI values."""

    def apply(config: Any) -> None:
        for parent in NATIVE_BLOCKS.get(config_name, []):
            node = OmegaConf.select(config, parent) if parent else config
            named = node.get("cfg")
            if named is None:
                continue
            loaded = OmegaConf.load(Path(named))
            if not OmegaConf.is_dict(loaded):
                raise ValueError(f"{named}: native configuration must be a mapping")
            composed = OmegaConf.merge(loaded, node.ultralytics)
            with open_dict(node):
                node.ultralytics = composed

    return apply


def _token() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def register_configs() -> None:
    """Register all eight commands without importing model runtime dependencies."""
    OmegaConf.register_new_resolver(RUN_STAMP_RESOLVER, _token, replace=True)
    store(HydraConf(job=JobConf(chdir=False), run=RunDir(dir=HYDRA_RUN_DIR)))
    tracking = builds(ClearMLConfig, populate_full_signature=True)
    evaluation = builds(EvaluationConfig, populate_full_signature=True)
    model = builds(ModelRef, populate_full_signature=True)
    inference = builds(InferenceConfig, populate_full_signature=True)
    native: dict[str, Any] = {"cfg": None, "ultralytics": {}}
    store(make_config(**native, clearml=tracking), name="train")
    store(
        make_config(
            **native,
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
            **native,
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
            inference=inference,
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
            train=make_config(**native),
            predict=make_config(**native),
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
