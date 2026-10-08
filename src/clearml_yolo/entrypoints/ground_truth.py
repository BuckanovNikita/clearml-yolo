"""CLI: ground truth."""

from clearml_yolo.application.use_cases.ground_truth import ground_truth
from clearml_yolo.entrypoints.hydra.common import launch


def main() -> None:
    launch("ground_truth", ground_truth)


if __name__ == "__main__":
    main()
