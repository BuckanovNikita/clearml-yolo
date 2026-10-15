"""Exercise document contracts and the maintenance command's dependency boundary."""

import ast
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
with pytest.MonkeyPatch.context() as import_path:
    import_path.syspath_prepend(str(ROOT))
    from scripts.check_docs import check_documents, main, parse_document, tracked_documents


def dependency_findings(source: str) -> set[str]:
    allowed = sys.stdlib_module_names | {"markdown_it", "pydantic"}
    forbidden: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            forbidden.update(
                alias.name for alias in node.names if alias.name.split(".")[0] not in allowed
            )
        elif isinstance(node, ast.ImportFrom) and (
            node.level or not node.module or node.module.split(".")[0] not in allowed
        ):
            forbidden.add(node.module or "relative import")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            if any(name.split(".")[0] == "importlib" for name in names):
                forbidden.add("dynamic import")
        elif (isinstance(node, ast.Name) and node.id in {"__import__", "eval", "exec"}) or (
            isinstance(node, ast.Attribute) and node.attr in {"import_module", "__import__"}
        ):
            forbidden.add("dynamic import")
    return forbidden


def test_dependency_contract() -> None:
    assert not dependency_findings((ROOT / "scripts/check_docs.py").read_text())
    assert not dependency_findings("import subprocess\nfrom markdown_it import MarkdownIt")


@pytest.mark.parametrize(
    "source",
    [
        "import clearml_yolo",
        "from torch import Tensor",
        "if TYPE_CHECKING:\n    import clearml",
        "def deferred():\n    import ultralytics",
        "import importlib as loader",
        "from importlib import import_module as load",
        "__import__('torch')",
        "from . import local",
    ],
)
def test_dependency_rejections(source: str) -> None:
    assert dependency_findings(source)


def test_dependency_is_declared_at_locked_version_in_development() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    parser = next(package for package in lock["package"] if package["name"] == "markdown-it-py")
    requirement = f"markdown-it-py=={parser['version']}"
    assert requirement in project["dependency-groups"]["dev"]
    assert not any(item.startswith("markdown-it-py") for item in project["project"]["dependencies"])
    root = next(package for package in lock["package"] if package["name"] == "clearml-yolo")
    assert {"name": "markdown-it-py"} in root["dev-dependencies"]["dev"]
    assert {"name": "markdown-it-py", "specifier": f"=={parser['version']}"} in root["metadata"][
        "requires-dev"
    ]["dev"]


def test_links_unicode_duplicates_html_and_reference_forms(tmp_path: Path) -> None:
    target = tmp_path / "other doc.md"
    target.write_text(
        "# Привет, `Мир`!\n\n# A & B\n\n# Repeat\n\n# Repeat\n\n# Repeat-1\n"
        '\n<a id="explicit"></a>\n\n<a name="legacy"></a>\n',
        encoding="utf-8",
    )
    (tmp_path / "plot.svg").write_text("<svg/>")
    source = tmp_path / "source.md"
    source.write_text(
        "# Source\n\n[x](other%20doc.md#%D0%BF%D1%80%D0%B8%D0%B2%D0%B5%D1%82-"
        "%D0%BC%D0%B8%D1%80)\n\n"
        "[x](<other doc.md#a--b>)\n\n[x](other%20doc.md#repeat-1)\n\n"
        "[x](other%20doc.md#repeat-1-1)\n\n[ref][label]\n\n[label][]\n\n[label]\n\n"
        "[label]: other%20doc.md#explicit\n\n![plot](plot.svg)\n\n"
        '<a href="other%20doc.md#legacy">HTML</a>\n\n<img src="plot.svg">\n\n'
        "[self](#source)\n\n[external](https://example.invalid/missing)\n\n"
        "[external](mailto:someone@example.invalid)\n\n[external](//example.invalid/missing)\n",
        encoding="utf-8",
    )
    assert check_documents(tmp_path, [source, target]) == []


def test_examples_are_inert_and_nested_fences_close(tmp_path: Path) -> None:
    source = tmp_path / "examples.md"
    source.write_text(
        "# Examples\n\n```markdown\n# Fake heading\n[bad](missing)\n```\n\n"
        "    [bad](missing)\n\n`[bad][undefined]` and `[bad](missing)`\n\n"
        "\\[escaped][undefined]\n\n> ```sh\n> touch do-not-create\n> ```\n\n"
        "- Example\n\n  ~~~mermaid\n  intentionally invalid Mermaid\n  ~~~\n",
        encoding="utf-8",
    )
    assert check_documents(tmp_path, [source]) == []
    assert not (tmp_path / "do-not-create").exists()
    parsed = parse_document(source, source.read_text())
    assert parsed.anchors == {"examples"}


@pytest.mark.parametrize(
    "content",
    [
        "```\ntext\n    ```\n",
        "```\ntext\n\t```\n",
        "  ```\n  text\n    ```\n",
        "> ```\n> text\n>     ```\n",
        "- ```\n  text\n      ```\n",
        "~~~\ntext\n    ~~~\n",
    ],
)
def test_indented_code_cannot_close_a_fence(tmp_path: Path, content: str) -> None:
    document = parse_document(tmp_path / "source.md", content)
    assert [issue.message for issue in document.issues] == ["unclosed fenced code block"]


@pytest.mark.parametrize(
    "content",
    [
        "```\ntext\n   ```\n",
        "  ```\n  text\n ```\t\n",
        "> ```\n> text\n>    ```\n",
        "> > ```\n> > text\n> > ```\n",
        "- ```\n  text\n     ```\n",
        "- item\n\n  > ~~~\n  > text\n  > ~~~~\n",
        "    ```\n    text\n    ```\n",
    ],
)
def test_parser_recognized_fences_and_indented_examples_are_valid(
    tmp_path: Path, content: str
) -> None:
    assert parse_document(tmp_path / "source.md", content).issues == []


@pytest.mark.parametrize(
    ("reference", "label"),
    [
        ("[a *b*][missing]", "missing"),
        ("[`label`][missing]", "missing"),
        ("[label][missing\n label]", "missing label"),
        ("[a\n **b**][missing\n label]", "missing label"),
        (r"[a \] b][missing]", "missing"),
        ("[a *b*][]", "a *b*"),
        ("![`label`][missing]", "missing"),
    ],
)
def test_undefined_explicit_references_preserve_inline_grammar(
    tmp_path: Path, reference: str, label: str
) -> None:
    document = parse_document(tmp_path / "source.md", f"# Doc\n\n{reference}\n")
    assert [(issue.line, issue.message) for issue in document.issues] == [
        (3, f"undefined reference: {label}")
    ]


def test_defined_formatted_multiline_and_escaped_references(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text(
        "# Doc\n\n[a *b*][defined]\n\n[`label`][defined]\n\n"
        "[label][MULTI\n line]\n\n[a\n **b**][multi line]\n\n"
        "[a *b*][]\n\n[defined]: #doc\n[multi line]: #doc\n[a *b*]: #doc\n\n"
        "`[a *b*][missing]` and ``[`label`][missing]``\n\n"
        "\\[a *b*][missing] and [label]\\[missing]\n\n"
        '<span title="[a *b*][missing]">literal</span>\n',
        encoding="utf-8",
    )
    assert check_documents(tmp_path, [source]) == []
    assert [link.target for link in parse_document(source, source.read_text()).links] == [
        "#doc"
    ] * 5


@pytest.mark.parametrize(
    ("content", "message", "line"),
    [
        ("# Doc\n\n[bad](missing.md)", "missing local target", 3),
        ("# Doc\n\n[bad](#absent)", "missing Markdown anchor", 3),
        ("# Doc\n\n[bad][unknown]", "undefined reference: unknown", 3),
        ("# Doc\n\n[unknown][]", "undefined reference: unknown", 3),
        ("# Doc\n\n```sh\necho no", "unclosed fenced code block", 3),
        ("# Doc\n\n```", "unclosed fenced code block", 3),
        ("# Doc\n\n[bad](../outside.md)", "local link leaves repository", 3),
        ("[r]: first.md\n[r]: second.md\n", "duplicate reference definition: R", 2),
    ],
)
def test_document_failures_have_source_locations(
    tmp_path: Path, content: str, message: str, line: int
) -> None:
    source = tmp_path / "source.md"
    source.write_text(content, encoding="utf-8")
    issues = check_documents(tmp_path, [source])
    assert len(issues) == 1
    assert issues[0].path == source
    assert issues[0].line == line
    assert message in issues[0].message


def test_unicode_combining_marks_and_inline_formatting(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text(
        "# **Café** [Пример](#café-пример-é-測試) `é` 測試\n\n[heading](#café-пример-é-測試)\n",
        encoding="utf-8",
    )
    assert check_documents(tmp_path, [source]) == []


def test_escaped_brackets_do_not_hide_later_undefined_references(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text(r"\[escaped][literal] and [bad][missing]")
    issues = check_documents(tmp_path, [source])
    assert len(issues) == 1
    assert issues[0].message == "undefined reference: missing"


def test_github_connector_punctuation_and_entity_heading_text(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("# A‿B &amp; C\n\n[heading](#a‿b--c)\n", encoding="utf-8")
    assert check_documents(tmp_path, [source]) == []


def test_symlink_targets_cannot_escape_repository(tmp_path: Path) -> None:
    (tmp_path / "outside").symlink_to(tmp_path.parent, target_is_directory=True)
    source = tmp_path / "source.md"
    source.write_text("[outside](outside/anything.md)")
    issues = check_documents(tmp_path, [source])
    assert "leaves repository" in issues[0].message


def test_missing_and_unreadable_documents_are_findings(tmp_path: Path) -> None:
    source = tmp_path / "bad.md"
    source.write_bytes(b"\xff")
    issues = check_documents(tmp_path, [source, tmp_path / "absent.md"])
    assert len(issues) == 2
    assert all("cannot read Markdown" in issue.message for issue in issues)


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(  # noqa: S603 - controlled temporary-repository fixture arguments.
        ["git", "-C", str(root), *args],  # noqa: S607 - Git is a required test tool.
        check=True,
        capture_output=True,
    ).stdout


def test_all_selects_only_project_owned_tracked_markdown_and_is_read_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    git(tmp_path, "init", "--quiet")
    included = [
        "README.md",
        "docs/history.md",
        ".specify/memory/constitution.md",
        ".specify/bugs/old/test.md",
        ".specify/assessments/old/intake.md",
        ".agents/skills/running-end-to-end-tests/SKILL.md",
    ]
    excluded = [
        "CHANGELOG.md",
        ".agents/skills/speckit-plan/SKILL.md",
        ".claude/commands/speckit.plan.md",
        ".specify/templates/spec-template.md",
        ".specify/extensions/bug/README.md",
        "external/dependency/README.md",
    ]
    for filename in included + excluded:
        path = tmp_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Valid\n" if filename in included else "[bad](absent)")
    (tmp_path / "CLAUDE.md").symlink_to("README.md")
    git(tmp_path, "add", ".")
    draft = tmp_path / "draft.md"
    draft.write_text("[bad](absent)")
    assert set(tracked_documents(tmp_path)) == {tmp_path / name for name in included}
    before_index = (tmp_path / ".git/index").read_bytes()
    before_files = {path: path.read_bytes() for path in tmp_path.rglob("*.md")}
    assert main(["--root", str(tmp_path), "--all"]) == 0
    assert "6 Markdown files; 0 issue(s)" in capsys.readouterr().out
    assert (tmp_path / ".git/index").read_bytes() == before_index
    assert {path: path.read_bytes() for path in before_files} == before_files
    assert main(["--root", str(tmp_path), str(draft)]) == 1
    assert "draft.md:1: missing local target" in capsys.readouterr().err


def test_cli_returns_two_for_repository_or_invocation_error(tmp_path: Path) -> None:
    assert main(["--root", str(tmp_path), "--all"]) == 2
    with pytest.raises(SystemExit) as error:
        main([])
    assert error.value.code == 2
