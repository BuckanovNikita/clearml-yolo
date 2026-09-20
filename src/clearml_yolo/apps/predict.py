"""CLI: predict."""

from __future__ import annotations

from clearml_yolo.apps.common import launch
from clearml_yolo.tasks.predict import predict


def main() -> None:
    launch("predict", predict)


if __name__ == "__main__":
    main()
