# Readable evaluation plots verification — 2026-10-07

## Automated checks

The full repository suite passed: 1,279 tests passed, 30 skipped. Ruff, mypy (146 source
files) and all 10 import-linter contracts passed. After the browser-derived null-gap
refinement, 34 affected rendering/report/identity tests passed; the independent reviewer
also ran 65 affected tests successfully. The all-file hook check regenerated CHANGELOG.md
from existing committed history; generated output was inspected and the changelog hook
passed on retry. That hook pass also reported concurrent evidence-file changes during
pytest, although all 1,279 tests passed; final commit hooks validate a stable staged
snapshot. Feature/release hooks use UV_NO_SYNC=1 against the verified installed
environment while the exact local uv source overrides are temporarily removed and
restored unstaged afterward; no quality hooks are bypassed.

Regression tests first reproduced four separate confusion events, per-class PR events,
encoded series, comparison tables, baseline publication and native validation PR upload.
Tests cover exact heatmap normalizations/order/background/zero denominators, PR data/hover,
Unicode escaping, test-only gating, slot reuse/collisions and callback restoration including
failure and DDP owner replay. Full precision AP remains in hover metadata; legend AP is
formatted for readability.

## Native publication and browser acceptance

A small two-class dataset with disjoint train/validation/test images and an empty image
per split exercised three full pipelines: CPU baseline without production baseline, CPU
candidate with baseline, and a single-GPU candidate with baseline. Each used native
training, prediction, evaluation, publication, comparison and reports.

Actual SDK events contained three grouped confusion slots (train/val/test) and one grouped
test PR chart. The four matrix modes and PR observations/hover matched producer JSON
exactly. Repeated candidate test publication reused its slot. Baseline charts, comparison
tables, encoded identifiers and native validation PR were absent from new Plots output.
Native non-PR diagnostic figures and scalar reporting remained.

All 11 baseline and 17 artifacts for each candidate were force-downloaded. Comparison
workbooks, exclusions, baseline/candidate dashboards and both reports remained; canonical
prediction CSVs retained both comparison contexts. All three native best models were
force-downloaded and loaded; checkpoint hashes matched producer and server identity.
Validation thresholds matched model metadata and remained frozen for other splits.

Authenticated ClearML browser testing toggled PR class visibility and switched confusion
to Row %. An additional published empty-class probe showed visible no-GT/no-prediction
legend entries with null gaps and no numerical points. All probe and pipeline resources
were cleaned; scoped verification found zero remaining projects/tasks.

## Packaging, documentation and review

Wheel and source distribution built offline and installed into separate fresh Python 3.12
environments using the current exact dependency versions. Both imported the installed
package, passed all ten command helps, generated ten configuration files and refused a
second generation without changing bytes. Source-distribution configuration generation
also passed with Task.init forbidden. Temporary environments were cleaned; no package
was uploaded.

Affected current contracts, Russian README and project E2E guidance were amended; prior
verification history was preserved. Eight amended Markdown documents and 116 local links
were validated by the documentation owner. Parent validation covered all 19 changed/new Markdown files and 119 local links/anchors.
Fresh independent read-only review returned ship with no actionable findings.

## Limits and evidence ownership

The 30 skipped suite tests and physical multi-GPU execution are not claimed as verified.
The independent review noted that ClearML may interpret HTML markup in raw series titles;
escaped persistent captions retain literal model names. The empty-class SDK probe needed
its owned reporter process terminated after successful browser checks; full application
pipelines completed and closed normally. A verification harness tail parse error after
successful CPU execution/downloads was corrected and did not affect application results.

Machine-specific logs, actual plot payloads, screenshots, task identifiers, downloaded
artifacts/models and cleanup records are retained with the global environment skill;
packaging logs and distributions remain in task-owned temporary evidence. This document
records portable acceptance outcomes only.
