"""Render packaged Russian tutorial pages using the existing maintenance dependency."""

import hashlib
import html
import json
from pathlib import Path

from markdown_it import MarkdownIt


def main() -> None:
    root = (
        Path(__file__).resolve().parents[1]
        / "src/clearml_yolo/adapters/documentation/assets/tutorials"
    )
    inventory = json.loads((root / "inventory.json").read_text(encoding="utf-8"))
    renderer = MarkdownIt("commonmark", {"html": False}).enable("table")
    for tutorial in inventory:
        source = root / tutorial["file"]
        content = source.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        body = renderer.render(content.decode("utf-8"))
        page = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(tutorial["title"])} — CY</title><link rel="stylesheet" href="/style.css"></head>
<body><main class="tutorial-page">
<nav><a href="/">← Справочник CY</a></nav>{body}</main></body></html>
<!-- source-sha256: {digest} -->
"""
        source.with_suffix(".html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
