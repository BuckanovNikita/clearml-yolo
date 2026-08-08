"""Every hydra-zen config registration in the project.

The store is global mutable state and rejects duplicate names, so all registrations
live here and each app imports this one module.

Each stage is registered twice, from one field set: at the top level under its own name, so
it runs as a standalone app with its own settings, and under a group without the keys the
pipeline fills in, so a full pipeline run names each of those exactly once. Which keys those
are is :data:`clearml_yolo.tasks.pipeline.PIPELINE_FILLED_KEYS`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from hydra.conf import HydraConf, JobConf
from hydra_zen import builds, make_config, store

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.gpu import AutoGpuConfig
from clearml_yolo.tasks.compare import InferenceConfig, ModelRef
from clearml_yolo.tasks.metrics import EvaluationConfig
from clearml_yolo.tasks.pipeline import PIPELINE_FILLED_KEYS
from clearml_yolo.tasks.report import BaselineConfig
from clearml_yolo.tasks.train import CHECKPOINT

TRAIN_PROJECT = "runs/detect"
PREDICTIONS_CSV = "runs/predictions.csv"
METRICS_DIR = "runs/metrics"

# Hydra composes the ultralytics parameter sets from files inside the installed package,
# because their comments are the point and a store entry cannot carry any. The path is
# declared per primary config: `hydra.searchpath` is resolved before the `hydra/config`
# store entry is composed, so setting it there is too late and the group is not found.
PACKAGE_CONF = {"searchpath": ["pkg://clearml_yolo.conf"]}

# The group reference is absolute, so one `ultralytics/` directory serves both the
# standalone apps and the stage blocks nested inside the pipeline. Written relatively,
# Hydra would look for `train/ultralytics/` and `predict/ultralytics/` as well, and the
# same file would have to exist three times.
ULTRALYTICS_GROUP = "/ultralytics@ultralytics"

# Where a standalone `cy-predict` looks with no weights named. Training writes into the
# ClearML experiment's own name, so this is built from that rather than from a second
# constant that would drift from it the first time either was changed.
DEFAULT_CHECKPOINT = CHECKPOINT.format(project=TRAIN_PROJECT, name=ClearMLConfig().task_name)

AutoGpuConf = builds(AutoGpuConfig, populate_full_signature=True)
ClearMLConf = builds(ClearMLConfig, populate_full_signature=True)
EvaluationConf = builds(EvaluationConfig, populate_full_signature=True)
InferenceConf = builds(InferenceConfig, populate_full_signature=True)

BaselineModelConf = builds(ModelRef, source="clearml", populate_full_signature=True)
# The candidate is the model under test, which by definition has not been promoted yet,
# so it must not inherit the baseline's prod tag — both sides would resolve to the same
# task and the comparison would report a model as identical to itself.
CandidateModelConf = builds(ModelRef, source="clearml", tags=[], populate_full_signature=True)
ModelLocalConf = builds(ModelRef, source="local", populate_full_signature=True)

BaselineClearMLConf = builds(BaselineConfig, source="clearml", populate_full_signature=True)
BaselineLocalConf = builds(
    BaselineConfig,
    source="local",
    directory="runs/previous/metrics",
    populate_full_signature=True,
)
BaselineNoneConf = builds(BaselineConfig, source="none", populate_full_signature=True)


def _train_fields() -> dict[str, Any]:
    return {
        "hydra_defaults": ["_self_", {ULTRALYTICS_GROUP: "train"}],
        "hydra": PACKAGE_CONF,
        # Filled by the group above; declared so the composed config has somewhere to put
        # it, which a structured config otherwise refuses.
        "ultralytics": None,
        "auto_gpu": AutoGpuConf,
        "clearml": ClearMLConf,
    }


def _predict_fields() -> dict[str, Any]:
    return {
        "hydra_defaults": ["_self_", {ULTRALYTICS_GROUP: "predict"}],
        "hydra": PACKAGE_CONF,
        "ultralytics": None,
        "weights": DEFAULT_CHECKPOINT,
        "ground_truth": "ground_truth.csv",
        "output": PREDICTIONS_CSV,
        "auto_gpu": AutoGpuConf,
        # Which architecture the weights are of: a batch table is keyed by it. Not an
        # ultralytics parameter — nothing is loaded from this name, so it stays out of
        # that block. Unset, the checkpoint is not asked.
        "model": None,
        # No downstream split list to honour, so every image in the ground truth is scored.
        "splits": None,
        "image_name": "name",
        "clearml": ClearMLConf,
    }


def _metrics_fields() -> dict[str, Any]:
    return {
        "predictions": PREDICTIONS_CSV,
        "ground_truth": "ground_truth.csv",
        "output_dir": METRICS_DIR,
        "splits": ["train", "val", "test"],
        "calibration_split": "val",
        "evaluation": EvaluationConf,
        "clearml": ClearMLConf,
    }


def _report_fields() -> dict[str, Any]:
    # The group is named relatively: standalone it resolves to "baseline", and inside
    # the pipeline Hydra prefixes it to "report/baseline" on its own.
    return {
        "hydra_defaults": ["_self_", {"baseline": "clearml"}],
        "metrics_dir": METRICS_DIR,
        "output_dir": "runs/reports",
        "splits": ["train", "val", "test"],
        "report_config_path": None,
        "baseline": None,
        "clearml": ClearMLConf,
    }


def _compare_fields() -> dict[str, Any]:
    return {
        "hydra_defaults": [
            "_self_",
            {"baseline_model": "clearml"},
            {"candidate_model": "clearml"},
        ],
        "baseline_model": None,
        "candidate_model": None,
        "ground_truth": "ground_truth.csv",
        "output_dir": "runs/comparison",
        # Thresholds are calibrated on val and must be reported on images val never saw.
        "split": "test",
        "inference": InferenceConf,
        "auto_gpu": AutoGpuConf,
        "iou_threshold": 0.5,
        "matching_strategy": "iou_prior",
        "q": 0.05,
        "bootstrap_iterations": 10000,
        "seed": 0,
        "clearml": ClearMLConf,
    }


STAGE_FIELDS: dict[str, Callable[[], dict[str, Any]]] = {
    "train": _train_fields,
    "predict": _predict_fields,
    "metrics": _metrics_fields,
    "report": _report_fields,
    "compare": _compare_fields,
}

# Inside the pipeline the comparison declares only the inference settings it owns; the
# rest are the predict stage's, merged in by run_pipeline. `device` is one of these on
# purpose: the comparison resolves one card for both models itself, and inheriting a
# device would put a hardware difference inside a comparison meant to isolate the model.
ComparisonInferenceConf = builds(InferenceConfig, device=None, reuse_existing=True)

PIPELINE_FIELD_OVERRIDES: dict[str, dict[str, Any]] = {
    "compare": {"inference": ComparisonInferenceConf}
}


def _stage_config(stage: str, *, in_pipeline: bool) -> Any:
    """Build one stage's config, without what run_pipeline fills in when it is a stage of one.

    Both variants come from one field set, so a default cannot be changed for the
    standalone app and left behind inside the pipeline.
    """
    filled: frozenset[str] = PIPELINE_FILLED_KEYS[stage] if in_pipeline else frozenset()
    fields = {key: value for key, value in STAGE_FIELDS[stage]().items() if key not in filled}
    if in_pipeline:
        fields.update(PIPELINE_FIELD_OVERRIDES.get(stage, {}))
        # `hydra` is the run's own node, and the pipeline declares it once at the top.
        # Left here it would become a `train.hydra` field: a stage keyword argument no
        # task takes, and no search path at all.
        fields.pop("hydra", None)
    defaults = fields.pop("hydra_defaults", None)
    if defaults is not None:
        # A group whose key the pipeline fills has nothing left to select.
        fields["hydra_defaults"] = [
            entry for entry in defaults if isinstance(entry, str) or not set(entry) & filled
        ]
    return make_config(**fields)


GroundTruthConf = make_config(
    data_yaml="data.yaml",
    output="ground_truth.csv",
    # Datasets that ship only train and val get a test split carved out of val, because
    # thresholds are calibrated on val and must be reported on images val never saw.
    test_fraction=0.5,
    seed=0,
)


PipelineConf = make_config(
    hydra=PACKAGE_CONF,
    hydra_defaults=[
        "_self_",
        {"train": "default"},
        {"predict": "default"},
        {"metrics": "default"},
        {"report": "default"},
        {"compare": "default"},
    ],
    train=None,
    predict=None,
    metrics=None,
    report=None,
    compare=None,
    clearml=ClearMLConf,
    # run_pipeline hands each of these to every stage that needs it. Overriding one of
    # these names the whole run; no stage block below declares it on its own.
    auto_gpu=AutoGpuConf,
    ground_truth="ground_truth.csv",
    splits=["train", "val", "test"],
    # Unset means the checkpoint this run's training stage writes. Set it when skip_train
    # points the run at a model somebody else trained.
    weights=None,
    skip_train=False,
    skip_predict=False,
    skip_metrics=False,
    skip_report=False,
    skip_compare=False,
)


def register_configs() -> None:
    """Populate the hydra-zen store. Safe to call more than once."""
    # Hydra's auto-chdir would invalidate every relative path in the config, and
    # ultralytics already manages its own run directories.
    store(HydraConf(job=JobConf(chdir=False)))

    for group in ("baseline", "report/baseline"):
        baseline_store = store(group=group)
        baseline_store(BaselineClearMLConf, name="clearml")
        baseline_store(BaselineLocalConf, name="local")
        baseline_store(BaselineNoneConf, name="none")

    for group, model_conf in (
        ("baseline_model", BaselineModelConf),
        ("candidate_model", CandidateModelConf),
    ):
        model_store = store(group=group)
        model_store(model_conf, name="clearml")
        model_store(ModelLocalConf, name="local")

    for stage in STAGE_FIELDS:
        store(_stage_config(stage, in_pipeline=False), name=stage)
        store(_stage_config(stage, in_pipeline=True), group=stage, name="default")

    store(GroundTruthConf, name="ground_truth")
    store(PipelineConf, name="pipeline")


register_configs()
