"""Predict dataset images with native settings and persist the evaluation table."""

__all__ = ["PredictResult"]
from pathlib import Path
from typing import Any

import pandas as pd

from clearml_yolo.application.contracts import (
    PREDICTION_COLUMNS,
    ClearMLConfig,
    ImageNameMode,
    PredictResult,
)
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.application.use_cases.publication import prepare_publisher, publish_results
from clearml_yolo.core import artifact_names
from clearml_yolo.core.identity import require_model_identity
from clearml_yolo.core.publication import FiftyOneConfig


def images_to_score(ground_truth: pd.DataFrame, splits: list[str] | None) -> list[str]:
    if "image_path" not in ground_truth:
        raise ValueError("Ground truth has no 'image_path' column")
    rows = ground_truth
    if splits is not None:
        if "split" not in rows:
            raise ValueError("Ground truth has no 'split' column")
        missing = set(splits) - set(rows["split"].unique())
        if missing:
            raise ValueError(f"No ground-truth rows for splits {sorted(missing)}")
        rows = rows[rows["split"].isin(splits)]
    if rows.empty:
        raise ValueError("No images to predict")
    return sorted(str(path) for path in rows["image_path"].unique())


def predict(
    weights: str | Path | None,
    ground_truth: str | Path,
    output: str | Path | None,
    clearml: ClearMLConfig,
    ultralytics: dict[str, Any],
    splits: list[str] | None = None,
    image_name: ImageNameMode = "name",
    ultralytics_predict: dict[str, Any] | None = None,
    fiftyone: FiftyOneConfig | None = None,
    model_label: str | None = None,
    *,
    deps: WorkflowDependencies,
) -> PredictResult:
    with deps.resources.trace_operation("workflow.predict"):
        task = deps.tracking.init_task(clearml, stage="predict")
        publisher = prepare_publisher(task, fiftyone, factory=deps.publisher_factory, deps=deps)
        deps.model.stage_settings(ultralytics, "train")
        settings = deps.model.prediction_settings(ultralytics_predict or {}, weights)
        selected = settings.pop("model", None)
        if selected is None:
            raise ValueError(
                "Prediction requires weights=<checkpoint> or ultralytics_predict.model"
            )
        checkpoint, source_identity = deps.repository.resolve_weights_with_identity(selected)
        checkpoint_path = Path(checkpoint)
        checkpoint_hash = (
            deps.tracking.file_digest(checkpoint_path)
            if deps.storage.is_file(checkpoint_path)
            else None
        )
        identity = require_model_identity(
            source_identity, model_label, checkpoint_hash=checkpoint_hash
        )
        resolution = deps.model.resolution_of(checkpoint, settings.get("imgsz"))
        settings["imgsz"] = resolution.scored_at
        deps.tracking.report_table(
            task,
            artifact_names.PREDICT_SECTION,
            artifact_names.RESOLUTION_SERIES,
            resolution.as_table(),
            identities={"model": identity},
        )
        if output is None:
            directory = deps.storage.task_run_dir(
                deps.storage.runs_root(), *deps.tracking.task_identity(task)
            )
            output = directory / "predictions.csv"
        output_path = deps.storage.write_path(output)
        deps.storage.mkdir(output_path.parent, parents=True, exist_ok=True)
        settings["project"] = settings.get("project") or str(
            deps.storage.resolve(output_path.parent) / "native"
        )
        settings["name"] = settings.get("name") or "predict"
        deps.storage.write_path(Path(settings["project"]) / str(settings["name"]))
        settings["mode"] = "predict"
        settings.pop("source", None)
        truth = deps.storage.read_csv(
            ground_truth, dtype={"image_name": str, "instance_label": str}
        )
        paths = images_to_score(truth, splits)
        groups = (
            [images_to_score(truth, [split]) for split in dict.fromkeys(splits)]
            if splits
            else [paths]
        )
        frames = [
            _predict_group(checkpoint, group, image_name, settings, output_path, index, deps=deps)
            for index, group in enumerate(groups)
        ]
        effective = frames[0].attrs.get("effective_args", settings)
        frame = pd.concat(frames, ignore_index=True).reindex(columns=PREDICTION_COLUMNS)
        deps.storage.write_csv(frame, output_path, index=False)
        recorded_hash = deps.tracking.write_prediction_provenance(
            output_path, checkpoint_path, identity
        )
        if recorded_hash != checkpoint_hash:
            raise ValueError("Checkpoint changed while producing predictions")
        deps.tracking.register_predictions(
            task,
            Path(ground_truth),
            output_path,
            output_dir=output_path.parent,
            model_id=f"checkpoint:{recorded_hash}" if recorded_hash else str(checkpoint),
            splits=splits,
            model_identity=identity,
        )
        if task is not None:
            deps.tracking.record_run_configuration(
                task,
                {
                    "prediction_result": {
                        "model": str(checkpoint),
                        "model_identity": identity.model_dump(mode="json"),
                        "native_normalization": _native_changes(settings, frames[0]),
                    }
                },
            )
        publish_results(
            publisher,
            task,
            output_dir=output_path.parent,
            ground_truth=ground_truth,
            predictions=output_path,
            prediction_splits=(
                splits
                if splits is not None
                else sorted(str(value) for value in truth["split"].unique())
            )
            if publisher.enabled
            else None,
            prediction_image_name=image_name,
            metadata={"model": str(checkpoint)},
            deps=deps,
        )
        deps.resources.log("INFO", "Wrote {} predictions to {}", len(frame), output_path)
        return PredictResult(
            predictions=output_path,
            resolution=resolution,
            effective_args=effective,
            model_identity=identity,
        )


def _native_changes(settings: dict[str, Any], frame: pd.DataFrame) -> dict[str, Any]:
    effective = frame.attrs.get("effective_args", {})
    changes = {
        key: {"requested": value, "effective": effective[key]}
        for key, value in settings.items()
        if key not in {"project", "name", "source", "model", "mode"}
        and key in effective
        and (value != effective[key])
    }
    normalized = frame.attrs.get("normalized_imgsz")
    requested = settings["imgsz"]
    expected = [requested, requested] if isinstance(requested, int) else list(requested)
    if len(expected) == 1:
        expected *= 2
    if normalized is not None and list(normalized) != expected:
        changes["imgsz"] = {"requested": requested, "effective": normalized}
    return changes


def _predict_group(
    checkpoint: str | Path,
    group: list[str],
    image_name: ImageNameMode,
    settings: dict[str, Any],
    output_path: Path,
    index: int,
    *,
    deps: WorkflowDependencies,
) -> pd.DataFrame:
    with deps.resources.trace_operation("prediction.group"):
        manifest_dir = output_path.parent / "prediction_inputs" / str(index)
        deps.storage.mkdir(manifest_dir, parents=True, exist_ok=True)
        manifest = manifest_dir / "images.txt"
        deps.storage.write_text(
            manifest,
            "\n".join(str(deps.storage.absolute(Path(path))) for path in group),
            encoding="utf-8",
        )
        config_path = output_path.parent / (
            "ultralytics_predict.yaml" if index == 0 else f"ultralytics_predict_{index}.yaml"
        )
        provisional = settings | {
            "source": str(deps.storage.resolve(manifest)),
            "model": str(checkpoint),
            "mode": "predict",
        }
        requested_path = config_path.with_stem(config_path.stem + "_requested")
        deps.model.write_native_yaml(
            requested_path, deps.model.requested_settings(provisional, "predict"), "predict"
        )
        deps.model.write_native_yaml(config_path, provisional, "predict")
        frame = deps.model.predict_on_images(
            checkpoint, group, image_name=image_name, manifest_dir=manifest_dir, **settings
        )
        effective_group = settings | frame.attrs.get("effective_args", {})
        effective_group.update(model=str(checkpoint), mode="predict")
        effective_group["source"] = str(deps.storage.resolve(manifest_dir / "images.txt"))
        config_path = output_path.parent / (
            "ultralytics_predict.yaml" if index == 0 else f"ultralytics_predict_{index}.yaml"
        )
        deps.model.write_native_yaml(config_path, effective_group, "predict")
        return frame
