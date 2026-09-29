"""Predict dataset images with native settings and persist the evaluation table."""

from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger
from pydantic import BaseModel, Field

from clearml_yolo import artifact_names
from clearml_yolo.clearml_models import resolve_weights
from clearml_yolo.clearml_report import report_table
from clearml_yolo.clearml_session import (
    ClearMLConfig,
    init_task,
    publish_table,
    record_run_configuration,
    task_identity,
)
from clearml_yolo.inference import (
    PREDICTION_COLUMNS,
    ImageNameMode,
    ScoredResolution,
    predict_on_images,
    resolution_of,
)
from clearml_yolo.native_config import prediction_settings, write_native_yaml
from clearml_yolo.publishing import create_publisher
from clearml_yolo.publishing.models import FiftyOneConfig
from clearml_yolo.run_identity import RUNS_ROOT, task_run_dir
from clearml_yolo.tasks.publication import prepare_publisher, publish_results


class PredictResult(BaseModel):
    predictions: Path
    resolution: ScoredResolution
    effective_args: dict[str, Any] = Field(default_factory=dict)


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
) -> PredictResult:
    task = init_task(clearml, stage="predict")
    publisher = prepare_publisher(task, fiftyone, factory=create_publisher)
    settings = prediction_settings(ultralytics, ultralytics_predict, weights)
    selected = settings.pop("model", None)
    if selected is None:
        raise ValueError("Prediction requires weights=<checkpoint> or ultralytics_predict.model")
    checkpoint = resolve_weights(selected)
    resolution = resolution_of(checkpoint, settings.get("imgsz"))
    settings["imgsz"] = resolution.scored_at
    report_table(
        task,
        artifact_names.PREDICT_SECTION,
        artifact_names.RESOLUTION_SERIES,
        resolution.as_table(),
    )
    if output is None:
        directory = task_run_dir(RUNS_ROOT, *task_identity(task))
        output = directory / "predictions.csv"
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    settings["project"] = settings.get("project") or str(output_path.parent.resolve() / "native")
    settings["name"] = settings.get("name") or "predict"
    settings["mode"] = "predict"
    settings.pop("source", None)
    truth = pd.read_csv(ground_truth, dtype={"image_name": str, "instance_label": str})
    paths = images_to_score(truth, splits)
    # Native rectangular padding depends on batch membership. Keep each split's
    # batches identical to standalone current-test comparison inference.
    groups = (
        [images_to_score(truth, [split]) for split in dict.fromkeys(splits)] if splits else [paths]
    )
    frames = [
        _predict_group(checkpoint, group, image_name, settings, output_path, index)
        for index, group in enumerate(groups)
    ]
    effective = frames[0].attrs.get("effective_args", settings)
    frame = pd.concat(frames, ignore_index=True).reindex(columns=PREDICTION_COLUMNS)

    frame.to_csv(output_path, index=False)
    if task is not None:
        publish_table(task, artifact_names.PREDICTIONS, output_path)
        publish_table(task, artifact_names.GROUND_TRUTH, Path(ground_truth))
        record_run_configuration(
            task,
            {
                "prediction_result": {
                    "model": str(checkpoint),
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
    )
    logger.info("Wrote {} predictions to {}", len(frame), output_path)
    return PredictResult(predictions=output_path, resolution=resolution, effective_args=effective)


def _native_changes(settings: dict[str, Any], frame: pd.DataFrame) -> dict[str, Any]:
    effective = frame.attrs.get("effective_args", {})
    changes = {
        key: {"requested": value, "effective": effective[key]}
        for key, value in settings.items()
        if key not in {"project", "name", "source", "model", "mode"}
        and key in effective
        and value != effective[key]
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
) -> pd.DataFrame:
    manifest_dir = output_path.parent / "prediction_inputs" / str(index)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = manifest_dir / "images.txt"
    manifest.write_text("\n".join(str(Path(path).absolute()) for path in group), encoding="utf-8")
    config_path = output_path.parent / (
        "ultralytics_predict.yaml" if index == 0 else f"ultralytics_predict_{index}.yaml"
    )
    provisional = settings | {
        "source": str(manifest.resolve()),
        "model": str(checkpoint),
        "mode": "predict",
    }
    write_native_yaml(config_path, provisional, "predict")
    frame = predict_on_images(
        checkpoint, group, image_name=image_name, manifest_dir=manifest_dir, **settings
    )
    effective_group = settings | frame.attrs.get("effective_args", {})
    effective_group.update(model=str(checkpoint), mode="predict")
    effective_group["source"] = str((manifest_dir / "images.txt").resolve())
    config_path = output_path.parent / (
        "ultralytics_predict.yaml" if index == 0 else f"ultralytics_predict_{index}.yaml"
    )
    write_native_yaml(config_path, effective_group, "predict")
    return frame
