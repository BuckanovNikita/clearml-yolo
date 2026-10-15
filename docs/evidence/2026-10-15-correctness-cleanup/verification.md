# Integrated verification — 2026-10-15

Base: `813ef01aa03adc5ec5067baa73131e6ed84718d2` on master. The original local
`[tool.uv.sources]` overrides and untracked grid-search draft are excluded from task
ownership. Runtime, tooling, tests, contract amendments and documentation were integrated
before these parent checks. Independent final review and release are recorded separately.

## Executed checks

| Check | Command / evidence | Result |
| --- | --- | --- |
| Focused input regressions | [Bug verification](../../../.specify/bugs/input-evaluation-correctness/test.md) | 23 dedicated regressions plus recorded workflow and BOM follow-up checks passed |
| Parent tooling integration | `uv run --frozen --no-sync pytest tests/test_architecture.py tests/test_tooling_boundaries.py tests/test_check_docs.py -q` | 248 passed, 5 warnings |
| Final tooling after independent-review corrections | Same combined command | 299 passed, 5 warnings; includes 30 new architecture and 21 new Markdown cases |
| Geometry/input fixture follow-up | `uv run --frozen --no-sync pytest tests/test_prediction_geometry.py tests/test_input_correctness.py -q` | 76 passed; runtime unchanged |
| Initial routine suite | `uv run --frozen --no-sync pytest` | 3 failed, 2,754 passed, 30 skipped, 7 deselected; geometry fixtures/error expectations required reconciliation below |
| Routine rerun after geometry reconciliation | `uv run --frozen --no-sync pytest` | 2,762 passed, 30 skipped, 7 deselected, 93 warnings; exit 0 |
| Standalone architecture gate | `uv run --frozen --no-sync pytest tests/test_architecture.py` | 194 passed, 5 warnings |
| Ruff | `uv run --frozen --no-sync ruff check .` | Exit 0 |
| mypy | `uv run --frozen --no-sync mypy .` | Exit 0; 335 source files |
| Vulture | `uv run --frozen --no-sync vulture` | Exit 0 |
| Import contracts | `uv run --frozen --no-sync lint-imports --no-cache` | 43 kept, 0 broken |
| Tracked documentation | `uv run --frozen --no-sync python scripts/check_docs.py --all` | Exit 0 |
| New documentation included explicitly | Same command plus task-owned untracked Markdown paths | 473 files, 0 issues after review corrections |
| Whitespace/patch integrity | `git diff --check` | Exit 0 |
| Installed distributions/configuration | [Packaging record](packaging-verification.md) | Fresh wheel core and sdist queue-UI environments passed |
| Real CPU/GPU, cache and publication | [Native record](native-verification.md) | Passed; downloaded evidence and owned-resource cleanup verified |
| Mermaid and navigation | [Documentation record](documentation.md) | Three rendered diagrams reviewed; fresh navigation finding corrected and rechecked |
| Portable usage source | Companion collection verification dated 2026-10-15 | Discovery, Markdown, frontmatter/unique keys, metadata, name/folder, three packaged local links and two explicit fresh-context scenarios passed |

The full rerun collected tests before the checker/architecture review corrections;
the final 299-test tooling run separately verifies their completed state and all 51
new cases. Final whole-repository Ruff, mypy (335 files), Vulture and import contracts
also passed after those corrections. Commit/release hooks will exercise the complete
final tree before delivery. Full logs remain under the ignored task evidence directory
`.tmp/correctness-docs-20261015/`; focused stage artifacts preserve earlier results.

The initial full run exposed two geometry fixtures whose predictions referenced
images absent from ground truth, now intentionally rejected by the canonical-membership
guard, and one assertion requiring the old missing-column error text. The fixture
reconciliation preserves geometry exclusion/warning assertions and adds explicit
unknown-image rejection before geometry filtering. It does not relax the identity
guard; native and installed runtime source identities remain unchanged.

## Architecture and documentation reconciliation

The input record inventories all 16 modified runtime modules. Storage owns lexical
parsing and CSV-relative resolution; pure core policy owns canonical membership;
application workflows consume typed storage/tracking ports. No new runtime import
exception or scientific dependency revision was added. Architecture-checker and
documentation-checker records cover their standalone executable tooling and negative
fixtures; the prose record has an inspected no-impact rationale and final scope.

`markdown-it-py` 4.2.0 was already locked and is now a direct development requirement;
the lock change adds only its two root development-metadata entries. Approved external
dependency revisions and source copies were unchanged. Static enforcement limits are
documented rather than presented as exhaustive proof of arbitrary Python behavior.

The documentation stage reconciles the constitution, queue amendments, feature 008,
input/publication/CLI guidance, architecture guide, README and portable usage source.
Historical requirement/task IDs and outcomes remain. Semantic amendments and authority
movements were recorded before conservative lossless cuts. The feature 031 navigation
notice and feature 008 historical-research supersession are later meaning clarifications,
outside the compression checkpoint.

All three module-impact records and the prose no-impact record passed the architecture
validator's acceptance phase after both fresh independent ship verdicts. Their executed
checks, final scope and exclusions are reconciled; [review evidence](review.md) retains
the initial findings and corrections. No required implementation/documentation gate
remains open; commit/tag delivery follows the repository's checked release workflow.

## Limits

This task does not close physical five-GPU, multi-user/multi-host NFS or target-runtime
CUDA 11.8 acceptance. Native synthetic fixtures establish behavior and serialization,
not accuracy/generalization. Compiled warmup was interrupted and not accepted; eager
CPU/single-GPU execution passed. Font and existing Hydra/Pydantic warnings remain visible.
Installed-package checks cover Python 3.12.13; the supported Python window is unchanged.
Portable skill evaluation used native Codex, not OpenCode/DeepSeek. No deployment,
upstream patch, GitHub Release, asset upload or package-registry publication is included.
