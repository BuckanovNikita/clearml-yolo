"""CLI: compare two trained models on the current test split."""

from __future__ import annotations

from hydra_zen import store, zen

import clearml_yolo.configs  # noqa: F401  registers every config
from clearml_yolo.configs import absorb_force_gpu_flag
from clearml_yolo.tasks.compare import compare


def main() -> None:
    absorb_force_gpu_flag()
    store.add_to_hydra_store(overwrite_ok=True)
    zen(compare).hydra_main(config_name="compare", config_path=None, version_base="1.3")


if __name__ == "__main__":
    main()
