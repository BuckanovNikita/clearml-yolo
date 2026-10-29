"""Reflink identical, same-named cache images without starting application services."""

import argparse
import sys

from clearml_yolo.entrypoints.options import parser_for


def parser() -> argparse.ArgumentParser:
    """Return an inert parser backed by shared option declarations."""
    return parser_for("cy-dedup")


def main() -> None:
    # This filesystem-only tool loads no SDK configuration; its atomic temporary
    # files are owned and cleaned beside their selected destination.
    from clearml_yolo.adapters.observability.tracing import trace_command

    trace_command("dedup")(_main)()


def _main() -> None:
    argument_parser = parser()
    arguments = argument_parser.parse_args()

    from clearml_yolo.adapters.storage.dedup import deduplicate
    from clearml_yolo.adapters.storage.filesystem import cy_home

    directory = arguments.directory
    if directory is None:
        directory = cy_home() / ".cache"
    try:
        result = deduplicate(directory.expanduser(), dry_run=arguments.dry_run)
    except (OSError, ValueError) as error:
        argument_parser.error(str(error))

    for issue in result.issues:
        sys.stderr.write(f"{issue}\n")
    prefix = "Dry run (candidates only): " if arguments.dry_run else ""
    sys.stdout.write(
        f"{prefix}scanned={result.scanned} duplicates={result.duplicates} "
        f"reflinked={result.reflinked} skipped={result.skipped} failures={result.failures}\n"
    )
    if result.failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
