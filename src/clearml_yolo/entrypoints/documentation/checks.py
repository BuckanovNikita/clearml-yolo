"""Validate installed assets, catalog coverage, links and tutorial preview cases."""

import hashlib
from html.parser import HTMLParser
from typing import override
from urllib.parse import unquote, urlsplit

from clearml_yolo.adapters.documentation.files import asset_bytes, asset_text
from clearml_yolo.core.documentation import Catalog, TutorialDoc
from clearml_yolo.entrypoints.documentation.catalog import check_coverage
from clearml_yolo.entrypoints.documentation.preview import preview


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.targets: list[str] = []

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.targets.append(value)


def _tutorial_errors(tutorial: TutorialDoc, paths: set[str], pages: set[str]) -> list[str]:
    errors: list[str] = []
    source = asset_bytes(f"tutorials/{tutorial.file}")
    content = source.decode("utf-8")
    page = asset_text(f"tutorials/{tutorial.file.removesuffix('.md')}.html")
    if f"source-sha256: {hashlib.sha256(source).hexdigest()}" not in page:
        errors.append(f"Stale generated tutorial: {tutorial.file}; run scripts/render_docs.py")
    headings = (
        "Предварительные условия",
        "Пример",
        "Ожидаемый результат",
        "Частые ошибки",
        "Проверка",
    )
    errors.extend(
        f"Missing tutorial section {heading}: {tutorial.file}"
        for heading in headings
        if heading not in content
    )
    links = _Links()
    links.feed(page)
    for target in links.targets:
        url = urlsplit(target)
        if url.fragment.startswith("field="):
            field = unquote(url.fragment.removeprefix("field="))
            if field not in paths:
                errors.append(f"Unknown field link: {tutorial.file}: {field}")
        elif (
            not url.scheme
            and url.path not in {"", "/", "/style.css"}
            and url.path.removeprefix("/tutorials/") not in pages
        ):
            errors.append(f"Broken tutorial link: {tutorial.file}: {target}")
    if not tutorial.previews:
        errors.append(f"No verification case for tutorial {tutorial.id}")
    for case in tutorial.previews:
        result = preview(case)
        errors.extend(f"{tutorial.id}: {error}" for error in result.errors)
        errors.extend(f"{tutorial.id}: {error}" for job in result.jobs for error in job.errors)
    return errors


def check_catalog(catalog: Catalog) -> list[str]:
    check_coverage(catalog)
    errors = [
        f"Empty asset: {asset}"
        for asset in ("index.html", "app.js", "style.css")
        if not asset_bytes(asset)
    ]
    paths = {item.path for item in catalog.fields}
    pages = {item.file.removesuffix(".md") + ".html" for item in catalog.tutorials}
    for tutorial in catalog.tutorials:
        errors.extend(_tutorial_errors(tutorial, paths, pages))
    commands = {command for tutorial in catalog.tutorials for command in tutorial.commands}
    missing = set(catalog.commands.values()) - commands
    if missing:
        errors.append(f"Commands without tutorial scenarios: {sorted(missing)}")
    groups = {group for tutorial in catalog.tutorials for group in tutorial.groups}
    required = {"model", "ultralytics", "ultralytics_predict", "transforms", "transform_overrides"}
    if required - groups:
        errors.append(f"Groups without tutorial scenarios: {sorted(required - groups)}")
    return errors
