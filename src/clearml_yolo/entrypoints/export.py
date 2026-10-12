"""CLI: export detector graph, build engine, or verify a deployment bundle."""

from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment,
    project_configuration_imports,
)


def main() -> None:
    initialize_runtime_environment()
    with project_configuration_imports():
        from clearml_yolo.application.use_cases.export import export_model
        from clearml_yolo.entrypoints.hydra.common import launch

    launch("export", export_model)


if __name__ == "__main__":
    main()
