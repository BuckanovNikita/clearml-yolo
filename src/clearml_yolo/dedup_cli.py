"""Reflink identical, same-named cache images without starting application services."""

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory", nargs="?", type=Path,
        help="cache to scan (default: CY_HOME/.cache or .cache in the current directory)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="report duplicate candidates without creating or replacing files",
    )
    arguments = parser.parse_args()

    from clearml_yolo.dedup import deduplicate
    from clearml_yolo.filesystem import cy_home

    directory = arguments.directory
    if directory is None:
        directory = cy_home() / ".cache"
    try:
        result = deduplicate(directory.expanduser(), dry_run=arguments.dry_run)
    except (OSError, ValueError) as error:
        parser.error(str(error))

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
