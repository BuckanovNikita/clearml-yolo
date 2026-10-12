"""Shared native Hydra groups for training and prediction overrides."""

import os
import socket
from typing import Any

from hydra.conf import HydraConf, JobConf, RunDir, SweepDir
from hydra_zen import builds, make_config, store
from omegaconf import MISSING, OmegaConf

from clearml_yolo.adapters.storage.filesystem import cy_home
from clearml_yolo.adapters.yolo.config import native_defaults, prediction_defaults, stage_settings
from clearml_yolo.application.contracts import ClearMLConfig, ModelRef
from clearml_yolo.core.evaluation.models import EvaluationConfig
from clearml_yolo.core.execution import AutoGPUControl
from clearml_yolo.core.export_requests import ExportSettings
from clearml_yolo.core.models import PRESETS, model_preset
from clearml_yolo.core.publication import FiftyOneConfig

RUN_STAMP_RESOLVER = "cy_run_token"
HYDRA_RUN_DIR = "${cy_home:}/outputs/${now:%Y-%m-%d}/${now:%H-%M-%S}-${cy_run_token:}"
PREDICTION_COMMANDS = frozenset({"train", "predict", "val", "pipeline", "compare"})
NATIVE_COMMANDS = PREDICTION_COMMANDS | {"export"}


def _native() -> dict[str, Any]:
    groups: list[Any] = ["_self_", {"model": "ultralytics"}, {"ultralytics": "_defaults"}]
    fields: dict[str, Any] = {
        "model": {},
        "ultralytics": stage_settings(native_defaults(), "train"),
    }
    groups.append({"ultralytics_predict": "_defaults"})
    fields["ultralytics_predict"] = prediction_defaults()
    fields["queue"] = make_config(enabled=True)
    fields["autogpu"] = AutoGPUControl().model_dump()
    groups.append({"override hydra/launcher": "cy_queue"})
    return {"hydra_defaults": groups, **fields}


def _token() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def register_configs() -> None:
    """Register application commands without importing model runtime dependencies."""
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
    store(
        {"_target_": "hydra_plugins.cy_queue.launcher.QueueLauncher"},
        group="hydra/launcher",
        name="cy_queue",
    )
    tracking = builds(ClearMLConfig, populate_full_signature=True)
    publishing = builds(FiftyOneConfig, populate_full_signature=True)
    evaluation = builds(EvaluationConfig, populate_full_signature=True)
    model = builds(ModelRef, populate_full_signature=True)
    # Hydra composes the default group before expanding multirun model choices.
    # Keep native override paths available in that root; YOLO still uses its own groups.
    store(model_preset("ultralytics").model_dump(mode="json"), group="model", name="ultralytics")
    for backend, presets in PRESETS.items():
        if backend != "ultralytics":
            for preset in presets:
                selection = f"{backend}/{preset}"
                store(
                    model_preset(selection).model_dump(mode="json"),
                    group=f"model/{backend}",
                    name=preset,
                    package="model",
                )
    store({}, group="ultralytics", name="_defaults")
    store({}, group="ultralytics_predict", name="_defaults")
    store(
        make_config(
            hydra_defaults=[
                "_self_",
                {"model": "fasterrcnn/resnet50_fpn"},
                {"override hydra/launcher": "cy_queue"},
            ],
            model={},
            export=ExportSettings().model_dump(mode="json"),
            weights=None,
            ground_truth=None,
            output_dir=None,
            clearml=tracking,
            queue=make_config(enabled=True),
            autogpu=AutoGPUControl().model_dump(),
        ),
        name="export",
    )
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
    store(
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
    store(
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
    store(
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
