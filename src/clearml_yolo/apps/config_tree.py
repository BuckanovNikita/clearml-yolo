"""CLI: write the full default configuration into a directory the user can edit.

Plain argparse rather than a Hydra app on purpose: a Hydra app would spin up its own
output directory and logging just to write a config file, and it cannot take a bare
positional path.
"""

from __future__ import annotations

import argparse

from clearml_yolo.config_tree import dump_config_tree


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("directory", help="where to write the config files")
    parser.add_argument(
        "--force", action="store_true", help="overwrite config files that are already there"
    )
    arguments = parser.parse_args()
    dump_config_tree(arguments.directory, overwrite=arguments.force)


if __name__ == "__main__":
    main()
