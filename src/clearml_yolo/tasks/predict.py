"""Predict dataset images with native settings and persist the evaluation table."""

from __future__ import annotations

from datetime import UTC, datetime
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
    connect_config_file,
    expect_artifacts,
    init_task,
    sanitize_configuration,
    upload_artifact,
)
from clearml_yolo.inference import ImageNameMode, ScoredResolution, predict_on_images, resolution_of
from clearml_yolo.run_identity import RUNS_ROOT, resolve_run_dir, resolve_run_id


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
) -> PredictResult:
    task = init_task(clearml, stage="predict")
    expect_artifacts(
        task,
        [
            artifact_names.PREDICTIONS,
            "ground_truth",
            "predict_image_membership",
            "predict_effective_arguments",
            "predict_model_reference",
            "predict_output_locations",
        ],
    )
    settings = dict(ultralytics)
    native_model = settings.pop("model", None)
    if weights is not None and native_model is not None and str(weights) != str(native_model):
        raise ValueError("weights conflicts with ultralytics.model")
    selected = weights or native_model
    if selected is None:
        raise ValueError("Prediction requires weights=<checkpoint> or ultralytics.model")
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
        directory = resolve_run_dir(
            RUNS_ROOT, resolve_run_id(clearml.task_name, None, datetime.now(tz=UTC)), None
        )
        output = directory / "predictions.csv"
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    settings.setdefault("project", str(output_path.parent.resolve() / "native"))
    settings.setdefault("name", "predict")
    truth = pd.read_csv(ground_truth, dtype={"image_name": str, "instance_label": str})
    paths = images_to_score(truth, splits)
    # Native rectangular padding depends on batch membership. Keep each split's
    # batches identical to standalone current-test comparison inference.
    groups = (
        [images_to_score(truth, [split]) for split in dict.fromkeys(splits)] if splits else [paths]
    )
    frames = [
        predict_on_images(checkpoint, group, image_name=image_name, **settings) for group in groups
    ]
    effective = frames[0].attrs.get("effective_args", settings)
    frame = pd.concat(frames, ignore_index=True)

    frame.to_csv(output_path, index=False)
    upload_artifact(task, artifact_names.PREDICTIONS, output_path)
    upload_artifact(task, "ground_truth", Path(ground_truth))
    upload_artifact(task, "predict_image_membership", {"images": paths})
    upload_artifact(task, "predict_effective_arguments", sanitize_configuration(effective))
    upload_artifact(task, "predict_model_reference", {"weights": str(checkpoint)})
    upload_artifact(
        task,
        "predict_output_locations",
        {
            "table": str(output_path.resolve()),
            "native": [item.attrs.get("save_dir") for item in frames],
        },
    )
    upload_artifact(
        task,
        "predict_effective_arguments_by_split",
        sanitize_configuration(
            {
                str(index): item.attrs.get("effective_args", settings)
                for index, item in enumerate(frames)
            }
        ),
    )
    _publish_native_outputs(task, frames)
    logger.info("Wrote {} predictions to {}", len(frame), output_path)
    return PredictResult(predictions=output_path, resolution=resolution, effective_args=effective)


def _publish_native_outputs(task: Any, frames: list[pd.DataFrame]) -> None:
    """Store native label/config outputs; source-containing rendered images stay local."""
    directories = {str(frame.attrs["save_dir"]) for frame in frames if frame.attrs.get("save_dir")}
    for index, directory in enumerate(sorted(directories)):
        root = Path(directory)
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in {".txt", ".csv", ".json", ".yaml", ".yml"}:
                continue
            name = f"predict_native_{index}_" + path.relative_to(root).as_posix().replace("/", "_")
            if path.suffix in {".json", ".yaml", ".yml"}:
                connect_config_file(task, name, path, allow_remote_override=False)
            else:
                upload_artifact(task, name, path)
