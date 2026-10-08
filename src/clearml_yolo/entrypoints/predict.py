"""CLI: predict."""

from clearml_yolo.application.use_cases.predict import predict
from clearml_yolo.entrypoints.hydra.common import launch


def main() -> None:
    launch("predict", predict)


if __name__ == "__main__":
    main()
