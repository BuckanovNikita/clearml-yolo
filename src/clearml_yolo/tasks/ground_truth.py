"""Track dataset conversion as its own invocation stage."""

from __future__ import annotations

from pathlib import Path

from clearml_yolo.clearml_session import (
    ClearMLConfig,
    connect_config_file,
    expect_artifacts,
    init_task,
    upload_artifact,
)
from clearml_yolo.ground_truth import build_ground_truth


def ground_truth(
    data_yaml: str,
    output: str,
    clearml: ClearMLConfig,
    test_fraction: float = 0.5,
    seed: int = 0,
) -> Path:
    task = init_task(clearml, stage="ground_truth")
    expect_artifacts(task, ["dataset_configuration", "ground_truth"])
    effective = connect_config_file(task, "dataset_configuration", Path(data_yaml))
    build_ground_truth(str(effective), output, test_fraction=test_fraction, seed=seed)
    upload_artifact(task, "ground_truth", Path(output))
    return Path(output)
