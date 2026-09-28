"""CLI: initialize a directory with editable example configurations."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", help="directory for example YAML configurations")
    parser.add_argument("--force", action="store_true", help="overwrite existing example files")
    arguments = parser.parse_args()

    # Initialization is local file generation; it needs neither a task nor model runtime.
    from clearml_yolo.config_tree import dump_config_tree

    try:
        dump_config_tree(arguments.directory, overwrite=arguments.force)
    except OSError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
