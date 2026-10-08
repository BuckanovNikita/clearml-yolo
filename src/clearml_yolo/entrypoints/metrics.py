"""CLI: metrics."""

from clearml_yolo.application.use_cases.metrics import compute_metrics
from clearml_yolo.entrypoints.hydra.common import launch


def main() -> None:
    launch("metrics", compute_metrics)


if __name__ == "__main__":
    main()
