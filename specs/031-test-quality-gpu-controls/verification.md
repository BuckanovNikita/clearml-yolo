# Verification: 2026-10-14

Implementation is based on `master` commit `665dfd3` (package `0.28.0`).
The pre-existing local `[tool.uv.sources]` overrides and untracked
`docs/cls-cls-pw-grid-search.md` are outside this task. Runtime dependency versions
and the approved external source copies were preserved. Only Hypothesis,
pytest-cov and coverage were added to the locked development environment.

## Failure reproduction and capability checks

A disposable interpreter with `os.pidfd_open` removed reproduced the original
`AttributeError` in guardian owner signalling. New capability tests initially
failed in 15 cases: missing APIs did not prevent native-scope entry or the new
probe interface was absent. After implementation all 15 passed. The combined
process-capability, tooling-boundary and direct-descendant suite passed 51 tests
in 25.08 seconds. The actual selected-interpreter shim deletes `os.pidfd_open`
before executing the production probe, rather than mocking its result.

Local checks open a self pidfd, send signal zero, probe P_PIDFD wait support,
query subreaper state and read process identity. Descriptors close on failure;
the supported probe preserves subreaper state. No fallback weakens cleanup.

## Queue controls and release retry

The queue workstream's controls plus existing GPU-resource tests passed 140 cases;
existing queue regressions passed 79 cases. Controls exercise real isolated locks,
real live-process refusal, normal verified cleanup, cross-root holds, owner identity,
legacy fencing and interrupted whole-allocation deletion. An added red/green case
caught a live marked descendant missed when historical ownership birth was zero;
force now scans conservatively instead of substituting the current tick.

Parent integration found a retry audit defect: an earlier verified audit could stay
verified after current evidence became uncertain. Two new tests failed first, then
passed after persisting a conservative downgrade before job state/capacity release.
A failed downgrade write retains both claim devices and the original job state.
The final control-only suite passed 39 tests; force still never signals.

## Generated and composed regression quality

The new modules and neighboring invalid-prediction/config/queue suites passed
56 tests in 56.71 seconds. Ruff and strict mypy passed for both new files.
Warnings were upstream Pydantic deprecation and missing CJK plotting glyphs.
Presentation workbook thresholds round; retained CSV and JSON assertions verify
exact scientific values independently of display formatting.

Three deliberately reintroduced semantic faults ran in separate Python processes.
Each process loaded a mutated module into memory before its selected test; no
repository source was changed. All three returned pytest exit 1 for the intended
behavior, with no syntax, import or collection failure:

| Fault | Selected new test | Observed failure |
| --- | --- | --- |
| Remove `dtype=_CACHED_TEXT_COLUMNS` from reinfer cache read | `test_real_prediction_cache_roundtrip_preserves_lexical_and_float_values` | Numeric image identifier became `[10]` instead of `['0010']`. |
| Omit checkpoint content digest from comparison cache identity | `test_comparison_cache_checkpoint_replacement_and_real_reports_preserve_source_pair` | Same-size/same-mtime replacement hit the actual cached-checkpoint provenance guard; workflow failed before reporting. |
| Disable `expected_revision != view.revision` rejection | `TestDurableQueueSequences` | Independent state machine expected stale-revision rejection and received no exception. |

The fault campaign driver returned exit 0 only after verifying those three
failures. A coverage-enabled run of the eight new tests also passed; branch HTML
and XML were produced under ignored `.tmp/` paths. Coverage is diagnostic and no
percentage threshold is claimed as proof of quality.

## Architecture and documentation checks

- Import-linter: 43 contracts kept, zero broken.
- Architecture and tooling-boundary pytest: 127 passed, five upstream warnings.
- Vulture: exit 0.
- Scoped Markdown lint after normalizing existing table separators and new file
  trailing blank lines: exit 0 with MD013 disabled for repository line lengths.
- Installed `cy-queue gpu --help` and `gpu release --help`: exit 0 and match docs.
- Architecture planning validator: exit 0 before implementation and after scope
  reconciliation. Hold storage remains in the lock adapter; `GPUControls` composes
  release, process verification and original-root state changes without a cycle.

Final full Ruff passed. Full mypy passed 317 source files; subsequent changes
passed their scoped rechecks, including the final four-file harness/marker check.
Final Vulture and import-linter also passed. Explicit marker selection and
explicit GPU-file collection both select seven physical scenarios; final marker
collection reported 7/2541. Twelve changed Markdown files passed lint, and 185
local file/anchor links passed validation. Earlier intermediate harness Ruff/mypy
errors were corrected before these checks.

The first broad run finished with 2449 passed, 30 skipped and six failures in
818.26 seconds. One existing PID-file test read an empty just-created file and
failed at int(''); its bounded reader now waits for nonempty content. Its full
13-test module passed in 24.11 seconds after correction. The other five failures
used the earlier control fixture (ownership_since=0) loaded during concurrent
implementation; production correctly refused inaccessible historical process
evidence. The final fixture records actual creation ticks; the explicit historical
case still tests zero-birth safety. The corrected fixture passed parent 39-test
and independent 85-test checks.

The fresh full default run, `uv run --frozen --no-sync pytest -q -ra`, returned
exit 0: **2503 passed, 30 skipped, seven deselected, 92 warnings in 693.59 seconds**.
The skips are 29 existing FiftyOne integration checks requiring an isolated
environment and one native reflink check unsupported by the test filesystem.
The seven deselections are the new physical GPU scenarios. Native
CPU DDP remained selected. The final malformed-URL regression was added after
this run collected tests and passed separately; it was also independently
rechecked. No physical GPU acceptance is included in these numbers.

Independent GPU-harness review reproduced a fallback budget bug using a real
TERM-ignoring owned child. Two added regressions failed first; fallback now has
its own 15-second budget and owner-stop errors cannot skip it. The 43-test harness
then passed in 18.04 seconds. Additional credential cases cover secret_key,
Authorization and signed-storage URL fields. Review also reproduced malformed
URL parsing replacing the original failure and losing receipts. Its new regression
failed first, then passed with conservative invalid-URL redaction. The harness
now contains 44 tests: 43 passed together and the final added regression passed
separately. No live GPU or remote credentials were used.

## Companion portable usage skill

Canonical `corp-skills` base is version `0.2.0`, commit
`1e0ed14ff1346eb168208118e089635e0f575351`. Updated its clearml-yolo `SKILL.md`,
`references/usage.md` and `references/evaluation.md`, with an Unreleased changelog
entry and dated companion evidence. No installation or release was performed.

`skills@1.7.1 add . --list` discovered all four packages. Markdown lint passed all
29 collection files. Unique-key YAML parsing, name/description checks and all
three packaged local links passed. The documentation-only companion architecture
record passed acceptance validation.

A fresh native agent explicitly read the updated package and separately applied
three new prompts in one context: physical GPU 1 under `CUDA_VISIBLE_DEVICES=3,1`,
stale GPU 2 with a possibly living guardian, and missing pidfd after training.
All expected criteria were observed: physical/logical distinction, owner holds,
current token/reason, whole allocation, live refusal, no force signals, no unsafe
cleanup fallback and no invented success. Source and actual help agreed. This
was explicit skill-application evaluation, not automatic routing, three cold
contexts or live OpenCode/DeepSeek validation.

## Independent review

Fresh read-only queue review found no production safety/correctness findings and
independently passed 85 tests covering capabilities, controls, properties,
composed workflows and test ownership. It confirmed conservative process refusal,
whole-allocation locking, owner holds/fencing, audit ordering and retry downgrade.
Follow-up confirmed the PID file synchronization correction and exact old-fixture
failure diagnosis.

Fresh read-only harness review inspected installed native callback/compile and
queue exec paths, publication formats, cleanup and documentation. Its two P2
findings (fallback starvation and malformed URL receipt loss) were resolved and
independently rechecked. It passed eight cleanup/redaction regressions and the
malformed endpoint test. Both reviewers accepted their local scope with no
remaining actionable findings; they do not claim physical acceptance.

## External acceptance

Physical multi-GPU/NCCL, compiled CUDA training and actual ClearML publication and
download have **not** been run in this task. They await the user's other machine
using [the exact GPU guide](../../docs/ddp-testing.md). T016 remains open;
offline tests do not satisfy that gate. The architecture acceptance validator
retains this missing check rather than fabricate a passing result. All local
checks and independent review are recorded as passed/accepted; overall acceptance
remains incomplete until the physical result is supplied and reviewed.
Final planning validation returned exit 0. Final acceptance validation returned
exit 1 solely for `checks[3].result.status: acceptance requires passed`, the
explicitly unexecuted physical GPU check.
