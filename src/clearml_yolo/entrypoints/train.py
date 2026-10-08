"""CLI: train."""

from clearml_yolo.application.use_cases.train import train
from clearml_yolo.entrypoints.hydra.common import launch


def main() -> None:
    launch("train", train)


if __name__ == "__main__":
    main()
