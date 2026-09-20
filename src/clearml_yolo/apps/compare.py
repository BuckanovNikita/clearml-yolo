"""CLI: compare."""

from __future__ import annotations

from clearml_yolo.apps.common import launch
from clearml_yolo.tasks.compare import compare


def main() -> None:
    launch("compare", compare)


if __name__ == "__main__":
    main()
