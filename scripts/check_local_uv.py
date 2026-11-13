"""Validate the existing local wheelhouse configuration before dependency bootstrap."""

import sys
import tomllib
from pathlib import Path


def main() -> None:
    try:
        links = tomllib.loads(Path("uv.toml").read_text(encoding="utf-8")).get("find-links", [])
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        sys.exit(f"local-deps: cannot read uv.toml: {exc}")
    if "external/wheelhouse" not in links:
        sys.exit('local-deps: uv.toml exists without find-links = ["external/wheelhouse"]; add that entry by hand.')


if __name__ == "__main__":
    main()
