# Error diagnostics release verification — 2026-10-06

Released version: **0.18.1**. Implementation commit: `34053b9`; checked release
commit: `47fcf4812017b63c53d4d8e49c8f54d783fa826e`. The annotated `v0.18.1`
tag resolves to that release commit. No distribution assets or registry packages
were published.

## Behavior and review

Project-owned caught errors now retain operation/resource context, exception type,
redacted messages and visible cause chains. DEBUG adds frame locations without
source excerpts or locals; existing DEBUG defaults and caller-owned sinks remain.
Optional FiftyOne publication failures continue without failing computation. ClearML
failure status privacy, required upload failures and interruption semantics remain.

The original diagnostic-loss path was reproduced with seven failing publication
assertions and corrected. Independent review found malformed credential URI and
nested secret-value cases; regression tests reproduced and fixed them, including
empty or malformed hosts. Final independent review returned ship, independently
passing all 33 formatter tests. Integration review confirmed that rebasing over the
concurrent 0.18.0 release preserved its deduplication feature and documentation.

## Verification

- Parent full suite before the final review additions: 1,192 passed, 29 skipped.
- Final formatter/publication checks: 56 passed; integrated deduplication/formatter/
  publication checks: 84 passed, one native reflink skip.
- Ruff, mypy and all nine import contracts passed.
- Normal implementation and release hooks passed, including the full pytest gate.
  Local source overrides were absent during commits and restored exactly afterward.
  No validation hook was bypassed.
- [Live acceptance](2026-10-06-error-diagnostics-live.md) covers native CPU/GPU,
  paired comparison, standalone validation/reporting, actual artifact/model download
  and Console readback, 36 native FiftyOne persistence checks, real enabled publication,
  optional failure continuation, required upload/callback/flush failure and SIGTERM.
- Final wheel and source distributions were installed in two independently populated
  environments. All ten command helps, eight generated execution configurations,
  overwrite protection/force behavior, installed source parity and dependency
  compatibility checks passed. Root distribution dependency metadata was unchanged.
- Changed Markdown structure, whitespace, fenced blocks and local links were validated.

The release helper ran unchanged. Its offline lock refresh used a disposable project
with the saved local dependency-source configuration, matching the established local
release procedure. Parsed lock data was verified identical except for the root
project version before acceptance. The release commit changes only `pyproject.toml`,
`uv.lock` and generated `CHANGELOG.md`; dependency pins/sources remain unchanged.
No release lock or recovery record remains.

## Publication and limits

Initial SSH/HTTPS attempts timed out across both available host environments.
Connectivity recovered, and an atomic SSH push published master and the explicit
`v0.18.1` tag. Remote branch, annotated tag object and peeled tag commit were checked
against their local values after publication. Remote verification is distinct from
the checked local commit/tag.

The original user's underlying backend OSError remains unidentified; the diagnostic
loss itself was verified using injected failures, including an actual completed
ClearML task. A first GPU run encountered an intermittent SDK model-readback failure;
a fresh retry passed, with both outcomes preserved in live evidence. Physical
multi-GPU execution, interactive browser behavior and successful native reflink block
sharing were not claimed.

Machine-specific logs, commands and locally built distributions are archived in the
global environment skill. Live task-owned resources were cleaned up; unrelated
services and dependency source copies were preserved.
