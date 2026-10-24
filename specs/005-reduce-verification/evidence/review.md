# Independent review — 2026-10-24

## First review after integrated verification

Two fresh native reviewers were requested with `gpt-6.1-sol` and high effort;
the host did not expose separate confirmation of their runtime settings. Their
instructions were read-only, with no write ownership or further delegation.

| Reviewer | Scope | Verdict |
| --- | --- | --- |
| `/root/review_verification_release` | Receipt identity and release safeguards | Fix first |
| `/root/review_runtime_architecture` | Runtime, dependencies, architecture and mutation equivalence | Fix first |

The receipt reviewer reproduced two stale-success cases with actual `fingerprint()`
calls in temporary repositories: editable directory symlinks were not traversed, and
new installed package modules absent from `RECORD` were not inventoried. The correction
traverses linked directories with cycle protection, fingerprints link identity, and
inventories owned installed package trees. Regressions cover target edits, equal-byte
retargets, new modules and valid Git staging of directory links.

The runtime reviewer independently rejected all 192 formerly forbidden adapter pairs
and 406 sampled forbidden SDK edges across all 23 baseline SDK roots using the actual
configured contracts. Existing dependency versions and exact external lock entries
were preserved. No additional runtime/interface defect was found.

Mutation survivor `x_match_detections__mutmut_47` was incorrectly described as equivalent:
floating-point assignment can change the selected score tie when its penalty changes
from `max(n,m)+1` to `max(n,m)+2`. The reviewer reproduced supported float64 inputs with
score errors `6.5937460680049415e-06` versus `6.627767370277572e-06`. A regression now
requires the nearest compatible score and fails against that actual mutant. Production
policy is unchanged. The other four survivor dispositions were independently approved.

The parent also reproduced an actual no-force reuse miss across host tool calls.
Only `CODEX_TOOL_CALL_ID` differed between normalized environment key hashes. All five
canonical log hashes still matched the originally captured receipt, ruling out delayed
log writes. That bookkeeping key is now removed from the actual check environment and
its identity, alongside Git/pre-commit/uv bookkeeping. Meaningful inputs remain checked.

Focused correction results: **68 receipt/tooling/lifecycle tests passed in 12.08s**;
**109 export-quality tests passed in 1.20s**, plus Ruff, strict mypy and diff checks.
Fresh mutation execution, canonical verification and a fresh final review are required
before acceptance. The earlier successful canonical run remains historical evidence
for its pre-review input view; it does not accept the corrected code.

## Parent challenge of the empty-side survivor

The parent subsequently rejected `x_match_detections__mutmut_29`, which the first
review had approved. A valid float64 box `[0, 0, 1e200, 1e200, 0.5, 0]` and an empty
opposite side return unmatched counts in the original. Under
`np.errstate(over="raise", invalid="raise")`, the `or` mutant enters unnecessary area
arithmetic and raises `FloatingPointError`. The existing three empty-population cases
now use these finite coordinates and strict arithmetic errors. Production code remains
unchanged. Only the two redundant float64 conversions and the tolerance-equality branch
remain equivalence candidates for final review.

## Second fresh review after the fifth canonical run

Fresh read-only reviewers `/root/final_review_receipts` and
`/root/final_review_runtime` were requested with `gpt-6.1-sol`, high effort and no
delegation or write ownership. Runtime settings were not separately observable.

The runtime reviewer returned **ship**. All 13 composition class/function ASTs match
the baseline after resolving import aliases. All 46 configured contracts passed on
the enriched real graph; five forbidden-boundary injections, three cycle layers,
effects, initializer and missing-target probes rejected violations. Dependency
versions/sources and the external lock entries were preserved.

The reviewer accepted all three final mutation equivalences: `_pair_iou` mutants 50
and 52 receive normalized base float64 arrays; `quality_gate` mutant 36's differing
equality case remains accepted by `math.isclose`. Actual generated functions agreed
on 50 bit-identical array comparisons and 16 quality-boundary comparisons. Recorded
input hashes and all actual mutant exit codes matched: 430 killed, three equivalent.

The receipt reviewer returned **fix first** after reproducing another omission:
generated directory names were excluded at every depth. An ignored
`tests/outputs/fixture.pt` changed without invalidating success; an installed package
subdirectory with the same name was also omitted. Prior dependency/link/environment/
release corrections were confirmed, with no additional release defect found.

The parent reproduced six failing regression cases before correction. Repository
output exclusions now apply only at the repository root; tree traversal excludes
VCS/tool caches, plus `.venv` only at an editable project root. Nested fixture/package
directories such as `outputs`, `build`, `runs`, `mutants`, `.tmp` and `.cache` are
inventoried. A production-verifier temporary-repository probe then changed an actual
read fixture from valid to invalid: the check reran, failed and removed its receipt.
Logs: `.tmp/cy005-nested-input-red.log` and `.tmp/cy005-nested-fixture-probe.log`.
Runtime, architecture and selected mutation inputs remain unchanged. Corrected
tooling still requires fresh canonical verification and independent final review.

Correction verification: **117 receipt/tooling/release tests passed in 99.41 seconds**
(`.tmp/cy005-nested-input-green.log`), with focused Ruff and strict mypy passing.
This includes directory-name regressions for ignored fixtures and a new installed
module absent from `RECORD`. The complete canonical gate is repeated for the changed
verifier; the unchanged mutation selection does not require another mutation run.

## Third fresh review and root configuration correction

After the sixth canonical run, `/root/release_acceptance_review` was requested with
`gpt-6.1-sol`, high effort, fresh context and no write ownership or delegation. The
reviewer confirmed the nested-directory fix, receipt log hashes, dependency preservation,
net reduction and complete architecture scope reconciliation. No runtime/release defect
was found. The verdict was **fix first** for a further input omission raised during
parent inspection and independently reproduced by the reviewer.

A newly ignored root `pytest.ini` escaped Git discovery and could supersede the tracked
pytest configuration. Actual pytest discovery selected it with collection-only enabled,
while the receipt fingerprint stayed unchanged. The parent also reproduced omission
of an ignored root fixture. Both regression cases failed before correction
(`.tmp/cy005-root-input-red.log`).

Root files are now inventoried independently of Git ignore rules. Ignored local fixture
data is hashed as an external input, while code and checking configuration must be
staged for a hook to accept the view. The existing partial-staging and path-limited-index
tests now share setup; both rejection paths remain and both now verify retry after the
correct file view is staged. Malformed-receipt cases share their field/value matrix.

Correction results: **119 receipt/tooling/release tests passed in 95.81 seconds**
(`.tmp/cy005-root-input-green.log`). After test consolidation, **46 receipt tests passed
in 8.71 seconds** (`.tmp/cy005-root-input-consolidated.log`), with Ruff and strict mypy
passing. Maintained Python is still reduced by one line. Fresh complete verification
and independent review remain required; selected mutation inputs are unchanged.

## Input inventory preflight and unified discovery

A bounded read-only preflight by `/root/input_inventory_preflight` was requested with
`gpt-6-astra`, high effort and no delegation while the seventh canonical run was in
progress. It reproduced the same omission for ignored `fixtures/tensor.pt`: the path
was governed but discovery only walked three hard-coded directories. The parent
interrupted the owned verifier; it exited unsuccessfully and left no success receipt.
The incomplete run is recorded in `.tmp/cy005-final-verify-v7.log` and must not be
counted as a passing suite. No unrelated processes or services were stopped.

Discovery now traverses every governed top-level directory. Known documentation,
agent metadata, generated output and tool-cache roots are excluded explicitly;
nested Markdown fixture data is included. Ignored fixture/external source data is
fingerprinted, while owned code/check configuration must match the staged view.
The staged-file check also fails closed when an owned path disappears during discovery.
Shared failure/interrupt setup preserves both rejection checks and adds interruption
retry coverage. Maintained Python remains reduced by two lines.

The same preflight reviewer found no further actionable discovery mismatch after
eight actual fingerprint probes: ignored binary/Markdown fixtures, configuration,
external Python source, nested output names, root Markdown data and a top-level
directory symlink target all invalidated success. This was bounded preflight evidence,
not final acceptance. Final focused results: **122 receipt/tooling/release tests passed
in 101.85 seconds**, plus Ruff and strict mypy (`.tmp/cy005-governed-tree-final.log`).
Fresh complete verification and fresh independent final review still follow.

## Final acceptance after the completed ninth run

Fresh independent reviewer `/root/final_acceptance` was requested with `gpt-6-astra`,
high effort, no write ownership and no delegation, after parent verification completed.
Requested runtime controls were not separately confirmed by the host. Verdict: **ship**,
with no actionable findings in the integrated diff.

The reviewer verified all five final log hashes and their successful results, the
separate actual receipt-reuse invocation, complete dependency/version preservation,
all ten mutation-input hashes and the net two-line maintained-Python reduction.
Six independent temporary-repository probes confirmed invalidation for ignored binary
and Markdown fixtures, nested output names, external Python, root configuration and
linked-directory contents. Static review covered staged views, atomic receipts, exact
release normalization, architecture ownership/negative checks, runtime changes and
cancellation coverage. No checkout verifier or full suite was rerun during review.

The earlier SIGILL remains unexplained. Focused reproduction attempts and the unchanged
complete ninth run passed, including the original failure path; the reviewer accepted
this evidence without claiming a diagnosis. Physical GPU/NCCL and live ClearML publication
remain unverified. Parent reconciliation covers every added, modified and deleted task
path; the exact original local uv override is excluded from committed changes and will
be restored unstaged after hooks. Architecture/documentation validation and authorized
commit/tag delivery complete the remaining workflow.
