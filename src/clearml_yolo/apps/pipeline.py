"""CLI: pipeline."""

from __future__ import annotations

from clearml_yolo.apps.common import launch
from clearml_yolo.tasks.pipeline import run_pipeline


def main() -> None:
    launch("pipeline", run_pipeline)


if __name__ == "__main__":
    main()
