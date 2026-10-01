# Implementation Plan: Reusable datasets and native ClearML tracking

**Branch**: `008-dataset-clearml-tracking` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

## Summary

Reuse a versioned CSV-addressed dataset and train directly from its prepared YAML. Enable
native owner callbacks, enrich and verify their one best model, replace broad uploads with
readable tables/workbooks, and resolve comparison inputs from source task links.

## Technical Context

**Language/Version**: Python 3.12, existing strict typing and uv toolchain.
**Primary Dependencies**: Installed Ultralytics, ClearML, Pydantic, filelock, pandas, openpyxl;
unchanged pinned digital-metrics/report-generator (pyproject.toml and uv.lock are authoritative).
**Storage**: Local shared cache with per-entry process lock and atomic directory publication;
ClearML native models and explicit artifact inventory.
**Testing**: pytest, Ruff, mypy, import-linter, pre-commit, real CPU/GPU ClearML runs.
**Target Platform**: Existing Python CLI platforms with process locks and atomic rename.
**Project Type**: Nine-entrypoint composable CLI.
**Performance Goals**: Zero repeat image copies/conversions/content hashing on a cache hit.
**Constraints**: No credentials, no worker publication, no global settings persistence, no
upstream dependency edits, no historical-task modifications, no commit/push.
**Scale/Scope**: Dataset preparation, training ownership, reporting, comparison, configuration.

## Constitution Check

Before research and after design: PASS against constitution 5.0.0. Typed interfaces and
module layers retained; native imports confined to permitted boundaries; one task and
owner-only publication; credentials sanitized; exact validation thresholds frozen; real
verification distinguished from mocks. Shared dataset lifecycle is independent of run cleanup.

## Project Structure

- `dataset.py`, `dataset_export.py`, new `dataset_cache.py`: preparation, names, locks,
  completion validation, immutable shared entries and consumer write protection.
- `native_runtime.py`, `clearml_session.py`, new `clearml_native.py`: native callback scope,
  canonical configuration, artifact deduplication and model completion barrier.
- `tasks/metrics.py`, `tasks/predict.py`, `tasks/report.py`, `tasks/publication.py`,
  `artifact_names.py`: canonical CSV and consolidated workbook publication.
- `tasks/train.py`, `tasks/pipeline.py`, `configs.py`, `config_tree.py`, `apps/common.py`:
  integration and cache option, native model finalization, remote replay.
- `clearml_models.py`, `tasks/compare.py`, `comparison/reinfer.py`: explicit best selection,
  exact threshold compatibility, source links, shared comparison configuration/workbook.
- `tests/`: regression tests colocated by corresponding source module.
- `contracts/`: cache/publication/model mappings; `quickstart.md`: runnable acceptance.

## Design decisions and interfaces

1. `cached_dataset(source, cache_dir=None, dataset_format="ndjson", required_splits=...)`
   is a context manager yielding PreparedDataset and guarding the native consumer lifetime.
   Default is explicit `XDG_CACHE_HOME/clearml-yolo/datasets`, else
   `CY_HOME/.cache/clearml-yolo/datasets`.
   Identity combines SHA-256 CSV bytes, format and preparation version. Staging publication
   rewrites absolute generated paths to the final entry before atomic rename. Completed
   metadata lists required relative files and split counts; readers reject corrupt entries.
   The conservative first implementation holds the entry lock through training, including
   DDP completion: native JPEG repair and .cache/.npy writes cannot race across invocations.
   Concurrent requests wait for the same entry; distinct entries can train concurrently.
   No GPU scheduling is introduced. Native-YAML inputs now use a separate locked cache of real
   image and label copies under `CY_HOME/.cache/clearml-yolo/native-datasets`; this supersedes the
   earlier assumption that native source inputs themselves could safely receive repair/cache writes.
   See the maintained [filesystem ownership contract](../../docs/filesystem-policy.md).
2. `upload_artifact` retains strict required-publication bookkeeping. Add
   `publish_table(task, name, path)` to deduplicate identical CSV bytes across stages while
   recording aliases internally; required declarations are satisfied by canonical publication.
   Empty header-bearing prediction tables remain valid. No dictionary/diagnostic uploads.
3. `record_run_configuration(task, values)` merges sanitized meaningful fields into one
   `run` object; `connect_config_file` attaches consumed configurations without artifacts.
   The launch boundary resolves canonical remote configuration before task execution and
   native General parameters own training arguments. Local commented YAML remains retained.
4. `native_runtime()` enables the installed callback mapping in the owner, disables inherited
   worker settings, and restores all modified state. Owner task is initialized before model
   execution. `finalize_native_model(task, model, trainer, architecture)` verifies callbacks,
   locates the registered best model, enriches that record and registers its completion
   barrier with the session. Never create a fallback second model when native registration fails.
5. `clearml_models` resolves best explicitly by model metadata/best.pt URL, with ambiguity
   failure and historical artifact fallback. New threshold CSV is validation-only; historical
   split payload remains readable. Shared source-link metadata contains task/model URLs.
6. Evaluation workbook contains summary, class results, matches, confusion matrix,
   thresholds and methodology. Comparison workbook includes paired counts, exclusions,
   methodology and source links. Report stage publishes only final dev/business workbooks.

## Parallel ownership

Dataset delegate owns dataset modules/tests. Native delegate owns runtime/session/new native
adapter/tests. Reporting delegate owns metrics/predict/report/publication/artifact names/tests.
Parent owns train/pipeline/CLI/configs/comparison/docs and integration tests. Freeze interfaces
above before dispatch. Reporting depends on the publication adapter contract, not its
implementation: independent files may proceed after contract freeze. Parent resolves interface
mismatches after delegates complete. Delegates never edit parent-owned files or task markers.

## Verification and acceptance

Tests cover cache hits/change/collisions/splits/concurrent requests/interruption; exact
inventories; callbacks/worker/settings; registration/upload/flush/interruption failures;
new and historical thresholds/models; local model support. Parent runs full checks and
inspects the complete feature diff against v0.8.0, then real E2E and Spec Kit convergence.
Fresh read-only gpt-5.6-sol/high review must return ASTRA REVIEW / VERDICT: ship.
No acceptance claim is permitted while real-run or review gates remain unavailable.

## DDP native callback compatibility

Installed Ultralytics suppresses integration callbacks in the launching DDP parent.
`native_ddp.py` captures exact callback inputs and event-time preview/plot snapshots
in rank zero, using the upstream callback serialization path. After training the
invocation owner replays all installed native ClearML callbacks and applies the
worker's effective training arguments before enriching the same output model.
Workers never initialize ClearML or publish. Incomplete event output fails the
invocation. Snapshots survive until model/artifact waits and flush complete.
Single-process training bypasses replay. Physical multi-GPU execution remains an
environment-dependent integration check; CPU worker relay evidence is separate.
