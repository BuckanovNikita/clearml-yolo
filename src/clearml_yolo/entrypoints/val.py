"""CLI: val."""

from clearml_yolo.application.use_cases.val import validate
from clearml_yolo.entrypoints.hydra.common import launch


def main() -> None:
    launch("val", validate)


if __name__ == "__main__":
    main()
