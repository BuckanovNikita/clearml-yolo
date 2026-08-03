"""CLI: compare the new model's dashboards against a baseline."""

from __future__ import annotations

from hydra_zen import store, zen

import clearml_yolo.configs  # noqa: F401  registers every config
from clearml_yolo.tasks.report import report


def main() -> None:
    store.add_to_hydra_store(overwrite_ok=True)
    zen(report).hydra_main(config_name="report", config_path=None, version_base="1.3")


if __name__ == "__main__":
    main()
