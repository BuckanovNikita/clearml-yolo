"""Coordinate scientific evaluation and artifact rendering through independent ports."""

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

import pandas as pd
from pydantic import JsonValue

from clearml_yolo.application.ports import TaskHandle, WorkflowDependencies
from clearml_yolo.core.evaluation.models import EvaluatedSplit
from clearml_yolo.core.identity import IdentityLinks, ModelIdentity


def evaluate_split(
    ground_truth: pd.DataFrame,
    raw_predictions: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    split: str,
    classes: list[str],
    thresholds: Mapping[str, float | int],
    required_classes: list[str] | None,
    iou_threshold: float,
    matching_strategy: str,
    ap_method: str,
    skip_cohen_kappa: bool,
    methodology: Mapping[str, JsonValue] | None = None,
    source_ground_truth: pd.DataFrame | None = None,
    source_predictions: pd.DataFrame | None = None,
    model_identity: ModelIdentity | None = None,
    output_dir: Path,
    suffix: str,
    dashboard_classes: set[str] | None = None,
    task: TaskHandle | None = None,
    deps: WorkflowDependencies,
) -> EvaluatedSplit:
    with deps.resources.trace_operation("evaluation.split", context={"split": split}):
        computed = deps.evaluation.compute_evaluation(
            ground_truth,
            raw_predictions,
            predictions,
            split=split,
            classes=classes,
            thresholds=thresholds,
            required_classes=required_classes,
            iou_threshold=iou_threshold,
            matching_strategy=matching_strategy,
            ap_method=ap_method,
            skip_cohen_kappa=skip_cohen_kappa,
            methodology=methodology,
            source_ground_truth=source_ground_truth,
            source_predictions=source_predictions,
            model_identity=model_identity,
        )
        populations = deps.tracking.population_counts(model_identity)
        computed = replace(
            computed,
            training_counts=populations.get("train") if populations is not None else None,
            population_counts=populations,
        )
        artifacts = deps.evaluation_writer.render_evaluation(
            computed,
            output_dir=output_dir,
            suffix=suffix,
            dashboard_classes=dashboard_classes,
            links=None if model_identity is None else deps.tracking.identity_links(task, model_identity),
        )
        return EvaluatedSplit.from_parts(computed, artifacts)


def identity_links(
    task: TaskHandle | None, identities: Mapping[str, ModelIdentity], *, deps: WorkflowDependencies
) -> dict[str, IdentityLinks]:
    """Resolve footer links for source identities from the invocation's own task session."""
    return {role: deps.tracking.identity_links(task, identity) for role, identity in identities.items()}
