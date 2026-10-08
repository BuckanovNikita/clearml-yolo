"""Track dataset conversion as its own invocation stage."""

from pathlib import Path

from clearml_yolo.application.contracts import ClearMLConfig
from clearml_yolo.application.ports import WorkflowDependencies


def ground_truth(
    data_yaml: str,
    output: str,
    clearml: ClearMLConfig,
    test_fraction: float = 0.5,
    seed: int = 0,
    *,
    deps: WorkflowDependencies,
) -> Path:
    task = deps.tracking.init_task(clearml, stage="ground_truth")
    effective = deps.tracking.connect_config_file(task, "dataset", Path(data_yaml))
    destination = deps.dataset.build_ground_truth(
        str(effective), output, test_fraction=test_fraction, seed=seed
    )
    deps.tracking.register_ground_truth(task, destination, output_dir=destination.parent)
    return destination
