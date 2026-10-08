"""CLI: pipeline."""

from clearml_yolo.application.use_cases.pipeline import run_pipeline
from clearml_yolo.entrypoints.hydra.common import launch


def main() -> None:
    launch("pipeline", run_pipeline)


if __name__ == "__main__":
    main()
