"""CLI: pipeline."""

from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment,
)


def main() -> None:
    initialize_runtime_environment()
    from clearml_yolo.application.use_cases.pipeline import run_pipeline
    from clearml_yolo.entrypoints.hydra.common import launch

    launch("pipeline", run_pipeline)


if __name__ == "__main__":
    main()
