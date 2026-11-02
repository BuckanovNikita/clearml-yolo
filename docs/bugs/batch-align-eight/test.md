# Verification: automatic batch alignment

- Slug: `batch-align-eight`, reused from assessment and fix.
- Date: 2026-11-02.
- Assessment: [assessment.md](assessment.md).
- Implementation: [fix.md](fix.md).
- Status: verified; canonical behavior, documentation, paired compatibility and fresh independent review passed.

## Original path and focused checks

Before the fix, `test_default_search_starts_at_eight_per_gpu` failed: expected 8,
observed 1. After implementation, `uv run --frozen --no-sync pytest
 tests/test_batch*.py -q` passed 461 tests. New aligned-grid cases cover one through
four ranks, capacities below/equal/above eight-image boundaries, ceilings not on the
grid, guided jumps and binary refinement, minimum capacity failure, numerical recovery,
failed confirmation, history replay and exclusion from automatic lookup. The frozen
schema-1/2 fixtures retain original bytes and source keys. Historical strategies
still execute their previous one-image transitions.

These are deterministic policy and integration receipts, not measured CUDA speed,
model-quality or physical multi-GPU capacity evidence. Existing native acceptance
limitations and explicit delivery exceptions remain unchanged. No assertion that
alignment increases throughput on a particular model/GPU is made.

## Documentation

`uv run --frozen --no-sync python scripts/verify.py --docs` passed Markdown/local
links, including new task documents. `python scripts/render_docs.py` regenerated the
packaged training tutorial and inventory. `uv run --frozen --no-sync cy-docs --check`
passed: 468 fields, 156 configurations and eight tutorials. Russian README, batch
contract, current-contract navigation, active feature spec/data model/interfaces,
quickstart and append-only tasks agree with the new policy. The companion portable
collection source is based on `83982d2`, proposed version 0.6.9; its package metadata,
discovery, Markdown, links and no-impact architecture checks passed.

## Paired latest-source and proposed release checks

CY baseline `6cccd554e30e359a06ac3c1553ed5789b3e4ccf7` was fetched from remote
master (the full exact identity is recorded at release below). The current remote
version is 0.44.6; proposed patch 0.44.7 is compatible with queue 0.1.7, source
`4e539f2`. A test-only queue companion changes the exact two-GPU fixture from global
8/per-GPU 4 to global 16/per-GPU 8; queue runtime, dependency bounds and version
remain unchanged. The primary dirty source checkouts and installed environments
were preserved; checks use independent copies.

Normal dependency-enabled installation succeeded with approved unchanged external
revisions. For proposed CY 0.44.7 and queue 0.1.7, source versions, installed metadata
and actual import origins agreed; `uv pip check` passed. Queue Ruff/formatting,
strict mypy, import contracts, command help and documentation passed. The complete
queue suite passed 582 tests, with seven physical opt-ins deselected and 19 warnings.
Current CY 0.44.6 paired with the same aligned fixture also passed 582 tests.
Final committed metadata and remote refs must be checked before publication.

## Canonical verification and review

The initial canonical run passed Ruff, strict mypy, Vulture and import-linter. It
was intentionally interrupted after governed tutorial assets changed, because its
input snapshot was obsolete; it supplies no successful acceptance receipt. The final
run starts after source/assets/tests and environment provisioning are frozen.
Final results, independent review, architecture acceptance and release refs follow
when executed. Batch-estimation policy is outside the maintained mutation selection;
selected evaluation/export/box validation logic and dependencies are unchanged.


## Final canonical result

`uv run --frozen --no-sync python scripts/verify.py` exited 0 with accepted stable
inputs and receipt `fc10c12da40942f5b3ac2cf4709e5d9c`. Ruff, strict mypy, Vulture and
import-linter passed. Complete ordinary pytest passed 4,701 tests, with 30 skips,
81 opt-in deselections and 182 warnings in 1,065.95 seconds. Architecture negative
cases and native CPU-DDP ran in that suite. No selected mutation module changed.
This passing final run supersedes the intentionally interrupted initial run.


## Independent review and architecture acceptance

Fresh independent review returned **ship** without blocking findings; see
[review.md](review.md). The reviewer independently reran 214 alignment/strategy/
numerical-recovery cases and evaluated the portable explanation scenarios.
Task-owned runtime scope and full diff are reconciled in the architecture record.
Its acceptance validator and documentation validation must pass before the normal
release commit. The final committed pair and publication refs are recorded below.
