# Bug Fix: Workspace cache boundary

- **Slug**: workspace-cache-boundary
- **Fixed**: 2026-10-01
- **Assessment**: [assessment.md](assessment.md)
- **Status**: applied

## Summary

Startup now redirects only project-owned data and the approved Ultralytics, ClearML and
FiftyOne stores. General dependency cache/configuration and Python temporary/bytecode settings
are left unchanged. Null CSV cache selection uses CY_HOME independently of ambient XDG.

## Changes

| Subsystem | Change | Notes |
|---|---|---|
| filesystem policy | Narrowed initialization and read-only FiftyOne data selections | Explicit settings and legacy ClearML alias preserved |
| package bootstrap | Removed automatic bytecode mutation | Normal interpreter behavior restored |
| dataset cache | Removed XDG precedence | Explicit dataset_cache_dir still wins |
| configuration export | Updated cache guidance | Generated examples explain the dedicated override |
| regressions | Updated cache/storage tests and added fresh-process coverage | General unset/explicit settings, tempfile and bytecode unchanged |
| documentation | Reconciled README, filesystem policy, feature 011, affected feature 008/009 guidance and E2E skill | Completed history and dated verification preserved |

## Tests Added or Updated

- Fresh-process startup asserts general environment, sys.pycache_prefix and cached tempfile
  destination remain unchanged, without creating generic dependency directories.
- Dataset-root regression covers XDG pointing under home and explicit dataset_cache_dir.
- Real native and publication imports verify approved workspace data directories and DDP cleanup.
- Existing default and explicit FiftyOne configurations remain read-only; configured dataset
  and database directories and environment precedence are preserved.
- Training/pipeline run-owned-cache rejection tests now select CY_HOME rather than XDG.

## Local Verification

- Before implementation, the three new startup/XDG regression cases failed as expected.
- Affected dataset/filesystem/train/pipeline selection: 68 passed, 4 Hydra/Pydantic warnings.
- First full suite: 720 passed, 8 opt-in integration skips, 4 Hydra/Pydantic warnings.
- mypy: no issues in 96 source files; import-linter: 9 contracts kept.
- Initial Ruff checks caught an unused import and long strings; these were corrected.
- Final checks and independent acceptance are recorded in [test.md](test.md).

## Deviations from Assessment

The documentation consistency pass also updated the project E2E skill/prerequisite text and
feature 008/009 quickstarts that required general runner cache/bytecode redirection. These
are affected policy consumers identified by the approved documentation scope; no installed
Spec Kit tooling, dependencies, or unrelated working-tree changes were edited.

## Documentation Stage

Updated active contracts and examples with the narrower storage ownership boundary. Historical
verification evidence remains unchanged. The final verification report records Markdown/link
validation and the independent review. Existing caches are neither migrated nor deleted.

## Follow-ups

No GPU/native training or remote ClearML upload acceptance is claimed for this bounded correction.
