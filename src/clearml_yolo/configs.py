"""Every hydra-zen config registration in the project.

The store is global mutable state and rejects duplicate names, so all registrations
live here and each app imports this one module.

Each stage is registered twice, from one factory: at the top level under its own name, so
it runs as a standalone app with its own settings, and under a group whose shared values
are interpolations, so a full pipeline run names each of them exactly once. Which values
those are is spelled out in :class:`SharedKeys`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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

# The comparison must re-run both checkpoints exactly as the candidate was predicted, so
# inside the pipeline its inference settings are the predict stage's. `device` is left out
# on purpose: the compare stage resolves one card for both models itself, and inheriting a
# device would put a hardware difference inside a comparison meant to isolate the model.
PipelineInferenceConf = builds(
    InferenceConfig,
    conf="${predict.conf}",
    iou="${predict.iou}",
    imgsz="${predict.imgsz}",
    batch="${predict.batch}",
    image_name="${predict.image_name}",
    populate_full_signature=True,
)

BaselineClearMLConf = builds(BaselineConfig, source="clearml", populate_full_signature=True)
BaselineLocalConf = builds(
    BaselineConfig,
    source="local",
    directory="runs/previous/metrics",
    populate_full_signature=True,
)
BaselineNoneConf = builds(BaselineConfig, source="none", populate_full_signature=True)


@dataclass(frozen=True)
class SharedKeys:
    """Every value more than one stage needs, and what each stage should point at for it.

    A stage config is built twice from the same factory. Standalone it gets the literal
    defaults below, because there is no other stage to agree with. Inside the pipeline it
    gets ``${...}`` interpolations into one top-level key, so ``ground_truth=`` on the
    command line reaches inference, scoring and the comparison at once instead of having to
    be repeated under three names — and, more importantly, cannot be changed for one stage
    and silently left stale for another.
    """

    clearml: Any
    auto_gpu: Any = AutoGpuConf
    ground_truth: Any = "ground_truth.csv"
    splits: Any = field(default_factory=lambda: ["train", "val", "test"])
    # Standalone inference has no downstream split list to honour, so it scores every image
    # in the ground truth; inside the pipeline it scores exactly what metrics will read.
    predict_splits: Any = None
    run_name: Any = "train"
    weights: Any = "runs/detect/train/weights/best.pt"
    predictions: Any = "runs/predictions.csv"
    metrics_dir: Any = "runs/metrics"
    inference: Any = InferenceConf
    iou_threshold: Any = 0.5
    matching_strategy: Any = "iou_prior"
    # The pipeline fills the candidate side in from the model it just trained, so offering
    # the key would only let a run name a different model than the one under test.
    candidate_model_group: bool = True


STANDALONE = SharedKeys(clearml=ClearMLConf)
PIPELINE = SharedKeys(
    clearml=PipelineStageClearMLConf,
    auto_gpu="${auto_gpu}",
    ground_truth="${ground_truth}",
    splits="${splits}",
    predict_splits="${splits}",
    run_name="${clearml.task_name}",
    weights="${train.project}/${train.name}/weights/best.pt",
    predictions="${predict.output}",
    metrics_dir="${metrics.output_dir}",
    inference=PipelineInferenceConf,
    iou_threshold="${metrics.evaluation.iou_threshold}",
    matching_strategy="${metrics.evaluation.matching_strategy}",
    candidate_model_group=False,
)


def train_config(shared: SharedKeys) -> Any:
    return make_config(
        model="yolo11n.pt",
        data="coco8.yaml",
        epochs=100,
        imgsz=640,
        batch=16,
        project="runs/detect",
        name=shared.run_name,
        device=None,
        auto_gpu=shared.auto_gpu,
        clearml=shared.clearml,
        train_kwargs={},
    )


def predict_config(shared: SharedKeys) -> Any:
    return make_config(
        weights=shared.weights,
        ground_truth=shared.ground_truth,
        output="runs/predictions.csv",
        auto_gpu=shared.auto_gpu,
        conf=0.001,
        iou=0.7,
        imgsz=640,
        batch=16,
        device=None,
        splits=shared.predict_splits,
        image_name="name",
        clearml=shared.clearml,
        predict_kwargs={},
    )


def metrics_config(shared: SharedKeys) -> Any:
    return make_config(
        predictions=shared.predictions,
        ground_truth=shared.ground_truth,
        output_dir="runs/metrics",
        splits=shared.splits,
        calibration_split="val",
        evaluation=EvaluationConf,
        clearml=shared.clearml,
    )


def report_config(shared: SharedKeys) -> Any:
    # The group is named relatively: standalone it resolves to "baseline", and inside
    # the pipeline Hydra prefixes it to "report/baseline" on its own.
    return make_config(
        hydra_defaults=["_self_", {"baseline": "clearml"}],
        metrics_dir=shared.metrics_dir,
        output_dir="runs/reports",
        splits=shared.splits,
        report_config_path=None,
        baseline=None,
        clearml=shared.clearml,
    )


def compare_config(shared: SharedKeys) -> Any:
    defaults: list[Any] = ["_self_", {"baseline_model": "clearml"}]
    candidate: dict[str, Any] = {}
    if shared.candidate_model_group:
        defaults.append({"candidate_model": "clearml"})
        candidate["candidate_model"] = None
    return make_config(
        hydra_defaults=defaults,
        baseline_model=None,
        **candidate,
        ground_truth=shared.ground_truth,
        output_dir="runs/comparison",
        # Thresholds are calibrated on val and must be reported on images val never saw.
        split="test",
        inference=shared.inference,
        auto_gpu=shared.auto_gpu,
        iou_threshold=shared.iou_threshold,
        matching_strategy=shared.matching_strategy,
        q=0.05,
        bootstrap_iterations=10000,
        seed=0,
        clearml=shared.clearml,
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
    # The values every stage below points at. Overriding one of these names the whole run.
    auto_gpu=AutoGpuConf,
    ground_truth="ground_truth.csv",
    splits=["train", "val", "test"],
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
    "report": report_config,
    "compare": compare_config,
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

    # The pipeline fills its candidate side in from the model it just trained, so only the
    # standalone comparison offers a candidate_model group.
    for group, model_conf in (
        ("baseline_model", BaselineModelConf),
        ("candidate_model", CandidateModelConf),
        ("compare/baseline_model", BaselineModelConf),
    ):
        model_store = store(group=group)
        model_store(model_conf, name="clearml")
        model_store(ModelLocalConf, name="local")

    for stage, factory in STAGE_CONFIG_FACTORIES.items():
        store(factory(STANDALONE), name=stage)
        store(factory(PIPELINE), group=stage, name="default")

    store(GroundTruthConf, name="ground_truth")
    store(PipelineConf, name="pipeline")


register_configs()
