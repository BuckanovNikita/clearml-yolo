"""CLI: initialize a directory with editable example configurations."""

import argparse

from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment,
    runtime_environment,
)
from clearml_yolo.entrypoints.options import parser_for


def parser() -> argparse.ArgumentParser:
    """Return an inert parser backed by shared option declarations."""
    return parser_for("cy-init-config")


def main() -> None:
    initialize_runtime_environment()
    from clearml_yolo.adapters.observability.tracing import trace_command

    trace_command("init-config")(_owned_main)()


def _owned_main() -> None:
    with runtime_environment():
        _main()


def _main() -> None:
    from clearml_yolo.adapters.observability.tracing import trace_operation

    argument_parser = parser()
    arguments = argument_parser.parse_args()

    # Initialization is local file generation; it needs neither a task nor model runtime.
    from clearml_yolo.entrypoints.hydra.config_tree import dump_config_tree

    try:
        with trace_operation("configuration.export", context={"destination": arguments.directory}):
            dump_config_tree(
                arguments.directory,
                command=arguments.command,
                model=arguments.model,
                overwrite=arguments.force,
            )
    except (OSError, ValueError) as error:
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
        argument_parser.error(
            f"Cannot initialize configuration directory {redact_text(arguments.directory)}: "
            + exception_summary(error)
        )


if __name__ == "__main__":
    main()
