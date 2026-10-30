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
                "  # Files remote of https://github.com (release archives):\n"
                "  export GHR=https://artifactory.example/artifactory/github-files\n"
                "Use per-host ~/.netrc credentials for GHR HTTP requests.\n"
                "GH (VCS) and HF_ENDPOINT apply only to standalone source/Hub resolution; "
                "they are not needed for bulk weights.\n"
                "Bulk preparation uses valid native caches or this project's pinned release only.\n"
                "GHR preserves owner/repo/releases/download/tag/file.\n"
                "For slow archive transfers, set CY_WEIGHTS_DOWNLOAD_TIMEOUT=3600 "
                "(positive finite seconds; default 1800 per attempt).\n"
                "Keep TLS verification enabled; configure SSL_CERT_FILE for a private CA.\n"
                "Retry: cy-download-weights\n"
                "Details: docs/model-assets.md\n"
            )
            raise SystemExit(1)


if __name__ == "__main__":
    main()
