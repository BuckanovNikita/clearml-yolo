"""Prepare supported named model weights in their native discovery caches."""

import argparse
import sys
from collections.abc import Sequence

from clearml_yolo.adapters.assets.preparation import prepare_catalogue
from clearml_yolo.adapters.observability.diagnostics import redact_text
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
from clearml_yolo.entrypoints.options import parser_for


def parser() -> argparse.ArgumentParser:
    """Return an inert parser backed by shared option declarations."""
    return parser_for("cy-download-weights")


def main(argv: Sequence[str] | None = None) -> None:
    argument_parser = parser()
    argument_parser.parse_args(argv)
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
            sys.stdout.write(
                "If Artifactory is required, configure its repository roots and retry:\n"
                "  export GHR=https://artifactory.example/artifactory/github-releases\n"
                "  export GH=https://artifactory.example/artifactory/github-vcs\n"
                "  # Optional Hub mirror for native Hub assets:\n"
                "  export HF_ENDPOINT=https://artifactory.example/artifactory/api/"
                "huggingfaceml/hf-remote\n"
                "Use per-host ~/.netrc credentials for GH/GHR HTTP requests; "
                "use HF_TOKEN only for the configured Hub endpoint.\n"
                "Keep TLS verification enabled; configure SSL_CERT_FILE for a private CA.\n"
                "Retry: cy-download-weights\n"
                "Details: docs/model-assets.md\n"
            )
            raise SystemExit(1)


if __name__ == "__main__":
    main()
