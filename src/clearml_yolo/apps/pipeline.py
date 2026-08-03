"""CLI: run every stage as a single experiment."""

from __future__ import annotations

from hydra_zen import store, zen

import clearml_yolo.configs  # noqa: F401  registers every config
from clearml_yolo.tasks.pipeline import run_pipeline


def main() -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    zen(run_pipeline).hydra_main(config_name="pipeline", config_path=None, version_base="1.3")


if __name__ == "__main__":
    main()
