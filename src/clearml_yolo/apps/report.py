"""CLI: report."""

from __future__ import annotations

from clearml_yolo.apps.common import launch
from clearml_yolo.tasks.report import report


def main() -> None:
    launch("report", report)


if __name__ == "__main__":
    main()
