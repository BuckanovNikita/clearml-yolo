"""Validate editable source metadata and report revisions for the paired release check."""

import argparse
import importlib.metadata
import json
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlparse


def check(directory: Path) -> None:
    """Require the source version and editable location to match the installed package."""
    project = tomllib.loads((directory / "pyproject.toml").read_text())["project"]
    distribution = importlib.metadata.distribution(project["name"])
    if distribution.version != project["version"]:
        sys.exit(f"paired-check: {project['name']} source {project['version']} != installed {distribution.version}")
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    location = Path(unquote(urlparse(direct.get("url", "")).path))
    editable = direct.get("dir_info", {}).get("editable", False)
    if not editable or location.resolve() != directory.resolve():
        sys.exit(f"paired-check: {project['name']} is not the editable install of {directory}: {direct}")


def report(directory: str, revision: str) -> None:
    """Print the source package identity and the supplied Git revision."""
    project = tomllib.loads((Path(directory) / "pyproject.toml").read_text())["project"]
    print(f"paired-check: {project['name']} {project['version']} {revision} {directory}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("check", help="Validate both editable installs")
    validate.add_argument("root", type=Path)
    validate.add_argument("queue", type=Path)
    describe = commands.add_parser("report", help="Report source identity and revision")
    describe.add_argument("project")
    describe.add_argument("revision")
    args = parser.parse_args()
    if args.command == "check":
        check(args.root)
        check(args.queue)
    else:
        report(args.project, args.revision)


if __name__ == "__main__":
    main()
