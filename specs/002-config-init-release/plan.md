# Implementation Plan: Configuration examples and 0.3.0 publication

**Branch**: `master` | **Date**: 2026-09-28 | **Spec**: [spec.md](spec.md)

## Summary

Record the completed restoration of the local configuration initializer and removal of
future-annotations imports, then validate, commit, push, and publish the pending 0.3.0.
This plan is retrospective for code already implemented; release tasks remain sequential.

> **Historical plan.** It records the v0.3.0 publication workflow. The later
> [native configuration feature](../003-ultralytics-config-groups/spec.md) replaced sparse
> native mappings with top-level native groups and expanded initializer output from eight
> command files to ten protected files. The maintained version is declared in
> [pyproject.toml](../../pyproject.toml).

## Technical Context

- Python 3.12; existing uv/uv_build toolchain and locked dependencies.
- argparse initializer; Hydra/hydra-zen/OmegaConf defaults exported as command-named YAML.
- Local filesystem storage only; no new service, schema, dependency package, or model runtime.
- Existing upstream dependencies become editable Git submodules at unchanged revisions.
- `.agents/skills` owns shared skills; `.claude/skills` links to that directory.
- pytest behavior checks, Ruff, strict mypy, seven import contracts, and pre-commit.
- Eight execution examples, two native group files, and nine installed console scripts;
  required inputs stay missing.
- At plan execution time, version 0.3.0 was verified in isolation, committed and published
  from master; v0.2.0 had been the latest published version.

## Constitution Check

The user explicitly changed two former rules. Constitution 3.0.0 replaced the mandatory
future import and config-generation prohibition, and distinguishes local initialization from
tracked execution. Constitution 4.0.0 later superseded its native configuration rules.
The original pre-design and post-design checks against all five principles were:

| Principle | Application |
|---|---|
| Typed, explicit Python | Remove imports; use Self and quoted runtime-incompatible references; retain strict checks |
| Module boundaries | Add config_tree between apps and configs; CLI modules remain independent |
| Configuration and ownership | Export central defaults; preserve missing inputs and user files; no task for initialization. The later [native configuration feature](../003-ultralytics-config-groups/spec.md) added full shared native defaults and prediction overrides. |
| Verification | Reproduce runtime annotation failures; verify pytest, CLI composition, packages, and live release paths |
| Communication and collaboration | Russian README, English artifacts, explicit evidence limits, task-owned staging and cleanup |

No remaining exception is required. The user explicitly authorized the source-layout change;
external dependency revisions and source code remain unchanged.

## Project Structure

```text
specs/002-config-init-release/
  spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md
  contracts/cli.md
  checklists/requirements.md
src/clearml_yolo/config_tree.py          # generate examples from current defaults
src/clearml_yolo/apps/config_tree.py     # positional directory and --force CLI
src/clearml_yolo/**/*.py                # remove future annotations imports
tests/test_config_tree.py               # generation/composition/file protection
tests/*.py                             # matching annotation migration
```

The generator remains outside the tracked execution adapter. Defaults are composed before
writing. All destinations are checked first; ordinary creation uses exclusive file creation.
Force replacement is limited to regular example files. Command names avoid Hydra schema-name
collisions. Filesystem failures are reported by argparse with a nonzero exit.

## Implementation and Release Sequence

1. Restore generator and entrypoint, tests, import contracts, and public documentation.
2. Remove future imports throughout src/tests. Use Self for receiver-returning methods,
   quote the FakeYolo forward reference and pandas Series generics evaluated at import time.
3. Amend governance and create this specification, decisions, contract, validation guide,
   and task record. Keep the local feature pointer untracked according to .specify/.gitignore.
4. Run all repository gates; verify both distributions in separate fresh environments.
5. Exercise current CPU/GPU execution and artifact retrieval on isolated task-owned resources.
   Record any unavailable or failing gate explicitly; preserve historical evidence separately.
6. Review the combined changes and evidence; stage only task-owned paths and commit without
   bypassing hooks. Push master, create the version tag at that commit, and publish a GitHub
   release with the verified wheel, source archive, checksums, and release notes.
7. Read back the remote commit/tag and published assets, verify downloaded asset hashes, and
   clean up temporary verification resources. Package-index publication is outside scope.

The user approved including concurrent dependency-source and skill-directory changes.
The isolated checkout now contains the combined snapshot. Initialize pinned submodules
before the locked development sync. Distribution metadata carries version requirements;
fresh-package verification supplies explicit upstream Git revisions without local sources.
Verify shared skill frontmatter, symlink resolution, template composition, and prerequisite
script interfaces before publication. Git writes remain serialized.
