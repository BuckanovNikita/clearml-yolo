# Verification evidence — 2026-11-10

## Scope and source state

Implementation branch: `012-editable-batch-sizes`, based on local/remote master
`f1a3755377ce76e919fe87e65d3a751c1fc9a76f`. Both source remotes were fetched.
Sibling queue base: `e93896734905b54129723f9d0ff3d8a70b9d7e00`, matching origin/main.
The sibling adaptation changes only the batch submission regression and related
contract wording; it replaces old JSON fixture/profile patching with editable YAML
and verifies assigned-device resolution while preserving requested null.

## Focused checks

Passed: search/CLI/list/numerical suite (722 tests); table/list suite after alias,
Unicode and source-provenance fixes (60 tests); training/profile/numerical suite
(72 tests), and architecture checks (3 tests). These are controlled CPU tests,
not native capacity or training evidence. Scoped Ruff and mypy passed. Queue Ruff,
format, mypy and source-path import contracts passed.

An initial project check caught three test-annotation issues; corrected before the
next verification run. The initial paired suite reported 526 passed, one failed:
the queue regression depended on the removed strict-profile lookup and JSON store.
The sibling regression was updated; final paired evidence is recorded below.

## Independent review

Bounded independent review of search, storage, CLI and documentation found and resolved:

- Aliased YAML mappings could change unrelated rows; publication now detaches mutable paths.
- Forced/background-sensitive and numerical/ceiling source limitations could disappear
  from table reuse; unchanged measured entries retain source metadata and CLI displays it.
- Augmentation/filesystem guidance retained superseded JSON/profile lookup wording;
  current contracts and Russian README are reconciled.

A separate reviewer examined training lookup (not its author), including explicit
batches, device/model/shape restrictions, per-device selection, provenance and removed
workload/recipe gates. User-facing schema wording was updated to name the editable table.

## Required gates

- Development verification: running; final result pending.
- Branch mutation: first bounded report completed, 8 of 30 changed functions,
  167 mutants: 119 killed, 48 survived, 0 not reached, 0 not run. Test selection used
  existing testmon nodes plus import fallback. Source provenance behavioral survivors
  are being addressed; final report and dispositions pending. Twenty-two functions
  were outside the default function budget, not claimed mutation-tested.
- Paired CY/queue: initial failure diagnosed above; final rerun pending.
- Clean-tip acceptance: pending. Read-only stand preflight returned UNAVAILABLE/3:
  shared stands at capacity. This defers live verification, not a pass.
- Final `prek run --all-files` with skips cleared: pending.
- Native bounded estimation and training lookup: deferred. pcboard could not identify
  this session using either host discovery or its session identifier, so safe GPU
  availability could not be established. No GPU job was launched and no wake-up was
  registered. Mocked tests do not establish native/GPU outcomes.
- Release: blocked by deferred required checks; no push authorization. No version,
  tag, merge or push is performed.

## Resource ownership

No shared stand objects or GPU processes were created. Paired-check uses task-owned
temporary environments and cleans them on exit. Mutation uses its own temporary
workspace. Pre-existing services, datasets and the other worktree remain untouched.
