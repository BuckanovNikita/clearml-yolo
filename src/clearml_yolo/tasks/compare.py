"""Compare two models on today's images, without retraining either of them.

Every input is a ClearML task or a local checkpoint, so this runs long after the
training that produced them and on a machine that has neither model on disk. Both
checkpoints are re-inferred over the *current* ground truth rather than compared through
their stored dashboards: those were computed on whatever images each run happened to
see, and differences between image sets read exactly like differences between models.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from loguru import logger
from pydantic import BaseModel, Field

from clearml_yolo import artifact_names
from clearml_yolo.clearml_models import (
    fetch_best_confidences,
    latest_completed_task_id,
    resolve_task_weights,
)
from clearml_yolo.clearml_report import report_comparison
from clearml_yolo.clearml_session import ClearMLConfig, init_task
from clearml_yolo.comparison.assemble import ComparisonTables, build_comparison_rows
from clearml_yolo.comparison.reinfer import VocabularyReport, reinfer_split
from clearml_yolo.comparison.scoring import score_split
from clearml_yolo.comparison.workbook import write_comparison_workbook
from clearml_yolo.gpu import AutoGpuConfig, resolve_inference
from clearml_yolo.inference import is_cuda_device, resolution_of, trained_imgsz

ModelSource = Literal["clearml", "local"]


class NoBaselineModelError(LookupError):
    """There is no previous model to compare against — a first run, not a mistake.

    Distinct from the ValueError a misconfigured ModelRef raises, so a pipeline can skip
    the comparison on the former without swallowing the latter.
    """


class ModelRef(BaseModel):
    """One side of the comparison: a ClearML task, or a checkpoint already on disk.

    With ``source='clearml'`` and no ``task_id``, the most recently finished task tagged
    ``prod`` is used, so a pipeline run compares itself against what is actually in
    production rather than against whatever ran last — which is as likely to be a failed
    experiment as a released model. Tag a run with ``clearml.tags=[prod]`` to promote it.
    """

    source: ModelSource = "clearml"
    task_id: str | None = None
    project_name: str | None = None
    task_name: str | None = None
    tags: list[str] = Field(default_factory=lambda: ["prod"])
    weights: Path | None = None
    # Thresholds are read from the task that calibrated them. Setting them here instead
    # is for models whose metrics stage never ran.
    thresholds: dict[str, float] | None = None


def _resolved_task_id(model: ModelRef, fallback_project: str | None) -> str:
    if model.task_id:
        return model.task_id
    project = model.project_name or fallback_project
    if not project:
        raise ValueError("source='clearml' needs task_id=<id> or a project to search")
    found = latest_completed_task_id(project, model.task_name, model.tags)
    if found is None:
        tagged = f" tagged {model.tags}" if model.tags else ""
        raise NoBaselineModelError(
            f"No completed ClearML task in project {project!r}{tagged} to compare against. "
            "Promote a run with clearml.tags=[prod], name one with "
            "compare.baseline_model.task_id=<id>, or clear compare.baseline_model.tags=[] "
            "to fall back to the last finished run."
        )
    return found


def _resolve_model(
    model: ModelRef, split: str, fallback_project: str | None
) -> tuple[Path, dict[str, float]]:
    """Locate one side's checkpoint and the thresholds it was calibrated at.

    The task is looked up once for both, so a project-wide search cannot resolve the
    weights of one run and the thresholds of another.
    """
    if model.source == "local":
        if model.weights is None:
            raise ValueError("source='local' needs weights=/path/to/best.pt")
        if model.thresholds is None:
            raise ValueError(
                "A local model carries no calibrated thresholds; set "
                "thresholds={class: conf} or point at the ClearML task whose metrics "
                "stage calibrated them."
            )
        return model.weights, model.thresholds

    task_id = _resolved_task_id(model, fallback_project)
    thresholds = (
        model.thresholds if model.thresholds is not None else fetch_best_confidences(task_id, split)
    )
    return resolve_task_weights(task_id), thresholds


class InferenceConfig(BaseModel):
    """How both checkpoints are re-run. Identical for the two, by construction.

    ``imgsz`` unset is read from the checkpoints themselves, and ``batch`` unset is sized
    by the GPU policy. ``model`` names the architecture under test, which is what a batch
    table is keyed by; the baseline may be a heavier model than the candidate, and if so
    the batch that suits it has to be set here by hand.
    """

    conf: float = 0.001
    iou: float = 0.7
    imgsz: int | None = None
    batch: int | None = None
    model: str | None = None
    device: str | None = None
    image_name: str = "name"
    reuse_existing: bool = True


class SettledInference(BaseModel):
    """The same settings once every "work this out for me" has been worked out.

    A type of its own rather than the config with narrower fields, because the difference
    is load-bearing: the prediction cache is named after these values, so everything that
    reads them has to run after they are decided and nothing may run before.
    """

    conf: float
    iou: float
    imgsz: int
    batch: int
    device: str | None
    image_name: str
    reuse_existing: bool


class CompareResult(BaseModel):
    """Where the comparison landed, and what it could not compare."""

    workbook: Path
    classes_compared: int
    classes_excluded: int
    degraded_classes: list[str] = Field(default_factory=list)


def _prediction_cache(
    destination: Path, role: str, split: str, weights: Path, inference: SettledInference
) -> Path:
    """Name a re-inference cache after the checkpoint and the settings that filled it.

    Keyed on the role alone, a second comparison in the same output directory reused the
    first one's predictions for whatever model it was now given — scoring one checkpoint's
    detections under another's name, which is precisely the substitution this whole
    comparison exists to remove. Size and modification time are part of the key so a
    retrained ``best.pt`` at an unchanged path is not mistaken for the old one, and the
    inference settings are part of it so predictions taken at one confidence, resolution or
    numeric precision are never compared against predictions taken at another. Precision
    matters here because the cache outlives a run: a warm FP32 cache from before half
    precision became the default would otherwise be scored against fresh FP16 detections.

    ``batch`` is among those settings, contrary to the intuition that it is only a memory
    knob. Ultralytics letterboxes each batch according to whether its images happen to
    share a shape, so the batch an image travelled in decides the geometry it was seen at
    — see the inference module's docstring.
    """
    identity = str(weights.resolve())
    if weights.is_file():
        stat = weights.stat()
        identity = f"{identity}:{stat.st_size}:{stat.st_mtime_ns}"
    identity = (
        f"{identity}:conf={inference.conf}:iou={inference.iou}:imgsz={inference.imgsz}"
        f":batch={inference.batch}:accelerated={is_cuda_device(inference.device)}"
    )
    digest = hashlib.sha256(identity.encode()).hexdigest()[:12]
    return destination / f"{role}_predictions_{split}_{digest}.csv"


def _scored(
    weights: Path,
    ground_truth: pd.DataFrame,
    split: str,
    output: Path,
    inference: SettledInference,
    thresholds: dict[str, float],
    classes: list[str],
    evaluation: dict[str, Any],
) -> tuple[Any, VocabularyReport]:
    predictions, vocabulary = reinfer_split(
        weights,
        ground_truth,
        split,
        output,
        conf=inference.conf,
        iou=inference.iou,
        imgsz=inference.imgsz,
        batch=inference.batch,
        device=inference.device,
        image_name=inference.image_name,
        reuse_existing=inference.reuse_existing,
    )
    split_truth = ground_truth[ground_truth["split"] == split].reset_index(drop=True)
    outcome = score_split(
        split_truth,
        predictions.reset_index(drop=True),
        classes,
        thresholds,
        iou_threshold=evaluation["iou_threshold"],
        matching_strategy=evaluation["matching_strategy"],
    )
    return outcome, vocabulary


def _settled(
    inference: InferenceConfig,
    auto_gpu: AutoGpuConfig | None,
    candidate: Path,
    baseline: Path,
) -> SettledInference:
    """Fill in every setting the two models are re-run under, once, for both of them.

    The card is resolved here rather than per model, because re-inferring the two on
    different hardware would put exactly the kind of difference this comparison exists to
    remove inside its own measurement. The resolution comes from the candidate, the model
    under test; if the baseline was trained at another one then no single number is fair
    to both, and that is said out loud rather than chosen silently.
    """
    selection = resolve_inference(
        auto_gpu, inference.device, inference.batch, model=inference.model, stage="predict"
    )
    imgsz = resolution_of(candidate, inference.imgsz)
    was_baseline_trained_at = trained_imgsz(baseline)
    if was_baseline_trained_at is not None and was_baseline_trained_at != imgsz:
        logger.warning(
            "The baseline was trained at imgsz {} and the candidate at {}; both are being "
            "re-inferred at {}, so part of any difference between them is the resolution",
            was_baseline_trained_at,
            imgsz,
            imgsz,
        )
    return SettledInference(
        **{
            **inference.model_dump(exclude={"model"}),
            "device": selection.device_name,
            "batch": selection.batch,
            "imgsz": imgsz,
        }
    )


def _degraded(tables: ComparisonTables) -> list[str]:
    per_class = tables.rows[~tables.rows["is_pooled"].astype(bool)]
    is_degraded = per_class["precision_verdict"].eq("degraded") | per_class["recall_verdict"].eq(
        "degraded"
    )
    return [str(name) for name in per_class.loc[is_degraded, "class_name"]]


def compare(
    baseline_model: ModelRef,
    candidate_model: ModelRef,
    ground_truth: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    inference: InferenceConfig,
    auto_gpu: AutoGpuConfig | None = None,
    split: str = "test",
    iou_threshold: float = 0.5,
    matching_strategy: str = "iou_prior",
    q: float = 0.05,
    bootstrap_iterations: int = 10_000,
    seed: int = 0,
) -> CompareResult:
    """Score both models on one split at their own frozen thresholds and report the diff."""
    task = init_task(clearml, stage="compare")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    truth = pd.read_csv(ground_truth)
    project = clearml.project_name if clearml.enabled else None
    baseline_weights, thresholds_baseline = _resolve_model(baseline_model, split, project)
    candidate_weights, thresholds_candidate = _resolve_model(candidate_model, split, project)
    if baseline_weights == candidate_weights:
        # Two lookups can land on one task — both sides searching a project by tag, say.
        # Every delta is then exactly zero, which reads as "the new model changed nothing"
        # rather than as the configuration mistake it is.
        raise ValueError(
            f"Both sides of the comparison resolved to the same checkpoint "
            f"({candidate_weights}), so there is nothing to compare. Name the two models "
            "explicitly with baseline_model.task_id and candidate_model.task_id."
        )

    settled = _settled(inference, auto_gpu, candidate_weights, baseline_weights)
    evaluation = {"iou_threshold": iou_threshold, "matching_strategy": matching_strategy}
    classes = sorted({str(label) for label in truth[truth["split"] == split]["instance_label"]})

    baseline_outcome, baseline_vocabulary = _scored(
        baseline_weights,
        truth,
        split,
        _prediction_cache(destination, "baseline", split, baseline_weights, settled),
        settled,
        thresholds_baseline,
        classes,
        evaluation,
    )
    candidate_outcome, candidate_vocabulary = _scored(
        candidate_weights,
        truth,
        split,
        _prediction_cache(destination, "candidate", split, candidate_weights, settled),
        settled,
        thresholds_candidate,
        classes,
        evaluation,
    )

    images = truth[truth["split"] == split]["image_name"].unique().tolist()
    tables = build_comparison_rows(
        baseline_outcome,
        candidate_outcome,
        thresholds_baseline=thresholds_baseline,
        thresholds_candidate=thresholds_candidate,
        images=images,
        baseline_classes=set(baseline_vocabulary.model_classes),
        candidate_classes=set(candidate_vocabulary.model_classes),
        q=q,
        iterations=bootstrap_iterations,
        seed=seed,
    )
    tables.methodology["baseline_weights"] = str(baseline_weights)
    tables.methodology["candidate_weights"] = str(candidate_weights)
    tables.methodology["split"] = split
    tables.methodology["iou_threshold"] = iou_threshold
    tables.methodology["matching_strategy"] = matching_strategy

    workbook = destination / f"{artifact_names.COMPARISON_WORKBOOK_PREFIX}_{split}.xlsx"
    write_comparison_workbook(tables.rows, tables.excluded, tables.methodology, workbook)
    report_comparison(task, split, tables.rows, tables.methodology)
    if task is not None:
        task.upload_artifact(
            name=artifact_names.per_split(artifact_names.COMPARISON_WORKBOOK_PREFIX, split),
            artifact_object=workbook,
        )

    degraded = _degraded(tables)
    logger.info(
        "Comparison of split {!r}: {} classes compared, {} excluded, {} degraded",
        split,
        len(tables.rows) - 1,
        len(tables.excluded),
        len(degraded),
    )
    return CompareResult(
        workbook=workbook,
        classes_compared=len(tables.rows) - 1,
        classes_excluded=len(tables.excluded),
        degraded_classes=degraded,
    )
