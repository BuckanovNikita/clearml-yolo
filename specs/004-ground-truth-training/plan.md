# Implementation Plan: Ground-Truth-Driven Training

**Branch**: `004-ground-truth-training` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

## Summary

Validate the supplied detection CSV once, remove and count invalid boxes, and export a
native NDJSON dataset by default or a flat dataset on request. Return a cleaned CSV for
all downstream evaluation. Keep conversion, images, manifests, and native byproducts
inside run-owned directories. Preserve legacy standalone native-data training.

## Technical Context

**Language/Version**: Python 3.12, existing uv toolchain.

**Primary Dependencies**: Existing Pydantic, Pillow, PyYAML, Ultralytics, Hydra/hydra-zen,
ClearML, and pinned external metrics/report dependencies. Require Ultralytics >=8.4.165
for native local NDJSON conversion and declare its aiohttp extra directly. Declare Pillow
directly because new dataset domain code imports it; do not change external dependency revisions.

**Storage**: Local run-owned files and non-image ClearML artifacts.

**Testing**: pytest behavior tests; Ruff, strict mypy, import-linter; real native training
and artifact-download acceptance using the project integration skill.

**Target Platform**: Existing native execution platforms and local filesystem inputs.

**Project Type**: CLI applications and domain modules.

**Performance Goals**: Read each source image's dimensions once per preparation; avoid
loading model dependencies during configuration or domain validation.

**Constraints**: Exact CSV membership, 0.01-pixel tolerance, deterministic classes,
no source mutation, one tracking task, no image uploads, no dependency monkeypatching.

**Scale/Scope**: Existing detection CSV workflow; no remote ingestion or generated splits.

## Constitution Check

Pre-design: PASS. Typed domain code will remain independent of Hydra/ClearML/native
model runtimes. Tasks own tracking. The pipeline owns outputs and passes actual producer
results. No scheduling, dependency patching, additional command, or disabled tracking.

Post-design: PASS after runtime and integration research and requirements review. Preserve all
existing import contracts while adding explicit domain layers for the new modules.

## Project Structure

- `dataset_records.py`: typed boxes/images/validation result and CSV validation.
- `dataset_export.py`: native NDJSON and flat writers consuming validated records.
- `dataset.py`: preparation orchestration, cleaned CSV and preparation record, data policy.
- `tasks/train.py`: prepares CSV data, publishes non-image records, returns cleaned CSV.
- `tasks/pipeline.py`: forwards format, required splits, and cleaned CSV to consumers.
- `configs.py`, `config_tree.py`: expose parameters and generated example guidance.
- `tests/test_dataset_records.py`, `tests/test_dataset_export.py`, `tests/test_dataset.py`:
  domain acceptance; existing training/pipeline/configuration tests cover integration.
- `pyproject.toml`: declare direct image dependency and maintain import contracts.
- `README.md`: Russian usage and migration guidance.

Files above are relative to `src/clearml_yolo/` unless they include a repository directory.
Feature artifacts live alongside this plan: research, data model, CLI/artifact contracts,
quickstart, requirement checklist, tasks, and dated verification evidence.

## Architecture and Interfaces

`validate_ground_truth(source, required_splits)` returns validated typed records without
writing files. `export_dataset(records, directory, dataset_format)` writes only owned
files and returns the native data reference. `prepare_dataset(source, directory,
dataset_format, required_splits)` reserves a fresh directory, validates, writes a cleaned
CSV and metadata, exports the selected format, and returns a typed `PreparedDataset`.

NDJSON export writes a native local manifest with header `path: "."` and per-split
image filenames. Training uses the Ultralytics >=8.4.165 converter with explicit run-owned
output, then passes its YAML to the trainer. No HTTP server or custom parser is needed.
Flat mode writes the native layout directly.

Training prepares under its project's `.datasets/<name>` sibling of the native output;
this avoids pre-creating the native training directory and triggering name incrementation.
The pipeline obtains the cleaned path from `TrainResult.cleaned_ground_truth` and uses it for prediction,
metrics, and comparison. Evaluation-only invocations retain existing behavior.

Invalid boxes are recoverable. Fatal schema, identity, split, and image errors remain
explicit. Count all dropped attempted annotation rows once and display the total before
native training, including zero. Preserve all images; an image losing its final box is
background. Require at least one valid training box and nonempty requested splits.

The data policy owns `data`, class filtering/remapping, full dataset fraction, detection
task, and validation split. Reject resume rather than allowing checkpoint settings to
replace CSV ownership. Prediction/comparison must not reintroduce class filters.
All overrides are recorded with their requested/effective values; unrelated settings
continue through existing native configuration handling.

## Parallel Execution and Remaining Workflow

Follow [workflow-plan.md](workflow-plan.md). Parallel research covers runtime compatibility
and integration/tracking contracts. Once interfaces are fixed, delegate disjoint record
validation and exporter modules while the parent implements preparation orchestration.
Delegate task/config integration to its research owner with explicit ownership; the parent
owns shared boundaries, documentation, verification, and final integration. Keep each
module's behavior tests with its owner. No concurrent writers to shared files.

Sequence: clarify (no new material questions) → plan/research/contracts → requirement
checklist review → tasks → read-only analysis → implement → repository and native checks
→ converge → complete appended tasks and verify → fresh independent review.

The parent inspects the complete diff and reruns required checks before fresh review.
Review must return `ship`; corrections require another fresh review. Use native subagents
with explicitly selected supported models/efforts and fresh context. Report observed
metadata and cost-telemetry limits honestly. Current tool uses `fork_context=false` for
fresh context; its public interface differs from the skill's named API.

## Verification Strategy

Test valid/invalid/background mixtures, zero/multiple error counts, coordinate round trips,
class and split determinism, image identity/stem collisions, native format consumption,
override precedence, resume rejection, cleaned evaluation, and output/artifact ownership.
Run the repository gates and real standalone/pipeline NDJSON and flat invocations. Inspect
and download required tracking artifacts, including failure paths and current-test
comparison. Record dated evidence and clean task-owned resources only.
