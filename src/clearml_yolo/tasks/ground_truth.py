"""Track dataset conversion as its own invocation stage."""

from pathlib import Path

from clearml_yolo.clearml_results import register_ground_truth
from clearml_yolo.clearml_session import (
    ClearMLConfig,
    connect_config_file,
    init_task,
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
    effective = connect_config_file(task, "dataset", Path(data_yaml))
    destination = build_ground_truth(str(effective), output, test_fraction=test_fraction, seed=seed)
    register_ground_truth(task, destination, output_dir=destination.parent)
    return destination
