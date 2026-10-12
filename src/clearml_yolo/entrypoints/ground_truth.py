"""CLI: ground truth."""

from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment,
)


def main() -> None:
    initialize_runtime_environment()
    from clearml_yolo.application.use_cases.ground_truth import ground_truth
    from clearml_yolo.entrypoints.hydra.common import launch

    launch("ground_truth", ground_truth)


if __name__ == "__main__":
    main()
