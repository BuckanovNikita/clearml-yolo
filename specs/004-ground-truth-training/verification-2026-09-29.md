# Ground-Truth Training Verification — 2026-09-29

## Scope and Runtime

CSV-driven standalone and pipeline training, native local NDJSON (default), flat export,
invalid-box recovery, configuration ownership, artifact lifecycle, and paired comparison.
Python 3.12; Ultralytics 8.4.165. No change to external submodule revisions or their lock entries.

The native NDJSON header uses `path: "."`; image records use split-local filenames.
Training calls the native converter with a run-owned output directory. A regression blocks
HTTP image requests while consuming the exported manifest. No image server was started.
The previous custom parser was removed after confirming released native support.

## Real Execution

Four CPU invocations ran against an isolated ClearML project: standalone NDJSON, standalone
flat, pipeline NDJSON without an automatic baseline, then pipeline flat with the completed
NDJSON pipeline promoted to baseline. Each invocation owned exactly one task.

Portable command settings: `ground_truth=<fixture.csv>`, `dataset_format=<ndjson|flat>`,
`ultralytics.model=yolo11n.yaml`, `ultralytics.pretrained=false`, `ultralytics.epochs=1`,
`ultralytics.imgsz=64`, `ultralytics.batch=2`, `ultralytics.workers=0`,
`ultralytics.device=cpu`, `ultralytics.plots=false`, `ultralytics.mosaic=0`,
`ultralytics.classes=[0]`, and `ultralytics.fraction=0.5`. Each command also supplied explicit
project, tag, task name, and isolated native project or pipeline run directory. Pipeline
comparison used 50 bootstrap iterations.

The fixture contains 12 local images: four per split, including one explicit background
per split; nine valid and three invalid annotations. Every invocation displayed
`Invalid bounding boxes dropped: 3` before training, retained all images and nine valid
boxes, and produced `best.pt`. Effective settings retained batch/epochs and enforced
`classes=null`, `fraction=1`, and `cls_remap=false`.

| Invocation | Status | Downloaded artifacts |
|------------|--------|----------------------|
| Standalone NDJSON | Completed | 19 |
| Standalone flat | Completed | 18 |
| Pipeline NDJSON | Completed; comparison skipped without baseline | 79 |
| Pipeline flat | Completed; paired comparison and both reports produced | 103 |

Every artifact was force-downloaded; required artifact-manifest entries reported uploaded.
Preparation counts and split membership matched the input. No dataset image paths appeared
in uploaded file inventories. Native training generated no duplicate ClearML tasks.
Candidate validation/test thresholds matched exactly. Baseline comparison thresholds matched
the baseline's stored validation thresholds. Paired comparison included the same four current
test image names and retained its comparison manifest and developer/business reports.

## Failure Evidence

Three controlled invocations used real ClearML task lifecycles and local CSV preparation.
Upload rejection and flush rejection were injected at their SDK boundaries; interruption
sent SIGTERM to the owned process. Upload/flush exited 1, interruption exited 143; all three
tasks were failed, with local preparation JSON and data YAML retained before cleanup.

The first live attempt found `cls_remap=None` invalid for the native boolean configuration.
A native `get_cfg` regression reproduced it; setting `False` fixed it, and all four later
training runs succeeded. Repeated invalid annotation rows were also reproduced as a fatal
duplicate error, then corrected to drop/count each invalid row while rejecting valid
annotation duplicates and duplicate background rows.

## Repository Checks

Ruff, strict mypy (71 source files), and all seven import contracts passed.
An initial full suite reported 430 passed and one release-tag fixture failure caused by a
dirty fixture lockfile. That unrelated case passed when rerun alone; no release code changed.
The full rerun passed: 431 tests, three existing deprecation warnings, 85.40 seconds.
Two subsequently added format cases passed in the seven-test exporter suite. Those tests
verify distinct same-stem images and native coordinate round trips within 0.01 pixels.
Final Ruff/mypy/import and whitespace checks passed after integration.

## Spec Kit Convergence

Reviewed 19 functional requirements, six success criteria, 15 story acceptance scenarios,
seven architecture/ownership decisions, and the five constitution principles. One medium
partial-verification finding remained: T010 did not explicitly test same-stem collisions
and coordinate round trips together. Appended T018, implemented it for both modes, and
verified it. The follow-up assessment found no remaining implementation gaps; independent
review subsequently passed as recorded below. No Spec Kit extension hooks were registered.

## Limits and Evidence Retention

These small runs prove execution and artifact contracts, not model quality or throughput.
GPU, physical multi-GPU/DDP, long training, and wheel/sdist release installation were not
exercised. Existing Hydra/Pydantic deprecation warnings remain. No commit or push was made.
Both task-owned ClearML projects and run directories were cleaned; zero tagged tasks
remained. Shared services were left intact. Machine-specific commands, logs, task IDs,
and cleanup evidence are archived through the
global `clearml-yolo-environment` skill rather than committed to this repository.

## Independent Review

The first fresh reviewer returned `fix-first`: Pillow reports JP2 as `jpeg2000`, while
our decoded-format check accepted only filename extensions. A real JP2 regression
reproduced the rejection; the installed native `check_image` accepted the same file.
The validator now accepts the decoded JPEG2000 alias. All 35 validation tests and
Ruff/mypy/import/whitespace checks passed after this fix. The second fresh read-only reviewer returned `ship` with no findings, confirming the
JP2 correction and integrated CSV/NDJSON contracts. All implementation and convergence
tasks are complete.


## Delegation and Usage Receipt

Parallel contributors owned validation, export, and task/configuration slices; a subsequent
bounded validation correction handled duplicate invalid boxes. Fresh read-only reviewers
examined the integrated change after parent verification, with a new review after correction. Requested model/effort settings
were explicit; runtime confirmation and token usage were not exposed by the native tools.

API-EQUIVALENT COST RECEIPT: unavailable for parent, implementers, and both reviewers because
per-call usage is unobservable. No token totals, USD estimates, or savings are claimed.

## Release Follow-up

After the user authorized commit, push, and release, the final 434-test suite passed and
all commit hooks passed on feature commit `ef7c6d9`. A native single-GPU NDJSON pipeline
then completed one epoch with AMP enabled, produced its checkpoint, evaluated validation
and test, and followed the expected missing-baseline skip path. Exactly one ClearML task
completed; all 79 artifacts were downloaded and validated. The pre-training invalid-box
count was three, CSV-owned overrides remained effective, and test thresholds matched
validation thresholds. This extends the earlier CPU-only verification scope; physical
multi-GPU/DDP remains unverified. Machine-specific logs are retained with the global
environment skill. Distribution-install and publication results are reported in the release.
