# Ticket87: metrics, comparison and standalone rendering — 2026-11-16

**Execution criteria passed; coordinator acceptance/review remains pending.**
The accepted native and JSON YOLO outputs were recovered through the ordinary
ClearML model adapter, reinferred on CPU, evaluated with their frozen thresholds,
compared and reported. Separate API readback forced every required result download.
Standalone Chromium interactions and screenshot inspection establish the visual
observations below; payload checks alone are not used as rendering evidence.

Scope follows the maintained [publication inventory](../../../docs/experiment-records.md#publication-inventory),
[scientific/reporting contract](../../../docs/shared-evaluation-reporting.md) and
[readable visualization contract](../../../docs/experiment-records.md#reports-and-readable-visualization).
This adds evidence for existing behavior; no product/specification change or
dependency revision was necessary.

## Inputs and commands

Worktree `/mnt/wsl/data/nkt/clearml-yolo` was on local `master` at `60b5c63`, equal
to local master; remote references were not fetched. Product/test sources were
unchanged. The [machine record](2026-11-16-metrics-comparison-reports.json) retains
source/lock hashes, task IDs, all observation receipts and hashes/sizes for 186
protected output files.

Both accepted `handoff.json` inventories were rehashed before invocation:

| Role | Case | Training task | Checkpoint SHA-256 |
| --- | --- | --- | --- |
| Baseline | `ultralytics-default-2e66fec4f0` | `d6158c43c4fa4b88b9cca75a7d6fd55b` | `49cd94e5b561cc67ac7d9a0c4738cd794c5324fa4f9b134ab4d14d5d58c1d171` |
| Candidate | `ultralytics-json-9a23ee0417` | `92d91a2e913047eda4abed3f4665d4dd` | `9b0fe35c1f2b20f84da806ee7d8a463feef300be31e7ae36068e7f55e7fdc637` |

The frozen seed-0 fixture remains unchanged. Each checkpoint used its own exact
validation thresholds; no recalibration or historical prediction substitution occurred.
Shared inference was CPU, batch 1, 640 pixels, confidence 0.001, NMS IoU 0.7,
compilation disabled. Statistics retained seed 0, 10,000 bootstrap iterations and
q=0.05. Both sides actually reinferred all 40 test images.

The retained `scripts/run.py` calls the ordinary Hydra `launch` boundary around
the product `compare`/`report` functions. A signature-preserving observer records
their actual return values and owning task IDs; it changes no inference, scoring,
publication or finalization behavior. Exact overrides are in
`attempt02/compare-invocation.json` and `report-invocation.json`.

```bash
timeout --signal=TERM --kill-after=15s 900s env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 nice -n19 taskset -c 0,1 uv run --locked python .tmp/ticket87/run.py compare
timeout --signal=TERM --kill-after=15s 600s env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 nice -n19 taskset -c 0,1 uv run --locked python .tmp/ticket87/run.py report
```

Each command exited zero. Explicit project/tags identify `cy-it-adb183 ticket87`;
credentials came from the lifecycle in memory. Successful tasks are comparison
`52669965f3f340cfa7630161174589d2` and report `a135a2aeaac847c48efb51b3ce188a4b`.
No new Output Model was registered and neither source training task was modified.

## Scientific and workbook observations

**Passed:** the actual `CompareResult` returns four compared classes and zero
excluded classes, agreeing with methodology. The statistical sheet contains four
class rows plus one pooled row; that pooled row is not counted as a class.
Its BH family has seven defined class/metric hypotheses. Class `2` has no baseline
predictions, so its baseline precision and precision test are `NA`, while its recall
test remains defined. Pooled adjusted p-values remain explicitly inapplicable.

**Passed:** both published contexts contain exactly the frozen 40 test images,
including 19 backgrounds, with distinct source checkpoint/model/training-task
identity and no train/validation image inclusion. The exact threshold values in
published prediction rows match their respective handoffs. Invalid zero-area boxes
remain represented as excluded rows rather than silently changing raw source CSVs.

Independent row tallies match each class's TP/FP/FN in both downloaded dashboards
and the comparison workbook. Pooled totals are baseline `(0, 1028, 56)` and
candidate `(2, 9542, 54)`; each is the sum of its four eligible class populations.
These smoke counts are not a model-quality qualification.

**Passed:** training annotation counts are recovered from the original verified
training populations, not the current evaluation population. The report's separate
training-count rule excludes class `2` from both models because it has three
training objects, below the configured minimum of 20. Classes `1`, `3`, `4` remain;
the AP availability summaries are `3/3`. This three-class report population is
distinct from the four statistically eligible comparison classes. A further 144
numeric developer-report cells match their source dashboard values. Every report sheet has
both source-task links, and embedded workbook identities match the two handoffs.

**Passed, offline controlled regressions:** seven existing product tests executed
in 26.09 seconds: the five parametrized comparison API eligibility cases and two
unknown-training-count report cases. The comparison cases replace external detector/
tracking boundaries; they establish empty-prediction, missing-vocabulary, absent-GT,
mixed eligible/excluded and all-eligible behavior, not extra native-model outcomes.

```bash
uv run --locked pytest --testmon-noselect tests/test_workflow_quality.py::test_comparison_counts_only_statistically_eligible_classes tests/test_report_count_issues.py::test_real_reports_preserve_unknown_rows_without_counting_them -q -n0 --basetemp=.tmp/ticket87/pytest
```

## Independent publication readback

**Passed:** `scripts/readback.py` ran as a separate SDK process with a newly selected
cache, required both tasks completed, and forced nonempty downloads into that cache.
All download hashes matched locally generated product outputs. The applicable
inventory was exactly eight comparison artifacts (GT, combined predictions, four
role/split dashboards, comparison workbook and exclusion CSV) plus two report
workbooks. Canonical configuration, plot payloads and headline values were retrieved
separately. Standalone commands do not require a pipeline outcome or training model.

The comparison task contains only candidate confusion-matrix and test PR plot
records; no baseline plot or comparison-table plot was added. Detailed comparison
tables remain downloadable workbooks. Exact receipts and downloaded publications
are retained under `attempt02/readback/`.

## Actual standalone rendering

**Passed:** an isolated headless Chromium process used port 9297 and a ticket-owned
profile, with GPU disabled. It did not use the other agent's browser or the user's
profile. `scripts/browser.cjs` drove actual mouse clicks/movement via CDP and saved
17 final screenshots plus 15 observation records with zero browser runtime errors.

- Native candidate confusion/PR figures came from the fresh API readback.
- Clicked Counts, Row %, Column % and Overall % on both native and controlled
  zero-row figures; exactly one heatmap was visible each time. All 136 rendered
  cell values match independent normalization arithmetic. Percentage color scales
  remain 0–100. Hover shows original count/denominator; a zero denominator visibly
  says `no observations` and displays finite zero.
- PR legends hide and restore traces. The controlled point hover visibly displays
  class, AP50, method, recall, precision, confidence and cumulative TP/FP.
- Controlled figures explicitly cover a class with GT but no predictions, a class
  without GT, lexical label `0001`, Unicode and an entirely empty class collection.
  Legends distinguish AP50 zero from unavailable recall/AP; the empty chart visibly
  says `No classes available` without invented points.
- Source captions and true/predicted axes were visually inspected. Product slot
  allocation reuses the same checkpoint/split label across stages and distinguishes
  a second checkpoint with `Comparison candidate`; stored identity wins over a
  conflicting fallback name. Exact source identifiers remain in machine evidence.
- Native and controlled unknown-count workbook values were also displayed as
  explicitly labelled HTML tables. The unknown worksheet retains its measured
  values and unavailable training count, while valid zero appears separately among
  count-filtered exclusions. These screenshots establish an HTML value view, not
  native Excel layout, printing or application behavior.

Figures use installed Plotly 6.9 `Figure` serialization with its bundled JavaScript.
An initial scratch renderer passed raw SDK dictionaries directly to Plotly.js and
omitted legacy string axis titles; standard Python serialization normalized those
titles correctly. Raw payloads and initial screenshots remain retained separately;
the final pass explicitly checks visible axis captions. No product payload or
scientific values were modified to make the visuals pass. Controlled edge figures
and workbook inputs are labelled fixtures, not fabricated native observations.

The embedded ClearML UI is **outside this campaign**. No embedded-UI or browser
rendering outcome is inferred from API data.

## Failures, cleanup and acceptance boundary

The first invocation failed before task creation because the scratch command used
an unsupported `half` override. A subsequent attempt inherited `compile=True`;
the coordinator was informed, its owned main process was terminated and the native
ownership boundary exited 143. Its failed task `2efa0343a79c40fca20dc071b6707eb1`
and log remain failed evidence. Observed main/worker/compiler PIDs exited; the
successful attempt used a separate output directory and explicit `compile=False`.
Scratch audit corrections also used the actual workbook identity reader and the
contracted linked source footer. These were verification-script errors, not product
defects, and are not counted as successful execution.

All selected final checks passed; none is deferred or waived. No product changes
required new typing, mutation or global-coverage runs. Native workflow consistency
review maps this evidence to ticket87 without changing maintained contracts.
The coordinator owns final independent acceptance, ledger integration and commits.

After retaining receipts, scripts, workbooks, CSVs, HTML and screenshots, the owned
browser was stopped and its descendants were absent. Comparison/report/readback,
audit and regression processes had exited. Exactly 47,732,329 bytes of ticket-owned
download caches, browser profile and pytest scratch were removed; all 186 protected
files were rehashed unchanged. `cleanup.json` records exact paths. Shared library
caches, fixtures, accepted handoffs, remote tasks and services were untouched.
Ticket93 retains final service/task cleanup ownership. No GPU training, product edit,
commit, push, deployment or release was performed by this task.

## Coordinator review

On 2026-11-16 the coordinator rehashed all 186 retained files and independently
inspected representative final native-normalization, PR-hover, empty-chart and
unknown-count screenshots. The audit distinguishes four compared classes from the
three-class report population and separately labels controlled edge fixtures.
Scoped outcomes and cleanup are accepted; final automatic verification of the
documentation commit remains required. No product change is introduced.
