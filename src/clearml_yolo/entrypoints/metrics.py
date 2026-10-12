"""CLI: metrics."""

from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment,
)


def main() -> None:
    initialize_runtime_environment()
    from clearml_yolo.application.use_cases.metrics import compute_metrics
    from clearml_yolo.entrypoints.hydra.common import launch

    launch("metrics", compute_metrics)


if __name__ == "__main__":
    main()
