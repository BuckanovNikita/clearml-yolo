# Cleanup audit and decisions — 2026-11-01

## Inspected state and scope

Root HEAD 0037059 is 20 commits behind recorded origin/master b23952c (CY 0.44.4).
The linked `.tmp/dinov3-release-20261031` worktree is at that newer source with an
unfinished DINOv3 amendment. A content inventory found 128 dirty root files identical
to the newer source and no untracked root file absent from its tree. Differing files
still need individual reconciliation; none may be discarded merely as stale.

Original007/008/009 releases are complete in newer source. Pending009 T020-T023 cover
final documentation, review/checks, hosted snapshot and code delivery. Existing006
physical/native gaps have explicit scoped delivery exceptions and remain unverified.

## Evidence-backed candidates

| Candidate | Evidence and contrary evidence | Disposition | Acceptance |
| --- | --- | --- | --- |
| Release TOML fixture extraction | Copies all text after semantic_release, including later local sources; reproduced protected-lock assertion failure | Fix fixture extraction, preserve assertions | Original failure with/without local overrides and unrelated later tables |
| Export preview presence checks | All three operation previews accepted missing inputs; runtime predicate rejected them | Share pure policy | Missing/valid/deferred cases, unchanged runtime messages and no preview effects |
| Metrics methodology helper | Definition has no active caller; renderer owns the used counterpart | Remove orphan and exclusive import | Existing metrics/reporting behavior |
| Hub snapshot publication | Duplicate atomic symlink/copy paths | Simplify inside existing adapter | Corruption/fallback/atomicity tests and final-source native restore/load |
| Configuration tests | 12 cases covered by stronger complete matrix, with a few unique assertions | Transfer assertions and remove repeats | Full command/model/profile and self-containment matrix retained |
| Dynamic import matrix | Six syntax forms and nine ownership rules are independently enforced | Split 54 into 15 | Every parser branch, shadowing outcome and owner rejection retained |
| Repeated graph/repository setup | Identical setup rebuilt across cases | Share immutable setup; benchmark seed copying | Independent writable states and measured improvement |
| Public field metadata | Derivable values, but direct JSON-schema output and compatibility tests expose them | Retain | Public introspection unchanged |
| Worker-role predicates | Small duplicate; direct sharing violates peer boundaries | Retain | No new import exception |

## Measurements and limitations

The bounded root-snapshot release/receipt/architecture run reported 366 passed,
1 failed in 65.99 seconds; the failure was fixture leakage. Tooling sources are
unchanged relative to newer source, but this is not a full current-source baseline.
Historical receipts showed pytest near 1000 seconds and reuse near 14 seconds; their
date precedes current source. Do not infer a current speedup or dominant individual
test family. Newer-source Ruff and Markdown/link checks passed during investigation;
these do not establish future implementation acceptance.

## Selected approach

The user selected public behavior preservation, completion of genuine pending work,
and optimization of the full gate. Reject smaller commit gates or deletion of unique
coverage. Keep trusted verification reuse already implemented by005. Record timings
in dated evidence, avoid new runtime/development dependencies, and keep approved
external revisions intact. Independent plan review identified the need for a scoped
native restoration rerun after changing Hub publication; include it in final acceptance.
