"""CLI: run inference and write a predictions table."""

from __future__ import annotations

from hydra_zen import store, zen

import clearml_yolo.configs  # noqa: F401  registers every config
from clearml_yolo.configs import absorb_force_gpu_flag
from clearml_yolo.tasks.predict import predict


def main() -> None:
    absorb_force_gpu_flag()
    store.add_to_hydra_store(overwrite_ok=True)
    zen(predict).hydra_main(config_name="predict", config_path=None, version_base="1.3")


if __name__ == "__main__":
    main()
