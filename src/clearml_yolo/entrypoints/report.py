"""CLI: report."""

from clearml_yolo.application.use_cases.report import report
from clearml_yolo.entrypoints.hydra.common import launch


def main() -> None:
    launch("report", report)


if __name__ == "__main__":
    main()
