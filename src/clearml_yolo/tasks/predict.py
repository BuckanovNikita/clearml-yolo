"""Predict dataset images with native settings and persist the evaluation table."""

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
from clearml_yolo.native_config import prediction_settings, write_native_yaml
from clearml_yolo.publishing import create_publisher
from clearml_yolo.publishing.models import FiftyOneConfig
from clearml_yolo.run_identity import RUNS_ROOT, resolve_run_dir, resolve_run_id
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
        directory = resolve_run_dir(
            RUNS_ROOT, resolve_run_id(clearml.task_name, None, datetime.now(tz=UTC)), None
        )
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
        _predict_group(task, checkpoint, group, image_name, settings, output_path, index)
        for index, group in enumerate(groups)
    ]
    effective = frames[0].attrs.get("effective_args", settings)
    requested_by_split = {
        str(i): frame.attrs.get("requested_args", settings) for i, frame in enumerate(frames)
    }
    native_shapes = {str(i): frame.attrs.get("normalized_imgsz") for i, frame in enumerate(frames)}
    expect_artifacts(
        task, ["predict_requested_arguments_by_split", "predict_normalized_image_sizes"]
    )
    upload_artifact(
        task, "predict_requested_arguments_by_split", sanitize_configuration(requested_by_split)
    )
    upload_artifact(task, "predict_normalized_image_sizes", native_shapes)
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


def _predict_group(
    task: Any,
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
    requested_path = config_path.with_name(config_path.stem + "_requested.yaml")
    write_native_yaml(requested_path, provisional, "predict")
    requested_name = requested_path.stem
    expect_artifacts(task, [requested_name])
    connect_config_file(task, requested_name, requested_path, allow_remote_override=False)
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
    config_name = "ultralytics_predict" if index == 0 else f"ultralytics_predict_{index}"
    expect_artifacts(task, [config_name])
    connect_config_file(task, config_name, config_path, allow_remote_override=False)
    return frame
