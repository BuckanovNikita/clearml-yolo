"""Every hydra-zen config registration in the project.

The store is global mutable state and rejects duplicate names, so all registrations
live here and each app imports this one module.

Each stage is registered twice: at the top level under its own name, so it runs as a
standalone app with its own ClearML settings, and under a group with an interpolated
ClearML block, so the pipeline names one experiment for all four stages at once.
"""

from __future__ import annotations

from typing import Any

from hydra.conf import HydraConf, JobConf
from hydra_zen import builds, make_config, store

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.gpu import AutoGpuConfig
from clearml_yolo.tasks.compare import InferenceConfig, ModelRef
from clearml_yolo.tasks.metrics import EvaluationConfig
from clearml_yolo.tasks.report import BaselineConfig

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

# Every stage inside the pipeline points at the top-level block, so one
# clearml.project_name / clearml.task_name override names the whole run.
PipelineStageClearMLConf = builds(
    ClearMLConfig,
    enabled="${clearml.enabled}",
    project_name="${clearml.project_name}",
    task_name="${clearml.task_name}",
    task_type="${clearml.task_type}",
    tags="${clearml.tags}",
    output_uri="${clearml.output_uri}",
    continue_task_id="${clearml.continue_task_id}",
    reuse_last_task_id="${clearml.reuse_last_task_id}",
)

BaselineClearMLConf = builds(BaselineConfig, source="clearml", populate_full_signature=True)
BaselineLocalConf = builds(
    BaselineConfig,
    source="local",
    directory="runs/previous/metrics",
    populate_full_signature=True,
)
BaselineNoneConf = builds(BaselineConfig, source="none", populate_full_signature=True)


def train_config(clearml: Any) -> Any:
    return make_config(
        model="yolo11n.pt",
        data="coco8.yaml",
        epochs=100,
        imgsz=640,
        batch=16,
        project="runs/detect",
        name="train",
        device=None,
        auto_gpu=AutoGpuConf,
        clearml=clearml,
        train_kwargs={},
    )


def predict_config(clearml: Any) -> Any:
    return make_config(
        weights="runs/detect/train/weights/best.pt",
        ground_truth="ground_truth.csv",
        output="runs/predictions.csv",
        auto_gpu=AutoGpuConf,
        conf=0.001,
        iou=0.7,
        imgsz=640,
        batch=16,
        device=None,
        splits=None,
        image_name="name",
        clearml=clearml,
        predict_kwargs={},
    )


def metrics_config(clearml: Any) -> Any:
    return make_config(
        predictions="runs/predictions.csv",
        ground_truth="ground_truth.csv",
        output_dir="runs/metrics",
        splits=["train", "val", "test"],
        calibration_split="val",
        evaluation=EvaluationConf,
        clearml=clearml,
    )


def report_config(clearml: Any) -> Any:
    # The group is named relatively: standalone it resolves to "baseline", and inside
    # the pipeline Hydra prefixes it to "report/baseline" on its own.
    return make_config(
        hydra_defaults=["_self_", {"baseline": "clearml"}],
        metrics_dir="runs/metrics",
        output_dir="runs/reports",
        splits=["train", "val", "test"],
        report_config_path=None,
        baseline=None,
        clearml=clearml,
    )


def compare_config(clearml: Any) -> Any:
    return make_config(
        hydra_defaults=[
            "_self_",
            {"baseline_model": "clearml"},
            {"candidate_model": "clearml"},
        ],
        baseline_model=None,
        candidate_model=None,
        ground_truth="ground_truth.csv",
        output_dir="runs/comparison",
        # Thresholds are calibrated on val and must be reported on images val never saw.
        split="test",
        inference=InferenceConf,
        auto_gpu=AutoGpuConf,
        iou_threshold=0.5,
        matching_strategy="iou_prior",
        q=0.05,
        bootstrap_iterations=10000,
        seed=0,
        clearml=clearml,
    )


GroundTruthConf = make_config(
    data_yaml="data.yaml",
    output="ground_truth.csv",
    # Datasets that ship only train and val get a test split carved out of val, because
    # thresholds are calibrated on val and must be reported on images val never saw.
    test_fraction=0.5,
    seed=0,
)


PipelineConf = make_config(
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
    skip_train=False,
    skip_predict=False,
    skip_metrics=False,
    skip_report=False,
    skip_compare=False,
)

STAGE_CONFIG_FACTORIES = {
    "train": train_config,
    "predict": predict_config,
    "metrics": metrics_config,
}


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

    for stage, factory in STAGE_CONFIG_FACTORIES.items():
        store(factory(ClearMLConf), name=stage)
        store(factory(PipelineStageClearMLConf), group=stage, name="default")

    store(report_config(ClearMLConf), name="report")
    store(report_config(PipelineStageClearMLConf), group="report", name="default")

    for stage in ("", "compare/"):
        for group, clearml_conf in (
            ("baseline_model", BaselineModelConf),
            ("candidate_model", CandidateModelConf),
        ):
            model_store = store(group=f"{stage}{group}")
            model_store(clearml_conf, name="clearml")
            model_store(ModelLocalConf, name="local")
    store(compare_config(ClearMLConf), name="compare")
    store(compare_config(PipelineStageClearMLConf), group="compare", name="default")

    store(GroundTruthConf, name="ground_truth")
    store(PipelineConf, name="pipeline")


register_configs()
