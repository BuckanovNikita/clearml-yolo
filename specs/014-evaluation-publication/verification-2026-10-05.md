# Evaluation publication verification — 2026-10-05

## Scope and implementation

Implemented the approved [specification](spec.md) and
[publication contract](contracts/publication.md): canonical effective GT/combined result
CSVs, explicit source lineage and matching evidence, original full/DTRK dashboards,
four interactive confusion views, authoritative AP50-checked class PR curves, project-local
display naming, checkpoint-bound model thresholds and owner-only completion finalization.
Historical publications and the pinned external dependencies remain unchanged.

Implementation used three bounded native agents with exclusive source/test ownership;
the parent integrated lifecycle/task wiring and verified the combined diff. Documentation
was updated independently. Requested agent controls were GPT-6.1 Sol high for export and
metadata, medium for rendering/documentation; runtime realization was not separately exposed.

## Automated checks

- Full pre-review suite: 1,146 passed, 9 opt-in FiftyOne tests skipped. Four existing
  Hydra/Pydantic deprecation warnings remained.
- Parent regression verification after review corrections: 69 passed, covering native
  naming, calibration metadata, explicit splits and model identity preservation.
- Live FiftyOne persistence suite: all 9 passed against an isolated external test database.
  Covered concurrent publication, dataset reuse, retry isolation, interrupted import,
  exact evaluated overlays, collapsed geometry and background samples. Dependency
  deprecation warnings did not affect results.
- Final `uv run pre-commit run --all-files` passed every configured hook, including
  Ruff, strict mypy, nine import contracts and the full pytest suite with live FiftyOne
  enabled. The final collection contained 1,158 tests. The final independent-review
  verdict was **ship**, with no remaining findings.
- Wheel and source distribution were rebuilt from the final implementation and installed
  into separate fresh environments. All nine command helps, generated configuration trees,
  overwrite protection and installed-package imports passed for both distributions.

## Native execution and server evidence

The synthetic dataset contained disjoint train/validation/test images, one labelled
Unicode class and a background image in each split. A one-epoch model exercised native
execution and publication; this is an integration check, not an accuracy claim.

CPU and single-GPU pipeline executions completed. A candidate without an automatic
baseline retained its dashboards/plots and skip evidence. After promoting the isolated
baseline, a GPU candidate ran paired current-test comparison and produced the unchanged
comparison, developer and business workbooks. The corrected native output directory
remained `detect/train` despite display-name collisions. Explicit test-only validation,
standalone comparison with nondefault matching/integration, and report-only execution
also completed. Report-only uploaded exactly its two reports and no evaluation plots.

Following the user's additional release gate, a final full GPU pipeline ran with FiftyOne
enabled, including training, prediction, train/val/test metrics, baseline reinference,
comparison and both reports. Its 17 required artifacts and 39 plot events were retrieved
from ClearML. The persisted six-sample FiftyOne dataset was complete, included backgrounds
and all three split overlays, retained exact matching fields, and matched the local
publication receipt and canonical ClearML configuration. No viewer server was started;
the preserved dataset/run reference is the existing visualization handoff.

Every artifact and owned checkpoint was force-downloaded. CSV schemas/contexts and workbook
sheets were inspected. Each best checkpoint's SHA-256 matched both model provenance and
calibration metadata; per-class thresholds matched the full-precision validation CSV.
Five downloaded raw confusion matrices matched their native matrix workbooks exactly;
all 15 normalized variants and five PR payloads passed axis/scale/annotation/hover checks.
Native training scalars, validation Debug Samples, console records and effective run/dataset
configuration remained present. Plot verification inspected persisted SDK payloads, not
browser-rendered interaction.

An early CPU run exposed directory creation before native training, causing Ultralytics to
increment the output name. A failing regression established the cause; registration now
uses the parent output directory, and subsequent CPU/GPU runs retained the expected path.
A standalone comparison attempt encountered a transient SDK lazy-model metadata read
failure. The task failed rather than completing with missing evidence; a fresh unchanged
invocation succeeded. The original backend response was unavailable. No dependency patch
or retry behavior was added.

## Review corrections

The first independent read-only review returned `fix-first` for a model naming race:
collision checks finished before the actual SDK model-name write. Constructor and setter
race regressions now prove the write occurs inside the bounded retry loop, reuses the
same model ID/URL, and verifies the final shared suffix. Exhaustion still fails clearly.
A separate regression proves explicit test-only evaluation retains calibration/prediction
evidence without inventing an unused GT-only train context.

## Documentation and boundaries

Updated Russian README, project/current contract summaries, publication and model metadata
contracts, and the end-to-end skill. No CLI syntax changed. Generated examples were
exercised by package checks and the final full pipeline. Markdown parsing, local links,
anchors, whitespace and conflict-marker checks apply to all changed Markdown files.

Physical multi-GPU execution and browser-rendered plot interaction were not exercised.
Machine-specific commands, task/model identifiers, raw downloaded plot records and logs
are archived with the global environment skill. The isolated ClearML project and its task/model records, the exact owned FiftyOne
dataset, and the tag-scoped local run directory were removed after evidence capture.
The guarded ClearML listing confirmed zero remaining projects/tasks for the run tag;
FiftyOne confirmed the owned dataset no longer exists. Shared services and unrelated data
remain intact.

## Final acceptance

A fresh independent read-only reviewer returned **ship** after the corrections and parent
verification. It inspected the final implementation, regression tests, dependency parity
and recorded native/persistence evidence; no additional defects were found. All 12 changed
Markdown files parsed successfully, with 98 local links/anchors validated and no whitespace
or conflict-marker errors. Release preparation follows the documented commit procedure;
Git version tags are the only publication mechanism.

## Release

Feature commit `0946121` passed ordinary hooks, with real FiftyOne persistence enabled.
Release commit `fd7f24a` created annotated tag `v0.15.0` after ordinary commit checks and
the recovery workflow's full post-commit validation. The first automatic preparation
encountered the documented offline editable-dependency resolution limitation while local
source overrides were absent. Recovery changed only the root project version in the
lockfile and retained the generated changelog; all dependency records and external
revisions remained unchanged. Exact local source overrides were restored unstaged after
each attempt. No hooks were bypassed.

Both final 0.15.0 distributions passed installation, all nine command helps, configuration
generation and overwrite protection. Their installed Python source files matched the
accepted checkout byte-for-byte. Only Git commits and the version tag are published;
no package, release asset or deployment is part of this release.
