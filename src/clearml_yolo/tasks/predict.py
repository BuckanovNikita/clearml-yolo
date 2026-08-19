"""Run inference over the dataset and persist predictions in digital-metrics' schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger
from pydantic import BaseModel

from clearml_yolo import artifact_names
from clearml_yolo.clearml_models import resolve_weights
from clearml_yolo.clearml_report import report_table
from clearml_yolo.clearml_session import ClearMLConfig, init_task, upload_dataframe
from clearml_yolo.gpu import AutoGpuConfig, remember_batch, resolve_inference
from clearml_yolo.inference import (
    ImageNameMode,
    ScoredResolution,
    is_cuda_device,
    predict_on_images,
    resolution_of,
)
from clearml_yolo.run_identity import LATEST_LINK_NAME, RUNS_ROOT
from clearml_yolo.ultralytics_params import fill_unset

# Where training leaves a checkpoint inside the run directory, relative to that directory.
# The training task spells the same path out of `TRAIN_DIR` and `CHECKPOINT`, and it is a
# sibling this module may not import, so `tests/test_configs.py` holds the two spellings in
# step instead — a shared constant would have to live in a layer neither of them owns.
TRAINED_CHECKPOINT = "detect/{name}/weights/best.pt"


class PredictResult(BaseModel):
    """The predictions table, plus the scale it was produced at.

    The resolution travels with the result for the same reason training's device does: a
    stage that follows inference in the same process would otherwise have to reopen the
    checkpoint to learn what the model was built for. The report stage is the one that
    needs it — the numbers it publishes were measured at ``scored_at``.
    """

    predictions: Path
    resolution: ScoredResolution


def images_to_score(ground_truth: pd.DataFrame, splits: list[str] | None) -> list[str]:
    """The images of the requested splits, each named once.

    Ground truth carries one row per annotation, so an image with twelve boxes would
    otherwise be inferred twelve times.
    """
    if "image_path" not in ground_truth.columns:
        raise ValueError(
            "Ground truth has no 'image_path' column, so there is nothing to run inference "
            f"on. Got columns: {sorted(ground_truth.columns)}"
        )
    rows = ground_truth
    if splits is not None:
        if "split" not in ground_truth.columns:
            raise ValueError(
                f"Splits {splits} were requested but the ground truth has no 'split' column"
            )
        rows = ground_truth[ground_truth["split"].isin(splits)]
        if rows.empty:
            available = sorted({str(value) for value in ground_truth["split"].unique()})
            raise ValueError(f"No ground-truth rows for splits {splits}; available: {available}")
    return [str(path) for path in rows["image_path"].unique()]


def checkpoint_of_last_training(task_name: str) -> Path:
    """The model the last training run of this experiment left, for a run handed no weights.

    Every training run repoints ``runs/latest`` at its own directory, whether it ran as a
    stage of a pipeline or as a standalone ``cy-train``, and writes its checkpoint under the
    ClearML experiment's name. Resolved here, from the name this run was actually given,
    rather than frozen into the config: built once at import it carries the *default*
    experiment name, so ``cy-train clearml.task_name=foo`` followed by a bare ``cy-predict``
    sent the two commands to two different directories.

    Refused rather than passed on, because this path is one this project built and not one
    anybody asked for: unnamed weights that are not there reach ultralytics as a failed
    download of a pretrained model, naming neither the link nor the experiment it looked
    under.
    """
    checkpoint = RUNS_ROOT / LATEST_LINK_NAME / TRAINED_CHECKPOINT.format(name=task_name)
    if checkpoint.is_file():
        return checkpoint
    raise FileNotFoundError(
        f"No checkpoint at {checkpoint}, where training of experiment {task_name!r} would "
        f"have left one. Train first with `cy-train clearml.task_name={task_name}`, or name "
        "the model outright with `weights=<path/to/best.pt>`."
    )


def predict(
    weights: str | Path | None,
    ground_truth: str | Path,
    output: str | Path,
    clearml: ClearMLConfig,
    ultralytics: dict[str, Any],
    auto_gpu: AutoGpuConfig | None = None,
    model: str | None = None,
    splits: list[str] | None = None,
    image_name: ImageNameMode = "name",
) -> PredictResult:
    """Infer over the dataset images and write a predictions CSV.

    ``ultralytics`` is the whole of ``conf/ultralytics/predict.yaml``: every parameter
    ultralytics accepts for detection prediction. Its ``conf`` is deliberately near zero,
    because per-class thresholds are chosen later during evaluation and filtering here
    would discard the detections that calibration needs.

    ``weights`` may be a local checkpoint or a ClearML task id, so inference can be run
    against a previously trained model without that model's files on hand. Left unset it is
    the checkpoint the last training run of this experiment wrote, which is how the
    standalone commands fill one run directory between them. With ``device`` left unset the
    run waits for a free card rather than letting ultralytics grab whichever one it likes.

    ``imgsz`` and ``batch`` left unset are answered by the checkpoint and by ``auto_gpu``
    respectively, so neither has to be repeated from the training that produced the
    weights. ``model`` is not an ultralytics parameter and stays out of that block: it
    names the architecture those weights are of, which is what a batch table is keyed by,
    and nothing is loaded from it.
    """
    # Before the experiment is opened: a run with nothing to load must refuse rather than
    # leave a ClearML task behind that never scored anything.
    checkpoint = (
        resolve_weights(weights)
        if weights is not None
        else checkpoint_of_last_training(clearml.task_name)
    )
    task = init_task(clearml, stage="predict")
    selection = resolve_inference(
        auto_gpu, ultralytics.get("device"), ultralytics.get("batch"), model=model, stage="predict"
    )
    accelerated = is_cuda_device(selection.device_name)

    settings = fill_unset(
        ultralytics,
        # Both scale with model size and both change which boxes come back, so thresholds
        # calibrated with them do not carry over to a run without them.
        quantize=16 if accelerated else 32,
        compile=accelerated,
    )
    settings["batch"] = selection.batch
    settings["device"] = selection.device_name
    resolution = resolution_of(checkpoint, ultralytics.get("imgsz"))
    settings["imgsz"] = resolution.scored_at
    # Published before inference rather than after it, so a run killed part way through
    # still records the scale its partial predictions were produced at.
    report_table(
        task,
        artifact_names.PREDICT_SECTION,
        artifact_names.RESOLUTION_SERIES,
        resolution.as_table(),
    )

    frame = predict_on_images(
        checkpoint,
        images_to_score(pd.read_csv(ground_truth), splits),
        image_name=image_name,
        **settings,
    )

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    logger.info("Wrote {} predictions to {}", len(frame), output_path)

    if auto_gpu is not None:
        remember_batch("predict", model, selection)
    upload_dataframe(task, artifact_names.PREDICTIONS, frame)
    return PredictResult(predictions=output_path, resolution=resolution)
