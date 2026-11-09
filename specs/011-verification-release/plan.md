# Implementation Plan: Verification and Release Workflow

**Branch**: `011-verification-release` | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/011-verification-release/spec.md`

## Summary

Adopt cveta2's verification and release model in clearml-yolo. Task becomes the command owner;
prek runs one serial `verify` hook behind a staging guard plus Conventional Commit validation;
live tests move to `tests/integration/` behind a run-tag lifecycle that wraps the existing
environment scripts; a new CPU stand smoke test gives change acceptance a live part;
`scripts/mutation.py` reports changed-function mutants; semantic-release's `build_command`
plus `release-commit-check` replace `scripts/local_release.py`, with integration and tagging
under `flock`. Sources are copied from `/mnt/wsl/data/nkt/cveta2` and adapted (see
[research.md](research.md)).

## Technical Context

**Language/Version**: Python `>=3.12.13,<3.14`; Bash for hook and status scripts
**Primary Dependencies**: Task via `go-task-bin`, prek, pytest with testmon, xdist, randomly,
pytest-cov and Hypothesis; mutmut; python-semantic-release; deptry; conventional-pre-commit
**Storage**: Per-worktree files: `.venv`, `.testmondata`, `.coverage`, tool caches,
`tests/integration/.run-tag`, `<git-common-dir>/clearml-yolo-release.lock`
**Testing**: pytest unit suite in `tests/`, live suite in `tests/integration/`
**Target Platform**: Linux/WSL2 workstation with the shared k8s ClearML stand and one GPU
**Project Type**: Python library and CLI (Hydra applications)
**Performance Goals**: Development verification for a one-file change avoids full-suite runs;
preflight returns within `CY_INFRA_CHECK_TIMEOUT` (default 60 s)
**Constraints**: No wheels or sdists in any stage; `digital-metrics` lock entry immutable;
heavy work honours pcboard; no pushes without authorization; no CI
**Scale/Scope**: ~187 test modules, 16 import contracts, 2 external editable sources

## Constitution Check

| Principle | Status |
|---|---|
| I. Typed Python | New Python (`scripts/mutation.py`, `tests/env_isolation.py`, `tests/integration/lifecycle.py`, smoke test) is strict-mypy, Ruff-clean, vulture-clean. |
| II. Module boundaries | `src/` is untouched; an architecture test keeps `clearml_yolo` from importing `tests` or `scripts`. |
| III. Run ownership | Live tests use explicit tagged ClearML project names and tags; cleanup by exact tag. |
| IV. Verification | **Amend wording**: commands move to Task stages; `prek run --all-files` remains the full hook check (it now runs `verify`). Mocked tests still do not establish GPU/upload outcomes; the smoke test is the live CPU evidence. |
| V. Collaboration | Staging guard never stashes; README stays Russian; dated evidence only in feature artifacts. |
| Constraints | No new runtime dependencies; dev-group additions only. Machine paths (`CY_QUEUE_DIR`, k8s-infra skill dir) are overridable with defaults. |

Gate result: PASS with one governed amendment (Principle IV wording, PATCH-level, via
`speckit-constitution`). Re-checked after design: unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/011-verification-release/
├── plan.md  research.md  data-model.md  quickstart.md
├── contracts/task-stages.md   contracts/release.md
└── tasks.md
```

### Source Code (repository root)

```text
Taskfile.yml                         # new: stage owner
.pre-commit-config.yaml              # rewritten: verify + manual stages + commit-msg
pyproject.toml / uv.lock             # dev deps, pytest addopts, deptry, coverage floor,
                                     # semantic_release build_command, mutmut settings
scripts/install-hooks.sh             # new
scripts/git-hook.sh                  # new: staging guard dispatcher
scripts/mutation.py                  # new: changed-function mutation driver
scripts/session_status.sh            # new: SessionStart report
scripts/local_release.py             # deleted
.claude/settings.json                # SessionStart hook (create or merge)
tests/env_isolation.py               # new pytest plugin
tests/conftest.py                    # xdist groups, Hypothesis profiles, integration marking
tests/integration/                   # new: conftest, lifecycle.py, moved live tests, CPU smoke
docs/development.md docs/ddp-testing.md AGENTS.md README.md
docs/adr/0001-semantic-release-with-flock.md
.specify/memory/constitution.md      # Principle IV wording amendment
.agents/skills/{verification-workflow,release,mutation-testing,running-integration-tests}/
```

**Structure Decision**: Repository tooling only; no `src/` changes.

## Complexity Tracking

No violations.
