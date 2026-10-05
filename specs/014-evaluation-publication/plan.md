# Implementation plan

Python 3.12, existing uv/Ruff/mypy/pytest/import-linter, pandas and pinned digital-metrics.
Reuse the approved user plan and current implementation; do not modify dependencies.

## Wave 0: Interfaces and constitution check

Use [interfaces](contracts/interfaces.md). Domain payloads have no SDK dependencies.
Session owns callbacks and resources; result adapter sits above scoring/reporting/session.
Snapshot filesystem identity before display rename. Preserve existing native model ID,
URL and verification closure. No installed Spec Kit tooling edits or new framework.
All engineering principles remain applicable. The historical recovery prohibition is
already superseded by the maintained 012 contract and explicit user instruction.

## Wave 1: Parallel ownership

- A: `result_schema.py`, `result_export.py`, `comparison/scoring.py`,
  `comparison/pr_curves.py`, dedicated tests. Complete lineage, exact CM and AP50 parity.
- B: `clearml_report.py`, dedicated interactive rendering tests. Four CM views and PR.
- C: `clearml_naming.py`, `clearml_native.py`, dedicated tests. Collision retries,
  stable model handle, verified threshold association. Report parent wiring needs.
- Parent: session lifecycle, `clearml_results.py`, tasks/apps, artifact names,
  import contracts and shared integration tests. Shard finalization precedes checks.

No child delegation, commits or releases. A/C request GPT-6.1 Sol high; B medium.
Parent retains selected runtime and reviews all interfaces/diffs.

## Wave 2: Integration and documentation

Test exact standalone/pipeline/skipped-stage inventory and native failure paths.
Documentation agent owns publication/model metadata contracts, CSV/plot/naming contracts,
project/current contract summaries, Russian README and end-to-end skill; parent verifies.
Run pytest, Ruff, mypy, import-linter, Markdown/link/example checks and real CPU/GPU/ClearML
artifact/model/plot checks. Fresh independent read-only review follows parent verification.
Record dated evidence and apply the repository release workflow only after acceptance;
Git tags only, preserving local source overrides and task-owned resource cleanup.
