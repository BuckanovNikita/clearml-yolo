"""CLI: ground truth."""

from __future__ import annotations

from clearml_yolo.apps.common import launch
from clearml_yolo.tasks.ground_truth import ground_truth


def main() -> None:
    launch("ground_truth", ground_truth)


if __name__ == "__main__":
    main()
