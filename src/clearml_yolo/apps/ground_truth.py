"""CLI: turn a YOLO dataset yaml into the ground-truth CSV every later stage reads."""

from __future__ import annotations

from hydra_zen import store, zen

import clearml_yolo.configs  # noqa: F401  registers every config
from clearml_yolo.ground_truth import build_ground_truth


def main() -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    zen(build_ground_truth).hydra_main(
        config_name="ground_truth", config_path=None, version_base="1.3"
    )


if __name__ == "__main__":
    main()
