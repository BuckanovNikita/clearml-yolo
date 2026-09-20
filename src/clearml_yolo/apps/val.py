"""CLI: val."""

from __future__ import annotations

from clearml_yolo.apps.common import launch
from clearml_yolo.tasks.val import validate


def main() -> None:
    launch("val", validate)


if __name__ == "__main__":
    main()
