# Verification: 2026-10-16

## Implementation and scope

Implemented native General projection, full canonical JSON replay snapshots,
opt-in controller hashing and prepared-dataset identity propagation. Runtime
changes are confined to the modules listed in [architecture.json](architecture.json).
The native callback calls the existing session boundary, whose
`prepare_native_parameters` combines projection and credential sanitization.
No import exceptions or dependency versions changed.

The pre-existing local `[tool.uv.sources]` section and untracked grid-search
document are outside task ownership. The companion corp-skills changes cover
usage guidance and behavioral evaluation only; installed skills are unchanged.

## Executed checks

- Publication/replay regressions reproduced the unfiltered parameters and missing
  canonical native settings before implementation. The focused publication suite
  then passed 92 tests. After correcting the adapter dependency, the affected
  publication/session/DDP suite passed 202 tests.
- Cache normalization: 86 tests passed, including the installed SDK's actual
  `_create_task_hash` path with fake task data, explicit controller overrides,
  scientific invalidation, parsing safety, immutability and idempotence. These
  checks do not establish a server cache hit.
- Dataset identity, train and session suites: 182 tests passed. New identity and
  JSON tests failed before implementation and passed afterward. The installed SDK
  successfully parsed the newly published JSON.
- Real native CPU distributed suite: 5 tests passed. It exercises two/four-rank
  Gloo training, native callbacks, checkpoint production and failure cleanup with
  a recording tracking boundary. It does not establish live ClearML publication
  or GPU execution.
- `uv run --frozen --no-sync lint-imports`: 43 contracts passed. The first
  integration run rejected a direct integrations-to-parameters import; routing
  through the existing session interface fixed it without weakening enforcement.
- `uv run --frozen --no-sync pytest tests/test_architecture.py -q`: 229 passed,
  including the new injected adapter-peer and inward-layer violations.
- `uv run --frozen --no-sync ruff check .`: passed.
- `uv run --frozen --no-sync mypy .`: passed, 347 source files.
- `uv run --frozen --no-sync vulture`: passed.
- `uv run --frozen --no-sync python scripts/check_docs.py --all` with explicit
  new feature paths: 516 Markdown files, zero issues.
- `uv build --no-sources --out-dir <temporary-directory>`: source archive and
  wheel built successfully. The wheel contains byte-identical cache/projection
  modules. After review corrections, both artifacts were rebuilt and each installed
  without dependency resolution into a fresh virtual environment. Installed-package
  source location, helper import/call and all 12 console-command help paths passed
  for both distributions. These environments reused the prepared dependency set;
  this was not a clean dependency-resolution or optional-backend installation test.
- `git diff --check`: passed.

The first full suite passed 3,057 tests, with 30 skipped, 7 deselected and 113
warnings in 690.22 seconds. Those skips/deselections do not establish the excluded
integration outcomes. SDK pyparsing, Hydra/Pydantic, reporting and font warnings
were recorded. This run predates the independent-review corrections below.

## Independent review corrections

The first review returned fix-first with reproduced legacy replay, malformed cache
marker and Unicode replay defects, plus a missing scoped purity check and an
embedding-documentation qualification. All five changes are implemented:

- Legacy absent-run/omitted-native-group recovery now happens at the session replay
  boundary before publishing the full snapshot. Eight new failing cases passed
  after correction; explicit empty modern groups/values retain authority.
- Both JSON writers use `ensure_ascii=False`; two installed-SDK Cyrillic/CJK/emoji
  and literal-backslash roundtrips failed before correction and passed afterward.
- Malformed device mappings and caller-supplied dataset tokens refuse the entire
  hash projection. Seven failing collision regressions now pass; the focused cache
  suite passes 93 tests.
- Scoped pure-adapter dependency rules reject SDK/session/storage edges. Four
  injected-edge tests failed before the new enforcement and passed afterward.
  Reused effect scanning rejects injected file/network/process calls, and a fresh
  interpreter guards import/call against SDK imports and filesystem/network/process
  effects. The final architecture suite passes 242 tests.
- Documentation states the CLI-owned full snapshot and embedding callers' recording
  responsibility, and specifies JSON text for controller configuration overrides.

Parent verification of the integrated corrections passed 513 tests (cache, projection,
architecture, model replay, command publication and session), 43 import contracts,
Ruff, mypy (347 source files) and 516 Markdown checks. Separate affected direct
execution/lifecycle verification passed 46 tests. Later review and final hook results
are recorded below. The pre-commit changelog hook generated the missing entry for already
committed queue documentation; this expected change was inspected and retained.

The second fresh review reproduced SDK/JSON escape ambiguity, project-dependent
model selection and skipped-stage input-root collisions. The corrections preserve
the whole representation for ambiguous active JSON escapes, retain fallback model
lookup projects, retain skipped-pipeline run roots, and leave unresolved escaped
device-list strings distinct. Twenty-four regressions failed before correction.
The resulting focused cache suite passes 128 tests. Parent verification of the
final integrated changes passes 548 tests, plus Ruff, mypy (347 source files),
43 import contracts and Vulture.

The full pytest hook passed 3,089 tests, with 30 skipped, 7 deselected and 133
warnings in 685.48 seconds. It collected the state before the second review fixes;
the later 548-test run covers those changes. The enclosing pre-commit invocation
returned failure because its changelog hook generated the inspected entry and
concurrent task-owned edits changed files during the pytest hook. The changelog
hook subsequently passed. A frozen-worktree hook rerun was scheduled; the first
pre-commit invocation is not reported as successful. The subsequent frozen rerun
passed its static hooks, then was interrupted during pytest after fresh review
found backend-specific invalid device aliases sharing valid identities. That
interrupted run is not acceptance evidence; its task-owned child processes were
checked absent afterward.

The device-consumer correction reproduced 67 invalid/valid selector collisions
through actual detector/export validators and installed SDK hashing. The native
parser/validator was exercised with CUDA discovery stubbed and no device allocation.
Native YOLO, typed native, strict/unknown single-device, GPU export and CPU-only
export contexts now use conservative selector rules. Missing/HOCON canonical runs
retain conservative General handling. The final focused cache suite passes 233
tests, with scoped Ruff/format and strict mypy passing. Parent integration checks,
fresh review and final hooks follow these changes.

Final parent integration verification passed 653 tests in 28.91 seconds, followed
by Ruff, mypy (347 files), 43 import contracts and Vulture. The final frozen
`UV_NO_SYNC=1 uv run --frozen --no-sync pre-commit run --all-files` returned exit 0:
all hooks passed, including the complete pytest suite. Successful hook output did
not print a final pytest count; the earlier full-suite counts above are historical.
The final source archive and wheel were rebuilt after the consumer correction,
byte-verified and reinstalled into the two prepared fresh environments; installed
helper import, equivalence and device-count separation passed for both.

Fresh independent review accepted the local source, including architecture, with
no blocking implementation findings. Its approved historical-clone qualification
was added to documentation after the frozen hooks. Only documentation/evidence
changed afterward; final documentation checks cover that amendment.

Final documentation validation passed 517 application Markdown files and the
companion's 40-file Markdown lint. Both repository whitespace checks passed.
The companion no-impact architecture acceptance validator passed. Application
architecture acceptance returned exit 1 solely for `checks[6].result.status`, the
declared live check still marked not-run. All source checks and independent review
are recorded as passed/accepted; this remaining requirement is not waived.

## Portable skill behavior

Two independent fresh native-agent contexts read the portable skill without
reading its expected evaluation answers. The equivalent-allocation case returned
explicit controller registration and callback composition, preserved full replay
and scientific settings, distinguished backend/count and explained remote-output
reuse. The unsafe-shortcut case rejected recursive key removal, scientific
collisions and worker registration, and retained legacy HOCON and unproven paths.
Both passed the relevant documented expectations without live work or edits.
A third fresh context correctly distinguished skipped-stage input roots, fallback
model projects and Unicode JSON overrides using only the portable guidance. It
also explained that a cache hit does not populate a new local directory. All
three evaluations passed. A fourth fresh context correctly qualified supported
YOLO multi-device equivalence and rejected extending it to RF-DETR/export selector
aliases. It read only the skill and usage guidance, with no expected answers or
workloads. This is native-agent evaluation, not live OpenCode
target-model execution.

## Live acceptance and delivery

The shared environment preflight returned WAIT on each attempt, before obtaining
run credentials, minting a tag or creating any resources. No task, pod, training
invocation or publication was started on the stand. Shared workloads were left
intact. Machine-specific preflight details remain outside project documentation.

Once capacity permits, the bounded acceptance run will use an isolated tagged
project and workspace, a tiny synthetic CSV dataset, random local YOLO weights,
one CPU epoch, and the real publication/download path. An external controller
will register the helper before lookup, execute an initial miss, verify a hit
after changing known output routing, and verify a miss after a scientific
override. GPU-index equivalence remains covered by the installed-SDK tests;
physical GPU execution requires available hardware and its own evidence.

Live publication/cache acceptance, required release checks, final architecture
acceptance and Git-only delivery remain open. No commits, tags, pushes, package
publication or skill installation have been performed.

Final ownership checks found no running task-owned test or live-harness processes.
Disposable build/install workspaces were removed after verification; the prepared
live harness and local check logs remain available for the pending acceptance run.

## Resumed release verification — 2026-10-19

The user renewed the release request after the previously reported acceptance and
coordination limitations. Delivery is prepared in an isolated clone of the released
queue-fix baseline. The canonical working tree and index remain untouched; the
concurrent lint-configuration split and unrelated grid-search draft are excluded.
The prerequisite is committed before feature 037 and the combined Git-only release.
The earlier temporary raw logs are no longer available; their dated observations
above remain historical. New release evidence is retained in a persistent private
archive, and normal hooks are rerun on the recovered source.

Actual native CPU execution and server cache lookup now pass against the integrated
036/037 source. The real PipelineController/ClearmlJob path produced an initial
miss, reused that exact completed task after output-routing changes, and missed
after changing weight decay. Draft controller nodes exercised SDK construction and
server lookup; the first job executed locally with the SDK's simulated-remote
environment. This establishes controller caching, not ClearML-agent scheduling.

Independent reads observed validated General, full run and run_overrides while the
task was in progress before preparation, and downloaded ground truth before
training. The final eight-image CSV included two empty images and matched its early
copy. The single downloaded best checkpoint matched the native file hash and
stored weight decay 0.0234. All 23 archived evidence files were rehashed by the
parent. Cleanup proved zero owned processes, tagged tasks or projects. Synthetic
random-weight CPU data establishes execution/publication, not model accuracy.

The first resumed full hook passed static checks and 3262 tests, with 30 skipped
and 7 deselected, but failed one queue-process fixture readiness assertion. Its
persisted job was already completed: the synthetic owner exited immediately after
spawning its detached rank, letting correct guardian cleanup terminate the rank
before readiness. The isolated test passed, and delaying rank initialization by
0.3 seconds reproduced the same failure deterministically. A bounded readiness
handshake before owner exit passed that delayed diagnostic. The diagnostic delay
was then removed. Production queue code, cleanup deadlines and test assertions
remain unchanged. The full process suite and final commit hook results follow.
