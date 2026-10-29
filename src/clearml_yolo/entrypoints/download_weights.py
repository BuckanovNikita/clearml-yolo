"""Prepare supported named model weights in their native discovery caches."""

import argparse
import sys
from collections.abc import Sequence

from clearml_yolo.adapters.assets.preparation import prepare_catalogue
from clearml_yolo.adapters.observability.diagnostics import redact_text
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="cy-download-weights", description=__doc__)
    parser.parse_args(argv)
    with runtime_environment():
        result = prepare_catalogue(automatic=False)
        for location in result.locations:
            sys.stdout.write(f"Cache destination: {redact_text(str(location))}\n")
        for asset in result.assets:
            sys.stdout.write(f"Prepared: {redact_text(str(asset.path))}\n")
        for failure in result.failures:
            sys.stdout.write(
                f"Failed: {redact_text(failure.selection)}: {redact_text(failure.message)}\n"
            )
        sys.stdout.write(
            f"Prepared {len(result.assets)} assets; {len(result.failures)} failures.\n"
        )
        if result.failures:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
