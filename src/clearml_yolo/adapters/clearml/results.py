"""Collect durable result contexts and publish canonical CSVs at owner completion."""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from clearml_yolo.adapters.clearml.report import report_confusion_matrices, report_pr_curves
from clearml_yolo.adapters.clearml.session import (
    expect_artifacts,
    invocation_resource,
    register_finalizer,
    upload_artifact,
)
from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.storage.filesystem import write_path
from clearml_yolo.core import artifact_names
from clearml_yolo.core.evaluation.models import EvaluatedSplit
from clearml_yolo.core.evaluation.result_rows import (
    assign_source_ids,
    build_ground_truth_rows,
    build_prediction_rows,
)
from clearml_yolo.core.evaluation.schema import ResultContext
from clearml_yolo.core.identity import ModelIdentity


def file_digest(path: Path) -> str:
    """Hash producer bytes without loading checkpoints into memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _provenance_path(predictions: Path) -> Path:
    return predictions.with_suffix(predictions.suffix + ".provenance.json")


def write_prediction_provenance(
    predictions: Path,
    checkpoint: Path,
    model_identity: ModelIdentity | None = None,
) -> str | None:
    """Bind prediction bytes to a local checkpoint, when one is available."""
    checkpoint_hash = file_digest(checkpoint) if checkpoint.is_file() else None
    if model_identity is not None and model_identity.checkpoint_sha256 != checkpoint_hash:
        raise ValueError("Model identity does not match prediction checkpoint bytes")
    _provenance_path(predictions).write_text(
        json.dumps(
            {
                "predictions_sha256": file_digest(predictions),
                "checkpoint_sha256": checkpoint_hash,
                "model_identity": model_identity.model_dump() if model_identity else None,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return checkpoint_hash


def prediction_checkpoint_hash(predictions: Path) -> str | None:
    """Reject stale provenance instead of assigning thresholds to another checkpoint."""
    path = _provenance_path(predictions)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("predictions_sha256") != file_digest(
        predictions
    ):
        raise ValueError("Prediction provenance does not match prediction CSV bytes")
    digest = payload.get("checkpoint_sha256")
    if digest is not None and (
        not isinstance(digest, str)
        or len(digest) != hashlib.sha256().digest_size * 2
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError("Prediction provenance contains an invalid checkpoint hash")
    return digest


def prediction_model_identity(predictions: Path) -> ModelIdentity | None:
    """Read only source identity associated with these exact prediction bytes."""
    checkpoint_hash = prediction_checkpoint_hash(predictions)
    path = _provenance_path(predictions)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("model_identity") is None:
        return None
    identity = ModelIdentity.model_validate(payload["model_identity"])
    if identity.checkpoint_sha256 != checkpoint_hash:
        raise ValueError("Prediction model identity does not match its checkpoint association")
    return identity


def _read_rows(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype={
            "image_name": str,
            "instance_label": str,
            "split": str,
            "source_row_id": str,
            "object_id": str,
            "context_id": str,
            "model_id": str,
            "model_name": str,
            "training_task_id": str,
            "checkpoint_sha256": str,
        },
        float_precision="round_trip",
    )


@trace_operation("clearml.results.csv.write")
def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(".pending")
    frame.to_csv(pending, index=False, float_format="%.17g")
    pending.replace(path)


@dataclass
class _ResultBundle:
    task: Any
    directory: Path
    truth: Path | None = None
    contexts: dict[tuple[str, str], tuple[ResultContext, Path]] = field(default_factory=dict)
    prediction_expected: bool = False
    plot_slots: dict[tuple[str, str, str], str] = field(default_factory=dict)

    def display_label(self, context: ResultContext, predictions: Path, role: str) -> str:
        identity = context.model_identity
        checkpoint = identity.checkpoint_sha256 if identity else None
        checkpoint = checkpoint or prediction_checkpoint_hash(predictions)
        model_id = (identity.model_id if identity else None) or context.model_id
        if checkpoint:
            source = ("checkpoint", checkpoint, context.split)
        elif model_id and model_id != "unidentified":
            source = ("model", model_id, context.split)
        else:
            source = ("context", context.context_id, context.split)
        existing = self.plot_slots.get(source)
        if existing is not None:
            return existing
        name = identity.model_name if identity else "Current model"
        base = f"{name} · {context.split}"
        label = base
        if label in self.plot_slots.values():
            stage = {
                "prediction": "Prediction",
                "comparison_candidate": "Comparison candidate",
            }.get(role, "Evaluation")
            label = f"{base} · {stage}"
            ordinal = 2
            while label in self.plot_slots.values():
                label = f"{base} · {stage} {ordinal}"
                ordinal += 1
        self.plot_slots[source] = label
        return label

    def set_truth(self, path: Path) -> pd.DataFrame:
        frame = assign_source_ids(_read_rows(path), row_type="ground_truth")
        destination = self.directory / "gt_csv.csv"
        if self.truth is None:
            expect_artifacts(self.task, [artifact_names.GROUND_TRUTH])
        elif not frame.equals(_read_rows(self.truth)):
            raise ValueError("One invocation cannot publish conflicting effective ground truth")
        _atomic_csv(frame, destination)
        self.truth = destination
        return frame

    def put(self, context: ResultContext, rows: pd.DataFrame) -> None:
        if not self.prediction_expected:
            expect_artifacts(self.task, [artifact_names.PREDICTIONS])
            self.prediction_expected = True
        key = (context.context_id, context.split)
        encoded = json.dumps(key, ensure_ascii=False).encode()
        path = self.directory / "contexts" / f"{hashlib.sha256(encoded).hexdigest()}.csv"
        values = context.model_dump(exclude={"model_identity"})
        if context.model_identity is not None:
            values.update(
                model_name=context.model_identity.model_name,
                training_task_id=context.model_identity.training_task_id,
                checkpoint_sha256=context.model_identity.checkpoint_sha256,
            )
        output = rows.assign(**values)
        _atomic_csv(output, path)
        self.contexts[key] = context, path
        # Persist the index too: failures leave both the shards and their identities.
        manifest = self.directory / "contexts.json"
        manifest.write_text(
            json.dumps(
                [
                    context.model_dump() | {"path": str(path)}
                    for _, (context, path) in sorted(self.contexts.items())
                ],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    @trace_operation("clearml.results.finalize")
    def finalize(self) -> None:
        if self.truth is not None:
            upload_artifact(self.task, artifact_names.GROUND_TRUTH, self.truth)
        if self.prediction_expected:
            with trace_operation("clearml.results.csv.assemble"):
                frames = [_read_rows(path) for _, (_, path) in sorted(self.contexts.items())]
                combined = pd.concat(frames, ignore_index=True)
                destination = self.directory / "predicts_csv.csv"
                _atomic_csv(combined, destination)
            upload_artifact(self.task, artifact_names.PREDICTIONS, destination)


def _bundle(task: Any, output_dir: Path) -> _ResultBundle:
    def create() -> _ResultBundle:
        bundle = _ResultBundle(task, write_path(output_dir) / "result_publication")
        register_finalizer(task, bundle.finalize)
        return bundle

    return invocation_resource(task, "clearml_results", create)


def register_ground_truth(task: Any, ground_truth: Path, *, output_dir: Path) -> None:
    """Retain only the effective dataset, never rejected preparation input rows."""
    if task is not None:
        _bundle(task, output_dir).set_truth(ground_truth)


def _context_id(predictions: Path, role: str) -> str:
    digest = hashlib.sha256(str(predictions.resolve()).encode()).hexdigest()[:20]
    return f"{role}:{digest}"


def _context(
    bundle: _ResultBundle,
    predictions: Path,
    role: str,
    split: str,
    model_id: str | None,
    model_identity: ModelIdentity | None = None,
) -> ResultContext:
    identity = _context_id(predictions, role)
    existing = bundle.contexts.get((identity, split))
    if existing is not None:
        previous = existing[0]
        if model_id is not None and model_id != previous.model_id:
            raise ValueError("Prediction context cannot change model identity")
        if model_identity is not None and previous.model_identity != model_identity:
            raise ValueError("Prediction context cannot change source identity")
        return previous
    return ResultContext(
        context_id=identity,
        model_id=model_id or "unidentified",
        split=split,
        model_identity=model_identity,
    )


def register_predictions(
    task: Any,
    ground_truth: Path,
    predictions: Path,
    *,
    output_dir: Path,
    model_id: str | None = None,
    role: str = "prediction",
    splits: list[str] | None = None,
    model_identity: ModelIdentity | None = None,
) -> None:
    """Persist not-evaluated rows until a later evaluation enriches the same context."""
    if task is None:
        return
    bundle = _bundle(task, output_dir)
    truth = bundle.set_truth(ground_truth)
    source = assign_source_ids(_read_rows(predictions), row_type="prediction")
    model_identity = model_identity or prediction_model_identity(predictions)
    if model_id is None and (checkpoint_hash := prediction_checkpoint_hash(predictions)):
        model_id = f"checkpoint:{checkpoint_hash}"
    selected = splits if splits is not None else list(truth["split"].dropna().unique())
    for split in selected:
        context = _context(bundle, predictions, role, str(split), model_id, model_identity)
        if (context.context_id, context.split) in bundle.contexts:
            continue
        scoped_truth = truth[truth["split"] == split]
        if scoped_truth.empty:
            raise ValueError(f"No ground-truth rows for split {split!r}")
        scoped_source = source[source["image_name"].isin(scoped_truth["image_name"])]
        rows = pd.concat(
            [
                build_ground_truth_rows(scoped_truth),
                build_prediction_rows(scoped_source, split=str(split)),
            ],
            ignore_index=True,
        )
        bundle.put(context, rows)
    scoped_images = truth.loc[truth["split"].isin(selected), "image_name"]
    outside = source[~source["image_name"].isin(scoped_images)]
    if not outside.empty:
        context = _context(
            bundle,
            predictions,
            f"{role}:unassigned",
            "unassigned",
            model_id,
            model_identity,
        )
        rows = build_prediction_rows(outside, split=context.split)
        rows["exclusion_reason"] = "outside_selected_splits"
        bundle.put(context, rows)


def publish_evaluation(
    task: Any,
    evaluated: EvaluatedSplit,
    ground_truth: Path,
    predictions: Path,
    *,
    output_dir: Path,
    model_id: str | None = None,
    role: str = "prediction",
) -> None:
    """Publish exact upstream dashboards/plots and enrich the durable CSV context."""
    if task is None:
        return
    bundle = _bundle(task, output_dir)
    bundle.set_truth(ground_truth)
    context = _context(
        bundle,
        predictions,
        role,
        evaluated.split,
        model_id,
        evaluated.model_identity,
    )
    bundle.put(context, evaluated.result_rows)
    stem = "metrics" if role == "prediction" else role
    names = {
        artifact_names.per_split(
            f"{stem}_dashboard_full", evaluated.split
        ): evaluated.dashboard_path,
        artifact_names.per_split(
            f"{stem}_dashboard_dtrk", evaluated.split
        ): evaluated.dtrk_dashboard_path,
    }
    expect_artifacts(task, list(names))
    for name, path in names.items():
        upload_artifact(task, name, path)
    if role != "comparison_baseline":
        display_label = bundle.display_label(context, predictions, role)
        report_confusion_matrices(
            task,
            context,
            evaluated.confusion_matrix,
            display_label=display_label,
        )
        if context.split == "test":
            report_pr_curves(task, context, evaluated.pr_curves, display_label=display_label)
