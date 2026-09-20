"""CLI: metrics."""

from __future__ import annotations

from clearml_yolo.apps.common import launch
from clearml_yolo.tasks.metrics import compute_metrics


def main() -> None:
    launch("metrics", compute_metrics)


if __name__ == "__main__":
    main()
