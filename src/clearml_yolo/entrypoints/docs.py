"""Open the local Russian configuration reference and tutorials."""

import signal
import sys
from collections.abc import Sequence
from types import FrameType

from clearml_yolo.entrypoints.options import parser_for

MAX_PORT = 65535


def _interrupt(_signum: int, _frame: FrameType | None) -> None:
    raise KeyboardInterrupt


def main(argv: Sequence[str] | None = None) -> int:
    parser = parser_for("cy-docs")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= MAX_PORT:
        parser.error("--port must be between 0 and MAX_PORT")
    # Assets, assembly and serving stay behind this explicit documentation boundary.
    from clearml_yolo.adapters.documentation.server import serve
    from clearml_yolo.adapters.documentation.worker import PreviewWorkers, worker_command
    from clearml_yolo.entrypoints.documentation.catalog import build_catalog
    from clearml_yolo.entrypoints.documentation.checks import check_catalog

    try:
        catalog = build_catalog()
        if args.check:
            errors = check_catalog(catalog)
            if errors:
                sys.stdout.write("\n".join(errors) + "\n")
                return 1
            sys.stdout.write(
                f"Documentation OK: {len(catalog.fields)} fields, "
                f"{len(catalog.configurations)} configurations, "
                f"{len(catalog.tutorials)} tutorials\n"
            )
            return 0
        workers = PreviewWorkers(worker_command("clearml_yolo.entrypoints.documentation.worker"))
        previous = signal.signal(signal.SIGTERM, _interrupt)
        try:
            serve(catalog, workers, port=args.port, browser=not args.no_browser)
        finally:
            workers.close()
            signal.signal(signal.SIGTERM, previous)
    except (OSError, ValueError) as error:
        sys.stderr.write(f"Documentation error: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
