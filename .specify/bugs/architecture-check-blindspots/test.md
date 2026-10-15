# Bug Verification: architecture check blind spots

- **Slug**: architecture-check-blindspots
- **Tested**: 2026-10-15
- **Assessment**: [assessment.md](assessment.md)
- **Fix**: [fix.md](fix.md)
- **Result**: passed — integrated verification and fresh independent review accepted

## Checks Performed

| Check | Command / action | Result |
| --- | --- | --- |
| Original failure paths | Regression snippets for local/nested runtime names, deeper missing attributes, definition-time calls, network/filesystem aliases and environment access | Pass; all reproduced blind spots are rejected |
| Architecture and tooling | `uv run --frozen --no-sync pytest tests/test_architecture.py tests/test_tooling_boundaries.py -q --tb=short` | Exit 0; 221 passed, 5 existing Hydra/Pydantic warnings; 3.77 seconds |
| Import contracts | `uv run --frozen --no-sync lint-imports` | Exit 0; 43 kept, 0 broken |
| Ruff | `uv run --frozen --no-sync ruff check tests/architecture_helpers.py tests/test_architecture.py tests/test_tooling_boundaries.py` | Exit 0; all checks passed |
| Typing | `uv run --frozen --no-sync mypy tests/architecture_helpers.py tests/test_architecture.py tests/test_tooling_boundaries.py` | Exit 0; no issues in 3 source files |
| Dead code | `uv run --frozen --no-sync vulture` | Exit 0 |
| Whitespace | `git diff --check -- tests/architecture_helpers.py tests/test_architecture.py tests/test_tooling_boundaries.py` | Exit 0 |
| Architecture planning | Shared architecture validator, `--phase plan`, task record and explicit repository root | Exit 0 before implementation; reconciled record also passes |
| Integrated documentation | `uv run --frozen --no-sync python scripts/check_docs.py --all` | Parent-owned integration gate; not claimed here |
| Fresh independent review | Final integrated review requested from parent | Pending |

## Evidence and Reconciliation

The original snippets were first run directly against unchanged helpers, all returning empty
findings. The initial added-regression run produced 40 failures and 132 passes; final tests
exercise those same source patterns plus scope and valid-re-export counterexamples. Actual
core/application trees, package initializers, console scripts, composed Hydra targets and
import graph still pass. No inspected snippet is executed by the static helper.

The delegated diff consists of the three named test/helper files and this bug directory.
No production source, runtime dependencies, installed workflow files, symlinks or shared
resources changed. Concurrent runtime/checker/documentation edits, pre-existing pyproject
local sources and the untracked grid-search draft are excluded from this workstream.

## Residual Risks and Recommendation

See the [static analysis limits](fix.md#static-analysis-limits). Parent integration must update
the authoritative architecture guide, validate documentation, obtain fresh independent review,
and complete the architecture acceptance record before reporting overall completion. Native
CPU/GPU/ClearML acceptance belongs to the separate runtime-correctness workstream.

## Independent-review correction verification — 2026-10-15

The initial direct probes confirmed empty core/application findings for the nested
class/global-import case and both later-module-import cases; the valid class-level
alias `C.run = f` was rejected. Added 28 fixtures initially produced **17 failed,
11 passed**. All pass after correction; two additional fixtures distinguish eager
definition-time effects from deferred final-module lookup.

| Check | Executed command | Result |
| --- | --- | --- |
| Architecture and tooling regression | `uv run --frozen --no-sync pytest tests/test_architecture.py tests/test_tooling_boundaries.py -q --tb=short` | Exit 0; **251 passed**, 5 existing Hydra/Pydantic warnings, 3.63 seconds |
| Ruff | `uv run --frozen --no-sync ruff check tests/architecture_helpers.py tests/test_architecture.py` | Exit 0 |
| Strict typing | `uv run --frozen --no-sync mypy tests/architecture_helpers.py tests/test_architecture.py` | Exit 0; 2 source files |
| Dead code | `uv run --frozen --no-sync vulture` | Exit 0 |
| Import contracts | `uv run --frozen --no-sync lint-imports` | Exit 0; 43 kept, 0 broken |
| Architecture planning record | Shared validator with `--phase plan` and explicit repository root | Exit 0 before the corrections |

Corrections preserve the original assessment and initial verification history. Parent
integration owns fresh follow-up review and architecture acceptance. This test-tooling
change does not alter the runtime/package snapshot and requires no native or packaging
rerun. Supported lookup and the post-initialization assumption are recorded in the
[correction notes](fix.md#independent-review-corrections--2026-10-15).

## Parent integrated acceptance

The final [verification](../../../docs/evidence/2026-10-15-correctness-cleanup/verification.md)
and [fresh independent review](../../../docs/evidence/2026-10-15-correctness-cleanup/review.md)
close this report's earlier pending integration status. Runtime source matches native
and installed-package acceptance; all review findings were corrected and independently
accepted. The architecture record is reconciled with the complete task-owned diff.
External five-GPU/NFS and documented static-analysis limits remain open. Release
delivery is recorded separately after commit/tag checks.
