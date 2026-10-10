"""CLI: initialize a directory with editable example configurations."""

import argparse

from clearml_yolo.adapters.observability.tracing import trace_command, trace_operation


@trace_command("init-config")
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", help="directory for example YAML configurations")
    parser.add_argument("--force", action="store_true", help="overwrite existing example files")
    arguments = parser.parse_args()

    # Initialization is local file generation; it needs neither a task nor model runtime.
    from clearml_yolo.entrypoints.hydra.config_tree import dump_config_tree

    try:
        with trace_operation("configuration.export", context={"destination": arguments.directory}):
            dump_config_tree(arguments.directory, overwrite=arguments.force)
    except OSError as error:
        from clearml_yolo.adapters.observability.diagnostics import (
            exception_summary,
            log_exception,
            redact_text,
        )

        log_exception(
            "Cannot initialize configuration directory",
            error,
            level="DEBUG",
            context={"destination": arguments.directory},
        )
        parser.error(
            f"Cannot initialize configuration directory {redact_text(arguments.directory)}: "
            + exception_summary(error)
        )


if __name__ == "__main__":
    main()
