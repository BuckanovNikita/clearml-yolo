# Documentation checker verification — 2026-10-15

## Executed checks

| Command | Observed result |
| --- | --- |
| Shared architecture validator, `--phase plan` | Exit 0 before implementation |
| `uv run --frozen --no-sync pytest tests/test_check_docs.py -q` | 27 passed |
| `uv run --frozen --no-sync ruff check scripts/check_docs.py tests/test_check_docs.py` | Passed |
| `uv run --frozen --no-sync mypy scripts/check_docs.py tests/test_check_docs.py` | Passed, two files |
| `uv run --frozen --no-sync vulture scripts/check_docs.py tests/test_check_docs.py` | Passed |
| `uv lock --check --offline` | Passed without changing lock versions/sources |
| `uv run --frozen --no-sync lint-imports` | 43 contracts kept, none broken |
| `uv run --frozen --no-sync pytest tests/test_architecture.py tests/test_tooling_boundaries.py -q` | 195 passed; five existing Hydra/Pydantic deprecation warnings |
| `uv run --frozen --no-sync python scripts/check_docs.py --all` | 448 tracked Markdown files, zero findings |
| Full scan plus eight feature documents and four new parent-owned contract documents | 460 Markdown files, zero findings |
| `uv run --frozen --no-sync python scripts/check_docs.py --help` | Exit 0; documented flags present |

The combined documentation invocation explicitly included `specs/033-documentation-checks/*.md`,
its `checklists/*.md`, `docs/module-architecture.md`, `docs/queue-lifecycles.md`,
`docs/input-provenance.md` and `docs/implementation-status.md`. This evidence file
was added after that scan and receives the final scoped documentation rerun.

## Scope and evidence interpretation

Behavior fixtures exercise local/percent-encoded paths, Unicode/combining and
connector characters, duplicate heading collisions, HTML anchors, images and
reference forms, escaped brackets, fenced and indented examples, undefined explicit
references, duplicate definitions, missing/escaping targets and unreadable files.
Temporary Git tests compare document bytes and `.git/index` bytes before/after
checking, and confirm untracked drafts and installed/generated assets are excluded.
Eight injected dependency violations reject direct, deferred, type-only, relative
and dynamic imports. The positive dependency fixture admits owned parser/stdlib imports.

The lock diff adds only markdown-it-py to the root development dependency and
requires-dev metadata; its existing 4.2.0 package record and all other package
versions/sources remain unchanged. The single pyproject development requirement
preserves the pre-existing local `[tool.uv.sources]` section exactly.

The checker excludes `CHANGELOG.md`, symlinks, `external/`, `node_modules/`,
`vendor/`, installed `speckit*` assets below agent/command directories, and `.specify/`
content other than project-owned `assessments/`, `bugs/` and `memory/`. Git selection
also excludes ignored and untracked files; explicitly supplied paths cover new work.
Referenced excluded files are checked as link destinations without scanning their
outgoing links. No external URL is fetched and no code example is executed.

Static Markdown checks do not validate Mermaid grammar, example runtime behavior,
external link availability, arbitrary HTML rendering or fragment IDs in non-Markdown
formats. These are explicit verification limits, not successful acceptance claims.

## Handoff and remaining acceptance

Implementation and scoped verification are complete. The parent owns documentation
navigation integration, final complete-diff review and fresh independent review,
architecture acceptance validation, routine/packaging checks and authorized release.
No commit, tag, push or installed workflow update was performed by this workstream.
All other concurrent edits and the untracked grid-search draft are outside its scope.

## Independent-review corrections — 2026-10-15

The fresh review reproduced two FR004 enforcement gaps. A four-space-indented
delimiter remained fence content under CommonMark but the checker treated it as a
closing delimiter. Undefined explicit references containing emphasis, inline code
or multiline labels escaped detection after inline token splitting. Added fixtures
first reproduced 13 failures with 35 passing tests: six fence indentation/tab/container
cases and seven formatted, multiline, collapsed or image reference cases.

Fence validation now observes the parser's consumed block and content while its
container indentation is available. Reference validation uses the parser's label
helper after the ordinary link rule, preserving escaped brackets, inline-code
examples and valid reference definitions. Positive fixtures cover closing fences
in lists/quotes, indented examples, formatted labels, whitespace-normalized multiline
definitions and unchanged resolved destinations. This changes no runtime modules,
dependencies, document selection, external access or example execution behavior.

| Follow-up check | Observed result |
| --- | --- |
| `uv run --frozen --no-sync pytest tests/test_check_docs.py -q` | 48 passed |
| `uv run --frozen --no-sync ruff check scripts/check_docs.py tests/test_check_docs.py` | Passed |
| `uv run --frozen --no-sync ruff format --check scripts/check_docs.py tests/test_check_docs.py` | Two files already formatted |
| `uv run --frozen --no-sync mypy scripts/check_docs.py tests/test_check_docs.py` | Passed, two files |
| `uv run --frozen --no-sync vulture scripts/check_docs.py tests/test_check_docs.py` | Passed |
| `uv run --frozen --no-sync python scripts/check_docs.py --all` | 448 tracked Markdown files, zero findings |
| Tracked Markdown plus explicitly supplied new task-owned Markdown | 473 files, zero findings |

The combined scan excludes the pre-existing untracked grid-search draft and retains
the documented generated, installed, dependency and symlink exclusions. The parent
also independently repeated the 48-test checker suite and 473-document scan. Final
complete-diff acceptance and fresh review remain parent-owned; this workstream
performed no commit or runtime/native rerun for the checker corrections.

## Parent acceptance

The [integrated checks](../../docs/evidence/2026-10-15-correctness-cleanup/verification.md)
and [fresh final review](../../docs/evidence/2026-10-15-correctness-cleanup/review.md)
accept the corrected checker and its architecture record. T009 is complete; release
delivery remains in the parent workflow. The portable application skill changed for
input fixes, while this development-only checker needs no portable command guidance.

## Release-hook fixture follow-up — 2026-10-16

The automatic version commit's hook suite reported one failure (2812 passed,
30 skipped, 7 deselected): the temporary Git fixture inherited `GIT_INDEX_FILE`,
so its `git add` populated the enclosing commit's temporary index and the fixture
had no `.git/index`. The source commit remained intact; that release attempt did
not produce a version commit or tag. A scoped probe reproduced the same failure
using a task-owned external index, without touching the real repository index.

The test module now clears inherited `GIT_*` variables through function-scoped
`monkeypatch`, following the existing release-test isolation pattern. This also
protects its in-process checker calls. The checker implementation is unchanged.
With the external index inherited, all 48 checker tests passed and that index
retained SHA-256 `17a80b8cee00405a62b210e3549943905d5d67513d73661d5d8fead2a8904b48`.
Ruff, scoped mypy, changed Markdown and whitespace checks passed. The feature's
existing module record passed planning validation before the correction.

Independent read-only reviewer `/root/fixture_isolation_review` returned **ship**,
rerunning all 48 tests, both workflow Markdown files and whitespace validation.
It inspected the original failure and corrected-run logs; index hash preservation
is parent evidence. Integration and checked release recovery are recorded in the
parent delivery evidence, preserving this failed attempt separately.
