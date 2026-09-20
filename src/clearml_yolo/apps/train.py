"""CLI: train."""

from __future__ import annotations

from clearml_yolo.apps.common import launch
from clearml_yolo.tasks.train import train


def main() -> None:
    launch("train", train)


if __name__ == "__main__":
    main()
