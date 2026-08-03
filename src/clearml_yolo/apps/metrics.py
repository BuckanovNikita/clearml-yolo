"""CLI: compute per-split detection metrics."""

from __future__ import annotations

from hydra_zen import store, zen

import clearml_yolo.configs  # noqa: F401  registers every config
from clearml_yolo.tasks.metrics import compute_metrics


def main() -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    zen(compute_metrics).hydra_main(config_name="metrics", config_path=None, version_base="1.3")


if __name__ == "__main__":
    main()
