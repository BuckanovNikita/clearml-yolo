# Instruction migration checks — 2026-11-02

## Scope and preservation

The task standardizes agent instruction discovery only. Existing application,
service, generated workflow and unrelated source changes are preserved. No runtime
API, database, dependency or deployment changes are made. The implementation checks below preceded commit/release activity; release
outcomes are reported by the coordinating task separately. No deployment or
skill installation is part of this migration.

Pre-existing tracked and untracked runtime/documentation work, including changes
to AGENTS.md, remains intact. The owned AGENTS.md hunk changes only adapter wording.
System Python initially lacked Pydantic; rerunning with the documented prepared
uv environment passed. This was an invocation/environment failure, not a doc failure.

## Executed checks

- `uv run --frozen --no-sync python scripts/check_docs.py --all` — PASS: 133 Markdown files, zero issues.
- `uv run --frozen --no-sync python scripts/check_docs.py AGENTS.md CLAUDE.md docs/plans/claude-codex-organization-20261102/plan.md` — PASS: three affected Markdown files, zero issues.

Planning and acceptance record validation use the shared architecture validator
with this repository as the explicit root. All root adapter and changed-document
relative links were inspected separately; Git whitespace checks cover owned paths.

## Limits and remaining integration

File checks establish physical instruction discovery structure, not actual loaded
model context. Fresh Claude/Codex sessions, Windows discovery, settings parity,
parent integration, independent final review and authorized commit/release remain
with the coordinating task. Relevant application/runtime suites were not rerun
because no application behavior changed. Missing required release checks must
remain acceptance gaps rather than being inferred from these documentation checks.

## Independent review

The coordinating parent reported fresh `project_review` verdict **SHIP** with no
blocking defects on 2026-11-02. The reviewer validated all twelve project no-impact
records and inspected the documentation evidence across the integrated migration.
No runtime acceptance is inferred from that review. Authorized repository commit
and release gates remain in force; failed gates must be reported separately.

## Release gate outcome

A current origin fetch succeeded. The source checkout remains 29 commits behind
origin/master and has extensive unrelated runtime changes. The paired queue source
is version 0.1.4 while the prepared installed queue metadata is 0.1.3. Therefore
the native latest-source/paired-installation gate is unmet. No workers are drained,
shared environment reinstalled, unrelated histories merged or hooks bypassed.
Task changes remain uncommitted pending the owning source/environment reconciliation.

## Current-source pair reconciliation

The old stale-source/version blocker was reassessed on current published heads:
CY `7d3d258` version `0.44.8` and cy-queue `32bea01` version `0.1.7`
(`clearml-yolo>=0.38,<0.45`). Isolated checkouts and a task-owned environment
preserve the original dirty trees, indexes, active workers and operational environment.
Approved external dependencies were cloned at their existing exact source commits.

Normal editable installation of both source checkouts succeeded without `--no-deps`;
`uv pip check` verified all 285 installed packages compatible. Queue acceptance:
582 tests passed, seven opt-in physical DDP tests were deselected, 19 dependency
deprecation warnings. Ruff lint/format, strict mypy (70 source files), both import
contracts and actual `cy-queue --help` passed. No GPU/physical DDP outcome is claimed.
Changed-document checks and architecture acceptance passed. CY canonical verification
and final commit/release results remain separate evidence below.

## Canonical first-run result and stable retry

CY's ordinary suite completed with 4,703 passed, 30 skipped and 81 deselected
(182 warnings), but the canonical wrapper returned exit 1 because its dependency
input inventory changed during verification. The coordinating parent had appended
the paired queue checkout's release-evidence Markdown and source-pair JSON while CY
was checking the editable dependency tree. That tree includes documentation.
This is a coordination failure, not a passing acceptance receipt or a detected
application regression. Prior logs are retained; no receipt is forged or reused.

Both source checkouts and the installed environment are frozen for a fresh full
canonical retry. The coordinating task records its final wrapper exit and release
receipts separately; no queued worker or operational environment is changed.

## Stable canonical acceptance

The fresh frozen-input retry completed with canonical wrapper exit 0 and an
accepted application receipt. Ruff, strict mypy, Vulture, import-linter and all
ordinary pytest commands passed: 4,703 tests passed, 30 skipped, 81 deselected,
182 warnings. The complete source/dependency fingerprint remained unchanged;
the rejected first run remains recorded above. No timeout, selector, allowlist
or gate was relaxed. The queue source remains frozen through CY publication.

The task-owned diff remains only the root Claude import adapter, its shared
AGENTS instruction and this documentation directory. Architecture acceptance
and final documentation checks precede the native commit and automatic release
evaluation. Documentation alone is not expected to produce a new version; the
coordinating publication receipt records the actual final commits and refs.
