"""Check project Markdown and local destinations without rewriting or fetching anything."""

import argparse
import subprocess
import sys
import unicodedata
from collections.abc import Iterable, Sequence
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, override
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
from markdown_it.common.utils import normalizeReference
from markdown_it.rules_block import StateBlock, fence
from markdown_it.rules_inline import StateInline
from markdown_it.token import Token
from pydantic import BaseModel, ConfigDict, Field

EXCLUDED_ROOTS = {"external", "node_modules", "vendor"}
SPECIFY_CONTENT = {"assessments", "bugs", "memory"}


class Issue(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: Path
    line: int
    message: str


class Link(BaseModel):
    model_config = ConfigDict(frozen=True)
    target: str
    line: int


class Document(BaseModel):
    anchors: set[str] = Field(default_factory=set)
    links: list[Link] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)


class HtmlDestinations(HTMLParser):
    """Extract explicit anchors and destinations; never render or execute HTML."""

    def __init__(self, document: Document, line: int) -> None:
        super().__init__(convert_charrefs=True)
        self.document = document
        self.line = line

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if anchor := values.get("id") or (values.get("name") if tag == "a" else None):
            self.document.anchors.add(anchor)
        key = "href" if tag == "a" else "src" if tag == "img" else ""
        if target := values.get(key):
            self.document.links.append(Link(target=target, line=self.line + self.getpos()[0] - 1))


def project_owned(path: Path) -> bool:
    """Select maintained prose, including project-owned workflow evidence."""
    parts = path.parts
    if path.suffix.lower() != ".md" or path.name == "CHANGELOG.md":
        return False
    if not parts or parts[0] in EXCLUDED_ROOTS:
        return False
    if parts[0] == ".specify":
        return len(parts) > 1 and parts[1] in SPECIFY_CONTENT
    return not (
        parts[0] in {".agents", ".claude", ".codex", ".github"}
        and any(part.startswith("speckit") for part in parts[1:])
    )


def contains_symlink(root: Path, path: Path) -> bool:
    return any(candidate.is_symlink() for candidate in (path, *path.parents) if candidate != root)


def tracked_documents(root: Path) -> list[Path]:
    result = subprocess.run(  # noqa: S603 - fixed read-only Git operation, no shell.
        ["git", "-C", str(root), "ls-files", "-z"],  # noqa: S607 - Git is a required tool.
        check=True,
        capture_output=True,
    )
    paths = [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]
    return sorted(
        root / path
        for path in paths
        if project_owned(path) and not contains_symlink(root, root / path)
    )


def heading_text(tokens: Iterable[Token]) -> str:
    pieces: list[str] = []
    for token in tokens:
        if token.children:
            pieces.append(heading_text(token.children))
        elif token.type in {"text", "text_special", "code_inline"}:
            pieces.append(token.content)
        elif token.type in {"softbreak", "hardbreak"}:
            pieces.append(" ")
    return "".join(pieces)


def heading_anchor(text: str, used: set[str]) -> str:
    # GitHub preserves Unicode letters/marks/numbers and connector punctuation.
    base = "".join(
        char
        for char in text.lower()
        if char in " -"
        or unicodedata.category(char)[0] in {"L", "M", "N"}
        or unicodedata.category(char) == "Pc"
    ).replace(" ", "-")
    anchor = base
    suffix = 0
    while anchor in used:
        suffix += 1
        anchor = f"{base}-{suffix}"
    used.add(anchor)
    return anchor


def checked_fence(state: StateBlock, start_line: int, end_line: int, silent: bool) -> bool:
    matched = fence(state, start_line, end_line, silent)
    if matched and not silent:
        token = state.tokens[-1]
        # The parser consumes a closing delimiter but excludes it from content.
        # Inspect while container indentation is still available in block state;
        # reconstructing it from raw lines loses list/quote and tab semantics.
        consumed = state.getLines(start_line + 1, state.line, state.sCount[start_line], True)
        token.meta["closed"] = consumed != token.content
    return matched


def undefined_reference(state: StateInline, silent: bool) -> bool:
    # This rule follows the normal link rule. Escapes, code and valid links have
    # already consumed their input; silent lookahead must not create diagnostics.
    if silent or state.src[state.pos] != "[":
        return False
    text_end = state.md.helpers.parseLinkLabel(state, state.pos, True)
    label_start = text_end + 1
    if text_end < 0 or label_start >= state.posMax or state.src[label_start] != "[":
        return False
    label_end = state.md.helpers.parseLinkLabel(state, label_start)
    if label_end < 0:
        return False
    label = state.src[label_start + 1 : label_end] or state.src[state.pos + 1 : text_end]
    if normalizeReference(label) in state.env.get("references", {}):
        return False
    token = state.push("undefined_reference", "", 0)
    token.content = " ".join(label.split())
    token.meta["line"] = state.src[: state.pos].count("\n")
    # Consume only the literal opening bracket, as the parser's text fallback
    # would. Remaining formatting still contributes its usual heading text.
    state.pending = "["
    state.pos += 1
    return True


def inspect_inline(document: Document, path: Path, token: Token, line: int) -> None:
    start_line = line
    for child in token.children or []:
        target = child.attrGet("href") if child.type == "link_open" else child.attrGet("src")
        if isinstance(target, str):
            document.links.append(Link(target=target, line=line))
        if child.type == "html_inline":
            HtmlDestinations(document, line).feed(child.content)
        elif child.type == "undefined_reference":
            document.issues.append(
                Issue(
                    path=path,
                    line=start_line + int(child.meta["line"]),
                    message=f"undefined reference: {child.content}",
                )
            )
        elif child.type in {"softbreak", "hardbreak"}:
            line += 1
        if child.children:
            inspect_inline(document, path, child, line)


def parse_document(path: Path, text: str) -> Document:
    document = Document()
    # markdown-it's environment is an opaque mapping with plugin-dependent values.
    environment: dict[str, Any] = {}
    parser = MarkdownIt("commonmark").enable(["table", "strikethrough"]).disable("text_join")
    parser.block.ruler.at(
        "fence", checked_fence, {"alt": ["paragraph", "reference", "blockquote", "list"]}
    )
    parser.inline.ruler.after("link", "undefined_reference", undefined_reference)
    tokens = parser.parse(text, environment)
    heading_ids: set[str] = set()
    for index, token in enumerate(tokens):
        line = token.map[0] + 1 if token.map else 1
        if token.type == "heading_open":
            document.anchors.add(
                heading_anchor(heading_text(tokens[index + 1].children or []), heading_ids)
            )
        elif token.type == "inline":
            inspect_inline(document, path, token, line)
        elif token.type == "html_block":
            HtmlDestinations(document, line).feed(token.content)
        elif token.type == "fence" and not token.meta["closed"]:
            document.issues.append(
                Issue(path=path, line=line, message="unclosed fenced code block")
            )
    for reference in environment.get("duplicate_refs", []):
        document.issues.append(
            Issue(
                path=path,
                line=int(reference["map"][0]) + 1,
                message=f"duplicate reference definition: {reference['label']}",
            )
        )
    return document


def load_document(path: Path, cache: dict[Path, Document]) -> Document:
    if path not in cache:
        try:
            cache[path] = parse_document(path, path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            cache[path] = Document(
                issues=[Issue(path=path, line=1, message=f"cannot read Markdown: {exc}")]
            )
    return cache[path]


def link_issue(root: Path, source: Path, link: Link, cache: dict[Path, Document]) -> str | None:
    try:
        url = urlsplit(link.target)
    except ValueError as exc:
        return f"invalid link {link.target!r}: {exc}"
    if url.scheme or url.netloc:
        return None
    decoded = unquote(url.path)
    target = (
        (root / decoded.lstrip("/") if decoded.startswith("/") else source.parent / decoded)
        if decoded
        else source
    )
    try:
        target = target.resolve()
        if not target.is_relative_to(root):
            return f"local link leaves repository: {link.target}"
        if not target.exists():
            return f"missing local target: {link.target}"
    except (OSError, ValueError) as exc:
        return f"invalid local target {link.target!r}: {exc}"
    return (
        anchor_issue(target, url.fragment, link.target, cache)
        if url.fragment and target.suffix.lower() == ".md" and target.is_file()
        else None
    )


def anchor_issue(
    target: Path, fragment: str, destination: str, cache: dict[Path, Document]
) -> str | None:
    document = load_document(target, cache)
    if any(issue.message.startswith("cannot read") for issue in document.issues):
        return f"cannot check target anchors: {destination}"
    if unquote(fragment) not in document.anchors:
        return f"missing Markdown anchor: {destination}"
    return None


def check_documents(root: Path, paths: Iterable[Path]) -> list[Issue]:
    root = root.resolve()
    cache: dict[Path, Document] = {}
    issues: list[Issue] = []
    for path in sorted(set(paths)):
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            issues.append(Issue(path=path, line=1, message="document leaves repository"))
            continue
        if contains_symlink(root, path):
            continue
        document = load_document(resolved, cache)
        issues.extend(document.issues)
        issues.extend(
            Issue(path=resolved, line=link.line, message=message)
            for link in document.links
            if (message := link_issue(root, resolved, link, cache))
        )
    return sorted(issues, key=lambda issue: (str(issue.path), issue.line, issue.message))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Project Markdown paths to check")
    parser.add_argument(
        "--all", action="store_true", help="Check all project-owned tracked Markdown"
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    if not args.all and not args.paths:
        parser.error("provide --all or at least one Markdown path")
    root = args.root.resolve()
    try:
        paths = tracked_documents(root) if args.all else []
        paths.extend(path.absolute() for path in args.paths)
        issues = check_documents(root, paths)
    except (OSError, subprocess.CalledProcessError, UnicodeError) as exc:
        sys.stderr.write(f"Documentation check could not start: {exc}\n")
        return 2
    for issue in issues:
        display = issue.path.relative_to(root) if issue.path.is_relative_to(root) else issue.path
        sys.stderr.write(f"{display}:{issue.line}: {issue.message}\n")
    sys.stdout.write(f"Checked {len(set(paths))} Markdown files; {len(issues)} issue(s).\n")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
