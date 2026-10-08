"""CLI: compare."""

from clearml_yolo.application.use_cases.compare import compare
from clearml_yolo.entrypoints.hydra.common import launch


def main() -> None:
    launch("compare", compare)


if __name__ == "__main__":
    main()
