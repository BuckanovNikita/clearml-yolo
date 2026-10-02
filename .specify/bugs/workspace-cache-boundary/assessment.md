# Bug Assessment: Workspace cache boundary

- **Slug**: workspace-cache-boundary
- **Created**: 2026-10-01
- **Source**: pasted user report and approved implementation plan
- **Verdict**: valid
- **Severity**: medium

## Report

The requested workspace storage was intended for dataset working copies and task-produced
artifacts. General tool/library caches should remain at their defaults. The approved plan
also retains ClearML downloads and FiftyOne dataset/database storage, and makes CSV cache
selection independent of XDG_CACHE_HOME.

## Symptom and Reproduction

Import an application entrypoint in a fresh process with CY_HOME set and general cache
variables absent. initialize_filesystem populates general XDG, Torch/CUDA/Triton/Numba,
Hugging Face, Matplotlib, bytecode, ETA and global temporary defaults beneath CY_HOME.
The package bootstrap also changes sys.pycache_prefix. Set XDG_CACHE_HOME elsewhere:
dataset_cache_root(None) incorrectly selects that location for working copies.
Static inspection confirms these behaviors; regression tests will exercise them before fixing.

## Suspected Code Paths and Root Cause

High confidence: src/clearml_yolo/filesystem.py sets broad dependency defaults and
mutates tempfile.tempdir; src/clearml_yolo/__init__.py redirects bytecode before imports;
src/clearml_yolo/dataset_cache.py reads XDG_CACHE_HOME for project working copies.
Existing tests and feature 011 documents encode the overly broad interpretation.

## Proposed Remediation

Narrow automatic settings to YOLO_CONFIG_DIR, CLEARML_CACHE_DIR and FiftyOne database,
default dataset and dataset-zoo directories. Preserve existing explicit environment and
FiftyOne configuration data paths without redirecting general configuration paths.
Remove bytecode bootstrap and general tempfile/environment overrides. Default CSV cache
to CY_HOME/.cache/clearml-yolo/datasets; retain explicit dataset_cache_dir.
Keep app-owned temporary files explicitly under CY_HOME/.tmp and native staging intact.

Files likely to change: filesystem.py, __init__.py, dataset_cache.py, config_tree.py,
tests/test_filesystem.py, test_dataset_cache.py, test_train.py and test_pipeline.py.
Documentation scope: README.md, docs/filesystem-policy.md, feature 011 active intent,
contracts, quickstart and appended task history; affected generated config comment and
cross-feature default-cache references. Preserve dated verification and completed history.

## Tests and Verification

First reproduce cache/temp/bytecode mutation and XDG-driven dataset routing in fresh
processes. Cover unset and explicit general settings, frozen launch root, explicit data
paths and legacy ClearML alias, read-only FiftyOne config, retained data locations,
owned temporary cleanup and native runtime restoration. Run affected tests then full
pytest, Ruff, mypy, import contracts, Markdown and local-link validation.

## Risks and Considerations

Restoring dependency defaults intentionally permits their writes outside CY_HOME.
Existing cache directories are neither removed nor migrated. Old exported environment
settings remain explicit user selections; a fresh process is necessary to see new defaults.
No dependency changes, commits or deployment are authorized. Preserve unrelated edits.

## Open Questions

None. Slug generated for the automatically routed, already approved remediation.
