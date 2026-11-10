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

- Development verification: passed through `prek run --all-files`, with skips cleared.
  The initial full run found four superseded expectations: removed `--classes` in parser
  defaults/help and immediate no-capacity at batch eight in probe tests. Narrow fixture
  corrections passed focused reruns (193 compatibility and 73 probe tests). No production
  change was needed. Subsequent full hook development verification passed.
- Branch mutation: passed advisory report; final 167 mutants, 153 killed, 14 equivalent
  or presentation survivors, zero unreached/unrun within eight selected functions.
  See [complete scope and dispositions](mutation-2026-11-10.md).
- Paired CY/queue: passed normal resolution, `uv pip check`, source/installed metadata,
  queue help and 527 queue tests (7 deselected). Versions: CY 0.47.0 and queue 0.1.10.
  The tested source changes are committed in CY `0d1889d` and queue `d3627a0`; subsequent
  changes are test expectations/assertions and dated evidence, not runtime behavior.
- Clean-tip acceptance: rerun pending. The preceding attempt passed static checks,
  properties (4753 passed, one skipped), coverage (4761 passed, one skipped, 84.30%
  against 84.12% required), and CPU stand smoke (one passed, 29 skipped, 81 deselected).
  The stand had become available after initial UNAVAILABLE/3 preflight. That attempt
  failed its final clean-worktree guard because mutation tests were added while it ran;
  it is not claimed as successful clean-tip acceptance.
- Final `prek run --all-files` after the final test commit: pending. Earlier full pipeline
  passed with skips cleared; newly added mutation regressions passed focused checks.
- Native bounded estimation and training lookup: deferred. pcboard could not identify
  this session using either host discovery or its session identifier, so safe GPU
  availability could not be established. No GPU job was launched and no wake-up was
  registered. Mocked tests do not establish native/GPU outcomes.
- Release: blocked by deferred required checks; no push authorization. No version,
  tag, merge or push is performed.

## Resource ownership

The CPU smoke run used the integration lifecycle's owned run tag and passed teardown;
its run-tag file was released. No GPU process was created. Paired-check temporary
virtual environments and retained mutation workspaces were removed after inspection.
Pre-existing services, datasets and the other worktree remain untouched. Verification
logs are retained locally as dated diagnostic evidence; no credentials were persisted.
