# Environment separation and cleanup — 2026-09-20

## Changes

- Removed generated configuration snapshots that referenced retired modules and the
  duplicate nested Spec Kit scaffold. Kept the active root workflows and feature metadata.
- Moved the three environment helpers, their tests and local stand guidance to the
  global `clearml-yolo-environment` skill. Removed the repository SessionStart probe;
  environment diagnosis is now on demand.
- Preserved all 15 original release-evidence files byte-for-byte in that skill's
  archive, with a SHA-256 manifest. Kept a portable release summary here.
- Removed implicit harness-based ClearML project/tag rewriting. Global run instructions
  pass both explicitly; application configuration now depends only on supplied values.
- Removed the unused scaffold greeting, checkpoint/dashboard constants and DataFrame
  upload wrapper. Preserved DataFrame artifact coverage, scoring tests, and DDP ownership.
- Updated README, migration notes, integration guidance and constitution 2.0.1 to
  separate project contracts from machine-specific operations.

## Verification

The new configuration regression first failed against the implicit rewrite, then passed
with explicit/default project and tags preserved under a populated harness environment.

- Repository pytest: 293 passed, four upstream hydra-zen/Pydantic warnings.
- Migrated helper pytest: 27 passed using fake infrastructure and curl commands.
- Ruff, strict mypy, seven import-linter contracts and pre-commit: passed.
- Shell syntax, both changed skill validators, local documentation links and diff checks: passed.
- All 15 archived files matched their original bytes; the migration manifest is retained
  with the global skill.
- Scan of active repository instructions, documentation, source and tests found no
  machine paths, stand endpoints or deleted helper command references. Harness variable
  names occur only in the regression proving that they no longer alter configuration.

No live training, GPU execution or infrastructure operation was performed for this cleanup.
The original release's live verification remains historical evidence, not a new run.
No new commit or push was performed. Fresh independent acceptance review returned
`ship`, with no findings. It independently verified all archive hashes, helper modes
and routing, and passed 52 focused configuration/helper tests. Global skill persistence
and versioning are separate from this repository.
